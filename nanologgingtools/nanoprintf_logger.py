#!/usr/bin/env python2
"""
Read data from serial port, split by newlines, prepend hostname and timestr
to every line and send to a nanomsg REP socket.
line format:
    "host1_1  2015-01-14T13:41:37.90 Hello world"
    "host1_4 x2015-01-14T13:41:37.90 Hello world"
The 'x' denotes a broken line (newline not received in time).
"""

import os
import sys
import time
import datetime
import errno

import serial

from nanomsg import REQ, REQ_RESEND_IVL
from nanomsg import Socket, SOL_SOCKET, RECONNECT_IVL, RECONNECT_IVL_MAX, DONTWAIT, NanoMsgAPIError

import logging

__author__ = "Elmo Trolla, Mattis Marjak, Andres Vahter, Raido Pahtma"
__license__ = "MIT"


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.NOTSET, format="%(asctime)s %(name)s %(levelname)-5s: %(message)s")

# drop messages that are in buf but older than this.
MAX_MSG_AGE = 30 * 60.0
MAX_ACK_TIMEOUT = 60.0


def log_timestr(t=None):
    """ '2010-01-18T18:40:42.232Z' utc time """
    if t is None:
        t = time.time()
    # return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S.%f")[:22]
    return datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def prepare_tx_line(portname, seqno, line, timestamp, broken=False):
    """
    output:
        boken = False: "hostname_portname 123ABC 2014-01-14T14:43:21.23Z this is the original line"
        boken = True : "hostname_portname 123ABC x2014-01-14T14:43:21.23Z this is the original line"
    """
    return "%s_%s %06X %s%s %s" % (os.uname()[1], portname, seqno, "x" if broken else "", log_timestr(timestamp), repr(line))


class NewlineParser:
    def __init__(self):
        self.buf = ""
        self.delimiter = "\n"

    def put(self, data):
        self.buf += data

    def __iter__(self):
        return self

    def next(self):
        t = self._get_next_line()
        return t

    def _get_next_line(self):
        while True:
            self.delete = self.buf.find(self.delimiter)
            if self.delete == -1:
                raise StopIteration
            t = self.buf[:self.delete]
            self.buf = self.buf[self.delete+1:]
            return t


def connect(server):
    soc = Socket(REQ)
    # start reconnecting after one second pause
    # max reconnect timer to one minute
    # request resend wait to shorter than the default 60 seconds
    #   (because nanomsg won't retry the send right at the moment of reconnection)
    soc.set_int_option(SOL_SOCKET, RECONNECT_IVL, 1000)
    soc.set_int_option(SOL_SOCKET, RECONNECT_IVL_MAX, 1000 * 60)
    soc.set_int_option(SOL_SOCKET, REQ_RESEND_IVL, 1000 * 10)
    soc.connect(server)  # "tcp://localhost:14999"
    return soc


def run(server, port="/dev/ttyUSB0", baud=115200, portname=None):
    """
    Read data from serial port, split by newlines,
    prepend hostname and timestr to every line and
    send to a nanomsg REP socket.
    """
    log.info("using port %s @ %s, sending to server %s", port, baud, server)

    # setup nanomsg
    soc = connect(server)
    soc_waiting_for_ack = None

    if portname is None:
        portname = port[-1]

    while True:
        try:
            # setup serial port and other variables
            serialport = None
            serial_timeout = 0.01 if sys.platform == "win32" else 0

            while serialport is None:
                try:
                    serialport = serial.Serial(port, baud, timeout=serial_timeout)
                    serialport.flushInput()
                except (serial.SerialException, OSError):
                    serialport = None
                    time.sleep(0.1)

            log.info("Opened %s." % (port))

            parser = NewlineParser()
            t_last_recv = time.time()

            outbuf_tx_index = 0
            outbuf = []  # (timestamp, "processed line")

            seqno = 0

            while True:
                s = serialport.read(1000)
                t = time.time()
                if s:
                    t_last_recv = t
                    parser.put(s)

                    for l in parser:
                        outbuf.append((t, prepare_tx_line(portname, seqno, l, t)))
                        seqno += 1

                # # this here is for testing the system if there's no serial port traffic
                # if t - t_last_recv > 0.5:
                #   t_last_recv = t
                #   outbuf.append( (t, prepare_tx_line(portname, seqno, "Hello world %s" % seqno, t)) )
                #   seqno += 1

                # if no newline character arrives after 0.2s of last recv and parser.buf
                # contains data, send out the partial line.
                if t - t_last_recv > 0.2 and parser.buf:
                    outbuf.append((t, prepare_tx_line(portname, seqno, parser.buf, t, broken=True)))
                    seqno += 1
                    parser.buf = ""

                # clean up the outbuf. remove entries older than 30 minutes.

                while outbuf:
                    if outbuf[0][0] < t - MAX_MSG_AGE:
                        outbuf.pop(0)
                    else:
                        break

                # send the next message to nanomsg only if the prev got some kind of answer

                if soc_waiting_for_ack is not None:
                    if time.time() - soc_waiting_for_ack > MAX_ACK_TIMEOUT:
                        log.warning("No ack for %d ... reconnecting. (queue %d)", MAX_ACK_TIMEOUT, len(outbuf))
                        soc_waiting_for_ack = None

                        soc.close()
                        soc = connect(server)
                    else:
                        try:
                            if soc.recv(flags=DONTWAIT):
                                soc_waiting_for_ack = None
                                # remove packets for which we just got the ack.
                                outbuf = outbuf[outbuf_tx_index:]
                        except NanoMsgAPIError as e:
                            if e.errno == errno.EAGAIN:
                                pass
                            else:
                                # unknown error!
                                raise

                if soc_waiting_for_ack is None and outbuf:
                    txmsg = "\n".join([e[1] for e in outbuf])  # join all messages to one big.
                    outbuf_tx_index = len(outbuf)

                    soc.send(txmsg)
                    soc_waiting_for_ack = time.time()

                time.sleep(.01)
        except serial.SerialException as e:
            log.warning("Serial port disconnected: %s. Will try to open again." % (e.message))


def main():
    from argparse import ArgumentParser
    ap = ArgumentParser(description="Printf UART logger that logs to nanomsg")
    ap.add_argument("server", help="nanomsg printf server, for example tcp://test2.arupuru.com:14999")
    ap.add_argument("port", help="Serial port")
    ap.add_argument("baud", default=115200, help="Serial port baudrate")
    ap.add_argument("--portname", default=None)
    args = ap.parse_args()
    run(**args.__dict__)


if __name__ == "__main__":
    main()

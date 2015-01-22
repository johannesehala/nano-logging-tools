#!/usr/bin/env python2

"""
Read data from serial port, split by newlines,
prepend hostname and timestr to every line and
send to a nanomsg REP socket.

line format:

	"koerkana1_1  2015-01-14T13:41:37.90 Hello world"
	"koerkana1_4 x2015-01-14T13:41:37.90 Hello world"

The 'x' denotes a broken line (no newline for too long).

"""

import logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.NOTSET, format="%(asctime)s %(name)s %(levelname)-5s: %(message)s")

import os
import sys
import serial
import time
import datetime
import errno

from nanomsg import REQ, REQ_RESEND_IVL
from nanomsg import Socket, SOL_SOCKET, RECONNECT_IVL, RECONNECT_IVL_MAX, DONTWAIT, NanoMsgAPIError


# drop messages that are in buf but older than this.
MAX_MSG_AGE = 60. * 30


def log_timestr(t=None):
	""" '2010-01-18T18:40:42.23Z' utc time """
	if t is None:
		t = time.time()
	#return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S.%f")[:22]
	return datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%dT%H:%M:%S.%f")[:22] + "Z"


def prepare_tx_line(portname, seqno, line, timestamp, broken=False):
	"""
	output:
	    boken = False: "hostname_portname 123ABC 2014-01-14T14:43:21.23Z this is the original line"
	    boken = True : "hostname_portname 123ABC x2014-01-14T14:43:21.23Z this is the original line"
	"""
	return "%s_%s %06X %s%s %s" % (os.uname()[1], portname, seqno, "x" if broken else "", log_timestr(timestamp), repr(line))


class NewlineParser:
	def __init__(self):
		self.buf       = ""
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
			self.delete = self.buf.find( self.delimiter )
			if self.delete == -1: raise StopIteration
			t = self.buf[:self.delete]
			self.buf = self.buf[self.delete+1:]
			return t


def run(server, port="/dev/ttyUSB0", baud=115200):
	"""
	Read data from serial port, split by newlines,
	prepend hostname and timestr to every line and
	send to a nanomsg REP socket.
	"""
	log.info("using port %s @ %s, sending to server %s", port, baud, server)

	# setup nanomsg

	soc = Socket(REQ)
	# start reconnecting after one second pause
	# max reconnect timer to one minute
	# request resend wait to shorter than the default 60 seconds
	#   (because nanomsg won't retry the send right at the moment of reconnection)
	soc.set_int_option(SOL_SOCKET, RECONNECT_IVL, 1000)
	soc.set_int_option(SOL_SOCKET, RECONNECT_IVL_MAX, 1000 * 60)
	soc.set_int_option(SOL_SOCKET, REQ_RESEND_IVL, 1000 * 10)
	soc.connect(server) # "tcp://localhost:14999"
	soc_waiting_for_ack = False

	# setup serial port and other variables

	serial_timeout = 0.01 if sys.platform == "win32" else 0
	serialport = serial.Serial(port, baud, timeout=serial_timeout)
	serialport.flushInput()
	port_num = port[-1]
	parser = NewlineParser()
	t_last_recv = time.time()

	outbuf_tx_index = 0
	disconnected = False
	outbuf = [] # (timestamp, "processed line")

	seqno = 0

	while 1:
		s = serialport.read(1000)
		t = time.time()
		if s:
			t_last_recv = t
			parser.put(s)

			for l in parser:
				outbuf.append( (t, prepare_tx_line(port_num, seqno, l, t)) )
				seqno += 1

		# # this here is for testing the system if there's no serial port traffic
		# if t - t_last_recv > 0.5:
		# 	t_last_recv = t
		# 	outbuf.append( (t, prepare_tx_line(port_num, seqno, "Hello world %s" % seqno, t)) )
		# 	seqno += 1

		# if no newline character arrives after 0.2s of last recv and parser.buf
		# contains data, send out the partial line.
		if t - t_last_recv > 0.2 and parser.buf:
			outbuf.append( (t, prepare_tx_line(port_num, seqno, parser.buf, t, broken=True)) )
			seqno += 1
			parser.buf = ""

		# clean up the outbuf. remove entries older than 30 minutes.

		while outbuf:
			if outbuf[0][0] < t - MAX_MSG_AGE:
				outbuf.pop(0)
			else:
				break

		# send the next message to nanomsg only if the prev got some kind of answer

		if soc_waiting_for_ack:
			try:
				if soc.recv(flags=DONTWAIT):
					soc_waiting_for_ack = False
					disconnected = False
					# remove packets for which we just got the ack.
					outbuf = outbuf[outbuf_tx_index:]
			except NanoMsgAPIError as e:
				if e.errno == errno.EAGAIN:
					disconnected = True
				else:
					# unknown error!
					raise

		if not soc_waiting_for_ack and outbuf:
			txmsg = "\n".join([e[1] for e in outbuf]) # join all messages to one big.
			outbuf_tx_index = len(outbuf)

			soc.send(txmsg)
			soc_waiting_for_ack = True

		time.sleep(.01)


if __name__ == "__main__":
	from argparse import ArgumentParser
	ap = ArgumentParser(description="Printf UART logger that logs to nanomsg")
	ap.add_argument("port")
	ap.add_argument("baud", default=115200)
	ap.add_argument("--server", default="tcp://test2.arupuru.com:14999")
	args = ap.parse_args()
	run(**args.__dict__)

#!/usr/bin/env python2
import re
import os
import errno
import logging

from nanomsg import Socket, PUB, SUB, REP, SUB_SUBSCRIBE
from nanomsg import SOL_SOCKET, RECONNECT_IVL, RECONNECT_IVL_MAX, DONTWAIT, NanoMsgAPIError


class PrintfLogForwarder(object):

    def __init__(self, filename, addr_publish):
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(logging.StreamHandler())

        self.addr_publish = addr_publish
        self.filename = os.path.abspath(filename)

        self.prefix = self.get_hostname_and_port()
        self.seq    = 1

        if not os.path.exists(self.filename):
            raise Exception("No such file")

        self.log.info("[*] Start publishing messages. To exit press CTRL+C")
        self.main_loop()

    def get_hostname_and_port(self):
        match = re.match("log_(.*)\.txt", os.path.basename(self.filename))
        if match:
            return ' '.join(match.groups())
        raise Exception("File name not in correct format")

    def main_loop(self):
        fle     = open(self.filename, 'r')
        soc_pub = self.make_nanomsg_connection(self.addr_publish)
        while 1:
            msg = self.get_message(fle)
            if msg is False:
                break
            else:
                try:
                    soc_pub.send( msg )
                except NanoMsgAPIError as e:
                    if e.errno == errno.EAGAIN:
                        break
                    else:
                        raise

    @staticmethod
    def make_nanomsg_connection(pub_addr):
        if pub_addr and pub_addr.lower() != "none":
            soc_pub = Socket(PUB)
            soc_pub.connect(pub_addr)
            return soc_pub
        raise Exception("Could not connect")

    def get_message(self, fle):
        lne = fle.readline()
        if len(lne) > 0:
            lne = ' '.join((self.prefix, '{:06X}'.format(self.seq), lne.strip()))
            self.log.info("{}".format(lne))
            return lne
        return False


if __name__ == "__main__":
    from argparse import ArgumentParser
    ap = ArgumentParser(description="printf-elastic-forwarder")
    ap.add_argument("filename",     help="File name to read messages to publish")
    ap.add_argument("addr_publish", help="Publish messages to nanomsg, format is: tcp://host:14998")

    args = ap.parse_args()
    PrintfLogForwarder(**args.__dict__)

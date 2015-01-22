#!/usr/bin/env python2

"""
Two possibilities to get loglines:
    * Receive loglines from printf-uart-nanomsg.py by serving a nanomsg REP socket.
    * Subscribe a nanomsg SUB socket to a nanoprintf-server.py PUB socket.

Forwards all loglines to a nanomsg PUB socket.

Logs all loglines to local logfiles. Separate file for every hostname/port.
"""

import logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.NOTSET, format="%(asctime)s %(name)s %(levelname)-5s: %(message)s")

import sys
import time
import errno

from nanomsg import Socket, PUB, SUB, REP, SUB_SUBSCRIBE
from nanomsg import SOL_SOCKET, RECONNECT_IVL, RECONNECT_IVL_MAX, DONTWAIT, NanoMsgAPIError

# dict of opened logfiles
g_logfiles = {}


def writelog(msg):
	"""
	"hostname_portname 123ABC x2014-01-14T14:43:21.23Z this is the original line"

	123ABC - seqno
	the x means the line is corrupt (no newline from uart for too long)
	"""
	hostname_n, seqno, rest = msg.split(None, 2)
	# create one log file for every hostname_n (unique for each host and serial port)
	if hostname_n not in g_logfiles:
		logfilename = "log_%s.txt" % hostname_n
		sys.stdout.write("\n")
		log.info("opening log file %s", logfilename)
		g_logfiles[hostname_n] = open(logfilename, "ab+")

	g_logfiles[hostname_n].write(rest + "\n")
	g_logfiles[hostname_n].flush()


def run(addr_listenprintf, addr_forward, addr_subscribe, uselog):

	log.info("listening for printf-uart-nanomsg: %s", addr_listenprintf)
	log.info("subscribing for messages to      : %s", addr_subscribe)
	log.info("forwarding messages to           : %s", addr_forward)
	log.info("logging messages to files        : %s", uselog)

	soc_rep = None
	soc_pub = None
	soc_sub = None

	if addr_listenprintf and addr_listenprintf.lower() != "none":
		soc_rep = Socket(REP)
		soc_rep.bind(addr_listenprintf)

	if addr_forward and addr_forward.lower() != "none":
		soc_pub = Socket(PUB)
		soc_pub.bind(addr_forward)

	if addr_subscribe and addr_subscribe.lower() != "none":
		soc_sub = Socket(SUB)
		soc_sub.set_string_option(SUB, SUB_SUBSCRIBE, "")
		# start reconnecting after one second pause
		# max reconnect timer to 30 seconds
		soc_sub.set_int_option(SOL_SOCKET, RECONNECT_IVL, 1000)
		soc_sub.set_int_option(SOL_SOCKET, RECONNECT_IVL_MAX, 1000 * 30)
		soc_sub.connect(addr_subscribe)

	while 1:
		# read from addr_listenprintf and forward to addr_forward

		if soc_rep:

			jumbomsg = None
			try:
				jumbomsg = soc_rep.recv(flags=DONTWAIT)
				print "jumbomsg", len(jumbomsg)
			except NanoMsgAPIError as e:
				if e.errno != errno.EAGAIN:
					raise

			if jumbomsg:
				# reply anything to the REQ socket or no more messages will arrive
				soc_rep.send("got it")
				# ONLY messages from the REQ socket can be jumbomessages (simple lines joined by newlines)
				msgs = jumbomsg.split("\n")
				for msg in msgs:
					hostname_n, rest = msg.split(None, 1)
					s = "a" if hostname_n[-1] == "1" else "d"
					sys.stdout.write(s)
					sys.stdout.flush()
					if soc_pub:
						soc_pub.send(msg)
					if uselog:
						writelog(msg)

		# read from addr_subscribe and forward to addr_forward

		if soc_sub:
			while 1:

				msg = None
				try:
					msg = soc_sub.recv(flags=DONTWAIT)
				except NanoMsgAPIError as e:
					if e.errno == errno.EAGAIN:
						break
					else:
						raise

				if msg:
					hostname_n, rest = msg.split(None, 1)
					sys.stdout.write(hostname_n[-1])
					sys.stdout.flush()
					if soc_pub:
						soc_pub.send(msg)
					if uselog:
						writelog(msg)

		time.sleep(0.01)


if __name__ == "__main__":
	from argparse import ArgumentParser
	ap = ArgumentParser(description="printf-uart-nanomsg receiver.\n ....")
	ap.add_argument("--listenprintf", dest="addr_listenprintf", default="tcp://*:14999", help="printf-uart-nanomsg connects here. using 'None' turns the listener off. default: tcp://*:14999")
	ap.add_argument("--forward", dest="addr_forward", default="tcp://*:14998", help="log subscribers connect here. using 'None' turns off. default: tcp://*:14998")
	ap.add_argument("--subscribe", dest="addr_subscribe", default=None, help="pull messages from another nanoprintf-server. default is off, but format is as usual: tcp://host:14998")
	ap.add_argument("--log", dest="uselog", action="store_true", help="write incoming messages to log files")
	args = ap.parse_args()
	run(**args.__dict__)

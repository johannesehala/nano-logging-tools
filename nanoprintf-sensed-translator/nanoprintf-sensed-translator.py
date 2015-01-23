#!/usr/bin/env python2

"""
Subscribe to nanoprintf-server and listen for connections from sensed on a PUB socket.
"""

import logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.NOTSET, format="%(asctime)s %(name)s %(levelname)-5s: %(message)s")

import sys
import time
import errno
import calendar

from nanomsg import Socket, PUB, SUB, REP, SUB_SUBSCRIBE
from nanomsg import SOL_SOCKET, RECONNECT_IVL, RECONNECT_IVL_MAX, DONTWAIT, NanoMsgAPIError


def timestr_to_timestamp(timestr):
	"""timestr format: '2014-02-11T18:46:22.13Z'"""
	frac = float(timestr[20:22]) / 100.
	return calendar.timegm(time.strptime(timestr[:19], "%Y-%m-%dT%H:%M:%S")) + frac


def transform_for_sensed(msg):

	# take apart lines like this
	# koerkana1_4 123ABC 2015-01-16 13:25:05.25Z 'N-cbuf 2B45 01 0C'

	try:
		hostname_n, seqno, timestr, rest = msg.split(None, 3)

		if timestr.startswith("x"):
			return

		timestamp = timestr_to_timestamp(timestr)

		# remove quotes
		rest = rest[1:-1]

		# use the koerkana index as node name. take the num 1 from koerkana1_4.
		name = hostname_n[8] if hostname_n.startswith("koerkana") else "-"

		nugget = rest
		if nugget.startswith("N-"):
			# yay. we have a sensed line!
			p = nugget.split()
			if p[0] == "N-etx":
				# 95391 2015-01-16 09:57:02.82 'D| CTPRE: 358|N-etx 00 E4D8 NO NO'
				# nanodbg("data etx", "index %u neighbor %u etx NO_ROUTE retx NO_ROUTE", i, entry->neighbor);
				# debug4("N-etx %02X %02X NO NO", i, entry->neighbor); // sensed
				header, node, index, neighbor, etx, retx = p
				return "data etx %.2f node %04X_%s index %u neighbor %u etx NO_ROUTE retx NO_ROUTE" % \
					(timestamp, int(node,16), name, int(index,16), int(neighbor,16))
			elif p[0] == "N-retx":
				# nanodbg("data etx", "index %u neighbor %u etx %u retx %u", i, entry->neighbor, linkEtx, entry->info.etx);
				# debug4("N-retx %02X %02X %02X %02X", i, entry->neighbor, linkEtx, entry->info.etx); // sensed
				header, node, index, neighbor, etx, retx = p
				return "data etx %.2f node %04X_%s index %u neighbor %u etx %u retx %u" % \
					(timestamp, int(node,16), name, int(index,16), int(neighbor,16), int(etx,16), int(retx,16))
			elif p[0] == "N-sctp":
				header, node, dest, origin, origin_seqno, amid, thl = p
				# nanodbg("event send_ctp_packet", "dest 0x%04X origin 0x%04X sequence %u amid 0x%02X thl %u", dest, hdr->origin, hdr->originSeqNo, hdr->type, hdr->thl);
				# debug4("N-sctp %04X %04X %02X %02X %02X", dest, hdr->origin, hdr->originSeqNo, hdr->type, hdr->thl); // sensed
				return "event send_ctp_packet %.2f node %04X_%s dest 0x%04X origin 0x%04X sequence %u amid 0x%02X thl %u" % \
					(timestamp, int(node,16), name, int(dest,16), int(origin,16), int(origin_seqno,16), int(amid,16), int(thl,16))
			elif p[0] == "N-cbuf":
				# nanodbg("data ctpf_buf_size", "used %u capacity %u", call MessagePool.maxSize() - call MessagePool.size(), call MessagePool.maxSize());
				# debug4("N-cbuf %02X %02X", call MessagePool.maxSize() - call MessagePool.size(), call MessagePool.maxSize());
				header, node, used, capacity = p
				return "data ctpf_buf_size %.2f node %04X_%s used %u capacity %u" % \
					(timestamp, int(node,16), name, int(used,16), int(capacity,16))

			elif p[0] == "N-bcn":
				# nanodbg("event beacon", "options 0x%02X parent 0x%04X etx %u", beaconMsg->options, beaconMsg->parent, beaconMsg->etx);
				# debug4("N-bcn %02X %04X %02X", beaconMsg->options, beaconMsg->parent, beaconMsg->etx); // sensed
				header, node, options, parent, etx = p
				return "event beacon %.2f node %04X_%s options 0x%02X parent 0x%04X etx %u" % \
					(timestamp, int(node,16), name, int(options,16), int(parent,16), int(etx,16))

			elif p[0] == "N-s":
				# nanodbg("event packet_to_activemessage", "dest 0x%04X amid 0x%02X", addr, id);
				# debug4("N-s %04X %02X", addr, id); // sensed
				header, node, dest_addr, amid = p
				return "event packet_to_activemessage %.2f node %04X_%s dest 0x%04X amid 0x%02X" % \
					(timestamp, int(node,16), name, int(dest_addr,16), int(amid,16))
			else:
				log.error("unknown sensed packet: %s", msg)
	except:
		log.exception("error parsing msg: %s", msg)


def run(addr_forward, addr_subscribe):

	log.info("subscribing for messages to      : %s", addr_subscribe)
	log.info("forwarding messages to PUB       : %s", addr_forward)

	soc_pub = None
	soc_sub = None

	soc_pub = Socket(PUB)
	soc_pub.bind(addr_forward)

	soc_sub = Socket(SUB)
	soc_sub.set_string_option(SUB, SUB_SUBSCRIBE, "")
	# start reconnecting after one second pause
	# max reconnect timer to 30 seconds
	soc_sub.set_int_option(SOL_SOCKET, RECONNECT_IVL, 1000)
	soc_sub.set_int_option(SOL_SOCKET, RECONNECT_IVL_MAX, 1000 * 30)
	soc_sub.connect(addr_subscribe)

	while 1:
		# read from addr_subscribe and forward to addr_forward

		if soc_sub:

			msg = None
			try:
				msg = soc_sub.recv(flags=DONTWAIT)
			except NanoMsgAPIError as e:
				if e.errno != errno.EAGAIN:
					raise
				else:
					time.sleep(0.01)

			if msg:
				#hostname_n, rest = msg.split(None, 1)
				print msg

				msg2 = transform_for_sensed(msg)
				if msg2:
					soc_pub.send(msg2)


if __name__ == "__main__":
	from argparse import ArgumentParser
	ap = ArgumentParser(description="translates messages from nanoprintf-server to sensed.")
	ap.add_argument("--forward", dest="addr_forward", default="tcp://*:55555", help="sensed connects here. default: tcp://*:55555")
	ap.add_argument("--subscribe", dest="addr_subscribe", default="tcp://localhost:14998", help="pull messages from this nanoprintf-server. default: tcp://localhost:14998")
	args = ap.parse_args()
	run(**args.__dict__)

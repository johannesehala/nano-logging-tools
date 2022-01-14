#!/usr/bin/env python2
import errno
import logging
import calendar
import time
from datetime import datetime

from elasticsearch import Elasticsearch
from nanomsg import Socket, PUB, SUB, REP, SUB_SUBSCRIBE
from nanomsg import SOL_SOCKET, RECONNECT_IVL, RECONNECT_IVL_MAX, DONTWAIT, NanoMsgAPIError

from .sensed_translator.nuggets import nuggets

# from interrupt_handler import bind_signals
# bind_signals()

ELASTICS_INDEX = 'printf'

class PrintfElasticForwarder(object):

    def __init__(self, addr_subscribe, addr_elastic, bind):
        self.log = logging.getLogger(__name__)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(logging.StreamHandler())
        self.bind_instead_of_connecting = bind
        self.addr_subscribe = addr_subscribe
        self.addr_elastic   = addr_elastic

    def run(self):
        self.log.info("[*] Waiting for messages. To exit press CTRL+C")
        soc_sub = self.make_nanomsg_connection()
        elastic = self.make_elastic_connection()
        while 1:
            try:
                msg = soc_sub.recv()
            except NanoMsgAPIError as e:
                if e.errno == errno.EAGAIN:
                    break
                else:
                    raise
            if msg:
                self.handle_message(msg, elastic)

    def make_elastic_connection(self):
        if self.addr_elastic:
            elastic = Elasticsearch([self.addr_elastic])
            if elastic.ping():
                elastic.indices.create(index='printf', ignore=400)
                # doc_types = map(lambda n: n['prefix'], nuggets)+['raw',]
                for doc_type in ['_default_']:
                    elastic.indices.put_mapping(doc_type, {"_timestamp" : {
                        "enabled" : True, "store": "yes", "path": "timestamp",
                        "format": "date_optional_time", "default" : None
                    }}, index='printf')
                return elastic
        raise Exception("Could not connect to elasticsearch")

    def make_nanomsg_connection(self):
        if self.addr_subscribe and self.addr_subscribe.lower() != "none":
            soc_sub = Socket(SUB)
            soc_sub.set_string_option(SUB, SUB_SUBSCRIBE, "")
            # start reconnecting after one second pause
            # max reconnect timer to 30 seconds
            soc_sub.set_int_option(SOL_SOCKET, RECONNECT_IVL, 1000)
            soc_sub.set_int_option(SOL_SOCKET, RECONNECT_IVL_MAX, 1000 * 30)
            if self.bind_instead_of_connecting:
                soc_sub.bind(self.addr_subscribe)
            else:
                soc_sub.connect(self.addr_subscribe)
            return soc_sub
        raise Exception("Could not connect to nanomsg")

    def handle_message(self, msg, elastic):
        self.log.info(" [+] Received {}".format(msg))
        hostname_n, seq_no, timestr, rest = msg.split(None, 3)
        # hostname,port = hostname_n[:-3], hostname_n[-3:]
        tm = self.timestr_to_datetime(timestr)
        rest = rest[1:-1]
        try:
            if rest.startswith("N-"):
                p = rest.split()
                fields = False
                for nugget in nuggets:
                    if p[0] == nugget['prefix']:
                        prefix = nugget['prefix']
                        fields = dict(list(zip(nugget['fields'], p)))
                        fields['host'] = hostname_n
                        fields['timestamp']   = tm
                        break
                if fields:
                    elastic.index(index=ELASTICS_INDEX, doc_type=prefix, body=fields)
                else:
                    self.log.exception(" [!] Nugget unpack error")
            else:
                lvl,mod_lne,payload = rest.split('|', 2)
                mod,lne = mod_lne.split(':')

                elastic.index(index=ELASTICS_INDEX, doc_type='raw', #timestamp=tm,
                              body={'msg':payload, 'host':hostname_n, 'timestamp':tm,
                                    'level':lvl.strip(), 'module':mod.strip(),
                                    'line':lne.strip()})
        except:
            self.log.exception(" [!] Elasticsearch error")

    @staticmethod
    def timestr_to_datetime(timestr):
        frac = float(timestr[20:22]) / 100.
        ts   = calendar.timegm(time.strptime(timestr[:19], "%Y-%m-%dT%H:%M:%S")) + frac
        return datetime.utcfromtimestamp(ts)


if __name__ == "__main__":
    from argparse import ArgumentParser
    ap = ArgumentParser(description="printf-elastic-forwarder")
    ap.add_argument("addr_subscribe", help="Pull messages from nanoprintf-server, format is: tcp://host:14998")
    ap.add_argument("addr_elastic",   help="Push messages to elasticsearch, format is: http://host:9200")
    ap.add_argument("--bind", help="Bind to pub socket instead of connecting", default=False, action='store_true')
    args = ap.parse_args()
    elfw = PrintfElasticForwarder(**args.__dict__)
    elfw.run()

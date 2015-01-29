nuggets = [
    # 95391 2015-01-16 09:57:02.82 'D| CTPRE: 358|N-etx 00 E4D8 NO NO'
    # nanodbg("data etx", "index %u neighbor %u etx NO_ROUTE retx NO_ROUTE", i, entry->neighbor);
    # debug4("N-etx %02X %02X NO NO", i, entry->neighbor); // sensed
    dict(prefix="N-etx", fields=['header', 'node', 'index', 'neighbor', 'etx', 'retx'],
         frmt="data etx %.2f node %04X_%s index %u neighbor %u etx NO_ROUTE retx NO_ROUTE",
         prep=lambda **k: [int(k['index'],16), int(k['neighbor'],16)]),

    # nanodbg("data etx", "index %u neighbor %u etx %u retx %u", i, entry->neighbor, linkEtx, entry->info.etx);
    # debug4("N-retx %02X %02X %02X %02X", i, entry->neighbor, linkEtx, entry->info.etx); // sensed
    dict(prefix="N-retx", fields=['header', 'node', 'index', 'neighbor', 'etx', 'retx'],
         frmt="data etx %.2f node %04X_%s index %u neighbor %u etx %u retx %u",
         prep=lambda **k: [int(k['index'],16), int(k['neighbor'],16), int(k['etx'],16), int(k['retx'],16)]),

    # nanodbg("event send_ctp_packet", "dest 0x%04X origin 0x%04X sequence %u amid 0x%02X thl %u", dest, hdr->origin, hdr->originSeqNo, hdr->type, hdr->thl);
    # debug4("N-sctp %04X %04X %02X %02X %02X", dest, hdr->origin, hdr->originSeqNo, hdr->type, hdr->thl); // sensed
    dict(prefix="N-sctp", fields=['header', 'node', 'dest', 'origin', 'origin_seqno', 'amid', 'thl'],
         frmt="event send_ctp_packet %.2f node %04X_%s dest 0x%04X origin 0x%04X sequence %u amid 0x%02X thl %u",
         prep=lambda **k: [int(k['dest'],16), int(k['origin'],16), int(k['origin_seqno'],16), int(k['amid'],16), int(k['thl'],16)]),

    # nanodbg("data ctpf_buf_size", "used %u capacity %u", call MessagePool.maxSize() - call MessagePool.size(), call MessagePool.maxSize());
    # debug4("N-cbuf %02X %02X", call MessagePool.maxSize() - call MessagePool.size(), call MessagePool.maxSize());
    dict(prefix="N-cbuf", fields=['header', 'node', 'used', 'capacity'],
         frmt="data ctpf_buf_size %.2f node %04X_%s used %u capacity %u",
         prep=lambda **k: [int(k['used'],16), int(k['capacity'],16)]),

    # nanodbg("event beacon", "options 0x%02X parent 0x%04X etx %u", beaconMsg->options, beaconMsg->parent, beaconMsg->etx);
    # debug4("N-bcn %02X %04X %02X", beaconMsg->options, beaconMsg->parent, beaconMsg->etx); // sensed
    dict(prefix="N-bcn", fields=['header', 'node', 'options', 'parent', 'etx'],
         frmt="event beacon %.2f node %04X_%s options 0x%02X parent 0x%04X etx %u",
         prep=lambda **k: [int(k['options'],16), int(k['parent'],16), int(k['etx'],16)]),

    # nanodbg("event packet_to_activemessage", "dest 0x%04X amid 0x%02X", addr, id);
    # debug4("N-s %04X %02X", addr, id); // sensed
    dict(prefix="N-s", fields=['header', 'node', 'dest_addr', 'amid'],
         frmt="event packet_to_activemessage %.2f node %04X_%s dest 0x%04X amid 0x%02X",
         prep=lambda **k: [int(k['dest_addr'],16), int(k['amid'],16)]),
]

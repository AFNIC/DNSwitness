#include "packet-defs.h"

int
main(int argc, char **argv)
{
    char           *filename;
    pcap_parser_file *handle;
    struct dns_packet *packet;
    if (argc < 2) {
        fatal("Usage: %s filename", argv[0]);
    }
    filename = argv[1];
    handle = pcap_file_open(filename);
    packet = malloc(sizeof(struct dns_packet));
    packet->qname = malloc(256);
    packet->src = malloc(256);
    packet->dst = malloc(256);
    while (true) {
        packet = get_next_packet(packet, handle);
        if (packet == NULL) {
            break;
        }
        fprintf
            (stdout,
             "%i: [%s]:%d -> [%s]:%d (QID %d, %s %d%s%s, Opcode %d, ques. \"%s\", qtype %i, qclass %i, resp. code %d, answer(s) %d%s, additional(s) %d, auth.(s) %d)\n",
             packet->rank, packet->src, packet->src_port, packet->dst,
             packet->dst_port, packet->query_id, packet->query ? "Q" : "R",
             packet->edns0 ? packet->edns0_size : 0, 
	     (packet->edns0 && packet->do_dnssec) ? " DO" : "",
             ((packet->query && packet->rd)
                                                      || (!packet->query
                                                          && packet->ra)) ?
             " recursive" : "", packet->opcode, packet->qname, packet->qtype,
             packet->qclass, packet->returncode, packet->ancount,
             packet->aa ? " (auth.)" : "", packet->arcount, packet->nscount);
    }
    pcap_file_close(handle);
    return 0;
}

/* Our data structures and utilities */

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

/* Application-specific headers */
#include <pcap.h>

void
                fatal(char *, ...);

struct dns_packet {
    unsigned int    rank;
    struct timeval  date;
    unsigned int    captured_length;
    unsigned int    length;     /* Original length on the cable */
    char           *src;        /* MUST be allocated by the caller */
    char           *dst;        /* MUST be allocated by the caller */
    char           *protocol;
    unsigned int    src_port, dst_port;
    bool            query;
    unsigned int    query_id;
    unsigned int    opcode;
    unsigned int    returncode;
    bool            aa, tc, rd, ra;
    char           *qname;      /* MUST be allocated by the caller */
    unsigned int    qtype, qclass;
    bool            edns0;
    unsigned int    edns0_size; /* Undefined if edns0 is false */
    bool            do_dnssec;  /* Undefined if edns0 is false */
    unsigned int    ancount, nscount, arcount;
};

typedef struct {
    pcap_t         *handle;
    unsigned long int packetnum;
    unsigned long int dnspacketnum;
    size_t          size;
    time_t          creation;
    struct timeval  firstpacket, lastpacket;
    int             datalink;
    unsigned short  snaplen;
} pcap_parser_file;

pcap_parser_file *pcap_file_open(char *);

struct dns_packet *get_next_packet(struct dns_packet *, pcap_parser_file *);

void            pcap_file_close(pcap_parser_file *);

#define PACKET_DEFS_H 1

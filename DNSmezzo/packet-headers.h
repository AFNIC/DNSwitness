/* Standard headers */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <arpa/inet.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdarg.h>
#include <unistd.h>
#include <time.h>
#include <libgen.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <errno.h>

/* Application-specific headers */
#include <pcap.h>

/* pcap variables, constants and macros */

#define SIZE_LOOP 4

/* Ethernet addresses are 6 bytes */
#define ETHER_ADDR_LEN	6

/* Ethernet headers are always exactly 14 bytes */
#define SIZE_ETHERNET 14

#define SIZE_IPv6 40

#define SIZE_FRAGMENT_HDR 8

#define SIZE_UDP 8

#define SIZE_DNS 12

#define IPv4_ETHERTYPE 0x0800

#define IPv6_ETHERTYPE 0x86DD

/* 802.1q */
#define VLAN_ETHERTYPE 0x8100

#define UDP 17

#define DNS_PORT 53

/* Ethernet header */
struct sniff_ethernet {
    uint8_t         ether_dhost[ETHER_ADDR_LEN];        /* Destination host address */
    uint8_t         ether_shost[ETHER_ADDR_LEN];        /* Source host address */
    uint16_t        ether_type; /* IP? ARP? RARP? etc */
};

/* IPv6 header. RFC 2460, section3. Reading /usr/include/netinet/ip6.h is
 * interesting */
struct sniff_ipv6 {
    uint32_t        ip_vtcfl;   /* version << 4 then traffic class and flow label */
    uint16_t        ip_len;     /* payload length */
    uint8_t         ip_nxt;     /* next header (protocol) */
    uint8_t         ip_hopl;    /* hop limit (ttl) */
    struct in6_addr ip_src, ip_dst;     /* source and dest address */
};
#define IPV6_VERSION(ip)          (ntohl((ip)->ip_vtcfl) >> 28)

struct sniff_eh {
    uint8_t         eh_next;    /* next header (protocol) */
    uint8_t         eh_length;
};

struct sniff_frag {
    uint8_t         frag_next;  /* next header (protocol) */
    uint8_t         frag_reserved;
    uint16_t        frag_offset_res_m;  /* Fragment offset then Reserved then M flag 
                                         */
    uint32_t        frag_identification;
};
#define FRAG_OFFSET(frag) (ntohs(frag->frag_offset_res_m) >> 3)

/* IPv4 header */
struct sniff_ipv4 {
    uint8_t         ip_vhl;     /* version << 4 | header length >> 2 */
    uint8_t         ip_tos;     /* type of service */
    uint16_t        ip_len;     /* total length */
    uint16_t        ip_id;      /* identification */
    uint16_t        ip_off;     /* fragment offset field */
#define IP_RF 0x8000            /* reserved fragment flag */
#define IP_DF 0x4000            /* dont fragment flag */
#define IP_MF 0x2000            /* more fragments flag */
#define IP_OFFMASK 0x1fff       /* mask for fragmenting bits */
    uint8_t         ip_ttl;     /* time to live */
    uint8_t         ip_p;       /* protocol */
    uint16_t        ip_sum;     /* checksum */
    struct in_addr  ip_src, ip_dst;     /* source and dest address */
};
#define IP_HL(ip)               (((ip)->ip_vhl) & 0x0f)
#define IPV4_VERSION(ip)                (((ip)->ip_vhl) >> 4)

/* UDP header */
struct sniff_udp {
    uint16_t        sport;      /* source port */
    uint16_t        dport;      /* destination port */
    uint16_t        udp_length;
    uint16_t        udp_sum;    /* checksum */
};

struct sniff_dns {
    /* RFC 1035, section 4.1 */
    /* This is only the DNS header, the sections (Question, Answer, etc) follow */
    uint16_t        query_id;
    uint16_t        codes;
    uint16_t        qdcount, ancount, nscount, arcount;
};
#define DNS_QR(dns)		((ntohs((dns)->codes) & 0x8000) >> 15)
#define DNS_OPCODE(dns)	((ntohs((dns)->codes) >> 11) & 0x000F)
#define DNS_RCODE(dns)	(ntohs((dns)->codes) & 0x000F)
#define DNS_AA(dns)   ((ntohs((dns)->codes) & 0x0400) >> 10)
#define DNS_TC(dns)   ((ntohs((dns)->codes) & 0x0200) >> 9)
#define DNS_RD(dns)   ((ntohs((dns)->codes) & 0x0100) >> 8)
#define DNS_RA(dns)   ((ntohs((dns)->codes) & 0x0080) >> 7)
#define DNS_DO_DNSSEC(z) ((z & 0x8000) >> 15)

/* RR types */
#define OPT 41

#define MAX_NAME 255
/* End of pcap variables, constants and macros */

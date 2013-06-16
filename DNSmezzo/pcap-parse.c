/* Converts a trace of DNS packets (pcap format) to C structures. 

   S. Bortzmeyer <bortzmeyer@afnic.fr> */

#include "packet-headers.h"

#include "packet-defs.h"

#define CHECK_SECTIONPTR(need) if (((long int)sectionptr - (long int)packet + (long int)need - 1) > (long int)decoded->captured_length) { \
                               if (verbose) { \
                                    fprintf(stdout, \
                                    "Warning: ignoring packet #%li because malformed (sectionptr moves out of the packet, captured length is %i bytes)\n", \
											input->packetnum, decoded->captured_length);				\
                               } \
                               goto next_packet; \
            				}

#ifdef PICKY_WITH_ALIGNMENT
uint16_t
unaligned_uint16(const uint8_t * p)
{
    /* This assumes big-endian values in data stream (which is standard for TCP/IP,
     * it is the "network byte order"). Stolen from
     * <http://stackoverflow.com/questions/529327/safe-efficient-way-to-access-unaligned-data-in-a-network-packet-from-c/529491#529491> 
     */
    unsigned char  *pByte = (unsigned char *) p;
    uint16_t        val = (pByte[0] << 8) | pByte[1];
    return val;
}
#endif

/* Defaults */
static bool     verbose = false;
static unsigned long maxpackets = 0;

void
fatal(char *msg, ...)
{
    va_list         args;
    va_start(args, msg);
    fprintf(stderr, "Fatal error: ");
    (void) vfprintf(stderr, msg, args);
    va_end(args);
    fprintf(stderr, "\n");
    exit(EXIT_FAILURE);
}

pcap_parser_file *
pcap_file_open(char *filename)
{
    char            errbuf[PCAP_ERRBUF_SIZE];
    pcap_parser_file *thefile;
    struct stat     result;
    thefile = malloc(sizeof(pcap_parser_file));
    thefile->packetnum = 0;
    thefile->dnspacketnum = 0;
    if (stat(filename, &result) != 0) {
        fatal("File %s does not exist or is not accessible: %s", filename,
              strerror(errno));
    }
    thefile->size = result.st_size;
    thefile->creation = result.st_ctime;
    thefile->firstpacket.tv_sec = 0;
    thefile->firstpacket.tv_usec = 0;
    thefile->lastpacket.tv_sec = 0;
    thefile->lastpacket.tv_usec = 0;
    thefile->handle = pcap_open_offline(filename, errbuf);
    if (thefile->handle == NULL) {
        fatal("Couldn't open file %s: %s\n", filename, errbuf);
    }
    thefile->datalink = pcap_datalink(thefile->handle);
    thefile->snaplen = pcap_snapshot(thefile->handle);
    if (verbose) {
        fprintf(stdout,
                "Analyzing %s, version %i.%i, type %s, max packet size %u bytes...\n",
                filename, pcap_major_version(thefile->handle),
                pcap_minor_version(thefile->handle),
                pcap_datalink_val_to_description(thefile->datalink),
                thefile->snaplen);
    }
    return thefile;
}

struct dns_packet *
get_next_packet(struct dns_packet *decoded, pcap_parser_file * input)
{
    /* Misc. variables */
    char            fqdn[MAX_NAME + 1];
    unsigned int    fqdn_length;

    /* pcap-related variables */
    const uint8_t  *packet;     /* The actual packet */
    struct pcap_pkthdr header;  /* The header that pcap gives us */
    const struct sniff_ethernet *ethernet;      /* The ethernet header */
    const struct sniff_sll *sll_link;   /* The SLL header */
    unsigned short  ethertype;
    const struct sniff_ipv4 *ipv4;      /* The IP header */
    const struct sniff_ipv6 *ipv6;
    const struct sniff_udp *udp;        /* The UDP header */
    const struct sniff_dns *dns;
    u_int           size_ip;
    u_int           size_layer2;
    unsigned short  ip_version;
    uint32_t        family;
    const uint8_t  *qsection;
    uint8_t         labelsize;
    uint16_t        add_type;
    uint16_t        edns_size;
    uint16_t        extended_rcode_and_version;
    uint16_t        zpart;
    uint            num_edns_options = 0;
    uint16_t        opt_len, option_code, option_length;
    uint16_t        option_codes[MAX_EDNS_OPTIONS];
    const uint8_t  *sectionptr;
    const uint8_t  *where_am_i; /* Cursor in packet */
    bool            end_of_name;
    unsigned int    size_header;
    bool            end_of_headers, fragmented;
    uint8_t         next_v6_header;
    const struct sniff_eh *eh;  /* The IPv6 extension header, if present */
    const struct sniff_frag *frag;

    assert(decoded->qname != NULL);
    /* Grab next packet */
    decoded->rank = input->packetnum;
  next_packet:
    packet = (uint8_t *) pcap_next(input->handle, &header);
    if (packet == NULL) {       /* End of file */
        return NULL;
    }
    input->packetnum++;
    decoded->length = header.len;
    decoded->captured_length = header.caplen;
    decoded->date = header.ts;
    if (input->firstpacket.tv_sec == 0 && input->firstpacket.tv_usec == 0) {
        input->firstpacket = header.ts;
    }
    input->lastpacket = header.ts;
    if (input->datalink == DLT_EN10MB) {
        size_layer2 = SIZE_ETHERNET;
        ethernet = (struct sniff_ethernet *) (packet);
        ethertype = ntohs(ethernet->ether_type);
        if (ethertype == VLAN_ETHERTYPE) {
            packet += 4;
            ethernet = (struct sniff_ethernet *) (packet);
            ethertype = ntohs(ethernet->ether_type);
        }
        if (ethertype == IPv6_ETHERTYPE) {
            ip_version = 6;
        } else if (ethertype == IPv4_ETHERTYPE) {
            ip_version = 4;
        } else {                /* Ignore other Ethernet types */
            goto next_packet;
        }
    } else if (input->datalink == DLT_LOOP) {   /* No Ethernet type for this data
                                                 * link */
        size_layer2 = SIZE_LOOP;
        family = (ntohl(*((uint32_t *) packet)));       /* TODO seems broken.
                                                         * Untested */
        if (family == PF_INET6) {
            ip_version = 6;
        } else if (family == PF_INET) {
            ip_version = 4;
        } else {                /* Ignore other packet types */
            goto next_packet;
        }
    } else if (input->datalink == DLT_LINUX_SLL) {      /* http://www.tcpdump.org/linktypes/LINKTYPE_LINUX_SLL.html 
                                                         */
        size_layer2 = SIZE_SLL;
        sll_link = (struct sniff_sll *) (packet);
        ethertype = ntohs(sll_link->protocol_type);
        if (ethertype == IPv6_ETHERTYPE) {
            ip_version = 6;
        } else if (ethertype == IPv4_ETHERTYPE) {
            ip_version = 4;
        } else {                /* Ignore other Ethernet types */
            goto next_packet;
        }
    } else {
        fatal("Unsupported data link type %s (%i)\n",
              pcap_datalink_val_to_description(input->datalink), input->datalink);
    }
    if (ip_version == 6) {
        ipv6 = (struct sniff_ipv6 *) (packet + size_layer2);
        size_ip = SIZE_IPv6;
        assert(IPV6_VERSION(ipv6) == 6);
        next_v6_header = ipv6->ip_nxt;
        size_header = 0;
        where_am_i = where_am_i + SIZE_IPv6;
        end_of_headers = false;
        fragmented = false;
        while (!end_of_headers) {
            /* Extension headers defined in RFC 2460, section 4 */
            if (next_v6_header == 0 ||
                next_v6_header == 43 || next_v6_header == 50
                || next_v6_header == 51 || next_v6_header == 60) {
                eh = (struct sniff_eh *) (where_am_i);
                next_v6_header = eh->eh_next;
                size_header = eh->eh_length;
            }
            /* Fragment */
            else if (next_v6_header == 44) {
                fragmented = 1;
                frag = (struct sniff_frag *) (where_am_i);
                next_v6_header = frag->frag_next;
                size_header = SIZE_FRAGMENT_HDR;
            } else {
                /* TODO: RFC 6564 says that the *future* headers will have the same
                 * format as Destination Options, with a length field, so we may be
                 * able to jump them even without knowledge of their content. */
                end_of_headers = true;
            }
            where_am_i = where_am_i + size_header;
            size_ip += size_header;
            if ((size_layer2 + size_ip) > decoded->captured_length) {
                if (verbose) {
                    fprintf(stdout,
                            "Warning: ignoring packet #%li because IPv6 headers too large\n",
                            input->packetnum);
                }
                goto next_packet;
            }
        }
        if (fragmented && FRAG_OFFSET(frag) == 0) {
            goto next_packet;
        }
    } else if (ip_version == 4) {
        ipv4 = (struct sniff_ipv4 *) (packet + size_layer2);
        size_ip = IP_HL(ipv4) * 4;
        assert(IPV4_VERSION(ipv4) == 4);
    } else {
        /* Should never happen */
        assert(0);
    }
    if ((ip_version == 6 && next_v6_header == UDP)
        || (ip_version == 4 && ipv4->ip_p == UDP)) {
        if (ip_version == 6) {
            assert(decoded->src != NULL);
            assert(decoded->dst != NULL);
            inet_ntop(AF_INET6, &ipv6->ip_src, decoded->src, INET6_ADDRSTRLEN);
            inet_ntop(AF_INET6, &ipv6->ip_dst, decoded->dst, INET6_ADDRSTRLEN);
        } else if (ip_version == 4) {
            assert(decoded->src != NULL);
            assert(decoded->dst != NULL);
            inet_ntop(AF_INET, &ipv4->ip_src, decoded->src, INET_ADDRSTRLEN);
            inet_ntop(AF_INET, &ipv4->ip_dst, decoded->dst, INET_ADDRSTRLEN);
        } else {
            goto next_packet;
        }
        udp = (struct sniff_udp *) (packet + size_layer2 + size_ip);
        decoded->src_port = (u_short) ntohs(udp->sport);
        decoded->dst_port = (u_short) ntohs(udp->dport);
        if (decoded->src_port == DNS_PORT || decoded->dst_port == DNS_PORT) {
            if (maxpackets > 0 && input->dnspacketnum >= maxpackets) {
                return NULL;
            }
            dns = (struct sniff_dns *) (packet + size_layer2 + size_ip + SIZE_UDP);
            decoded->query = DNS_QR(dns) == 0 ? true : false;
            decoded->query_id = dns->query_id;
            decoded->opcode = DNS_OPCODE(dns);
            decoded->returncode = DNS_RCODE(dns);
            decoded->aa = DNS_AA(dns) ? true : false;
            decoded->tc = DNS_TC(dns) ? true : false;
            decoded->rd = DNS_RD(dns) ? true : false;
            decoded->ra = DNS_RA(dns) ? true : false;
            decoded->ancount = ntohs(dns->ancount);
            decoded->nscount = ntohs(dns->nscount);
            decoded->arcount = ntohs(dns->arcount);
            qsection = (uint8_t *) (packet +
                                    size_layer2 + size_ip + SIZE_UDP + SIZE_DNS);
            fqdn[0] = '\0';
            end_of_name = false;
            for (sectionptr = qsection; !end_of_name;) {
                CHECK_SECTIONPTR(1);
                labelsize = (uint8_t) * sectionptr;
                if (labelsize == 0) {
                    sectionptr++;
                    end_of_name = true;
                } else if (labelsize > 63) {
                    /* It can be an error/attack or it can be compression (RFC 1035, 
                     * section 4.1.4). Today, we ignore packets with compression (we 
                     * just parse the question section, anyway). * * * * * * * *
                     * TODO */
                    if (verbose) {
                        fprintf(stdout,
                                "Warning: ignoring packet #%li because labelsize > 63\n",
                                input->packetnum);
                    }
                    goto next_packet;
                } else {
                    CHECK_SECTIONPTR(labelsize);
                    if (strlen(fqdn) == 0) {
                        strncpy(fqdn, (char *)
                                sectionptr + 1, labelsize);
                        fqdn_length = labelsize;
                    } else {
                        fqdn_length = strlen(fqdn);
                        if (fqdn_length + labelsize > MAX_NAME) {
                            if (verbose) {
                                fprintf(stdout,
                                        "Warning: ignoring packet #%li because malformed (FQDN length is already %i and label size is %i bytes)\n",
                                        input->packetnum, fqdn_length, labelsize);
                            };
                            goto next_packet;
                        }
                        strncat(fqdn, ".", 1);
                        strncat(fqdn, (char *)
                                sectionptr + 1, labelsize);
                        fqdn_length += (labelsize + 1);
                    }
                    if (fqdn_length > MAX_NAME) {
                        if (verbose) {
                            fprintf(stdout,
                                    "Warning: ignoring packet #%li because FQDN length > %i\n",
                                    input->packetnum, MAX_NAME);
                        }
                        goto next_packet;
                    }
                    fqdn[fqdn_length] = '\0';
                    sectionptr = sectionptr + labelsize + 1;
                    CHECK_SECTIONPTR(0);
                }
            }
            CHECK_SECTIONPTR(2);
            strcpy(decoded->qname, fqdn);
#ifdef PICKY_WITH_ALIGNMENT
            decoded->qtype = unaligned_uint16(sectionptr);
#else
            decoded->qtype = ntohs(*((uint16_t *) sectionptr));
#endif
            sectionptr += 2;
            CHECK_SECTIONPTR(2);
#ifdef PICKY_WITH_ALIGNMENT
            decoded->qclass = unaligned_uint16(sectionptr);
#else
            decoded->qclass = ntohs(*((uint16_t *) sectionptr));
#endif
            sectionptr += 2;
            decoded->edns0 = false;
            if (decoded->query) {
                edns_size = 0;
                if (dns->ancount == 0 && dns->nscount == 0) {
                    /* Probably by far the most common case in queries... */
                    if (dns->arcount != 0) {    /* There is an additional section.
                                                 * Probably the OPT * * * * * * * *
                                                 * * * * * of EDNS */
                        CHECK_SECTIONPTR(1);
                        labelsize = (uint8_t) * sectionptr;
                        if (labelsize == 0) {   /* Yes, EDNS0 */
                            sectionptr += 1;
                            CHECK_SECTIONPTR(2);
#ifdef PICKY_WITH_ALIGNMENT
                            add_type = unaligned_uint16(sectionptr);
#else
                            add_type = ntohs(*((uint16_t *) sectionptr));
#endif
                            sectionptr += 2;
                            CHECK_SECTIONPTR(2);
                            if (add_type == OPT) {
#ifdef PICKY_WITH_ALIGNMENT
                                edns_size = unaligned_uint16(sectionptr);
#else
                                edns_size = ntohs(*((uint16_t *) sectionptr));
#endif
                                decoded->edns0 = true;
                                /* RFC 2671 */
                                sectionptr += 2;
                                CHECK_SECTIONPTR(2);
#ifdef PICKY_WITH_ALIGNMENT
                                extended_rcode_and_version =
                                    unaligned_uint16(sectionptr);
#else
                                extended_rcode_and_version =
                                    ntohs(*((uint16_t *) sectionptr));
#endif
                                sectionptr += 2;
                                CHECK_SECTIONPTR(2);
#ifdef PICKY_WITH_ALIGNMENT
                                zpart = unaligned_uint16(sectionptr);
#else
                                zpart = ntohs(*((uint16_t *) sectionptr));
#endif
                                /* RFC 3225 */
                                decoded->do_dnssec =
                                    DNS_DO_DNSSEC(zpart) ? true : false;
                            }
                            sectionptr += 2;
                            CHECK_SECTIONPTR(2);
#ifdef PICKY_WITH_ALIGNMENT
                            opt_len = unaligned_uint16(sectionptr);
#else
                            opt_len = ntohs(*((uint16_t *) sectionptr));
#endif
                            sectionptr += 2;
                            while (opt_len > 0
                                   && num_edns_options < MAX_EDNS_OPTIONS) {
                                CHECK_SECTIONPTR(2);
#ifdef PICKY_WITH_ALIGNMENT
                                option_code = unaligned_uint16(sectionptr);
#else
                                option_code = ntohs(*((uint16_t *) sectionptr));
#endif
                                option_codes[num_edns_options] = option_code;
                                sectionptr += 2;
                                CHECK_SECTIONPTR(2);
#ifdef PICKY_WITH_ALIGNMENT
                                option_length = unaligned_uint16(sectionptr);
#else
                                option_length = ntohs(*((uint16_t *) sectionptr));
#endif
                                opt_len -= (option_length + 4);
                                num_edns_options++;
                                sectionptr += option_length;
                            }
                            memcpy(decoded->edns_options, option_codes,
                                   num_edns_options * sizeof(option_code));
                            decoded->num_edns_options = num_edns_options;
                        }
                    }
                }
            }
            if (decoded->edns0) {
                decoded->edns0_size = (unsigned int) edns_size;
            }
            input->dnspacketnum++;
            return decoded;
        }
    }
    goto next_packet;
}

void
pcap_file_close(pcap_parser_file * thefile)
{
    pcap_close(thefile->handle);
    free(thefile);
}

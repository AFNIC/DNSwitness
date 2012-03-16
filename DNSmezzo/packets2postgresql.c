/* Converts a list of DNS packets (read in a pcap trace file) to a
   PostgreSQL database.

   S. Bortzmeyer <bortzmeyer@afnic.fr> */

/* TODO: No more segfaults and memory corruption. But still try it
   under splint and under garder gcc options. See
   http://stackoverflow.com/questions/154630/recommended-gcc-warning-options-for-c */

/* TODO: warnings when compiling on UltraSparc/NetBSD, worth some investigation

packets2postgresql.c: In function 'current_time':
packets2postgresql.c:46: warning: passing argument 1 of 'gmtime' from incompatible pointer type
packets2postgresql.c: In function 'lower':
packets2postgresql.c:56: warning: array subscript has type 'char'
packets2postgresql.c: In function 'main':
packets2postgresql.c:451: warning: passing argument 1 of 'gmtime' from incompatible pointer type
packets2postgresql.c:457: warning: passing argument 1 of 'gmtime' from incompatible pointer type

The gmtime problem seems serious since, on UltraSparc/NetBSD, the
program runs but stores only 1970-01-01 00:00:00 for the dates of the
packets.

*/

/* Standard headers */
#include <unistd.h>
#include <time.h>
#include <string.h>
#include <strings.h>
#include <arpa/inet.h>
#include <ctype.h>
#include <limits.h>
#include <sys/stat.h>
#include <unistd.h>

/* Application-specific headers */
#include <libpq-fe.h>

#include "packet-defs.h"

#include "dkim-regdom.h"
#include "tld-canon.h"

#define MAX_TIME_SIZE 256
#define MAX_NAME 255
#define ISO_FORMAT "%F %H:%M:%SZ"

static char    *progname;

static void
usage()
{
    (void) fprintf(stderr, "Usage: %s filename.pcap\n", progname);
    exit(EXIT_FAILURE);
}

static char    *
current_time()
{
    char           *result = malloc(MAX_TIME_SIZE);
    struct timeval  tv;
    struct tm      *time;
    (void) gettimeofday(&tv, NULL);
    time = gmtime(&tv.tv_sec);
    strftime(result, MAX_TIME_SIZE, "%Y-%m-%dT%H:%M:%SZ", time);
    return result;
}

void
lower(char *to, const char *from)
{
    unsigned int    i;
    for (i = 0; i < strlen(from); i++) {
        to[i] = tolower(from[i]);
    }
    to[i] = '\0';
}

void
escape(char *to, const char *from)
/* http://www.postgresql.org/docs/current/interactive/sql-copy.html */
{
    unsigned int    i, j;
    j = 0;
    for (i = 0; i < strlen(from); i++) {
        switch (from[i]) {
        case 10:
        case 13:
            to[j++] = '\\';
            to[j++] = 'n';
            break;
        case 9:
            to[j++] = '\\';
            to[j++] = 't';
            break;
        case 92:
            if (from[i+1] == '.') {
                to[j++] = '.';
                i++;
            }
            break;
        default:
            to[j++] = from[i];
            break;
        }
    }
    to[j] = '\0';
}

/*
 * Create a new string with all occurrences of [substr] being
 * replaced by [replacement] in [string].
 * Returns the new string, or NULL if out of memory.
 * The caller is responsible for freeing this new string.
 * http://coding.debuntu.org/c-implementing-str_replace-replace-all-occurrences-substring
 * Licence: GPL v2+
 */
char *
str_replace ( const char *string, const char *substr, const char *replacement ){
  char *tok = NULL;
  char *newstr = NULL;
  char *oldstr = NULL;
  char *head = NULL;
 
  /* if either substr or replacement is NULL, duplicate string a let caller handle it */
  if ( substr == NULL || replacement == NULL ) return strdup (string);
  newstr = strdup (string);
  head = newstr;
  while ( (tok = strstr ( head, substr ))){
    oldstr = newstr;
    newstr = malloc ( strlen ( oldstr ) - strlen ( substr ) + strlen ( replacement ) + 1 );
    /*failed to alloc mem, free old string and return NULL */
    if ( newstr == NULL ){
      free (oldstr);
      return NULL;
    }
    memcpy ( newstr, oldstr, tok - oldstr );
    memcpy ( newstr + (tok - oldstr), replacement, strlen ( replacement ) );
    memcpy ( newstr + (tok - oldstr) + strlen( replacement ), tok + strlen ( substr ), strlen ( oldstr ) - strlen ( substr ) - ( tok - oldstr ) );
    memset ( newstr + strlen ( oldstr ) - strlen ( substr ) + strlen ( replacement ) , 0, 1 );
    /* move back head right after the last replacement */
    head = newstr + (tok - oldstr) + strlen( replacement );
    free (oldstr);
  }
  return newstr;
}

#define METADATA_INT 1
#define METADATA_DOUBLE 2

#define METADATA_BASE 10

void           *
get_metadata(name, key, type)
    char           *name;
    char           *key;
    int             type;
{
    char           *data;
    int            *iresult;
    double         *fresult;
    data = strstr(name, key);
    if (data == NULL) {
        return NULL;
    } else {
        data = data + strlen(key) + 1;
        switch (type) {
        case METADATA_INT:
            iresult = malloc(sizeof(int));
            *iresult = strtol(data, NULL, METADATA_BASE);
            if (*iresult <= 0) {
                fprintf(stderr, "Cannot find a value in %s\n", data);
                exit(1);
            }
            return iresult;
        case METADATA_DOUBLE:
            fresult = malloc(sizeof(double));
            *fresult = strtod(data, NULL);
            if (*fresult <= 0.0) {
                fprintf(stderr, "Cannot find a value in %s\n", data);
                exit(1);
            }
            return fresult;
        default:
            fprintf(stderr, "Invalid metadata type %i\n", type);
            break;
        }
        return NULL;
    }
}

#define SQL_PACKET_COMMAND "COPY DNS_Packets \
           (file, rank, date, length, src_address, dst_address, protocol, src_port, dst_port, \
            query, query_id, opcode, rcode, aa, tc, rd, ra, qname, qtype, qclass, edns0_size, do_dnssec, \
            ancount, nscount, arcount, registered_domain, lowercase_qname) FROM STDIN;"
#define PREPARED_PACKET_STMT "copy-data"
#define SQL_FILE_COMMAND "INSERT INTO Pcap_Files (hostname, filename, datalinktype, snaplength, filesize, filedate, stoppedat, samplingrate) VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id;"
#define NUM_FILE_PARAMS 8
#define PREPARED_FILE_STMT "insert-filename"
#define SQL_FILEEND_COMMAND "UPDATE Pcap_Files SET totalpackets=$1, storedpackets=$2, firstpacket=$3, lastpacket=$4 \
                                WHERE id=$5;"
#define NUM_FILEEND_PARAMS 5
#define PREPARED_FILEEND_STMT "update-filename"
#define SQL_CREATE_CONSTRAINT_UNIQUE_ID "ALTER TABLE TABLE_NAME ADD CONSTRAINT id_key_TABLE_NAME UNIQUE(id);"
#define SQL_CREATE_CONSTRAINT_REF_FILE "ALTER TABLE TABLE_NAME ADD CONSTRAINT fk_file_TABLE_NAME FOREIGN KEY (file) REFERENCES Pcap_files(id);"
#define SQL_CREATE_INDEXES_COMMAND "CREATE INDEX qname_idx_TABLE_NAME ON TABLE_NAME(qname); \
        CREATE INDEX reg_domain_idx_TABLE_NAME ON TABLE_NAME(registered_domain); \
        CREATE INDEX lc_qname_idx_TABLE_NAME ON TABLE_NAME(lowercase_qname); \
        CREATE INDEX date_idx_TABLE_NAME ON TABLE_NAME(date); \
        CREATE INDEX rcode_idx_TABLE_NAME ON TABLE_NAME(rcode);"
#define MAX_INTEGER_WIDTH 30
#define MAX_FLOAT_WIDTH 40
#define MAX_TIMESTAMP_WIDTH 60
#define MAX_STRING 512
#define FMT_PACKET_MAX_SIZE 1024        /* Measured against an actual database,
                                         * where the average size is currently
                                         * (2010-09-20) around 520 bytes */
#define INCREMENT 10000
#define BUFFER_SIZE (INCREMENT * FMT_PACKET_MAX_SIZE)

/* Defaults */
static bool     verbose = false;
static bool     dry_run = false;
static unsigned long maxpackets = 0;
static bool     parse_filename = false;

int
main(int argc, char *argv[])
{
    /* Misc. variables */
    char           *filename, *ct, *hostname[MAX_NAME], errbuf[PCAP_ERRBUF_SIZE];
    pcap_parser_file *inputfile;
    struct dns_packet *packet;
    int             ch;
    unsigned long   packetnum = 0;

    /* PostgreSQL-related variables */
    char           *conninfo = "dbname=essais";
    char           *table_name;
    PGconn         *conn = NULL;
    ConnStatusType  status;
    PGresult       *result;
    struct tm       file_creation, date_firstpacket, date_lastpacket;
    int            *sampling;
    char           *buffer, *bufptr, *tmp, *tmp2, *tmp3;       /* SQL COPY input buffer */
    unsigned long   copied;
    const char     *file_params[NUM_FILE_PARAMS];
    const char     *fileend_params[NUM_FILEEND_PARAMS];
    unsigned int    file_id;

    progname = argv[0];
    while ((ch = getopt(argc, argv, "nvm:c:p")) != -1) {
        switch (ch) {
        case 'v':
            verbose = true;
            break;
        case 'n':
            dry_run = true;
            break;
        case 'm':
            maxpackets = (unsigned long) atoi(optarg);
            if (maxpackets == 0) {
                fatal("illegal max. packets value");
            }
            break;
        case 'c':
            conninfo = optarg;
            break;
        case 'p':
            parse_filename = true;
            break;
        default:
            usage();
        }
    }
    argc -= optind;
    argv += optind;
    if (argc < 1) {
        usage();
    }
    filename = argv[0];
    inputfile = pcap_file_open(filename);
    if (inputfile == NULL) {
        fatal("Couldn't open file %s: %s\n", filename, errbuf);
    }
    if (verbose) {
        ct = current_time();
        fprintf(stdout, "%s Dissecting %s and sending to \"%s\"\n", ct,
                filename, conninfo);
        /* TODO: retrieve from inputfile other parameters such as the snapshot size */
        free(ct);
    }
    if (!dry_run) {
        conn = PQconnectdb(conninfo);
        if (conn == NULL) {
            fatal("Cannot connect to the database (unknown reason)");
        }
        status = PQstatus(conn);
        if (status != CONNECTION_OK) {
            fatal(PQerrorMessage(conn));
        }
        /* We find lot of funny characters in domain names, not always UTF-8.
         * Setting the client encoding to Latin-1 is arbitrary, but it is to
         * be sure the program won't crash (because any string is valid 
         * Latin-1, unlike UTF-8). */
        result = PQexec(conn, "SET CLIENT_ENCODING TO 'LATIN-1';");
        if (PQresultStatus(result) != PGRES_COMMAND_OK) {
            fatal("Cannot set encoding");
        }
        PQclear(result);
        result = PQexec(conn, "BEGIN;");
        if (PQresultStatus(result) != PGRES_COMMAND_OK) {
            fatal("Cannot start transaction");
        }
        /* TODO: may be not add it if there are no packets? */
        PQclear(result);
        result = PQprepare(conn, PREPARED_FILE_STMT, SQL_FILE_COMMAND, 1, NULL);
        if (PQresultStatus(result) != PGRES_COMMAND_OK) {
            fatal("Cannot prepare statement: %s", PQresultErrorMessage(result));
        }
    }
    status = gethostname((char *) hostname, MAX_NAME);
    if (status != 0) {
        fatal("Cannot retrieve host name");
    }
    file_params[0] = (char *) hostname;
    file_params[1] = malloc(PATH_MAX + 1);
    realpath(filename, (char *) file_params[1]);
    file_params[2] = pcap_datalink_val_to_description(inputfile->datalink);
    file_params[3] = malloc(MAX_INTEGER_WIDTH);
    sprintf((char *) file_params[3], "%i", inputfile->snaplen);
    file_params[4] = malloc(MAX_INTEGER_WIDTH);
    sprintf((char *) file_params[4], "%li", (long int) inputfile->size);
    file_params[5] = malloc(MAX_TIMESTAMP_WIDTH);
    file_creation = *gmtime(&inputfile->creation);
    strftime((char *) file_params[5], MAX_TIMESTAMP_WIDTH, ISO_FORMAT,
             &file_creation);
    if (maxpackets > 0) {
        file_params[6] = malloc(MAX_INTEGER_WIDTH);
        sprintf((char *) file_params[6], "%li", maxpackets);
    } else {
        file_params[6] = NULL;
    }
    if (parse_filename) {
        sampling = (int *) get_metadata(filename, "SAMPLING", METADATA_INT);
        if (sampling == NULL) {
            file_params[7] = NULL;
        } else {
            file_params[7] = malloc(MAX_FLOAT_WIDTH);
            sprintf((char *) file_params[7], "%f", 1.0 / (*sampling));
        }
    } else {
        file_params[7] = NULL;
    }

    tmp = malloc(MAX_STRING);
    table_name = malloc(MAX_STRING);

    if (!dry_run) {
        PQclear(result);
        result =
            PQexecPrepared(conn, PREPARED_FILE_STMT, NUM_FILE_PARAMS, file_params,
                           NULL, NULL, 0);
        if (PQresultStatus(result) == PGRES_TUPLES_OK) {
            file_id = (unsigned int) atoi(PQgetvalue(result, 0, 0));
            if (file_id == 0) {
                fatal("Cannot retrieve file_id after inserting file name %s",
                      filename);
            }
        } else {
            fatal("Result for '%s' with \"%s\" is %s", SQL_FILE_COMMAND,
                  file_params[0], PQresultErrorMessage(result));
        }
        PQclear(result);
        sprintf(tmp, "%d", file_id);
        strcpy(table_name, "DNS_Packets_");
        strcat(table_name, tmp);
        free(tmp);
        tmp = str_replace(SQL_PACKET_COMMAND, "DNS_Packets", table_name);
        result = PQprepare(conn, PREPARED_PACKET_STMT, tmp, 1, NULL);
        free(tmp);
        if (PQresultStatus(result) != PGRES_COMMAND_OK) {
            fatal("Cannot prepare statement: %s", PQresultErrorMessage(result));
        }
        PQclear(result);
        result =
            PQprepare(conn, PREPARED_FILEEND_STMT, SQL_FILEEND_COMMAND, 1, NULL);
        if (PQresultStatus(result) != PGRES_COMMAND_OK) {
            fatal("Cannot prepare statement: %s", PQresultErrorMessage(result));
        }
    }
    packet = malloc(sizeof(struct dns_packet));
    packet->qname = malloc(MAX_NAME);
    packet->src = malloc(INET6_ADDRSTRLEN);
    packet->dst = malloc(INET6_ADDRSTRLEN);
    buffer = malloc(BUFFER_SIZE);
    if (buffer == NULL) {
        fatal("Cannot malloc %i bytes for the COPY input buffer", BUFFER_SIZE);
    }
    bufptr = buffer;
    PQclear(result);
    result = PQexecPrepared(conn, PREPARED_PACKET_STMT, 0, NULL, NULL, NULL, 0);
    if (PQresultStatus(result) == PGRES_COPY_IN) {
        /* OK */
    } else {
        fatal("Result for '%s' is %s", SQL_PACKET_COMMAND,
              PQresultErrorMessage(result));
    }

    // read TLDs only once at daemon startup
    tldnode* tree = readTldTree(tldString);

    tmp = malloc(MAX_STRING);
    tmp2 = malloc(MAX_STRING);

    for (;;) {
        /* Grab a packet */
        packet = get_next_packet(packet, inputfile);
        if (packet == NULL) {
            break;
        }
        sprintf(tmp, "%i\t", file_id);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        sprintf(tmp, "%i\t", packet->rank);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        strftime(tmp, MAX_TIMESTAMP_WIDTH,
                 "%Y-%m-%d:%H:%M:%SZ",
                 gmtime((const time_t *) &packet->date.tv_sec));
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        *bufptr = '\t';
        bufptr++;
        sprintf(tmp, "%i\t", packet->length);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        sprintf(tmp, "%s\t", packet->src);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        sprintf(tmp, "%s\t", packet->dst);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        strcpy(bufptr, "UDP\t");        /* TODO: add TCP support one day... */
        bufptr += strlen("UDP\t");
        sprintf(tmp, "%i\t", packet->src_port);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        sprintf(tmp, "%i\t", packet->dst_port);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        strcpy(bufptr, packet->query ? "true" : "false");
        bufptr += strlen(packet->query ? "true" : "false");
        *bufptr = '\t';
        bufptr++;
        sprintf(tmp, "%i\t", packet->query_id);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        sprintf(tmp, "%i\t", packet->opcode);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        sprintf(tmp, "%i\t", packet->returncode);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        strcpy(bufptr, packet->aa ? "true" : "false");
        bufptr += strlen(packet->aa ? "true" : "false");
        *bufptr = '\t';
        bufptr++;
        strcpy(bufptr, packet->tc ? "true" : "false");
        bufptr += strlen(packet->tc ? "true" : "false");
        *bufptr = '\t';
        bufptr++;
        strcpy(bufptr, packet->rd ? "true" : "false");
        bufptr += strlen(packet->rd ? "true" : "false");
        *bufptr = '\t';
        bufptr++;
        strcpy(bufptr, packet->ra ? "true" : "false");
        bufptr += strlen(packet->ra ? "true" : "false");
        *bufptr = '\t';
        bufptr++;
        escape(tmp, packet->qname);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        *bufptr = '\t';
        bufptr++;
        sprintf(tmp, "%i\t", packet->qtype);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        sprintf(tmp, "%i\t", packet->qclass);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        if (packet->edns0) {
            sprintf(tmp, "%i\t", packet->edns0_size);
            strcpy(bufptr, tmp);
            bufptr += strlen(tmp);
            strcpy(bufptr, packet->do_dnssec ? "true" : "false");
            bufptr += strlen(packet->do_dnssec ? "true" : "false");
            *bufptr = '\t';
            bufptr++;
        } else {
            strcpy(bufptr, "\\N\t\\N\t");
            bufptr += strlen("\\N\t\\N\t");
        }
        sprintf(tmp, "%i\t", packet->ancount);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        sprintf(tmp, "%i\t", packet->nscount);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        sprintf(tmp, "%i\t", packet->arcount);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        lower(tmp2, packet->qname);
        if (strcmp(tmp2, "") != 0) {
            tmp3 = getRegisteredDomain(tmp2, tree);
        } else {
            tmp3 = NULL;
        }
        if (tmp3 == NULL) { /* this is already a TLD */
            escape(tmp, tmp2);
        } else {
            escape(tmp, tmp3);
        }
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        *bufptr = '\t';
        bufptr++;
        escape(tmp, tmp2);
        strcpy(bufptr, tmp);
        bufptr += strlen(tmp);
        free(tmp3);
        *bufptr = '\r';
        bufptr++;
        packetnum++;
        if (maxpackets > 0 && packetnum >= maxpackets) {
            break;
        }
        if (packetnum % INCREMENT == 0) {
            if (!dry_run) {
                copied = PQputCopyData(conn, buffer, bufptr - buffer);
                if (copied != 1) {
                    fatal
                        ("Cannot put data (look at the PostgreSQL log, an error probably happened before): %s",
                         PQerrorMessage(conn));
                }
                bufptr = buffer;
            }
        }
    }
    freeTldTree(tree);
    if (!dry_run) {
        if (bufptr > buffer) {
            /* Flush the buffer */
            copied = PQputCopyData(conn, buffer, bufptr - buffer);
            free(buffer);
            if (copied != 1) {
                fatal("Cannot put data when flushing the buffer: %s",
                      PQerrorMessage(conn));
            }
        }
        copied = PQputCopyEnd(conn, NULL);
        if (copied != 1) {
            fatal("Cannot end the data stream: %s", PQerrorMessage(conn));
        }
    }
    if (verbose) {
        ct = current_time();
        fprintf(stdout, "%s Done, %lu DNS packets stored%s\n",
                ct, packetnum, (maxpackets > 0
                                            && packetnum >=
                                            maxpackets) ?
                " - interrupted before the end because max packets read" : "");
        free(ct);
    }
    fileend_params[0] = malloc(MAX_INTEGER_WIDTH);
    fileend_params[1] = malloc(MAX_INTEGER_WIDTH);
    sprintf((char *) fileend_params[0], "%lu", inputfile->packetnum);
    sprintf((char *) fileend_params[1], "%lu", inputfile->dnspacketnum);
    fileend_params[2] = malloc(MAX_TIMESTAMP_WIDTH);
    date_firstpacket = *gmtime(&inputfile->firstpacket.tv_sec);
    strftime((char *) fileend_params[2], MAX_TIMESTAMP_WIDTH, ISO_FORMAT,
             &date_firstpacket);
    if (maxpackets == 0) {      /* Otherwise, the timestamp of the last packet is
                                 * not significant */
        fileend_params[3] = malloc(MAX_TIMESTAMP_WIDTH);
        date_lastpacket = *gmtime(&inputfile->lastpacket.tv_sec);
        strftime((char *) fileend_params[3], MAX_TIMESTAMP_WIDTH, ISO_FORMAT,
                 &date_lastpacket);
    } else {
        fileend_params[3] = NULL;
    }
    fileend_params[4] = malloc(MAX_INTEGER_WIDTH);
    sprintf((char *) fileend_params[4], "%i", file_id);
    if (!dry_run) {
        PQclear(result);
        result =
            PQexecPrepared(conn, PREPARED_FILEEND_STMT, NUM_FILEEND_PARAMS,
                           fileend_params, NULL, NULL, 0);
        if (PQresultStatus(result) == PGRES_COMMAND_OK) {
            /* OK */
        } else {
            fatal("Result for '%s' with \"%s\" is %s", SQL_FILEEND_COMMAND,
                  fileend_params[2], PQresultErrorMessage(result));
        }
    }
    /* Finalise the session */
    pcap_file_close(inputfile);
    if (!dry_run) {
        PQclear(result);
        result = PQexec(conn, "COMMIT;");
        if (PQresultStatus(result) != PGRES_COMMAND_OK) {
            fatal("Cannot commit transaction");
        }
        PQclear(result);

        tmp = str_replace(SQL_CREATE_CONSTRAINT_UNIQUE_ID, "TABLE_NAME", table_name);
        result = PQexec(conn, tmp);
        free(tmp);
        if (PQresultStatus(result) != PGRES_COMMAND_OK) {
            fatal("Error while creating the UNIQUE(id) constraint: %s", PQresultErrorMessage(result));
        }
        PQclear(result);

        tmp = str_replace(SQL_CREATE_CONSTRAINT_REF_FILE, "TABLE_NAME", table_name);
        result = PQexec(conn, tmp);
        free(tmp);
        if (PQresultStatus(result) != PGRES_COMMAND_OK) {
            fatal("Error while creating the foreign key (file) constraint: %s", PQresultErrorMessage(result));
        }
        PQclear(result);

        tmp = str_replace(SQL_CREATE_INDEXES_COMMAND, "TABLE_NAME", table_name);
        result = PQexec(conn, tmp);
        free(tmp);
        if (PQresultStatus(result) != PGRES_COMMAND_OK) {
            fatal("Error while creating indexes: %s", PQresultErrorMessage(result));
        }
        PQclear(result);
        PQfinish(conn);
    }
    return (0);
}

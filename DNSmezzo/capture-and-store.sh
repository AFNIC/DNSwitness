#!/bin/sh 

# Script which can be run on a name server (or a machine sniffing the
# name server's traffic, for instance with Ethernet port mirroring) to
# collect data and to send them to a DNSmezzo collector.

set -e

# Can be overriden from an env. variable
INTERFACE=${MEZZO_INTERFACE:-eth0}
GROUP=adm
# 20 => 1/20, so 5 %
SAMPLING=${SAMPLING:-20}
MEZZO_DIR=${MEZZO_DIR:-/var/tmp/mezzo}
PKT2PSQK_USER=${PKT2PSQK_USER:-dnsmezzo}
HOST=${MEZZO_HOST:-unknownhost}
DURATION=${DURATION:-43200}
CONNINFO="${CONNINFO:-dbname=dnsmezzo}"
SSH_USER=${MEZZO_SSH_USER:-dnsmezzo}
SSH_HOST=${MEZZO_SSH_HOST:-mezzo.invalid}
SSH_DIR=${MEZZO_SSH_DIR:-/tmp}
SSH_IDENTITY_FILE=${MEZZO_SSH_IDENTITY_FILENAME:-/does/not/exist}
MEZZO_USE_SSH=${MEZZO_USE_SSH:-no}

FILE_TMPL=${MEZZO_DIR}/mezzo-${HOST}-dns-SAMPLING-${SAMPLING}.%Y-%m-%d.%H:%M.pcap
FILENAME=$(date -u +${FILE_TMPL})
FILTER="port 53"
PCAPDUMP_OPTS="-s 256 -m 0640 -t 999999 -u ${USER} -g ${GROUP} -T ${DURATION} -i ${INTERFACE} -S ${SAMPLING} -R -w ${FILENAME}"
PCAPDUMP_USER=root
PKTS2PSQL_OPTS="-v -p"

sudo -u ${PCAPDUMP_USER} pcapdump -f "${FILTER}" ${PCAPDUMP_OPTS}

if [ -z "${MEZZO_USE_SSH}" ] || [ "${MEZZO_USE_SSH}" = "no" ]; then
    sudo -u ${PKT2PSQK_USER} \
	packets2postgresql ${PKTS2PSQL_OPTS} -c "${CONNINFO}" ${FILENAME}
else
    sudo -u ${PCAPDUMP_USER} scp -i ${SSH_IDENTITY_FILE} ${FILENAME} ${SSH_USER}@${SSH_HOST}:${SSH_DIR}
    sudo -u ${PCAPDUMP_USER} ssh -i ${SSH_IDENTITY_FILE} ${SSH_USER}@${SSH_HOST} \
	/usr/local/sbin/packets2postgresql "${PKTS2PSQL_OPTS} -c '${CONNINFO}' ${SSH_DIR}/$(basename ${FILENAME})"
    sudo -u ${PCAPDUMP_USER} ssh -i ${SSH_IDENTITY_FILE} ${SSH_USER}@${SSH_HOST} rm -f ${SSH_DIR}/$(basename ${FILENAME})
fi

rm -f ${FILENAME}
#!/bin/sh 

# Script for storing pcap_files found in a directory 

set -e

PKTS2PSQL=/usr/local/sbin/packets2postgresql
PKTS2PSQL_OPTS="-v -p"
CONNINFO="host=db.generic-nic.net user=dnsmezzo dbname=dnsmezzo sslmode=require"


if [ -n "$1" ] && [ -d "$1" ]
then
	DIRECTORY=$1
else  
	echo "Directory to parse must be given"
	exit -1
fi  

echo storing files from directory $DIRECTORY

for file in $DIRECTORY/*
do
	echo "   => storing $file ...";
	$PKTS2PSQL ${PKTS2PSQL_OPTS} -c "${CONNINFO}" $file
	sleep 30
done


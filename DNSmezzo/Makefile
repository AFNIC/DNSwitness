# http://stackoverflow.com/questions/154630/recommended-gcc-warning-options-for-c
# http://gcc.gnu.org/onlinedocs/gcc-4.3.2/gcc/Warning-Options.html

REG_DOM_LIB_PATH=dkim-regdom
# pcap files are often large so we use stat64
CFLAGS= -Wall -Wextra -g -O0 -I$(shell pg_config --includedir) -I${REG_DOM_LIB_PATH} -D_FILE_OFFSET_BITS=64
LDFLAGS=-lpcap -lpq -L$(shell pg_config --libdir)
# On UltraSparc and probably on Alpha, add -DPICKY_WITH_ALIGNMENT

BASE_NAME=DNSmezzo
TARBALL=/tmp/${BASE_NAME}.tar
GZIP=gzip --best --force --verbose
RM=rm -f
MV=mv -f
INSTALL=install
INSTALLDIR=/usr/local/sbin

all: packets2postgresql test1

%.o: %.c packet-defs.h packet-headers.h
	${CC} ${CFLAGS} -c $<

regdomlib:
	${MAKE} -C ${REG_DOM_LIB_PATH}

test1: test1.o pcap-parse.o
	${CC} ${LDFLAGS} -o $@ $^

packets2postgresql: packets2postgresql.o pcap-parse.o regdomlib
	${CC} ${LDFLAGS} -o $@ packets2postgresql.o pcap-parse.o ${REG_DOM_LIB_PATH}/dkim-regdom.o

dnstypes: dns-parameters.sql

dns-parameters.sql: dns-parameters
	./dnsparameters2sql.py > $@ || rm -f $@

dns-parameters:
	wget -O $@ http://www.iana.org/assignments/dns-parameters

dist: clean
	(cd domain-name-type; ${MAKE} clean)
	(cd ..; tar --create --exclude=.svn --exclude=*.pcap --exclude=*~ --exclude=store-dbms --exclude=Kiminsky --exclude=nxdomain --exclude=*.out --exclude=*.log --verbose --file ${TARBALL} ${BASE_NAME})	
	${GZIP} ${TARBALL}

install: all
	${INSTALL} packets2postgresql capture-and-store.sh ${INSTALLDIR}

clean: clean-reg-dom-lib
	${RM} *.o test1 packets2postgresql *~

clean-reg-dom-lib:
	${MAKE} -C ${REG_DOM_LIB_PATH} clean


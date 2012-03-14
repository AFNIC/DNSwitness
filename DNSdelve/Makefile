BASE_NAME=DNSdelve
TARBALL=/tmp/${BASE_NAME}.tar
GZIP=gzip --best --force --verbose
RM=rm -f
MV=mv -f

.SUFFIXES: .1 .pod

default:
	@echo "Use setup.py"
	exit 1

all:
	@echo "Use setup.py"
	exit 1

man: dnsdelve.1

.pod.1:
	pod2man $< > $@.tmp || (${RM} $@.tmp && false)
	${MV} $@.tmp $@

dist: clean
	(cd ..; tar --create --exclude=.svn --exclude=*~ --exclude=RIPE-Dubai --exclude=*.db --verbose --file ${TARBALL} ${BASE_NAME})
	${GZIP} ${TARBALL}

clean:
	${RM} dnsdelve.1 *~ *.pyc

# $Id: Makefile 8433 2009-04-14 12:29:16Z bortzmeyer $


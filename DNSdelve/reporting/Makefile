STYLESHEET=page.xslt

all: index.html ipv6 dnssec spf redirections
# TODO: wildcards

ipv6: 	
	if [ ! -e ipv6-DATABASE ]; then touch ipv6-DATABASE; fi
	${MAKE} ipv6.html

ipv6.dat: ipv6-DATABASE plot-v6.py
	python plot-v6.py > $@

ipv6.svg: ipv6.dat ipv6-svg.gp
	gnuplot ipv6-svg.gp > $@

ipv6.png: ipv6.dat ipv6.gp
	gnuplot ipv6.gp > $@

ipv6.html: ipv6-DATABASE ipv6-page.py ipv6.svg ipv6.png ipv6.tmpl.xhtml
	python ipv6-page.py

dnssec: 	
	if [ ! -e dnssec-DATABASE ]; then touch dnssec-DATABASE; fi
	${MAKE} dnssec.html

dnssec.dat: dnssec-DATABASE plot-dnssec.py
	python plot-dnssec.py > $@

dnssec.svg: dnssec.dat dnssec-svg.gp
	gnuplot dnssec-svg.gp > $@

dnssec.png: dnssec.dat dnssec.gp
	gnuplot dnssec.gp > $@

dnssec.html: dnssec-DATABASE dnssec-page.py dnssec.svg dnssec.png dnssec.tmpl.xhtml
	python dnssec-page.py

spf: 	
	if [ ! -e spf-DATABASE ]; then touch spf-DATABASE; fi
	${MAKE} spf.html

spf.dat: spf-DATABASE plot-spf.py
	python plot-spf.py > $@

spf.svg: spf.dat spf-svg.gp
	gnuplot spf-svg.gp > $@

spf.png: spf.dat spf.gp
	gnuplot spf.gp > $@

spf.html: spf-DATABASE spf-page.py spf.svg spf.png spf.tmpl.xhtml
	python spf-page.py

redirections:
	if [ ! -e redirections-DATABASE ]; then touch redirections-DATABASE; fi
	${MAKE} redirections.html

redirections.dat: redirections-DATABASE plot-redirections.py
	python plot-redirections.py > $@

redirections.svg: redirections.dat redirections-svg.gp
	gnuplot redirections-svg.gp > $@

redirections.png: redirections.dat redirections.gp
	gnuplot redirections.gp > $@

redirections.html: redirections-DATABASE redirections-page.py redirections.svg redirections.png redirections.tmpl.xhtml
	python redirections-page.py

%.html: %.xml ${STYLESHEET} 
	xsltproc  \
		--output $@ ${STYLESHEET} $< && xmllint --noout --valid $@

install: all
	cp -a -p *.html *.png *.svg /var/www/results.dnsdelve.net/
	
clean:
	rm -f *.png *.svg *.html *.dat *~ *DATABASE


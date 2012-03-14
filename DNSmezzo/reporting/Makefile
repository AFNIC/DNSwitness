STYLESHEET=page.xslt

all: index.html ipv6 nxdomain top100 qtypes updates respsize

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

qtypes:
	if [ ! -e qtypes-DATABASE ]; then touch qtypes-DATABASE; fi
	${MAKE} qtypes.html

qtypes.dat: qtypes-DATABASE plot-qtypes.py
	python plot-qtypes.py > $@

qtypes.svg: qtypes.dat qtypes-svg.gp
	gnuplot qtypes-svg.gp > $@

qtypes.png: qtypes.dat qtypes.gp
	gnuplot qtypes.gp > $@

qtypes.html: qtypes-DATABASE qtypes-page.py qtypes.svg qtypes.png qtypes.tmpl.xhtml
	python qtypes-page.py

nxdomain: 	
	if [ ! -e nxdomain-DATABASE ]; then touch nxdomain-DATABASE; fi
	${MAKE} nxdomain.html

nxdomain.html: nxdomain-DATABASE nxdomain.tmpl.xhtml
	python nxdomain-page.py

top100:
	if [ ! -e top100-DATABASE ]; then touch top100-DATABASE; fi
	${MAKE} top100.html

top100.html: top100-DATABASE top100.tmpl.xhtml
	python top100-page.py

updates:
	if [ ! -e updates-DATABASE ]; then touch updates-DATABASE; fi
	${MAKE} updates.html

updates.dat: updates-DATABASE plot-updates.py
	python plot-updates.py > $@

updates.svg: updates.dat updates-svg.gp
	gnuplot updates-svg.gp > $@

updates.png: updates.dat updates.gp
	gnuplot updates.gp > $@

updates.html: updates-DATABASE updates-page.py updates.svg updates.png updates.tmpl.xhtml
	python updates-page.py

respsize:
	if [ ! -e respsize-DATABASE ]; then touch respsize-DATABASE; fi
	${MAKE} respsize.html

respsize.dat: respsize-DATABASE plot-respsize.py
	python plot-respsize.py > $@

respsize.svg: respsize.dat respsize-svg.gp
	gnuplot respsize-svg.gp > $@

respsize.png: respsize.dat respsize.gp
	gnuplot respsize.gp > $@

respsize.html: respsize-DATABASE respsize-page.py respsize.svg respsize.png respsize.tmpl.xhtml
	python respsize-page.py

%.html: %.xml ${STYLESHEET} 
	xsltproc  \
		--output $@ ${STYLESHEET} $< && xmllint --noout --valid $@

install: all
	cp -a -p *.html *.png *.svg /var/www/results.dnsmezzo.net/
	
clean:
	rm -f *.png *.svg *.html *.dat *~ *DATABASE


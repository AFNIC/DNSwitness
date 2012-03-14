set terminal png
set xdata time
set timefmt "%d/%m/%Y"
set format x "%m/%y"
set xtics nomirror rotate by -45 scale 0
set xlabel "Run date"
set ylabel "Number of DNSSEC domains per million"
set title "DNSSEC in .FR domains"
set style line 1 linewidth 100
plot "dnssec.dat" using 1:2:3 title "DNSKEY" with yerrorlines, "dnssec.dat" using 1:4:5 title "Signed" with yerrorlines

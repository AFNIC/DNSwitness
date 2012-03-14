set terminal png
set xdata time
set timefmt "%d/%m/%Y"
set format x "%m/%y"
set xtics nomirror rotate by -45 scale 0
set xlabel "Run date"
set yrange [0:]
set ylabel "Percentage of SPF records (RFC 4408) in .FR domains"
set title "SPF in .FR domains"
set style line 1 linewidth 100
plot "spf.dat" using 1:2:3 title "SPF" with yerrorlines

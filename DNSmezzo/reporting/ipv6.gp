set terminal png
set xdata time
set timefmt "%d/%m/%Y"
set format x "%m/%y"
set xlabel "Run date"
set ylabel "%age of v6 queries"
set yrange [0:]
set key off
set title "IPv6 in .FR DNS requests"
set style line 1 linewidth 100
plot "ipv6.dat" using 1:3 title "v6" with lines

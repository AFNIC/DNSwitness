set terminal png
set xdata time
set timefmt "%d/%m/%Y"
set format x "%m/%y"
set xtics nomirror rotate by -45 scale 0
set xlabel "Run date"
set ylabel "%age of v6 domains"
set yrange [0:]
set title "IPv6 in .FR domains"
set key left top
set style line 1 linewidth 100
plot "ipv6.dat" using 1:2:3 title "v6-enabled" with yerrorlines, "ipv6.dat" using 1:4:5 title "v6-full" with yerrorlines, "ipv6.dat" using 1:6:7 title "v6-web" with yerrorlines, "ipv6.dat" using 1:8:9 title "v6-email" with yerrorlines, "ipv6.dat" using 1:10:11 title "v6-dns" with yerrorlines

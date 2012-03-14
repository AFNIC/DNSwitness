set terminal svg
set object 1 rect from screen 0, 0, 0 to screen 1, 1, 0 behind
set object 1 rect fc  rgb "white"  fillstyle solid 1.0
set xdata time
set timefmt "%d/%m/%Y"
set format x "%m/%y"
set xlabel "Run date"
set ylabel "%age of query types"
set yrange [0:]
set key on
set title "QTYPE in .FR DNS requests"
set style line 1 linewidth 100
plot "qtypes.dat" using 1:2 title "A" with lines, "qtypes.dat" using 1:3 title "NS" with lines, "qtypes.dat" using 1:4 title "MX" with lines, "qtypes.dat" using 1:5 title "AAAA" with lines, "qtypes.dat" using 1:6 title "Others" with lines

set terminal png
set xdata time
set timefmt "%d/%m/%Y"
set format x "%m/%y"
set xlabel "Run date"
set ylabel "%age of dynamic updates"
set yrange [0:]
set key off
set title "Dynamic Updates in .FR DNS requests"
set style line 1 linewidth 100
plot "updates.dat" using 1:2 title "DU" with lines

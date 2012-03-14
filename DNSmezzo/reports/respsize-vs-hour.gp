set terminal png
set xdata time
set timefmt "%H:%M:%S"
set format x "%H:%M"
set xlabel "Time in UTC"
set ylabel "Average length of replies in bytes"
set yrange [0:]
set key off
set title "Length of data after .FR was signed"
set style line 1 linewidth 100
plot "respsize-vs-hour.dat" using 1:2 title "length" with lines

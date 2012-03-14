# http://confuseddevelopment.blogspot.com/2009/01/creating-bar-charts-with-gnuplot.html
# http://gnuplot.sourceforge.net/demo/histograms.html

set terminal svg
set object 1 rect from screen 0, 0, 0 to screen 1, 1, 0 behind
set object 1 rect fc  rgb "white"  fillstyle solid 1.0
set key invert reverse Left outside
set border 3
set style data histogram
set style histogram rowstacked
set style fill solid 0.5
set xtics nomirror rotate by -45 scale 0
set xlabel "Run date"
set ylabel "%age of responses"
set yrange [0:1]
unset ytics
set title "Total packet size (in bytes) in .FR DNS responses"
plot "respsize.dat" using 2:xtic(1) title "0-127", "" using 3 title "128-255", "" using 4 title "256-511", "" using 5 title "512-1023", "" using 6 title "1023-2055","" using 7 title "2048-infinite"




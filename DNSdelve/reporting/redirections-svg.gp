set terminal svg
set object 1 rect from screen 0, 0, 0 to screen 1, 1, 0 behind
set object 1 rect fc  rgb "white"  fillstyle solid 1.0
set xdata time
set timefmt "%d/%m/%Y"
set format x "%m/%y"
set xlabel "Run date"
set ylabel "%age of redirections"
set yrange [0:]
set key outside
set title "Destination of redirected domains in .FR (HTTP)"
set style line 1 linewidth 100
plot "redirections.dat" using 1:2 title ".net" with lines, "redirections.dat" using 1:3 title ".com" with lines, "redirections.dat" using 1:4 title ".fr" with lines, "redirections.dat" using 1:5 title ".org" with lines, "redirections.dat" using 1:6 title ".eu" with lines, "redirections.dat" using 1:7 title ".de" with lines, "redirections.dat" using 1:8 title ".info" with lines, "redirections.dat" using 1:9 title ".be" with lines, "redirections.dat" using 1:10 title "Others" with lines

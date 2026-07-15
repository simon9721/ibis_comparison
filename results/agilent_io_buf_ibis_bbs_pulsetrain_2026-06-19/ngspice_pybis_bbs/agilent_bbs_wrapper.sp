* Local ngspice wrapper for BBS General SPICE output
.include 'Agilent_E5071B_GSPICE.txt'
.subckt s_equivalent p1 p2 p3 p4
Xbbs p1 p2 p3 p4 0 Agilent_E5071B_GSPICE
.ends s_equivalent

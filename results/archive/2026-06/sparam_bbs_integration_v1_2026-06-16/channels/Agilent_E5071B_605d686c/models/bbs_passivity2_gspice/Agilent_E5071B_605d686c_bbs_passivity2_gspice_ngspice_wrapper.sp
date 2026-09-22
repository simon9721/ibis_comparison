* ngspice wrapper for BroadbandSPICE General SPICE output
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_bbs_integration_v1_2026-06-16/channels/Agilent_E5071B_605d686c/bbs/passivity2/gspice/BBSResult_Agilent_E5071B/Agilent_E5071B_GSPICE.txt'
.subckt s_equivalent p1 p2 p3 p4
Xbbs p1 p2 p3 p4 0 Agilent_E5071B_GSPICE
.ends s_equivalent

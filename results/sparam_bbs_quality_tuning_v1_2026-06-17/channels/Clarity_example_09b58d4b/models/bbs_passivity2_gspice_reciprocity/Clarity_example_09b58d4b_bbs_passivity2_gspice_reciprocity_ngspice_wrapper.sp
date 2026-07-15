* ngspice wrapper for BroadbandSPICE General SPICE output
.include 'C:/Users/sh3qm/code/ibis_comparison/results/sparam_bbs_quality_tuning_v1_2026-06-17/channels/Clarity_example_09b58d4b/bbs/reciprocity/passivity2/gspice/BBSResult_Clarity_example/Clarity_example_GSPICE.txt'
.subckt s_equivalent p1 p2
Xbbs p1 p2 0 Clarity_example_GSPICE
.ends s_equivalent

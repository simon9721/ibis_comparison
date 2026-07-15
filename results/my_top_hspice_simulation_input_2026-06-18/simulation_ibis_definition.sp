
.subckt Tx_ABC_Serdes
+ 6     7     1     10

X_SpeedXP_auto_Tx_ABC_Serdes
+ 6     7     1     10
+ SpeedXP_auto_Tx_ABC_Serdes

.ends


.subckt SpeedXP_auto_Tx_ABC_Serdes
+ nd_out_6     nd_out_7     nd_out_1     nd_out_10

* .connect gndbus1 nd_out_10

.subckt stimulusout1p
+ 1 2
v1 1 2
+ PWL(
+ 0.0000000000e+00	0
+ 1.0000000000e-13	1
+ 4.0000000000e-10	1
+ 4.0010000000e-10	0
+ 8.0000000000e-10	0
+ 8.0010000000e-10	0
+ )
.ends

.subckt stimulusout1n
+ 1 2
v1 1 2
+ PWL(
+ 0.0000000000e+00	1
+ 1.0000000000e-13	0
+ 4.0000000000e-10	0
+ 4.0010000000e-10	1
+ 8.0000000000e-10	1
+ 8.0010000000e-10	1
+ )
.ends

B_SpeedXP_auto_6    pwrbus1_6    nd_out_10    nd_out_6    nd_in_6    pwrbus1_6    nd_out_10
+    file = 'C:\Program Files\Cadence\SPB_24.1\share\topxp\SerialLink\ibis_sparam_thru\scd_example.ibs'
+    model = 'sla_out'
+    Typ = typ
+    power = off
+    buffer = output
+    ramp_fwf = 0
+    ramp_rwf = 0
V_SpeedXP_auto_pwrbus1_6    pwrbus1_6    nd_out_10    1
X_SpeedXP_auto_6_St     nd_in_6    0    stimulusout1p

B_SpeedXP_auto_7    pwrbus1_7    nd_out_10    nd_out_7    nd_in_7    pwrbus1_7    nd_out_10
+    file = 'C:\Program Files\Cadence\SPB_24.1\share\topxp\SerialLink\ibis_sparam_thru\scd_example.ibs'
+    model = 'sla_out'
+    Typ = typ
+    power = off
+    buffer = output
+    ramp_fwf = 0
+    ramp_rwf = 0
V_SpeedXP_auto_pwrbus1_7    pwrbus1_7    nd_out_10    1
X_SpeedXP_auto_7_St     nd_in_7    0    stimulusout1n

.ends



.subckt Tx_ABC_Serdes_Test_Fixture
+ in_6     in_7     in_1     in_10


** Signals
* For 6
r_6 in_6 out_6 50
v_6 out_6 in_10 0.9

* For 7
r_7 in_7 out_7 50
v_7 out_7 in_10 0.9

** Powers
* For 1

** Grounds
* For 10

** For differential Pins
.ends Tx_ABC_Serdes_Test_Fixture



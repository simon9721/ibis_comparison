.subckt Tx_ABC_Serdes
+ 6     7     1     10     in

* generate stimulus for negative
einn inn 10 volt='1-v(in, 10)'

X_speedXP_auto_Tx_ABC_Serdes
+ in     inn     6     7     1     10
+ SpeedXP_auto_Tx_ABC_Serdes

.ends Tx_ABC_Serdes

.subckt SpeedXP_auto_Tx_ABC_Serdes
+ nd_in_6     nd_in_7     nd_out_6     nd_out_7     nd_out_1     nd_out_10


B_SpeedXP_auto_6    pwrbus1_6    nd_out_10    nd_out_6    nd_in_6    pwrbus1_6    nd_out_10
+    file = 'C:\Program Files\Cadence\SPB_24.1\share\topxp\SerialLink\ibis_sparam_thru\scd_example.ibs'
+    model = 'sla_out'
+    Typ = typ
+    power = off
+    buffer = output
+    ramp_fwf = 0
+    ramp_rwf = 0
V_SpeedXP_auto_pwrbus1_6    pwrbus1_6    nd_out_10    1

B_SpeedXP_auto_7    pwrbus1_7    nd_out_10    nd_out_7    nd_in_7    pwrbus1_7    nd_out_10
+    file = 'C:\Program Files\Cadence\SPB_24.1\share\topxp\SerialLink\ibis_sparam_thru\scd_example.ibs'
+    model = 'sla_out'
+    Typ = typ
+    power = off
+    buffer = output
+    ramp_fwf = 0
+    ramp_rwf = 0
V_SpeedXP_auto_pwrbus1_7    pwrbus1_7    nd_out_10    1

.ends SpeedXP_auto_Tx_ABC_Serdes

.subckt Rx_ABC_Serdes
+ 8     9     1     10     rxnode

X_speedXP_auto_Rx_ABC_Serdes
+ 8     9     1     10
+ SpeedXP_auto_Rx_ABC_Serdes

erxnode rxnode 10 volt='v(8, 9)'

.ends Rx_ABC_Serdes

.subckt SpeedXP_auto_Rx_ABC_Serdes
+ nd_in_8     nd_in_9     nd_out_1     nd_out_10


B_SpeedXP_auto_8    pwrbus1_8    nd_out_10    nd_in_8    nd_out_of_in_8
+    file = 'C:\Program Files\Cadence\SPB_24.1\share\topxp\SerialLink\ibis_sparam_thru\scd_example.ibs'
+    model = 'sla_in'
+    Typ = typ
+    power = off
+    buffer = input
+    ramp_fwf = 2
+    ramp_rwf = 2
V_SpeedXP_auto_pwrbus1_8    pwrbus1_8    nd_out_10    1

B_SpeedXP_auto_9    pwrbus1_9    nd_out_10    nd_in_9    nd_out_of_in_9
+    file = 'C:\Program Files\Cadence\SPB_24.1\share\topxp\SerialLink\ibis_sparam_thru\scd_example.ibs'
+    model = 'sla_in'
+    Typ = typ
+    power = off
+    buffer = input
+    ramp_fwf = 2
+    ramp_rwf = 2
V_SpeedXP_auto_pwrbus1_9    pwrbus1_9    nd_out_10    1

.ends SpeedXP_auto_Rx_ABC_Serdes

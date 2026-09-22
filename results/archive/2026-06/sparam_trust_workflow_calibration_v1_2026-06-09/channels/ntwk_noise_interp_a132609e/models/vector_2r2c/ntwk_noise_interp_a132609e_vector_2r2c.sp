* EQUIVALENT CIRCUIT FOR VECTOR FITTED S-MATRIX
* Created using scikit-rf vectorFitting.py
*
.SUBCKT s_equivalent p1 p2
*
* Port network for port 1
V1 p1 s1 0
R1 s1 0 50.0
Gr1_1_1 0 s1 x1_a1 0 0.0
Gr2_re_1_1 0 s1 x2_re_a1 0 0.0
Gr2_im_1_1 0 s1 x2_im_a1 0 0.0
Gr3_1_1 0 s1 x3_a1 0 0.0
Gr4_re_1_1 0 s1 x4_re_a1 0 0.0
Gr4_im_1_1 0 s1 x4_im_a1 0 0.0
Gr1_1_2 0 s1 x1_a2 0 0.0
Gr2_re_1_2 0 s1 x2_re_a2 0 0.0
Gr2_im_1_2 0 s1 x2_im_a2 0 0.0
Gr3_1_2 0 s1 x3_a2 0 0.0
Gr4_re_1_2 0 s1 x4_re_a2 0 0.0
Gr4_im_1_2 0 s1 x4_im_a2 0 0.0
*
* State networks driven by port 1
Cx1_a1 x1_a1 0 1.0
Gx1_a1 0 x1_a1 p1 0 0.07071067811865475
Fx1_a1 0 x1_a1 V1 3.5355339059327378
Rp1_a1 0 x1_a1 9.923104888406947e-13
Cx2_re_a1 x2_re_a1 0 1.0
Gx2_re_a1 0 x2_re_a1 p1 0 0.1414213562373095
Fx2_re_a1 0 x2_re_a1 V1 7.0710678118654755
Rp2_re_re_a1 0 x2_re_a1 1.2175774847321923e-11
Gp2_re_im_a1 0 x2_re_a1 x2_im_a1 0 65555245601.39183
Cx2_im_a1 x2_im_a1 0 1.0
Gp2_im_re_a1 0 x2_im_a1 x2_re_a1 0 -65555245601.39183
Rp2_im_im_a1 0 x2_im_a1 1.2175774847321923e-11
Cx3_a1 x3_a1 0 1.0
Gx3_a1 0 x3_a1 p1 0 0.07071067811865475
Fx3_a1 0 x3_a1 V1 3.5355339059327378
Rp3_a1 0 x3_a1 6.44689976067757e-11
Cx4_re_a1 x4_re_a1 0 1.0
Gx4_re_a1 0 x4_re_a1 p1 0 0.1414213562373095
Fx4_re_a1 0 x4_re_a1 V1 7.0710678118654755
Rp4_re_re_a1 0 x4_re_a1 3.379538158365934e-09
Gp4_re_im_a1 0 x4_re_a1 x4_im_a1 0 294646398.4103971
Cx4_im_a1 x4_im_a1 0 1.0
Gp4_im_re_a1 0 x4_im_a1 x4_re_a1 0 -294646398.4103971
Rp4_im_im_a1 0 x4_im_a1 3.379538158365934e-09
*
* Port network for port 2
V2 p2 s2 0
R2 s2 0 50.0
Gd2_1 0 s2 p1 0 0.20000000000000004
Fd2_1 0 s2 V1 10.000000000000002
Gr1_2_1 0 s2 x1_a1 0 -0.0027144678809163316
Gr2_re_2_1 0 s2 x2_re_a1 0 0.0002959193490006989
Gr2_im_2_1 0 s2 x2_im_a1 0 5.336060896833716e-05
Gr3_2_1 0 s2 x3_a1 0 -1.1628693209470132e-05
Gr4_re_2_1 0 s2 x4_re_a1 0 2.8535047608424624e-07
Gr4_im_2_1 0 s2 x4_im_a1 0 2.072600845497109e-06
Gr1_2_2 0 s2 x1_a2 0 0.0
Gr2_re_2_2 0 s2 x2_re_a2 0 0.0
Gr2_im_2_2 0 s2 x2_im_a2 0 0.0
Gr3_2_2 0 s2 x3_a2 0 0.0
Gr4_re_2_2 0 s2 x4_re_a2 0 0.0
Gr4_im_2_2 0 s2 x4_im_a2 0 0.0
*
* State networks driven by port 2
Cx1_a2 x1_a2 0 1.0
Gx1_a2 0 x1_a2 p2 0 0.07071067811865475
Fx1_a2 0 x1_a2 V2 3.5355339059327378
Rp1_a2 0 x1_a2 9.923104888406947e-13
Cx2_re_a2 x2_re_a2 0 1.0
Gx2_re_a2 0 x2_re_a2 p2 0 0.1414213562373095
Fx2_re_a2 0 x2_re_a2 V2 7.0710678118654755
Rp2_re_re_a2 0 x2_re_a2 1.2175774847321923e-11
Gp2_re_im_a2 0 x2_re_a2 x2_im_a2 0 65555245601.39183
Cx2_im_a2 x2_im_a2 0 1.0
Gp2_im_re_a2 0 x2_im_a2 x2_re_a2 0 -65555245601.39183
Rp2_im_im_a2 0 x2_im_a2 1.2175774847321923e-11
Cx3_a2 x3_a2 0 1.0
Gx3_a2 0 x3_a2 p2 0 0.07071067811865475
Fx3_a2 0 x3_a2 V2 3.5355339059327378
Rp3_a2 0 x3_a2 6.44689976067757e-11
Cx4_re_a2 x4_re_a2 0 1.0
Gx4_re_a2 0 x4_re_a2 p2 0 0.1414213562373095
Fx4_re_a2 0 x4_re_a2 V2 7.0710678118654755
Rp4_re_re_a2 0 x4_re_a2 3.379538158365934e-09
Gp4_re_im_a2 0 x4_re_a2 x4_im_a2 0 294646398.4103971
Cx4_im_a2 x4_im_a2 0 1.0
Gp4_im_re_a2 0 x4_im_a2 x4_re_a2 0 -294646398.4103971
Rp4_im_im_a2 0 x4_im_a2 3.379538158365934e-09
.ENDS s_equivalent

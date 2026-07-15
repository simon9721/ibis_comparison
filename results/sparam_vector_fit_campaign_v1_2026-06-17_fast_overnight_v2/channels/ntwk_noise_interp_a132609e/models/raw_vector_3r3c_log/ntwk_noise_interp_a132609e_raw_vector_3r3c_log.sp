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
Gr4_1_1 0 s1 x4_a1 0 0.0
Gr5_re_1_1 0 s1 x5_re_a1 0 0.0
Gr5_im_1_1 0 s1 x5_im_a1 0 0.0
Gr6_re_1_1 0 s1 x6_re_a1 0 0.0
Gr6_im_1_1 0 s1 x6_im_a1 0 0.0
Gr1_1_2 0 s1 x1_a2 0 0.0
Gr2_re_1_2 0 s1 x2_re_a2 0 0.0
Gr2_im_1_2 0 s1 x2_im_a2 0 0.0
Gr3_1_2 0 s1 x3_a2 0 0.0
Gr4_1_2 0 s1 x4_a2 0 0.0
Gr5_re_1_2 0 s1 x5_re_a2 0 0.0
Gr5_im_1_2 0 s1 x5_im_a2 0 0.0
Gr6_re_1_2 0 s1 x6_re_a2 0 0.0
Gr6_im_1_2 0 s1 x6_im_a2 0 0.0
*
* State networks driven by port 1
Cx1_a1 x1_a1 0 1.0
Gx1_a1 0 x1_a1 p1 0 0.07071067811865475
Fx1_a1 0 x1_a1 V1 3.5355339059327378
Rp1_a1 0 x1_a1 9.038845878176492e-13
Cx2_re_a1 x2_re_a1 0 1.0
Gx2_re_a1 0 x2_re_a1 p1 0 0.1414213562373095
Fx2_re_a1 0 x2_re_a1 V1 7.0710678118654755
Rp2_re_re_a1 0 x2_re_a1 1.3023322337666129e-11
Gp2_re_im_a1 0 x2_re_a1 x2_im_a1 0 48335152653.56173
Cx2_im_a1 x2_im_a1 0 1.0
Gp2_im_re_a1 0 x2_im_a1 x2_re_a1 0 -48335152653.56173
Rp2_im_im_a1 0 x2_im_a1 1.3023322337666129e-11
Cx3_a1 x3_a1 0 1.0
Gx3_a1 0 x3_a1 p1 0 0.07071067811865475
Fx3_a1 0 x3_a1 V1 3.5355339059327378
Rp3_a1 0 x3_a1 2.0704962059645947e-11
Cx4_a1 x4_a1 0 1.0
Gx4_a1 0 x4_a1 p1 0 0.07071067811865475
Fx4_a1 0 x4_a1 V1 3.5355339059327378
Rp4_a1 0 x4_a1 7.703808360855079e-11
Cx5_re_a1 x5_re_a1 0 1.0
Gx5_re_a1 0 x5_re_a1 p1 0 0.1414213562373095
Fx5_re_a1 0 x5_re_a1 V1 7.0710678118654755
Rp5_re_re_a1 0 x5_re_a1 4.911735143712536e-10
Gp5_re_im_a1 0 x5_re_a1 x5_im_a1 0 1793401693.2385662
Cx5_im_a1 x5_im_a1 0 1.0
Gp5_im_re_a1 0 x5_im_a1 x5_re_a1 0 -1793401693.2385662
Rp5_im_im_a1 0 x5_im_a1 4.911735143712536e-10
Cx6_re_a1 x6_re_a1 0 1.0
Gx6_re_a1 0 x6_re_a1 p1 0 0.1414213562373095
Fx6_re_a1 0 x6_re_a1 V1 7.0710678118654755
Rp6_re_re_a1 0 x6_re_a1 4.271610970046247e-09
Gp6_re_im_a1 0 x6_re_a1 x6_im_a1 0 433476926.4781461
Cx6_im_a1 x6_im_a1 0 1.0
Gp6_im_re_a1 0 x6_im_a1 x6_re_a1 0 -433476926.4781461
Rp6_im_im_a1 0 x6_im_a1 4.271610970046247e-09
*
* Port network for port 2
V2 p2 s2 0
R2 s2 0 50.0
Gd2_1 0 s2 p1 0 0.2000000000000003
Fd2_1 0 s2 V1 10.000000000000016
Gr1_2_1 0 s2 x1_a1 0 0.008960509530891968
Gr2_re_2_1 0 s2 x2_re_a1 0 -0.0005064234270408994
Gr2_im_2_1 0 s2 x2_im_a1 0 -0.0015671480809273464
Gr3_2_1 0 s2 x3_a1 0 -0.0010914209529562945
Gr4_2_1 0 s2 x4_a1 0 6.912874680776514e-05
Gr5_re_2_1 0 s2 x5_re_a1 0 -2.3001811015392347e-06
Gr5_im_2_1 0 s2 x5_im_a1 0 -1.2769200199923241e-05
Gr6_re_2_1 0 s2 x6_re_a1 0 -1.1128313440277742e-06
Gr6_im_2_1 0 s2 x6_im_a1 0 -4.437662232756531e-07
Gr1_2_2 0 s2 x1_a2 0 0.0
Gr2_re_2_2 0 s2 x2_re_a2 0 0.0
Gr2_im_2_2 0 s2 x2_im_a2 0 0.0
Gr3_2_2 0 s2 x3_a2 0 0.0
Gr4_2_2 0 s2 x4_a2 0 0.0
Gr5_re_2_2 0 s2 x5_re_a2 0 0.0
Gr5_im_2_2 0 s2 x5_im_a2 0 0.0
Gr6_re_2_2 0 s2 x6_re_a2 0 0.0
Gr6_im_2_2 0 s2 x6_im_a2 0 0.0
*
* State networks driven by port 2
Cx1_a2 x1_a2 0 1.0
Gx1_a2 0 x1_a2 p2 0 0.07071067811865475
Fx1_a2 0 x1_a2 V2 3.5355339059327378
Rp1_a2 0 x1_a2 9.038845878176492e-13
Cx2_re_a2 x2_re_a2 0 1.0
Gx2_re_a2 0 x2_re_a2 p2 0 0.1414213562373095
Fx2_re_a2 0 x2_re_a2 V2 7.0710678118654755
Rp2_re_re_a2 0 x2_re_a2 1.3023322337666129e-11
Gp2_re_im_a2 0 x2_re_a2 x2_im_a2 0 48335152653.56173
Cx2_im_a2 x2_im_a2 0 1.0
Gp2_im_re_a2 0 x2_im_a2 x2_re_a2 0 -48335152653.56173
Rp2_im_im_a2 0 x2_im_a2 1.3023322337666129e-11
Cx3_a2 x3_a2 0 1.0
Gx3_a2 0 x3_a2 p2 0 0.07071067811865475
Fx3_a2 0 x3_a2 V2 3.5355339059327378
Rp3_a2 0 x3_a2 2.0704962059645947e-11
Cx4_a2 x4_a2 0 1.0
Gx4_a2 0 x4_a2 p2 0 0.07071067811865475
Fx4_a2 0 x4_a2 V2 3.5355339059327378
Rp4_a2 0 x4_a2 7.703808360855079e-11
Cx5_re_a2 x5_re_a2 0 1.0
Gx5_re_a2 0 x5_re_a2 p2 0 0.1414213562373095
Fx5_re_a2 0 x5_re_a2 V2 7.0710678118654755
Rp5_re_re_a2 0 x5_re_a2 4.911735143712536e-10
Gp5_re_im_a2 0 x5_re_a2 x5_im_a2 0 1793401693.2385662
Cx5_im_a2 x5_im_a2 0 1.0
Gp5_im_re_a2 0 x5_im_a2 x5_re_a2 0 -1793401693.2385662
Rp5_im_im_a2 0 x5_im_a2 4.911735143712536e-10
Cx6_re_a2 x6_re_a2 0 1.0
Gx6_re_a2 0 x6_re_a2 p2 0 0.1414213562373095
Fx6_re_a2 0 x6_re_a2 V2 7.0710678118654755
Rp6_re_re_a2 0 x6_re_a2 4.271610970046247e-09
Gp6_re_im_a2 0 x6_re_a2 x6_im_a2 0 433476926.4781461
Cx6_im_a2 x6_im_a2 0 1.0
Gp6_im_re_a2 0 x6_im_a2 x6_re_a2 0 -433476926.4781461
Rp6_im_im_a2 0 x6_im_a2 4.271610970046247e-09
.ENDS s_equivalent

* EQUIVALENT CIRCUIT FOR VECTOR FITTED S-MATRIX
* Created using scikit-rf vectorFitting.py
*
.SUBCKT s_equivalent p1 p2
*
* Port network for port 1
V1 p1 s1 0
R1 s1 0 50.0
Gr1_1_1 0 s1 x1_a1 0 0.0
Gr2_1_1 0 s1 x2_a1 0 0.0
Gr3_1_1 0 s1 x3_a1 0 0.0
Gr4_re_1_1 0 s1 x4_re_a1 0 0.0
Gr4_im_1_1 0 s1 x4_im_a1 0 0.0
Gr5_re_1_1 0 s1 x5_re_a1 0 0.0
Gr5_im_1_1 0 s1 x5_im_a1 0 0.0
Gr6_re_1_1 0 s1 x6_re_a1 0 0.0
Gr6_im_1_1 0 s1 x6_im_a1 0 0.0
Gr1_1_2 0 s1 x1_a2 0 0.0
Gr2_1_2 0 s1 x2_a2 0 0.0
Gr3_1_2 0 s1 x3_a2 0 0.0
Gr4_re_1_2 0 s1 x4_re_a2 0 0.0
Gr4_im_1_2 0 s1 x4_im_a2 0 0.0
Gr5_re_1_2 0 s1 x5_re_a2 0 0.0
Gr5_im_1_2 0 s1 x5_im_a2 0 0.0
Gr6_re_1_2 0 s1 x6_re_a2 0 0.0
Gr6_im_1_2 0 s1 x6_im_a2 0 0.0
*
* State networks driven by port 1
Cx1_a1 x1_a1 0 1.0
Gx1_a1 0 x1_a1 p1 0 0.07071067811865475
Fx1_a1 0 x1_a1 V1 3.5355339059327378
Rp1_a1 0 x1_a1 2.468207035822993e-12
Cx2_a1 x2_a1 0 1.0
Gx2_a1 0 x2_a1 p1 0 0.07071067811865475
Fx2_a1 0 x2_a1 V1 3.5355339059327378
Rp2_a1 0 x2_a1 1.986971548294757e-11
Cx3_a1 x3_a1 0 1.0
Gx3_a1 0 x3_a1 p1 0 0.07071067811865475
Fx3_a1 0 x3_a1 V1 3.5355339059327378
Rp3_a1 0 x3_a1 7.011072542887738e-11
Cx4_re_a1 x4_re_a1 0 1.0
Gx4_re_a1 0 x4_re_a1 p1 0 0.1414213562373095
Fx4_re_a1 0 x4_re_a1 V1 7.0710678118654755
Rp4_re_re_a1 0 x4_re_a1 1.4686625051954033e-10
Gp4_re_im_a1 0 x4_re_a1 x4_im_a1 0 12218827584.491585
Cx4_im_a1 x4_im_a1 0 1.0
Gp4_im_re_a1 0 x4_im_a1 x4_re_a1 0 -12218827584.491585
Rp4_im_im_a1 0 x4_im_a1 1.4686625051954033e-10
Cx5_re_a1 x5_re_a1 0 1.0
Gx5_re_a1 0 x5_re_a1 p1 0 0.1414213562373095
Fx5_re_a1 0 x5_re_a1 V1 7.0710678118654755
Rp5_re_re_a1 0 x5_re_a1 8.228071946961779e-10
Gp5_re_im_a1 0 x5_re_a1 x5_im_a1 0 12061089204.497772
Cx5_im_a1 x5_im_a1 0 1.0
Gp5_im_re_a1 0 x5_im_a1 x5_re_a1 0 -12061089204.497772
Rp5_im_im_a1 0 x5_im_a1 8.228071946961779e-10
Cx6_re_a1 x6_re_a1 0 1.0
Gx6_re_a1 0 x6_re_a1 p1 0 0.1414213562373095
Fx6_re_a1 0 x6_re_a1 V1 7.0710678118654755
Rp6_re_re_a1 0 x6_re_a1 5.46297909887745e-10
Gp6_re_im_a1 0 x6_re_a1 x6_im_a1 0 4558622724.893911
Cx6_im_a1 x6_im_a1 0 1.0
Gp6_im_re_a1 0 x6_im_a1 x6_re_a1 0 -4558622724.893911
Rp6_im_im_a1 0 x6_im_a1 5.46297909887745e-10
*
* Port network for port 2
V2 p2 s2 0
R2 s2 0 50.0
Gd2_1 0 s2 p1 0 0.19999999999994775
Fd2_1 0 s2 V1 9.999999999997389
Gr1_2_1 0 s2 x1_a1 0 0.3396017733076441
Gr2_2_1 0 s2 x2_a1 0 -0.0031589927604056167
Gr3_2_1 0 s2 x3_a1 0 -0.000966711164625313
Gr4_re_2_1 0 s2 x4_re_a1 0 -4.81481813783776e-05
Gr4_im_2_1 0 s2 x4_im_a1 0 -0.00014419784623591447
Gr5_re_2_1 0 s2 x5_re_a1 0 1.61988049552795e-07
Gr5_im_2_1 0 s2 x5_im_a1 0 -5.988983692859635e-07
Gr6_re_2_1 0 s2 x6_re_a1 0 2.469837985233211e-05
Gr6_im_2_1 0 s2 x6_im_a1 0 -2.8549512676778035e-06
Gr1_2_2 0 s2 x1_a2 0 0.0
Gr2_2_2 0 s2 x2_a2 0 0.0
Gr3_2_2 0 s2 x3_a2 0 0.0
Gr4_re_2_2 0 s2 x4_re_a2 0 0.0
Gr4_im_2_2 0 s2 x4_im_a2 0 0.0
Gr5_re_2_2 0 s2 x5_re_a2 0 0.0
Gr5_im_2_2 0 s2 x5_im_a2 0 0.0
Gr6_re_2_2 0 s2 x6_re_a2 0 0.0
Gr6_im_2_2 0 s2 x6_im_a2 0 0.0
*
* State networks driven by port 2
Cx1_a2 x1_a2 0 1.0
Gx1_a2 0 x1_a2 p2 0 0.07071067811865475
Fx1_a2 0 x1_a2 V2 3.5355339059327378
Rp1_a2 0 x1_a2 2.468207035822993e-12
Cx2_a2 x2_a2 0 1.0
Gx2_a2 0 x2_a2 p2 0 0.07071067811865475
Fx2_a2 0 x2_a2 V2 3.5355339059327378
Rp2_a2 0 x2_a2 1.986971548294757e-11
Cx3_a2 x3_a2 0 1.0
Gx3_a2 0 x3_a2 p2 0 0.07071067811865475
Fx3_a2 0 x3_a2 V2 3.5355339059327378
Rp3_a2 0 x3_a2 7.011072542887738e-11
Cx4_re_a2 x4_re_a2 0 1.0
Gx4_re_a2 0 x4_re_a2 p2 0 0.1414213562373095
Fx4_re_a2 0 x4_re_a2 V2 7.0710678118654755
Rp4_re_re_a2 0 x4_re_a2 1.4686625051954033e-10
Gp4_re_im_a2 0 x4_re_a2 x4_im_a2 0 12218827584.491585
Cx4_im_a2 x4_im_a2 0 1.0
Gp4_im_re_a2 0 x4_im_a2 x4_re_a2 0 -12218827584.491585
Rp4_im_im_a2 0 x4_im_a2 1.4686625051954033e-10
Cx5_re_a2 x5_re_a2 0 1.0
Gx5_re_a2 0 x5_re_a2 p2 0 0.1414213562373095
Fx5_re_a2 0 x5_re_a2 V2 7.0710678118654755
Rp5_re_re_a2 0 x5_re_a2 8.228071946961779e-10
Gp5_re_im_a2 0 x5_re_a2 x5_im_a2 0 12061089204.497772
Cx5_im_a2 x5_im_a2 0 1.0
Gp5_im_re_a2 0 x5_im_a2 x5_re_a2 0 -12061089204.497772
Rp5_im_im_a2 0 x5_im_a2 8.228071946961779e-10
Cx6_re_a2 x6_re_a2 0 1.0
Gx6_re_a2 0 x6_re_a2 p2 0 0.1414213562373095
Fx6_re_a2 0 x6_re_a2 V2 7.0710678118654755
Rp6_re_re_a2 0 x6_re_a2 5.46297909887745e-10
Gp6_re_im_a2 0 x6_re_a2 x6_im_a2 0 4558622724.893911
Cx6_im_a2 x6_im_a2 0 1.0
Gp6_im_re_a2 0 x6_im_a2 x6_re_a2 0 -4558622724.893911
Rp6_im_im_a2 0 x6_im_a2 5.46297909887745e-10
.ENDS s_equivalent

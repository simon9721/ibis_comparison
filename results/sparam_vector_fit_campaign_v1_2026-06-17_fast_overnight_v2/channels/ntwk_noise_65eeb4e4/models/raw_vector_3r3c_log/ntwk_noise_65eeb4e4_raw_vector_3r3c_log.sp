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
Gr3_re_1_1 0 s1 x3_re_a1 0 0.0
Gr3_im_1_1 0 s1 x3_im_a1 0 0.0
Gr4_1_1 0 s1 x4_a1 0 0.0
Gr5_re_1_1 0 s1 x5_re_a1 0 0.0
Gr5_im_1_1 0 s1 x5_im_a1 0 0.0
Gr6_re_1_1 0 s1 x6_re_a1 0 0.0
Gr6_im_1_1 0 s1 x6_im_a1 0 0.0
Gr1_1_2 0 s1 x1_a2 0 0.0
Gr2_1_2 0 s1 x2_a2 0 0.0
Gr3_re_1_2 0 s1 x3_re_a2 0 0.0
Gr3_im_1_2 0 s1 x3_im_a2 0 0.0
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
Rp1_a1 0 x1_a1 2.5749565327542546e-12
Cx2_a1 x2_a1 0 1.0
Gx2_a1 0 x2_a1 p1 0 0.07071067811865475
Fx2_a1 0 x2_a1 V1 3.5355339059327378
Rp2_a1 0 x2_a1 2.287892116652049e-11
Cx3_re_a1 x3_re_a1 0 1.0
Gx3_re_a1 0 x3_re_a1 p1 0 0.1414213562373095
Fx3_re_a1 0 x3_re_a1 V1 7.0710678118654755
Rp3_re_re_a1 0 x3_re_a1 1.1470016516938513e-10
Gp3_re_im_a1 0 x3_re_a1 x3_im_a1 0 14263163853.232092
Cx3_im_a1 x3_im_a1 0 1.0
Gp3_im_re_a1 0 x3_im_a1 x3_re_a1 0 -14263163853.232092
Rp3_im_im_a1 0 x3_im_a1 1.1470016516938513e-10
Cx4_a1 x4_a1 0 1.0
Gx4_a1 0 x4_a1 p1 0 0.07071067811865475
Fx4_a1 0 x4_a1 V1 3.5355339059327378
Rp4_a1 0 x4_a1 7.937612415534067e-11
Cx5_re_a1 x5_re_a1 0 1.0
Gx5_re_a1 0 x5_re_a1 p1 0 0.1414213562373095
Fx5_re_a1 0 x5_re_a1 V1 7.0710678118654755
Rp5_re_re_a1 0 x5_re_a1 1.2081955441690968e-09
Gp5_re_im_a1 0 x5_re_a1 x5_im_a1 0 12176543093.163328
Cx5_im_a1 x5_im_a1 0 1.0
Gp5_im_re_a1 0 x5_im_a1 x5_re_a1 0 -12176543093.163328
Rp5_im_im_a1 0 x5_im_a1 1.2081955441690968e-09
Cx6_re_a1 x6_re_a1 0 1.0
Gx6_re_a1 0 x6_re_a1 p1 0 0.1414213562373095
Fx6_re_a1 0 x6_re_a1 V1 7.0710678118654755
Rp6_re_re_a1 0 x6_re_a1 6.776782046328521e-10
Gp6_re_im_a1 0 x6_re_a1 x6_im_a1 0 5030399799.02475
Cx6_im_a1 x6_im_a1 0 1.0
Gp6_im_re_a1 0 x6_im_a1 x6_re_a1 0 -5030399799.02475
Rp6_im_im_a1 0 x6_im_a1 6.776782046328521e-10
*
* Port network for port 2
V2 p2 s2 0
R2 s2 0 50.0
Gd2_1 0 s2 p1 0 0.19999999999997461
Fd2_1 0 s2 V1 9.999999999998732
Gr1_2_1 0 s2 x1_a1 0 0.14475517880399424
Gr2_2_1 0 s2 x2_a1 0 0.002087925012212419
Gr3_re_2_1 0 s2 x3_re_a1 0 -0.0002313478702076949
Gr3_im_2_1 0 s2 x3_im_a1 0 -7.612360449001737e-05
Gr4_2_1 0 s2 x4_a1 0 -0.000833928715224826
Gr5_re_2_1 0 s2 x5_re_a1 0 -1.2055863335197574e-06
Gr5_im_2_1 0 s2 x5_im_a1 0 0.0
Gr6_re_2_1 0 s2 x6_re_a1 0 1.4544664406091378e-05
Gr6_im_2_1 0 s2 x6_im_a1 0 -3.2007262761691844e-06
Gr1_2_2 0 s2 x1_a2 0 0.0
Gr2_2_2 0 s2 x2_a2 0 0.0
Gr3_re_2_2 0 s2 x3_re_a2 0 0.0
Gr3_im_2_2 0 s2 x3_im_a2 0 0.0
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
Rp1_a2 0 x1_a2 2.5749565327542546e-12
Cx2_a2 x2_a2 0 1.0
Gx2_a2 0 x2_a2 p2 0 0.07071067811865475
Fx2_a2 0 x2_a2 V2 3.5355339059327378
Rp2_a2 0 x2_a2 2.287892116652049e-11
Cx3_re_a2 x3_re_a2 0 1.0
Gx3_re_a2 0 x3_re_a2 p2 0 0.1414213562373095
Fx3_re_a2 0 x3_re_a2 V2 7.0710678118654755
Rp3_re_re_a2 0 x3_re_a2 1.1470016516938513e-10
Gp3_re_im_a2 0 x3_re_a2 x3_im_a2 0 14263163853.232092
Cx3_im_a2 x3_im_a2 0 1.0
Gp3_im_re_a2 0 x3_im_a2 x3_re_a2 0 -14263163853.232092
Rp3_im_im_a2 0 x3_im_a2 1.1470016516938513e-10
Cx4_a2 x4_a2 0 1.0
Gx4_a2 0 x4_a2 p2 0 0.07071067811865475
Fx4_a2 0 x4_a2 V2 3.5355339059327378
Rp4_a2 0 x4_a2 7.937612415534067e-11
Cx5_re_a2 x5_re_a2 0 1.0
Gx5_re_a2 0 x5_re_a2 p2 0 0.1414213562373095
Fx5_re_a2 0 x5_re_a2 V2 7.0710678118654755
Rp5_re_re_a2 0 x5_re_a2 1.2081955441690968e-09
Gp5_re_im_a2 0 x5_re_a2 x5_im_a2 0 12176543093.163328
Cx5_im_a2 x5_im_a2 0 1.0
Gp5_im_re_a2 0 x5_im_a2 x5_re_a2 0 -12176543093.163328
Rp5_im_im_a2 0 x5_im_a2 1.2081955441690968e-09
Cx6_re_a2 x6_re_a2 0 1.0
Gx6_re_a2 0 x6_re_a2 p2 0 0.1414213562373095
Fx6_re_a2 0 x6_re_a2 V2 7.0710678118654755
Rp6_re_re_a2 0 x6_re_a2 6.776782046328521e-10
Gp6_re_im_a2 0 x6_re_a2 x6_im_a2 0 5030399799.02475
Cx6_im_a2 x6_im_a2 0 1.0
Gp6_im_re_a2 0 x6_im_a2 x6_re_a2 0 -5030399799.02475
Rp6_im_im_a2 0 x6_im_a2 6.776782046328521e-10
.ENDS s_equivalent

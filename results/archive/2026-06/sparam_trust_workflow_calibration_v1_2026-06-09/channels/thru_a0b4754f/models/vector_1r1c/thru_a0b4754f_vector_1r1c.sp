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
Gd1_2 0 s1 p2 0 0.019999999999999997
Fd1_2 0 s1 V2 0.9999999999999998
Gr1_1_2 0 s1 x1_a2 0 -7.757638132488403e-06
Gr2_re_1_2 0 s1 x2_re_a2 0 0.0
Gr2_im_1_2 0 s1 x2_im_a2 0 -1.1287182957894337e-06
*
* State networks driven by port 1
Cx1_a1 x1_a1 0 1.0
Gx1_a1 0 x1_a1 p1 0 0.07071067811865475
Fx1_a1 0 x1_a1 V1 3.5355339059327378
Rp1_a1 0 x1_a1 1.0110056730183958e-12
Cx2_re_a1 x2_re_a1 0 1.0
Gx2_re_a1 0 x2_re_a1 p1 0 0.1414213562373095
Fx2_re_a1 0 x2_re_a1 V1 7.0710678118654755
Rp2_re_re_a1 0 x2_re_a1 4.3224422402305095e-11
Gp2_re_im_a1 0 x2_re_a1 x2_im_a1 0 18527595739.693314
Cx2_im_a1 x2_im_a1 0 1.0
Gp2_im_re_a1 0 x2_im_a1 x2_re_a1 0 -18527595739.693314
Rp2_im_im_a1 0 x2_im_a1 4.3224422402305095e-11
*
* Port network for port 2
V2 p2 s2 0
R2 s2 0 50.0
Gd2_1 0 s2 p1 0 0.019999999999999997
Fd2_1 0 s2 V1 0.9999999999999998
Gr1_2_1 0 s2 x1_a1 0 -7.757638132488403e-06
Gr2_re_2_1 0 s2 x2_re_a1 0 0.0
Gr2_im_2_1 0 s2 x2_im_a1 0 -1.1287182957894337e-06
Gr1_2_2 0 s2 x1_a2 0 0.0
Gr2_re_2_2 0 s2 x2_re_a2 0 0.0
Gr2_im_2_2 0 s2 x2_im_a2 0 0.0
*
* State networks driven by port 2
Cx1_a2 x1_a2 0 1.0
Gx1_a2 0 x1_a2 p2 0 0.07071067811865475
Fx1_a2 0 x1_a2 V2 3.5355339059327378
Rp1_a2 0 x1_a2 1.0110056730183958e-12
Cx2_re_a2 x2_re_a2 0 1.0
Gx2_re_a2 0 x2_re_a2 p2 0 0.1414213562373095
Fx2_re_a2 0 x2_re_a2 V2 7.0710678118654755
Rp2_re_re_a2 0 x2_re_a2 4.3224422402305095e-11
Gp2_re_im_a2 0 x2_re_a2 x2_im_a2 0 18527595739.693314
Cx2_im_a2 x2_im_a2 0 1.0
Gp2_im_re_a2 0 x2_im_a2 x2_re_a2 0 -18527595739.693314
Rp2_im_im_a2 0 x2_im_a2 4.3224422402305095e-11
.ENDS s_equivalent

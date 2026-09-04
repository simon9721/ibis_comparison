* ============================================================
* Sanity check for ngspice boolean/nested ternary behavior used
* in the pybis runtime selector logic.
* ============================================================

VNI ni 0 0.5
VN2 n2 0 0.0

B1 out_or   0 V = (V(ni) > 0 || V(n2) < -0.1) ? 1 : 2
B2 out_and  0 V = (V(ni) > 0 && V(n2) > -0.1) ? 3 : 4
B3 out_nest 0 V = (1 > 0.5) ? ((V(ni) > 0 && V(n2) > -0.1) ? 5 : 6) : 7

.op
.print op v(out_or) v(out_and) v(out_nest)
.end

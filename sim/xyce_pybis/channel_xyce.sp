* ============================================================
* channel_ngspice.sp  ???  10-section lumped RLGC ladder
* Models 10 cm FR4 microstrip trace (1 cm per section)
*
* Target: Z0 = 50 Ohm, FR4 (er=4.3)
*
* Per-section values (per 1 cm):
*   R = 0.05   Ohm  (conductor loss, 1oz copper ~1.9mm wide trace)
*   L = 3.46   nH   (series inductance)
*   C = 1.384  pF   (shunt capacitance)
*   G = 1e-6   S    (dielectric loss, FR4 tan_d ~ 0.02 at low freq)
*
* Verification:
*   Z0  = sqrt(L/C) = sqrt(3.46n/1.384p) = 50.0 Ohm
*   td  = sqrt(L*C) = sqrt(3.46n*1.384p) = 69.2 ps/section
*   Total delay (10 sections) = 692 ps
*
* Ports:
*   tx_out  ??? driven by transmitter buffer output
*   n10b    ??? receiver end, connect to termination / rx buffer
*
* NOTE on G-element in NGspice:
*   NGspice uses behavioral current source syntax:
*   Gxxx n+ n- value={conductance * v(n+, n-)}
*   This is equivalent to a linear shunt conductance to ground.
*
* Simulator: Xyce
* Missouri S&T EMC Lab ??? IBIS Comparison Study ??? April 2026
* ============================================================

* ---- Section 1 ----
R1   tx_out  n1a   0.05
L1   n1a     n1b   3.46n
C1   n1b     0     1.384p
R_G1   n1b     0     1meg

* ---- Section 2 ----
R2   n1b     n2a   0.05
L2   n2a     n2b   3.46n
C2   n2b     0     1.384p
R_G2   n2b     0     1meg

* ---- Section 3 ----
R3   n2b     n3a   0.05
L3   n3a     n3b   3.46n
C3   n3b     0     1.384p
R_G3   n3b     0     1meg

* ---- Section 4 ----
R4   n3b     n4a   0.05
L4   n4a     n4b   3.46n
C4   n4b     0     1.384p
R_G4   n4b     0     1meg

* ---- Section 5 ----
R5   n4b     n5a   0.05
L5   n5a     n5b   3.46n
C5   n5b     0     1.384p
R_G5   n5b     0     1meg

* ---- Section 6 ----
R6   n5b     n6a   0.05
L6   n6a     n6b   3.46n
C6   n6b     0     1.384p
R_G6   n6b     0     1meg

* ---- Section 7 ----
R7   n6b     n7a   0.05
L7   n7a     n7b   3.46n
C7   n7b     0     1.384p
R_G7   n7b     0     1meg

* ---- Section 8 ----
R8   n7b     n8a   0.05
L8   n8a     n8b   3.46n
C8   n8b     0     1.384p
R_G8   n8b     0     1meg

* ---- Section 9 ----
R9   n8b     n9a   0.05
L9   n9a     n9b   3.46n
C9   n9b     0     1.384p
R_G9   n9b     0     1meg

* ---- Section 10 ----
R10  n9b     n10a  0.05
L10  n10a    n10b  3.46n
C10  n10b    0     1.384p
R_G10   n10b     0     1meg

* n10b is the receiver end node


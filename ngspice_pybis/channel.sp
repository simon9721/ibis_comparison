* ============================================================
* channel.sp  —  10-section lumped RLGC ladder
* Models 10 cm FR4 microstrip trace (1 cm per section)
*
* Per-section values:
*   R = 0.5  Ohm  (conductor loss)
*   L = 7    nH   (series inductance)
*   C = 1.2  pF   (shunt capacitance)  Z0 ~ 76 Ohm
*   G = 1e-3 S    (dielectric loss, shunt conductance)
*
* Ports:  tx_out  (driven by tx buffer output)
*         ch_out (drives termination / rx buffer input)
*
* Topology per section:
*   tx_out --[R]--[L]--+-- ... --ch_out
*                     |
*                    [C],[G] to GND
*
* NOTE on G-element in HSPICE:
*   Bare "Gxxx n+ n- value" is NOT valid HSPICE syntax.
*   HSPICE requires the 4-node VCCS form:
*       Gxxx  n+  n-  nc+  nc-  value
*   For a shunt conductance to GND: nc+ = n+, nc- = 0
*   i.e. I(n+ -> 0) = G * V(n+, 0)
*
* Missouri S&T EMC Lab — Signal Integrity Group
* IBIS Comparison Study — April 2026
* ============================================================

* ---- Section 1 ----
R1   tx_out  n1a   0.5
L1   n1a    n1b   7n
C1   n1b    0     1.2p
G1   n1b    0     n1b  0  0.001

* ---- Section 2 ----
R2   n1b    n2a   0.5
L2   n2a    n2b   7n
C2   n2b    0     1.2p
G2   n2b    0     n2b  0  0.001

* ---- Section 3 ----
R3   n2b    n3a   0.5
L3   n3a    n3b   7n
C3   n3b    0     1.2p
G3   n3b    0     n3b  0  0.001

* ---- Section 4 ----
R4   n3b    n4a   0.5
L4   n4a    n4b   7n
C4   n4b    0     1.2p
G4   n4b    0     n4b  0  0.001

* ---- Section 5 ----
R5   n4b    n5a   0.5
L5   n5a    n5b   7n
C5   n5b    0     1.2p
G5   n5b    0     n5b  0  0.001

* ---- Section 6 ----
R6   n5b    n6a   0.5
L6   n6a    n6b   7n
C6   n6b    0     1.2p
G6   n6b    0     n6b  0  0.001

* ---- Section 7 ----
R7   n6b    n7a   0.5
L7   n7a    n7b   7n
C7   n7b    0     1.2p
G7   n7b    0     n7b  0  0.001

* ---- Section 8 ----
R8   n7b    n8a   0.5
L8   n8a    n8b   7n
C8   n8b    0     1.2p
G8   n8b    0     n8b  0  0.001

* ---- Section 9 ----
R9   n8b    n9a   0.5
L9   n9a    n9b   7n
C9   n9b    0     1.2p
G9   n9b    0     n9b  0  0.001

* ---- Section 10 ----
R10  n9b    n10a  0.5
L10  n10a   n10b  7n
C10  n10b   0     1.2p
G10  n10b   0     n10b 0  0.001

* ch_out is n10b — connect to Rterm / rx buffer in top-level netlist
* (add alias if needed: Vshort ch_out n10b 0)

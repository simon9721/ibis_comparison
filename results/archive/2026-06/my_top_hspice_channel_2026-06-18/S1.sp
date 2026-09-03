* Reconstructed TopXP S1 channel wrapper for HSPICE.
* Instance order from exported deck:
*   X2 tx_p tx_ref tx_n rx_p rx_ref rx_n S1_sparams_4port_bnp
* The underlying Cadence BNP is a 4-port single-ended model with common reference.
* Port order follows Cadence's differential 4-port example:
*   S port1=tx_p, port2=rx_p, port3=tx_n, port4=rx_n, ref=tx_ref.
.subckt S1_sparams_4port_bnp tx_p tx_ref tx_n rx_p rx_ref rx_n
S_S1 tx_p rx_p tx_n rx_n tx_ref MNAME=S1_MODEL
.model S1_MODEL S BNPFILE="sparams_4port.bnp"
.ends S1_sparams_4port_bnp

This directory was made to test /ex1 with hspice.
In ex1, .ibs model was obtained using spectre. 
When user simulates using hspice, the simulations 
either did not converge or produced garbage (extremely large currents). 
The reason for this is that HSPICE has problems with bad models 
whereas SPECTRE fares relatively well. When simulated using a proper model, 
hspice produces better ibis models. This was confirmed in this test.


for a cmos pushpull inverter chain output digital buffer, you know what im talking about?
Yes. You mean a CMOS output buffer built as a chain of inverters, where each stage progressively increases in transistor size so the final stage can drive a relatively large capacitive load.

Conceptually:

logic input → small inverter → larger inverter → larger inverter → ... → output

Each inverter is a push-pull CMOS stage:

PMOS on top, connected to 
V
D
D
V 
DD
​
 
NMOS on bottom, connected to GND
Gates tied together as the stage input
Drains tied together as the stage output
So when the output is driven HIGH, the PMOS sources current into the load; when driven LOW, the NMOS sinks current from the load.

The reason for the inverter chain is that directly driving a very large output transistor pair from a tiny logic gate would present excessive gate capacitance. Instead, the stages are typically tapered, roughly

W
1
<
W
2
<
W
3
<
⋯
<
W
N
W 
1
​
 <W 
2
​
 <W 
3
​
 <⋯<W 
N
​
 
with a roughly constant sizing ratio between stages.

For an SI/IBIS-style view, the last stage is especially important because its PMOS/NMOS 
I
 ⁣
−
 ⁣
V
I−V behavior, package parasitics, and load determine the output waveform, rise/fall times, overshoot, etc.

If this is the structure you're referring to, yes—I know exactly what you mean.

so are the pre-drivers behave like current sources? if yes, why?
Not in the strict sense. A normal CMOS pre-driver stage is still fundamentally a voltage-driven push-pull stage, not an ideal current source.

What creates the confusion is that, during part of a transition, the conducting MOSFET can operate in saturation, where its drain current is relatively insensitive to 
V
D
S
V 
DS
​
 . In that interval it can look approximately current-source-like.

For example, during a LOW-to-HIGH transition, the PMOS in the pre-driver charges the gate capacitance of the next stage:

I
≈
C
L
d
V
d
t
I≈C 
L
​
  
dt
dV
​
 
where 
C
L
C 
L
​
  is mostly the next inverter's MOS gate capacitance.

If the PMOS is in saturation, a simplified long-channel expression is

I
D
≈
1
2
μ
p
C
o
x
W
L
(
V
S
G
−
∣
V
T
P
∣
)
2
I 
D
​
 ≈ 
2
1
​
 μ 
p
​
 C 
ox
​
  
L
W
​
 (V 
SG
​
 −∣V 
TP
​
 ∣) 
2
 
and importantly, there is little explicit dependence on the output voltage 
V
o
u
t
V 
out
​
 . So during that part of the edge:

I
D
≈
roughly constant
I 
D
​
 ≈roughly constant
and therefore

d
V
o
u
t
d
t
≈
I
D
C
L
dt
dV 
out
​
 
​
 ≈ 
C 
L
​
 
I 
D
​
 
​
 
which gives a roughly linear voltage ramp. That's the sense in which people may say the pre-driver is "acting like a current source."

But it does not stay that way throughout the transition. As 
V
o
u
t
V 
out
​
  approaches 
V
D
D
V 
DD
​
 , the PMOS leaves saturation and enters the triode/linear region. Then its current decreases toward zero. So the actual behavior is more like:

strong current
→
approximately current-source-like
→
decreasing current
→
0
strong current→approximately current-source-like→decreasing current→0
Likewise, for a HIGH-to-LOW transition, the NMOS initially sinks substantial current from the next-stage gate capacitance. For part of the transition it may be in saturation and look current-source-like, then eventually enter the linear region as 
V
o
u
t
V 
out
​
  approaches ground.

A useful mental model is therefore:

CMOS pre-driver
≠
current source
CMOS pre-driver

=current source
​
 
but

during part of a transition, its MOSFET may behave approximately like one
during part of a transition, its MOSFET may behave approximately like one
​
 
The reason this matters for an inverter chain is that each pre-driver's job is essentially to source or sink charge into the gate capacitance of the next larger stage:

Q
=
C
g
Δ
V
Q=C 
g
​
 ΔV
and the current determines how quickly that charge can be moved:

t
r
i
s
e
/
f
a
l
l
∼
Q
I
=
C
g
Δ
V
I
t 
rise/fall
​
 ∼ 
I
Q
​
 = 
I
C 
g
​
 ΔV
​
 
So from a timing perspective, thinking of the pre-driver as supplying a finite charging/discharging current is often very useful.

There is one important exception: slew-rate-controlled output drivers often deliberately use current-starved inverters or controlled bias currents. In those designs, the pre-driver can be intentionally made much more current-source-like.


Pasted markdown.md
Document
read this, does the theories backing the claims hold?

Worked for 1m 34s
Parts of it hold, but several claims are stated much more strongly than the underlying physics justifies. The core modeling idea is credible; I would revise the theoretical argument before presenting it as a physics-derived methodology.

The most important distinction is this:

The current-limited inverter-chain model is a physically motivated reduced-order model. It is not uniquely derived from CMOS device physics.

That distinction affects several sections.

Claim in the document	Assessment	Why
IBIS I-V + V-T data can be used to obtain 
K
u
(
t
)
K 
u
​
 (t)/
K
d
(
t
)
K 
d
​
 (t)	Yes, with wording correction	IBIS does not literally contain 
K
u
(
t
)
K 
u
​
 (t). Simulators can derive time-varying pullup/pulldown weighting coefficients from V-T waveforms, I-V tables, 
C
comp
C 
comp
​
 , and fixture information. The established 2EQ/2UK formulation does exactly this. 
K
u
(
t
)
=
m
a
p
(
g
(
t
)
)
K 
u
​
 (t)=map(g(t)) cannot be uniquely factored from a normal transition	Yes	This is a genuine identifiability problem. If only the composite 
K
u
(
t
)
K 
u
​
 (t) is observed, infinitely many latent trajectories 
g
(
t
)
g(t) and static maps 
f
(
g
)
f(g) can generate it. But this is your modeling assumption, not something IBIS itself asserts.
A full transition “visits only the two ends” of gate travel	No, literally false	The gate obviously traverses all intermediate values. The correct statement is that the internal gate coordinate is unobserved, so the measured full-swing waveform constrains only the composite 
K
u
(
t
)
K 
u
​
 (t), not its factorization. 
A truncated pulse exposes information that a normal transition does not	Yes	This is one of the strongest parts of the reasoning. Reversing the command while internal stages are still in flight makes the response depend on internal dynamic state. That gives information about the latent trajectory that a single unidirectional full-swing transition cannot separate.
A truncated pulse is “the only instrument”	Too strong	It is a very useful external probe, but not the only possible one. Multi-level stimuli, varying slew rate, paired pulses, PRBS/history-dependent excitation, multiple loads, supply perturbations, or internal probing can also provide additional identifiability.
CMOS inverter ≈ current source followed by resistor	Good first-order intuition	A MOSFET with fixed gate overdrive is relatively current-source-like in saturation and increasingly resistive in triode. This is a legitimate compact approximation.
Therefore the proposed stage equation is forced by CMOS physics	No	Physics motivates the form, but does not uniquely produce the particular min(...), the linear taper, the chosen 
h
(
u
)
h(u), the common 
x
lin
x 
lin
​
 , or 
p
=
1
p=1. Those are model-architecture choices.
A chain suppresses short pulses and stage count matters strongly	Yes	CMOS chains exhibit glitch degradation/inertial filtering; narrow pulses can shrink and disappear after several stages. Literature explicitly observes this behavior. 
Each stage outputs “nothing” until its input crosses 
v
t
v 
t
​
 	Not physically literal	MOS current changes continuously. A hard threshold is a reduced-order approximation. Short-pulse extinction is real; the hard switching law is not fundamental MOS physics.
Rise/fall 
K
u
K 
u
​
 -versus-gate collapse proves output stage has “no memory”	Too strong	It supports a quasi-static, approximately single-valued map under the tested conditions. MOS structures still contain nonlinear capacitances and charge storage. Removing or accounting for 
C
comp
C 
comp
​
  can make a memoryless approximation good, but cannot establish zero physical memory. 
C
comp
C 
comp
​
  matters when extracting 
K
u
K 
u
​
 	Yes	IBIS V-T measurements include buffer capacitance effects, and simulators reconcile those effects with the explicit 
C
comp
C 
comp
​
 . The IBIS Cookbook explicitly defines 
C
comp
C 
comp
​
  as transistor/die-pad/on-die-interconnect capacitance and notes that V-T extraction includes it. 
K
u
≤
1
K 
u
​
 ≤1 is an identity that lets you determine the true 
C
comp
C 
comp
​
 	I would not call this a physical identity	It is a sensible regularization for a simple normalized on/off weighting interpretation, but extracted IBIS weighting functions can reflect nonidealities, imperfect separation, overlap, fixture errors, capacitance errors, etc. Treat 
K
u
≤
1
K 
u
​
 ≤1 as a modeling constraint, not a fundamental law.
The current-source argument in Section 4 deserves special attention because it is the physics foundation of the proposed stage law. The document says:

“a CMOS inverter driving a large load is a current source while its input sits at the rail … and becomes a resistor only near the destination rail” 

The first half is reasonable, but the “only near the destination rail” part is not generally correct from the textbook long-channel MOS equations.

For an NMOS discharging a capacitor with 
V
i
n
=
V
D
D
V 
in
​
 =V 
DD
​
 ,

I
D
≈
1
2
β
n
(
V
D
D
−
V
T
N
)
2
I 
D
​
 ≈ 
2
1
​
 β 
n
​
 (V 
DD
​
 −V 
TN
​
 ) 
2
 
while the NMOS is saturated, and the saturation condition is

V
o
u
t
≥
V
D
D
−
V
T
N
.
V 
out
​
 ≥V 
DD
​
 −V 
TN
​
 .
Once

V
o
u
t
<
V
D
D
−
V
T
N
,
V 
out
​
 <V 
DD
​
 −V 
TN
​
 ,
the NMOS is in triode:

I
D
=
β
n
[
(
V
D
D
−
V
T
N
)
V
o
u
t
−
V
o
u
t
2
2
]
.
I 
D
​
 =β 
n
​
 [(V 
DD
​
 −V 
TN
​
 )V 
out
​
 − 
2
V 
out
2
​
 
​
 ].
So it is current-source-like initially and becomes increasingly resistive as the output approaches ground. But depending on 
V
T
/
V
D
D
V 
T
​
 /V 
DD
​
 , the triode portion can occupy a substantial fraction of the swing—not merely the last tiny region near ground.

Likewise, during PMOS charging with 
V
i
n
=
0
V 
in
​
 =0, the PMOS is saturated approximately while

V
o
u
t
≲
∣
V
T
P
∣
,
V 
out
​
 ≲∣V 
TP
​
 ∣,
and then enters triode as 
V
o
u
t
V 
out
​
  rises toward 
V
D
D
V 
DD
​
 .

Modern short-channel devices complicate this with velocity saturation, channel-length modulation, nonlinear capacitances, etc.; simple 
R
on
C
L
R 
on
​
 C 
L
​
  or average-current models are routinely used specifically because exact transient MOS behavior is more complicated. MIT and other standard CMOS treatments likewise model inverter propagation delay through capacitive charging/discharging and effective/average current rather than asserting an ideal current source throughout the swing. 

Your equation

d
v
d
t
=
s
up
h
(
u
)
min
⁡
(
1
,
1
−
v
x
lin
)
dt
dv
​
 =s 
up
​
 h(u)min(1, 
x 
lin
​
 
1−v
​
 )
does nevertheless have a clean physical interpretation. Since

I
=
C
d
v
d
t
,
I=C 
dt
dv
​
 ,
the first portion,

d
v
d
t
≈
s
up
,
dt
dv
​
 ≈s 
up
​
 ,
means approximately constant charging current and therefore a ramp. Then, near the rail,

d
v
d
t
∝
1
−
v
,
dt
dv
​
 ∝1−v,
which gives

C
d
v
d
t
∝
V
D
D
−
V
,
C 
dt
dv
​
 ∝V 
DD
​
 −V,
equivalent to an approximately resistive pullup. So the equation is physically sensible. What does not follow is the statement that MOS physics “forces exactly four numbers.” 

The more defensible wording would be something like:

“MOS device physics suggests a compact two-regime stage model: an approximately current-limited region followed by an approximately resistive approach to the destination rail. We represent that behavior with a four-parameter reduced-order law.”

That is strong and technically supportable.

There is also a problem in Section 2 that I would definitely fix. The document says:

“Any two models that agree about the endpoints agree about the entire full-swing waveform.” 

That is simply not true. Two systems can have the same initial and final states and radically different trajectories. What your argument actually needs is:

K
u
(
t
)
=
f
(
g
(
t
)
)
K 
u
​
 (t)=f(g(t))
is known, but 
g
(
t
)
g(t) and 
f
f individually are unknown. For any suitable monotonic reparameterization 
ϕ
ϕ,

g
~
(
t
)
=
ϕ
(
g
(
t
)
)
g
~
​
 (t)=ϕ(g(t))
and

f
~
(
x
)
=
f
(
ϕ
−
1
(
x
)
)
f
~
​
 (x)=f(ϕ 
−1
 (x))
produce exactly the same

f
~
(
g
~
(
t
)
)
=
f
(
g
(
t
)
)
=
K
u
(
t
)
.
f
~
​
 ( 
g
~
​
 (t))=f(g(t))=K 
u
​
 (t).
That is the rigorous mathematical reason the full-swing waveform cannot identify the two factors. It is much stronger than the endpoint argument and is actually correct.

The truncated pulse then makes sense mathematically: the reversal asks the state trajectory to evolve under a different input before it reaches the terminal state, adding constraints that different factorizations generally will not satisfy identically. So the central intuition of Sections 1–2 is good; the current wording of the proof is not.

Similarly, the short-pulse-chain argument is directionally sound. Narrow pulses really can degrade and disappear as they traverse CMOS stages; published CMOS glitch-propagation work describes both degradation and eventual inertial elimination. 
 But I would replace:

“Each stage needs its input past 
v
t
v 
t
​
  before it delivers anything”

with something like:

“Each stage has a strongly nonlinear input-to-output drive characteristic. A sufficiently shallow or short excursion produces too little output excursion to drive the following stage through its effective switching region, so pulse depth/width can progressively degrade until the disturbance is extinguished.”

That is much closer to transistor physics while preserving the reason 
K
K matters. 

One other subtle issue: the document says constraining stages to be identical is appropriate because “a real tapered predriver approximately is” identical. 
 A tapered buffer is emphatically not identical in transistor dimensions—later stages are intentionally larger. What can be approximately identical is their normalized dynamics, if the chain has roughly constant electrical fanout and similarly scaled devices. I would state that explicitly.

On the IBIS side, the document is on firmer ground. IBIS explicitly uses static I-V tables plus switching V-T information, and recommended CMOS V-T characterization uses different loads to isolate pullup/pulldown turn-on and turn-off behavior. The Cookbook also says package parasitics should be removed while 
C
comp
C 
comp
​
  effects remain in the switching extraction. 
 
C
comp
C 
comp
​
  itself represents transistor, die-pad, and on-die-interconnect capacitance and varies with frequency and bias, so reducing it to one constant is inherently approximate. 

So my overall technical assessment is:

The empirical model and experimental results can absolutely be legitimate. The physics provides a reasonable prior for the model family. But the document currently overstates several modeling assumptions as laws of CMOS physics.

The parts I would change before defending this technically are:

Replace the endpoint argument with the formal non-identifiability/reparameterization argument.
Change “current source” to approximately current-limited/current-source-like in the relevant operating region.
Change “physics forces exactly four numbers” to physics motivates this four-parameter reduced-order form.
Change “output stage carries no memory” to the measurements support a quasi-static single-valued map after capacitive correction over the tested regime.
Change “extinguishes rather than attenuates” to can progressively degrade and eventually extinguish short pulses.
Treat 
K
u
≤
1
K 
u
​
 ≤1 as a model constraint/diagnostic, not an unquestionable physical identity.
Clarify that “identical stages” means identical normalized stage dynamics, not equal transistor sizes.
With those changes, the theoretical story becomes substantially stronger: IBIS provides the observable composite switching behavior; that composite is structurally non-identifiable; stressed/reversing excitation adds latent-state information; and a MOS-motivated current-limited inverter-chain prior regularizes the otherwise underdetermined inverse problem. That formulation is technically defensible.

can you explain clearly so i can understand all the equations, how they related to the MOS physics? and is there relevant contents in the 'microelectronic circuit' (the famous book)?

Worked for 1m 6s
Yes. The relevant physics is standard MOSFET/inverter material, and Microelectronic Circuits by Sedra/Smith is a very good book for building the foundation.

The easiest way to understand your document is to start from one CMOS inverter driving a capacitor, derive its waveform from MOS equations, and then compare that directly with the reduced-order equation in the document.

Your document proposes this stage law: 

d
v
d
t
=
s
u
p
h
(
u
)
min
⁡
(
1
,
1
−
v
x
l
i
n
)
−
s
d
n
h
(
1
−
u
)
min
⁡
(
1
,
v
x
l
i
n
)
dt
dv
​
 =s 
up
​
 h(u)min(1, 
x 
lin
​
 
1−v
​
 )−s 
dn
​
 h(1−u)min(1, 
x 
lin
​
 
v
​
 )
​
 
It looks complicated, but essentially every term corresponds to a simple physical idea.

1. Start with one CMOS inverter
A CMOS inverter is:

V
D
D
→
PMOS
→
V
o
u
t
→
NMOS
→
G
N
D
V 
DD
​
 →PMOS→V 
out
​
 →NMOS→GND
and the output normally sees some capacitance:

C
L
.
C 
L
​
 .
That capacitance includes the gate capacitance of the next inverter plus wiring and parasitic capacitance.

The most important equation for everything in your document is

I
=
C
d
V
d
t
I=C 
dt
dV
​
 
​
 
or equivalently

d
V
d
t
=
I
C
.
dt
dV
​
 = 
C
I
​
 
​
 .
This equation connects MOS current to digital edge shape.

If the transistor delivers approximately constant current,

I
≈
I
0
,
I≈I 
0
​
 ,
then

d
V
d
t
≈
I
0
C
.
dt
dV
​
 ≈ 
C
I 
0
​
 
​
 .
Therefore

V
(
t
)
≈
V
(
0
)
+
I
0
C
t
.
V(t)≈V(0)+ 
C
I 
0
​
 
​
 t.
That is a linear ramp.

This is exactly the basic idea behind the document's 
s
u
p
s 
up
​
  and 
s
d
n
s 
dn
​
 .

2. Why can a MOSFET look like a current source?
Consider an NMOS first.

The textbook long-channel equations are approximately:

Triode region
I
D
=
μ
n
C
o
x
W
L
[
(
V
G
S
−
V
T
)
V
D
S
−
V
D
S
2
2
]
.
I 
D
​
 =μ 
n
​
 C 
ox
​
  
L
W
​
 [(V 
GS
​
 −V 
T
​
 )V 
DS
​
 − 
2
V 
DS
2
​
 
​
 ].
Saturation region
I
D
≈
1
2
μ
n
C
o
x
W
L
(
V
G
S
−
V
T
)
2
.
I 
D
​
 ≈ 
2
1
​
 μ 
n
​
 C 
ox
​
  
L
W
​
 (V 
GS
​
 −V 
T
​
 ) 
2
 .
Ignore channel-length modulation for the moment.

Notice something very important.

In saturation,

I
D
≈
1
2
β
(
V
G
S
−
V
T
)
2
I 
D
​
 ≈ 
2
1
​
 β(V 
GS
​
 −V 
T
​
 ) 
2
 
does not contain 
V
D
S
V 
DS
​
 .

So if 
V
G
S
V 
GS
​
  is fixed,

I
D
≈
constant
.
I 
D
​
 ≈constant.
That's why we say:

MOSFET in saturation is approximately current-source-like
MOSFET in saturation is approximately current-source-like
​
 
—not that it is an ideal current source.

Sedra/Smith covers exactly this foundation in its MOSFET chapters. In the 8th edition, Chapter 5 covers device operation and I-V characteristics, including channel pinch-off/current saturation, 
i
D
−
v
D
S
i 
D
​
 −v 
DS
​
  curves, p-channel MOSFETs, and finite output resistance in saturation. 

3. Apply that to an inverter falling edge
Suppose

V
i
n
:
0
→
V
D
D
.
V 
in
​
 :0→V 
DD
​
 .
Then:

PMOS turns OFF.
NMOS turns ON.
NMOS discharges 
C
L
C 
L
​
 .
So approximately

C
L
d
V
o
u
t
d
t
=
−
I
N
.
C 
L
​
  
dt
dV 
out
​
 
​
 =−I 
N
​
 .
Therefore

d
V
o
u
t
d
t
=
−
I
N
C
L
dt
dV 
out
​
 
​
 =− 
C 
L
​
 
I 
N
​
 
​
 
​
 
If the NMOS is approximately current-source-like,

I
N
≈
I
0
,
I 
N
​
 ≈I 
0
​
 ,
then

d
V
o
u
t
d
t
≈
−
I
0
C
L
.
dt
dV 
out
​
 
​
 ≈− 
C 
L
​
 
I 
0
​
 
​
 .
So the output falls roughly as a ramp.

For example, if

C
L
=
1
 pF
C 
L
​
 =1 pF
and

I
N
=
1
 mA
,
I 
N
​
 =1 mA,
then

d
V
d
t
=
10
−
3
10
−
12
=
10
9
V
s
=
1
V
n
s
.
dt
dV
​
 = 
10 
−12
 
10 
−3
 
​
 =10 
9
  
s
V
​
 =1 
ns
V
​
 .
So a roughly 1-V swing takes roughly 1 ns.

That's the physical meaning of a slew-rate parameter.

4. But the MOSFET does not remain in saturation
This is where the document's model becomes interesting.

For NMOS saturation,

V
D
S
≥
V
G
S
−
V
T
.
V 
DS
​
 ≥V 
GS
​
 −V 
T
​
 .
During discharge:

V
D
S
=
V
o
u
t
,
V 
DS
​
 =V 
out
​
 ,
and if the gate is held at 
V
D
D
V 
DD
​
 ,

V
G
S
=
V
D
D
.
V 
GS
​
 =V 
DD
​
 .
Therefore saturation requires

V
o
u
t
≥
V
D
D
−
V
T
.
V 
out
​
 ≥V 
DD
​
 −V 
T
​
 .
Suppose

V
D
D
=
1.0
V
,
V
T
=
0.3
V
.
V 
DD
​
 =1.0V,V 
T
​
 =0.3V.
Then saturation requires

V
o
u
t
≳
0.7
V
.
V 
out
​
 ≳0.7V.
So during the beginning of the discharge,

1.0
V
→
0.7
V
,
1.0V→0.7V,
the NMOS is approximately current-source-like.

Below that, it enters the triode region.

Then its current becomes increasingly dependent on 
V
o
u
t
V 
out
​
 .

As 
V
o
u
t
→
0
V 
out
​
 →0,

I
D
→
0.
I 
D
​
 →0.
So the actual waveform isn't

constant slope all the way to 0
.
constant slope all the way to 0.
Instead it looks conceptually like

roughly ramp-like
→
slower approach to the rail
.
roughly ramp-like→slower approach to the rail.
​
 
That's the physics the document is trying to capture.

5. Near the rail, MOS behavior starts looking resistive
Take the triode equation again:

I
D
=
β
[
(
V
G
S
−
V
T
)
V
D
S
−
1
2
V
D
S
2
]
.
I 
D
​
 =β[(V 
GS
​
 −V 
T
​
 )V 
DS
​
 − 
2
1
​
 V 
DS
2
​
 ].
When 
V
D
S
V 
DS
​
  becomes small,

V
D
S
2
V 
DS
2
​
 
is much smaller than 
V
D
S
V 
DS
​
 , so approximately

I
D
≈
β
(
V
G
S
−
V
T
)
V
D
S
.
I 
D
​
 ≈β(V 
GS
​
 −V 
T
​
 )V 
DS
​
 .
Define

G
e
f
f
=
β
(
V
G
S
−
V
T
)
.
G 
eff
​
 =β(V 
GS
​
 −V 
T
​
 ).
Then

I
D
≈
G
e
f
f
V
D
S
.
I 
D
​
 ≈G 
eff
​
 V 
DS
​
 .
Since

G
=
1
R
,
G= 
R
1
​
 ,
this is

I
D
≈
V
D
S
R
e
f
f
.
I 
D
​
 ≈ 
R 
eff
​
 
V 
DS
​
 
​
 .
That's resistor behavior.

So the physical progression is roughly

saturation
⇒
current-source-like
saturation⇒current-source-like
​
 
followed by

triode near rail
⇒
resistor-like
.
triode near rail⇒resistor-like.
​
 
That is the physical justification for the document's two-regime model.

6. Now look at the document equation
Take only the discharging part:

d
v
d
t
=
−
s
d
n
h
(
1
−
u
)
min
⁡
(
1
,
v
x
l
i
n
)
dt
dv
​
 =−s 
dn
​
 h(1−u)min(1, 
x 
lin
​
 
v
​
 )
​
 
Assume for now that the stage is fully commanded to discharge, so

h
(
1
−
u
)
=
1.
h(1−u)=1.
Then

d
v
d
t
=
−
s
d
n
min
⁡
(
1
,
v
x
l
i
n
)
.
dt
dv
​
 =−s 
dn
​
 min(1, 
x 
lin
​
 
v
​
 ).
There are two regions.

Region A: 
v
>
x
l
i
n
v>x 
lin
​
 
Then

v
x
l
i
n
>
1
x 
lin
​
 
v
​
 >1
so

min
⁡
(
1
,
v
x
l
i
n
)
=
1.
min(1, 
x 
lin
​
 
v
​
 )=1.
Therefore

d
v
d
t
=
−
s
d
n
dt
dv
​
 =−s 
dn
​
 
​
 
which gives

v
(
t
)
=
v
0
−
s
d
n
t
.
v(t)=v 
0
​
 −s 
dn
​
 t.
That's a ramp.

Physically:

approximately current-limited discharge
approximately current-limited discharge
​
 
because constant 
d
v
/
d
t
dv/dt means constant current.

7. What is 
s
d
n
s 
dn
​
  physically?
Suppose 
v
v is normalized:

v
=
V
o
u
t
V
D
D
.
v= 
V 
DD
​
 
V 
out
​
 
​
 .
Then

V
o
u
t
=
V
D
D
v
.
V 
out
​
 =V 
DD
​
 v.
Therefore

d
V
o
u
t
d
t
=
V
D
D
d
v
d
t
.
dt
dV 
out
​
 
​
 =V 
DD
​
  
dt
dv
​
 .
Since

I
=
C
L
d
V
o
u
t
d
t
,
I=C 
L
​
  
dt
dV 
out
​
 
​
 ,
we get

I
=
C
L
V
D
D
d
v
d
t
.
I=C 
L
​
 V 
DD
​
  
dt
dv
​
 .
If

d
v
d
t
=
−
s
d
n
,
dt
dv
​
 =−s 
dn
​
 ,
then approximately

s
d
n
≈
I
d
i
s
c
h
a
r
g
e
C
L
V
D
D
s 
dn
​
 ≈ 
C 
L
​
 V 
DD
​
 
I 
discharge
​
 
​
 
​
 
and similarly

s
u
p
≈
I
c
h
a
r
g
e
C
L
V
D
D
.
s 
up
​
 ≈ 
C 
L
​
 V 
DD
​
 
I 
charge
​
 
​
 .
​
 
So 
s
u
p
s 
up
​
  and 
s
d
n
s 
dn
​
  aren't really “currents.”

They are better thought of as

normalized slew rates
normalized slew rates
​
 
that bundle together

transistor drive current
load capacitance
.
load capacitance
transistor drive current
​
 .
The document calling 
s
u
p
s 
up
​
  “the stage's charging current” is therefore shorthand; dimensionally, in this ODE it is closer to current divided by capacitance and voltage. 

8. What happens below 
x
l
i
n
x 
lin
​
 ?
Now suppose

v
<
x
l
i
n
.
v<x 
lin
​
 .
Then

min
⁡
(
1
,
v
x
l
i
n
)
=
v
x
l
i
n
.
min(1, 
x 
lin
​
 
v
​
 )= 
x 
lin
​
 
v
​
 .
So

d
v
d
t
=
−
s
d
n
x
l
i
n
v
.
dt
dv
​
 =− 
x 
lin
​
 
s 
dn
​
 
​
 v.
This is the classic first-order equation

d
v
d
t
=
−
k
v
.
dt
dv
​
 =−kv.
Its solution is

v
(
t
)
=
v
(
t
0
)
e
−
k
(
t
−
t
0
)
v(t)=v(t 
0
​
 )e 
−k(t−t 
0
​
 )
 
​
 
where

k
=
s
d
n
x
l
i
n
.
k= 
x 
lin
​
 
s 
dn
​
 
​
 .
Therefore

v
(
t
)
=
v
(
t
0
)
e
−
s
d
n
x
l
i
n
(
t
−
t
0
)
v(t)=v(t 
0
​
 )e 
− 
x 
lin
​
 
s 
dn
​
 
​
 (t−t 
0
​
 )
 
​
 
and the effective time constant is

τ
d
n
=
x
l
i
n
s
d
n
.
τ 
dn
​
 = 
s 
dn
​
 
x 
lin
​
 
​
 .
​
 
That's exactly what an RC circuit does:

V
(
t
)
=
V
0
e
−
t
/
R
C
.
V(t)=V 
0
​
 e 
−t/RC
 .
So the model deliberately says:

constant-current ramp
→
RC-like exponential tail
.
constant-current ramp→RC-like exponential tail.
​
 
That part of the model has a very clean physical interpretation.

9. Charging is the mirror image
The charging term is

d
v
d
t
=
s
u
p
h
(
u
)
min
⁡
(
1
,
1
−
v
x
l
i
n
)
.
dt
dv
​
 =s 
up
​
 h(u)min(1, 
x 
lin
​
 
1−v
​
 ).
Far from the upper rail,

1
−
v
>
x
l
i
n
,
1−v>x 
lin
​
 ,
so

d
v
d
t
=
s
u
p
.
dt
dv
​
 =s 
up
​
 .
Therefore

v
(
t
)
=
v
0
+
s
u
p
t
.
v(t)=v 
0
​
 +s 
up
​
 t.
Again, a ramp.

Near 
V
D
D
V 
DD
​
 ,

1
−
v
<
x
l
i
n
,
1−v<x 
lin
​
 ,
so

d
v
d
t
=
s
u
p
x
l
i
n
(
1
−
v
)
.
dt
dv
​
 = 
x 
lin
​
 
s 
up
​
 
​
 (1−v).
Define

w
=
1
−
v
.
w=1−v.
Then

d
w
d
t
=
−
s
u
p
x
l
i
n
w
,
dt
dw
​
 =− 
x 
lin
​
 
s 
up
​
 
​
 w,
giving

1
−
v
=
(
1
−
v
0
)
e
−
s
u
p
x
l
i
n
t
.
1−v=(1−v 
0
​
 )e 
− 
x 
lin
​
 
s 
up
​
 
​
 t
 .
Thus

v
(
t
)
=
1
−
(
1
−
v
0
)
e
−
t
/
τ
u
p
v(t)=1−(1−v 
0
​
 )e 
−t/τ 
up
​
 
 
​
 
with

τ
u
p
=
x
l
i
n
s
u
p
.
τ 
up
​
 = 
s 
up
​
 
x 
lin
​
 
​
 .
​
 
Again: exactly the shape you'd expect from a resistive transistor charging a capacitor near the rail.

10. So what exactly is 
x
l
i
n
x 
lin
​
 ?
In the model,

x
l
i
n
x 
lin
​
 
determines how close to the destination rail you get before the model changes from

constant slew
constant slew
to

exponential slew
.
exponential slew.
For discharge:

v
>
x
l
i
n
⇒
constant rate
v>x 
lin
​
 ⇒constant rate
and

v
<
x
l
i
n
⇒
exponential tail
.
v<x 
lin
​
 ⇒exponential tail.
For charge, the transition occurs around

v
=
1
−
x
l
i
n
.
v=1−x 
lin
​
 .
So if

x
l
i
n
=
0.45
,
x 
lin
​
 =0.45,
the model begins tapering around

v
=
0.45
v=0.45
on discharge and

v
=
0.55
v=0.55
on charge.

Your document describes 
x
l
i
n
x 
lin
​
  as

“where saturation gives way to triode.” 

I would not interpret that literally.

For an ideal long-channel NMOS, the actual saturation-to-triode boundary for full gate drive is

V
o
u
t
=
V
D
D
−
V
T
N
.
V 
out
​
 =V 
DD
​
 −V 
TN
​
 .
If

V
T
=
0.3
V
D
D
,
V 
T
​
 =0.3V 
DD
​
 ,
that would be

v
≈
0.7
,
v≈0.7,
not necessarily 
0.45
0.45.

So I'd interpret 
x
l
i
n
x 
lin
​
  as

an effective transition parameter
an effective transition parameter
​
 
rather than literally the textbook MOS saturation boundary.

It's absorbing the real device's nonlinear I-V curve into a very simple two-region approximation.

That's an important distinction.

11. What does 
h
(
u
)
h(u) mean?
The document annotates 
h
(
u
)
h(u) as the part controlled by 
v
t
v 
t
​
  and 
p
p:

“
v
t
,
p
v 
t
​
 ,p: drive follows the input through the switching threshold.” 

But the markdown you gave me does not actually define the mathematical expression for 
h
(
u
)
h(u). So I shouldn't invent its exact formula.

Conceptually, however, it represents this idea:

The transistor isn't either

0
%
0%
or

100
%
100%
on.

Its current depends strongly on input voltage.

For a MOS transistor in saturation,

I
D
∝
(
V
G
S
−
V
T
)
2
I 
D
​
 ∝(V 
GS
​
 −V 
T
​
 ) 
2
 
in the long-channel square-law approximation.

So if the input only reaches, say,

0.6
V
D
D
,
0.6V 
DD
​
 ,
the transistor may provide substantially less current than with

V
G
S
=
V
D
D
.
V 
GS
​
 =V 
DD
​
 .
Thus the model writes something like

s
u
p
×
h
(
u
)
s 
up
​
 ×h(u)
where

0
≤
h
(
u
)
≤
1.
0≤h(u)≤1.
You can think of it as

h
(
u
)
=
fraction of full transistor drive caused by this input level
.
h(u)=fraction of full transistor drive caused by this input level.
​
 
v
t
v 
t
​
  determines roughly where useful drive begins.

p
p controls how sharply current increases above that threshold.

This is loosely inspired by MOS overdrive behavior

V
O
V
=
V
G
S
−
V
T
V 
OV
​
 =V 
GS
​
 −V 
T
​
 
and

I
D
∝
V
O
V
 
2
I 
D
​
 ∝V 
OV
2
​
 
for the simple long-channel model.

But again:

h
(
u
)
 is a reduced-order approximation, not the MOS equation itself
.
h(u) is a reduced-order approximation, not the MOS equation itself.
​
 
12. Why does 
p
p become invisible under full-swing operation?
This statement in your document actually makes good sense. It says that 
p
p cannot be identified from full-swing behavior because the stage input sits at the rail. 

Suppose

u
=
1.
u=1.
Most normalized drive functions are constructed so that

h
(
1
)
=
1
h(1)=1
regardless of curvature.

For example, hypothetically,

h
(
u
)
=
(
u
−
v
t
1
−
v
t
)
p
.
h(u)=( 
1−v 
t
​
 
u−v 
t
​
 
​
 ) 
p
 .
At

u
=
1
,
u=1,
you get

h
(
1
)
=
(
1
−
v
t
1
−
v
t
)
p
=
1
p
=
1.
h(1)=( 
1−v 
t
​
 
1−v 
t
​
 
​
 ) 
p
 =1 
p
 =1.
So whether

p
=
1
,
1.5
,
2
p=1,1.5,2
doesn't matter.

But if

u
=
0.7
,
u=0.7,
then it matters a lot.

That is why a partial input can reveal 
p
p, while a full-rail input may not.

This is an identifiability issue, not specifically MOS physics.

13. What is 
v
t
v 
t
​
  in the chain model?
Don't confuse this with the physical MOSFET threshold 
V
T
V 
T
​
 .

The document's

v
t
v 
t
​
 
appears to be an effective inverter-stage handoff threshold.

Imagine stage 1 produces

v
1
(
t
)
.
v 
1
​
 (t).
Stage 2 doesn't respond strongly until 
v
1
v 
1
​
  moves sufficiently through its transition region.

A real CMOS inverter has a voltage transfer curve like this:

V
i
n
≈
0
⇒
V
o
u
t
≈
V
D
D
V 
in
​
 ≈0⇒V 
out
​
 ≈V 
DD
​
 
then a high-gain switching region, then

V
i
n
≈
V
D
D
⇒
V
o
u
t
≈
0.
V 
in
​
 ≈V 
DD
​
 ⇒V 
out
​
 ≈0.
There is an effective switching point often called something like

V
M
.
V 
M
​
 .
The model's 
v
t
v 
t
​
  is conceptually closer to

effective inverter switching/handoff level
effective inverter switching/handoff level
​
 
than to an individual transistor's threshold voltage.

Sedra/Smith's CMOS-inverter material is directly relevant here: in the 8th edition, Chapter 16 includes the inverter VTC and CMOS inverter operation. 

14. Why does a chain of stages suppress a short pulse?
Now take

stage 1
→
stage 2
→
stage 3
→
⋯
stage 1→stage 2→stage 3→⋯
Suppose the input pulse is long.

Stage 1 gets enough time to reach nearly the rail:

0
→
1.
0→1.
Stage 2 therefore gets a strong input and also reaches nearly the rail.

Everything propagates normally.

But suppose the pulse ends very early.

Stage 1 might only reach

0.55.
0.55.
Then the input reverses.

Stage 2 therefore never sees a full-strength input.

Maybe stage 2 reaches only

0.35.
0.35.
Then stage 3 sees an even weaker excursion.

Eventually:

0.55
→
0.35
→
0.15
→
0.03
0.55→0.35→0.15→0.03
and the pulse effectively disappears.

That is what the document means by pulse “extinguishing.” 

A physical CMOS circuit doesn't have a magical hard rule saying

u
<
v
t
⇒
I
=
0.
u<v 
t
​
 ⇒I=0.
Instead current becomes progressively small.

The model replaces that continuous transistor behavior with a compact effective threshold.

15. Why does stage count 
K
K matter so much?
Suppose every stage weakens a partial excursion somewhat.

For one stage:

0.8
→
0.7.
0.8→0.7.
Two stages:

0.8
→
0.7
→
0.58.
0.8→0.7→0.58.
Seven stages could turn the same short excursion into something much smaller.

So even if two different chains produce almost the same full transition delay, their response to a partial/truncated pulse can be radically different.

That's a major point of your document, and it is physically plausible.

For normal full-swing switching, you mostly observe:

total delay
+
final edge shape
.
total delay+final edge shape.
Many distributions of delay among stages can produce similar results.

A short pulse tests whether the intermediate nodes had enough time to develop.

That's why 
K
K becomes observable under truncation.

16. The final map(gate) is a different thing
Your document defines a final map as

K
u
=
clip
⁡
(
g
−
v
t
,
m
a
p
1
−
v
t
,
m
a
p
,
0
,
1
)
α
K 
u
​
 =clip( 
1−v 
t,map
​
 
g−v 
t,map
​
 
​
 ,0,1) 
α
 
​
 
up to scaling between off and on levels. 

This is not the pre-driver dynamics.

It says:

Given that the final internal gate has reached value 
g
g, how strongly is the output-stage pullup represented in the IBIS 
K
u
K 
u
​
  coefficient?

Break it down.

If

g
<
v
t
,
m
a
p
,
g<v 
t,map
​
 ,
then the clip makes

K
u
=
0.
K 
u
​
 =0.
If

g
=
1
,
g=1,
then

K
u
=
1.
K 
u
​
 =1.
Between them,

K
u
=
(
g
−
v
t
,
m
a
p
1
−
v
t
,
m
a
p
)
α
.
K 
u
​
 =( 
1−v 
t,map
​
 
g−v 
t,map
​
 
​
 ) 
α
 .
17. What does 
α
α do?
Suppose the normalized intermediate value is

x
=
0.5.
x=0.5.
If

α
=
1
,
α=1,
then

K
u
=
0.5.
K 
u
​
 =0.5.
If

α
=
2
,
α=2,
then

K
u
=
0.25.
K 
u
​
 =0.25.
If

α
=
0.5
,
α=0.5,
then

K
u
≈
0.707.
K 
u
​
 ≈0.707.
So:

α
>
1
α>1
means the map turns on relatively late, while

α
<
1
α<1
means it turns on earlier.

There is a tempting connection to

I
D
∝
(
V
G
S
−
V
T
)
2
,
I 
D
​
 ∝(V 
GS
​
 −V 
T
​
 ) 
2
 ,
but don't interpret 
α
=
2
α=2 as “the MOS square law.”

K
u
K 
u
​
  is an IBIS weighting coefficient, not directly MOS drain current.

Thus:

α
=
empirical curvature of gate state
→
K
u
α=empirical curvature of gate state→K 
u
​
 
​
 
rather than a MOSFET physical exponent.

18. This explains the factorization
The document starts from

K
u
(
t
)
=
map
⁡
(
g
(
t
)
)
.
K 
u
​
 (t)=map(g(t)).
​
 
That's a useful way to think about it. 

There are two separate questions:

Dynamic problem
Where is the internal gate at time 
t
t?

g
(
t
)
g(t)
​
 
That's the pre-driver chain.

Parameters such as

K
,
 
s
u
p
,
 
s
d
n
,
 
v
t
,
 
x
l
i
n
,
 
p
K, s 
up
​
 , s 
dn
​
 , v 
t
​
 , x 
lin
​
 , p
govern this.

Static problem
Given gate position 
g
g, how much of the final output device is effectively on?

K
u
=
f
(
g
)
K 
u
​
 =f(g)
​
 
Parameters such as

v
t
,
m
a
p
,
α
v 
t,map
​
 ,α
govern that.

Together,

input
→
g
(
t
)
⏟
predriver dynamics
→
f
(
g
)
⏟
output-stage map
→
K
u
(
t
)
input→ 
predriver dynamics
g(t)
​
 
​
 → 
output-stage map
f(g)
​
 
​
 →K 
u
​
 (t)
​
 
This separation is conceptually very useful.

19. But why can't ordinary IBIS tell the two apart?
Suppose all you know is

K
u
(
t
)
.
K 
u
​
 (t).
Maybe the true system is:

g
(
t
)
=
slow ramp
g(t)=slow ramp
with an early-turning map.

Or perhaps

g
(
t
)
=
fast ramp
g(t)=fast ramp
with a late-turning map.

Both might produce exactly the same

K
u
(
t
)
.
K 
u
​
 (t).
Mathematically, if

K
u
(
t
)
=
f
(
g
(
t
)
)
,
K 
u
​
 (t)=f(g(t)),
take any monotonic transformation

g
~
(
t
)
=
ϕ
(
g
(
t
)
)
.
g
~
​
 (t)=ϕ(g(t)).
Then define

f
~
(
x
)
=
f
(
ϕ
−
1
(
x
)
)
.
f
~
​
 (x)=f(ϕ 
−1
 (x)).
Now:

f
~
(
g
~
(
t
)
)
=
f
(
ϕ
−
1
(
ϕ
(
g
(
t
)
)
)
)
=
f
(
g
(
t
)
)
=
K
u
(
t
)
.
f
~
​
 ( 
g
~
​
 (t))=f(ϕ 
−1
 (ϕ(g(t))))=f(g(t))=K 
u
​
 (t).
So the measured output cannot distinguish them.

That's the rigorous reason for the document's “factorization” problem.

It's not specifically MOS physics; it's an inverse-problem/identifiability issue.

20. Why does a truncated pulse help?
Consider a normal command:

0
→
1
0→1
and leave it there.

Eventually every reasonable internal model reaches

g
=
1.
g=1.
But now send

0
→
1
→
0
0→1→0
before the chain finishes.

Suppose the reversal occurs when

g
=
0.43
g=0.43
in model A but

g
=
0.78
g=0.78
in model B.

Those models may have looked identical under the normal full-swing transition.

Now their future trajectories differ dramatically.

So the truncated pulse acts like a probe of:

where the hidden internal state was when reversal occurred
.
where the hidden internal state was when reversal occurred.
​
 
That part of your document is conceptually strong.

21. Where does 
C
c
o
m
p
C 
comp
​
  enter?
The output pad current contains not only conductive transistor current but capacitive current:

I
C
=
C
c
o
m
p
d
V
d
t
.
I 
C
​
 =C 
comp
​
  
dt
dV
​
 .
​
 
So conceptually the measured pad current is something like

I
p
a
d
=
I
t
r
a
n
s
i
s
t
o
r
+
C
c
o
m
p
d
V
d
t
I 
pad
​
 =I 
transistor
​
 +C 
comp
​
  
dt
dV
​
 
with sign conventions depending on how currents are defined.

Therefore when extracting the transistor contribution,

I
t
r
a
n
s
i
s
t
o
r
=
I
p
a
d
−
C
c
o
m
p
d
V
d
t
.
I 
transistor
​
 =I 
pad
​
 −C 
comp
​
  
dt
dV
​
 .
That explains an observation in the document. On a rising edge,

d
V
d
t
>
0
,
dt
dV
​
 >0,
while on a falling edge,

d
V
d
t
<
0.
dt
dV
​
 <0.
So an error in 
C
c
o
m
p
C 
comp
​
  affects the two directions with opposite signs. That's why the document says an incorrect 
C
c
o
m
p
C 
comp
​
  can open a rise/fall loop in a plot that would otherwise collapse onto one curve. 

The underlying

I
=
C
 
d
V
/
d
t
I=CdV/dt
physics there is solid.

22. Putting the whole model together
You can mentally reduce the entire proposal to this:

MOS current
→
d
V
d
t
→
predriver trajectory
→
final-gate state
→
K
u
→
pad current
.
MOS current→ 
dt
dV
​
 →predriver trajectory→final-gate state→K 
u
​
 →pad current.
​
 
More explicitly:

V
i
n
p
u
t
(
t
)
V 
input
​
 (t)
goes through

K
 inverter stages
K inverter stages
whose approximate dynamics obey

d
v
d
t
=
available drive
⏟
h
(
u
)
×
max slew
⏟
s
×
rail taper
⏟
min
⁡
(
⋯
 
)
.
dt
dv
​
 = 
h(u)
available drive
​
 
​
 × 
s
max slew
​
 
​
 × 
min(⋯)
rail taper
​
 
​
 .
That produces

g
(
t
)
.
g(t).
Then

K
u
(
t
)
=
f
(
g
(
t
)
)
.
K 
u
​
 (t)=f(g(t)).
Finally the IBIS output stage uses 
K
u
(
t
)
K 
u
​
 (t), 
K
d
(
t
)
K 
d
​
 (t), its I-V tables, and 
C
c
o
m
p
C 
comp
​
  to generate pad behavior.

That is the cleanest interpretation of the architecture.

23. Where to read this in Microelectronic Circuits
If by the “famous book” you mean Sedra & Smith, Microelectronic Circuits, yes—it's almost exactly the right textbook background.

For the 8th edition, I'd read these in this order:

Chapter 5 — MOS Field-Effect Transistors

The most relevant parts are the sections on applying 
v
D
S
v 
DS
​
 , channel pinch-off/current saturation, p-channel MOSFETs, and the 
i
D
−
v
D
S
i 
D
​
 −v 
DS
​
  characteristics. Those give you the physics behind

current-source-like saturation
→
triode/resistive behavior
.
current-source-like saturation→triode/resistive behavior.
The detailed TOC puts these around §§5.1.4–5.1.7 and §5.2. 

Then read Chapter 16 — CMOS Digital Logic Circuits, especially the CMOS inverter and its voltage-transfer characteristic. That's the foundation for understanding the stage switching threshold and why an intermediate input voltage gives only partial drive. 

Most directly related to your predriver chain is Chapter 17 — Digital Design: Power, Speed, and Area. It explicitly covers dynamic operation of the CMOS inverter, propagation delay, load capacitance, transistor sizing, fan-in/fan-out, and “Driving a Large Capacitance.” 

The 8th-edition structure is officially listed by Oxford as Chapter 5 MOSFETs, Chapter 16 CMOS Digital Logic Circuits, and Chapter 17 Digital Design: Power, Speed, and Area. 

The one conceptual correction I would keep in mind
When reading your document, don't think:

the proposed equation IS the MOSFET physics
.
the proposed equation IS the MOSFET physics.
​
 
Think:

MOS physics
⟹
a plausible simplified stage equation
.
MOS physics⟹a plausible simplified stage equation.
​
 
The real transistor follows nonlinear equations such as

I
D
(
V
G
S
,
V
D
S
,
V
B
S
,
…
)
.
I 
D
​
 (V 
GS
​
 ,V 
DS
​
 ,V 
BS
​
 ,…).
The proposed model compresses all of that into something like:

input-dependent drive
×
current-limited slew
×
rail-dependent taper
.
input-dependent drive×current-limited slew×rail-dependent taper.
​
 
That simplification is precisely why the model only needs a handful of parameters.

And of all the equations in the document, the most important physical chain to remember is:

I
D
(
V
G
S
,
V
D
S
)
⟹
I
=
C
d
V
d
t
⟹
V
s
t
a
g
e
(
t
)
⟹
g
(
t
)
⟹
K
u
(
t
)
.
I 
D
​
 (V 
GS
​
 ,V 
DS
​
 )⟹I=C 
dt
dV
​
 ⟹V 
stage
​
 (t)⟹g(t)⟹K 
u
​
 (t).
​
 
Once that chain is clear, most of the recipe becomes much easier to reason about.

so we assume we're working in the saturation region? and so if Vgs is fixed I_D is about constant, but doesn't Vgs keep chaning?
i see later you explained. so this model tried to model/approximate both regions: current source for the saturation region, and another equation for the triode region?
Yes to both, with one important refinement.

Do we assume saturation, and what about changing 
V
G
S
V 
GS
​
 ?
For the simplest full-swing inverter analysis, we often assume the input has already switched to a rail, so for the conducting NMOS:

V
G
S
≈
V
D
D
V 
GS
​
 ≈V 
DD
​
 
and is therefore approximately fixed. Then, while the NMOS is in saturation,

I
D
≈
1
2
β
(
V
G
S
−
V
T
)
2
I 
D
​
 ≈ 
2
1
​
 β(V 
GS
​
 −V 
T
​
 ) 
2
 
so 
I
D
I 
D
​
  is approximately constant as 
V
o
u
t
V 
out
​
  changes.

But you are right: during a real finite-slew input edge, 
V
G
S
V 
GS
​
  is changing.

That is exactly why the model has the factor

h
(
u
)
h(u)
in

d
v
d
t
=
−
s
d
n
 
h
(
1
−
u
)
 
min
⁡
(
1
,
v
x
l
i
n
)
.
dt
dv
​
 =−s 
dn
​
 h(1−u)min(1, 
x 
lin
​
 
v
​
 ).
Conceptually:

h
(
u
)
 models changing gate drive
h(u) models changing gate drive
​
 
while

min
⁡
(
⋯
 
)
 models changing 
V
D
S
/output-region behavior
min(⋯) models changing V 
DS
​
 /output-region behavior
​
 
So the model is not really saying:

“
V
G
S
V 
GS
​
  is always fixed.”

It is saying:

“When the input is fully at the rail, the maximum available drive is roughly current-limited; if the input is only partially there, reduce that drive according to 
h
(
u
)
h(u).”

That matches the description in the document, where 
v
t
,
p
v 
t
​
 ,p are associated with how the drive follows the input through its switching region. 

A useful decomposition is:

I
D
≈
I
max
⁡
×
h
(
V
G
S
)
⏟
gate-drive dependence
×
q
(
V
D
S
)
⏟
output-voltage dependence
.
I 
D
​
 ≈I 
max
​
 × 
gate-drive dependence
h(V 
GS
​
 )
​
 
​
 × 
output-voltage dependence
q(V 
DS
​
 )
​
 
​
 .
The proposed model is essentially doing this in normalized form.

Yes: it is trying to approximate both saturation and triode behavior.
That's the core idea.

For a discharging NMOS, simplify the model to

d
v
d
t
=
−
s
d
n
h
(
1
−
u
)
min
⁡
(
1
,
v
x
l
i
n
)
.
dt
dv
​
 =−s 
dn
​
 h(1−u)min(1, 
x 
lin
​
 
v
​
 ).
Assume first that the input is fully asserted:

h
(
1
−
u
)
=
1.
h(1−u)=1.
Then there are two regimes.

Regime 1: saturation/current-limited approximation
When

v
>
x
l
i
n
,
v>x 
lin
​
 ,
the min term becomes 1:

d
v
d
t
=
−
s
d
n
.
dt
dv
​
 =−s 
dn
​
 .
Therefore the voltage falls at approximately constant slope:

v
(
t
)
=
v
0
−
s
d
n
t
.
v(t)=v 
0
​
 −s 
dn
​
 t.
Because

I
=
C
d
V
d
t
,
I=C 
dt
dV
​
 ,
constant 
d
v
/
d
t
dv/dt means approximately constant current:

I
≈
constant
.
I≈constant.
So this corresponds to the model's approximation of

MOS saturation
→
current-source-like behavior
.
MOS saturation→current-source-like behavior
​
 .
Regime 2: triode/resistive approximation
Once

v
<
x
l
i
n
,
v<x 
lin
​
 ,
the equation becomes

d
v
d
t
=
−
s
d
n
x
l
i
n
v
.
dt
dv
​
 =− 
x 
lin
​
 
s 
dn
​
 
​
 v.
Now current decreases as the output voltage decreases:

I
∝
v
.
I∝v.
That's exactly the form you'd get from a resistor:

I
=
V
R
.
I= 
R
V
​
 .
Combined with

I
=
C
d
V
d
t
,
I=C 
dt
dV
​
 ,
you get

C
d
V
d
t
=
−
V
R
,
C 
dt
dV
​
 =− 
R
V
​
 ,
or

d
V
d
t
=
−
1
R
C
V
.
dt
dV
​
 =− 
RC
1
​
 V.
Hence

V
(
t
)
=
V
0
e
−
t
/
R
C
.
V(t)=V 
0
​
 e 
−t/RC
 .
So:

triode near the destination rail
≈
resistor charging/discharging 
C
triode near the destination rail≈resistor charging/discharging C
​
 
and the model reproduces that with the second branch of the min() term.

The document explicitly describes 
x
l
i
n
x 
lin
​
  as the point where its current-limited behavior gives way to the triode-like behavior. 

The best way to visualize the whole approximation is:

Input changes
Input changes
↓
↓
V
G
S
 changes
V 
GS
​
  changes
controlled approximately by

h
(
u
)
h(u)
​
 
↓
↓
Then, for whatever gate drive exists, the output transistor sees changing 
V
D
S
V 
DS
​
 :

saturation-like region
→
triode-like region
saturation-like region→triode-like region
​
 
represented by

min
⁡
(
1
,
v
x
l
i
n
)
min(1, 
x 
lin
​
 
v
​
 )
​
 
for discharge.

So you can almost read the model as

d
v
d
t
=
maximum slew
⏟
s
×
how strongly gate is driving
⏟
h
(
u
)
×
saturation vs. triode effect
⏟
min
⁡
(
⋯
 
)
dt
dv
​
 = 
s
maximum slew
​
 
​
 × 
h(u)
how strongly gate is driving
​
 
​
 × 
min(⋯)
saturation vs. triode effect
​
 
​
 
​
 
That is probably the cleanest physical interpretation.

One caveat: the model is not using the actual MOS triode equation

I
D
=
β
[
(
V
G
S
−
V
T
)
V
D
S
−
V
D
S
2
2
]
.
I 
D
​
 =β[(V 
GS
​
 −V 
T
​
 )V 
DS
​
 − 
2
V 
DS
2
​
 
​
 ].
Instead it replaces it near the rail with the simpler approximation

I
D
∝
V
D
S
.
I 
D
​
 ∝V 
DS
​
 .
So it is best described as:

a two-regime reduced-order approximation of MOS behavior
a two-regime reduced-order approximation of MOS behavior
​
 
rather than a direct implementation of the MOS equations.
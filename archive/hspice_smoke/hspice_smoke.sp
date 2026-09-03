* Minimal HSPICE smoke test
.option post=2
v1 in 0 pulse(0 1 0 1n 1n 5n 10n)
r1 in 0 1k
.tran 1n 20n
.end

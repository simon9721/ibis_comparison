Test Xyce simulations
No tasks in progress


Xyce is on my desktop. can you check if it's working by running actual simulations?
Saturday 10:33 PM


Worked for 2m 51s
I checked by trying to run an actual Xyce transient smoke-test netlist, not just by looking for files.

Result: Xyce is not currently working/available from the Desktop environment.

What I found:

Xyce / xyce is not on PATH in PowerShell.
Xyce is also not available inside MSYS Bash.
I searched under C:\Users\simom and C:\msys64 and did not find Xyce.exe.
The only Xyce-related evidence on the Desktop is:
haast\xyce-continue2.log
PySpice’s Xyce support folder
a BAV21.lib@xyce model file
The xyce-continue2.log shows the attempted Xyce build failed while linking Trilinos, with undefined references in Ifpack.
ngspice is installed at:

C:\Users\simom\Desktop\spice\ngspice-46_64\Spice64\bin\ngspice.exe

So the practical answer is: ngspice is present, but Xyce itself does not appear to be installed or successfully built right now.

2 files changed
+7
-7
Undo

Review

xyce_smoke_test.cir
xyce_smoke_test.cir




Saturday 10:35 PM
im sure it's intalled somether, can you check?
Saturday 10:36 PM


Worked for 3m 41s
You were right, it is installed. I found it here:

C:\Program Files\XyceNF_7.10\bin\Xyce.exe

I ran actual simulations with it:

Version check: XyceNF Release 7.10.0
DC divider smoke test: 1 V -> 1k/1k divider -> 0.5 V, and Xyce produced V(OUT) = 5.00000000e-01
Transient RC smoke test: completed successfully with 83 successful steps, 0 failed linear solves, and generated the expected charging/discharging waveform data
So yes: Xyce is installed and working. It just isn’t on your normal PATH, which is why Xyce failed from a regular PowerShell prompt. Use the full path, or launch through the “Xyce 7.10 NORAD Command Prompt” shortcut.

2 files changed
+14
-0
Undo

Review

xyce_dc_smoke.cir
xyce_tran_smoke.cir




Saturday 10:40 PM
ok now in my download folder there's xdm-2.6.0-win64. can you install and test that for me?
Saturday 10:44 PM


Worked for 16m 40s
Installed and tested.

XDM is installed here:

C:\Users\simom\AppData\Local\XDM_2.6.0

Use it with:

C:\Users\simom\AppData\Local\XDM_2.6.0\bin\xdm.bat --help
A few notes from the install:

The ZIP was portable, not a normal installer.
Its bundled EXE was broken as-shipped on this machine because the package contains debug-built native Python modules but not all the runtime pieces they need.
I fixed it locally by adding:
Python 3.9 embeddable runtime
proper Boost Python 1.77 debug DLL from NuGet
Windows SDK debug UCRT
a small xdm.bat launcher that sets the native DLL paths correctly
Test result:

XDM --help works and reports xdm 2.6.0.
I converted a small PSpice RC transient netlist to Xyce format.
Then I ran the translated netlist with your Xyce 7.10 install.
Xyce completed successfully with 0 failed linear solves and 0 nonlinear convergence failures, and generated valid probe data for V(IN) and V(OUT).
So: XDM is installed and working, but use the new xdm.bat launcher rather than the original xdm_bdl.exe.

3 files changed
+26
-0
Undo

Review

xdm.bat
xdm_launcher.py
xdm_test_pspice.cir




Saturday 11:00 PM
nice. now, look at the ibis_comparison_plan.md in /ibis_comparison. can you follow the plan and look at what was done in ngpisce and repeat in xyce?
Saturday 11:14 PM


Worked for 10m 10s
Done. I followed the plan and repeated the relevant ngspice work in Xyce.

The useful result: Xyce successfully runs the transistor-level io_buf.sp reference case.

Created:

XYCE_RESULTS_2026-05-09.md (line 1)
xyce_refspice
xyce_pybis
Key outcomes:

xyce_refspice/tb_refspice_pulse_new50ohm_xyce.cir: PASS, 20 ns completed.
xyce_refspice/tb_refspice_prbs7_new50ohm_xyce.cir: PASS, 1000 ns completed in 2.46 s.
xyce_pybis/tb_validation_pulse_xyce_pybis.cir: syntax port works, but simulation stalls around 1.092 ns.
xyce_pybis/tb_pybis_prbs7_new50ohm_xyce.cir: fails DCOP.
xyce_pybis/tb_pybis_prbs7_new50ohm_xyce_uic_100n.cir: gets past startup, then stalls at first PRBS rising edge around 35.174 ns.
I also updated ibis_comparison_plan.md (line 37) with Xyce experiment rows and a short addendum.

Bottom line: Xyce is solid for the transistor-level reference flow, but the pybis2spice behavioral model is not numerically portable to Xyce yet. It can be made syntactically valid, but its B-source/table timing network hits timestep/DCOP traps.


README.md
Document · MD
Open


README.md
Document · MD
Open


XYCE_RESULTS_2026-05-09.md
Document · MD
Open


ibis_comparison_plan.md
Document · MD
Open

15 files changed
+321
-26
Undo

Review

README.md
tb_pybis_prbs7_new50ohm_xyce.cir
tb_validation_pulse_xyce_pybis.cir
_xyce_expr_probe.cir
_xyce_pwl_probe.cir
_xyce_table_probe.cir
README.md
tb_refspice_prbs7_new50ohm_xyce.cir
tb_refspice_pulse_new50ohm_xyce.cir
tb_pybis_prbs7_new50ohm_xyce_uic_100n.cir
XYCE_RESULTS_2026-05-09.md
ibis_comparison_plan.md
_xyce_expr_probe.cir
_xyce_pwl_probe.cir
_xyce_table_probe.cir




Saturday 11:24 PM
ok please work on the pybis cases. start with simpler cases (for example just one rising edge etc.) don't jump to prbs stream yet
Saturday 11:26 PM


Worked for 11m 17s
I worked the pybis side from the bottom up, no PRBS jump.

Main breakthrough: the direct Xyce syntax port is too sharp numerically, but a Xyce-only relaxed model works for simple deterministic cases.

Created:

driver_OutputInput_Typical_xyce_relaxed.sub
Simple Rload decks:
tb_test_rise_late_xyce_uic_relaxed.cir
tb_test_rfr_xyce_uic_relaxed.cir
tb_test_rfall_late_xyce_uic_relaxed.cir
Simple T-line deck:
tb_validation_pulse_200p_tline_xyce_relaxed.cir
Simple new-channel decks:
tb_channel_rise_200p_xyce_relaxed.cir
tb_channel_rfr_200p_xyce_relaxed.cir
What changed in the relaxed model:

tanh(200*...) gates were changed to tanh(20*...)
This is Xyce-only for now, and should be treated as a numerical experiment, not final correlation truth yet.
Results:

Delayed 200 ps rise into 50 ohm Rload: PASS to 20 ns
Fast 200 ps rise/fall into 50 ohm Rload: PASS to 20 ns
Slow delayed rise/fall into 50 ohm Rload: PASS to 20 ns
200 ps pulse into ideal 50 ohm T-line: PASS to 20 ns
200 ps rise into new 50 ohm RLGC channel: PASS to 30 ns
200 ps rise/fall into new 50 ohm RLGC channel: PASS to 30 ns
Still true:

no-uic pybis decks fail DCOP in Xyce
original sharp-gate pybis model stalls near threshold crossings
original 5 ps compact pulse still stalls even relaxed, so 200 ps edges are the sane next baseline
I updated XYCE_RESULTS_2026-05-09.md (line 150) and xyce_pybis/README.md (line 1) with the new findings. No Xyce processes are left running.


XYCE_RESULTS_2026-05-09.md
Document · MD
Open


README.md
Document · MD
Open

10 files changed
+208
-4
Undo

Review

tb_test_rfr_xyce.cir
tb_test_rise_fall_xyce.cir
tb_test_rise_xyce.cir
tb_test_rfall_late_xyce_uic.cir
tb_test_rise_late_xyce_uic.cir
tb_validation_pulse_200p_tline_xyce_relaxed.cir
XYCE_RESULTS_2026-05-09.md
README.md
tb_channel_rfr_200p_xyce_relaxed.cir
tb_channel_rise_200p_xyce_relaxed.cir




Saturday 11:38 PM
ok what's next? continue testing and plot meaniful results for me to review.
Saturday 11:39 PM


Worked for 9m
Continued the pybis/Xyce testing and made review plots.

What changed:

Ran tb_channel_twopulse_200p_xyce_relaxed.cir: completed to 20 ns.
Ran tb_channel_pulsetrain_200p_xyce_relaxed10.cir: completed to 40 ns in ~3.6s.
Added plots and metrics via plot_xyce_pybis_progress.py.
Updated notes in XYCE_RESULTS_2026-05-09.md and xyce_pybis/README.md.
Main review files:

Xyce vs ngspice Rload overlay
Rload comparison metrics
Xyce relaxed channel cases
Two-pulse channel result
Relaxed10 pulse-train result
All Xyce relaxed metrics
Key takeaway: tanh20 now works through single edge, rise/fall, and two isolated pulses, but still bogs down on repeated switching. tanh10 completes the repeated pulse train, so the next useful step is tuning smoothing against ngspice accuracy before touching PRBS. No Xyce process is left running.


XYCE_RESULTS_2026-05-09.md
Document · MD
Open


README.md
Document · MD
Open


xyce_vs_ngspice_pybis_rload_overlay.png
Image · PNG
Open


xyce_vs_ngspice_pybis_rload_metrics.csv
Spreadsheet · CSV
Open


xyce_pybis_relaxed_channel_cases.png
Image · PNG
Open


xyce_pybis_relaxed_twopulse.png
Image · PNG
Open


xyce_pybis_relaxed10_pulsetrain.png
Image · PNG
Open


xyce_pybis_relaxed_metrics.csv
Spreadsheet · CSV
Open

7 files changed
+454
-7
Undo

Review

tb_channel_pulsetrain_200p_xyce_relaxed.cir
plot_xyce_pybis_progress.py
XYCE_RESULTS_2026-05-09.md
README.md
tb_channel_pulsetrain_200p_xyce_relaxed10.cir
tb_channel_twopulse_200p_xyce_relaxed.cir
plot_xyce_pybis_progress.py




Saturday 11:48 PM

You’re out of Codex messages
Your rate limit resets on May 12, 2026, 9:49 PM. To continue using Codex, add credits or upgrade to Pro today.
Upgrade
Add Credits




Full access




Work locally

Progress
Inspect pybis/Xyce stress runner and patch obvious issues
Run two clean stress cases across ngspice/Xyce refspice and pybis
Generate and inspect eye, edge-family, and transient overlays
Add and run coarse 30 cm cross-flow stress setup
Summarize what improved and what remains unstable

Artifacts

README.md

README.md

README.md

README.md

stress_matrix_summary.png

ui2_len30cm_loss5_eye_overlay.png
Show 83 more

Sources
Web search

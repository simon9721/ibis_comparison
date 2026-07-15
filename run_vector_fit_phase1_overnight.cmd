@echo off
setlocal

set STUDY=results\sparam_vector_fit_campaign_v2_phase1_overnight_2026-06-18
set SKRF_TARGET=%TEMP%\ibis_skrf_target
set NGSPICE=\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\ngspice-46_64\Spice64\bin\ngspice.exe
set HSPICE=hspice

set CANDS=auto_fit_default,auto_fit_tight,auto_fit_low_order,auto_fit_high_order,vector_3r3c_lin,vector_3r3c_log,vector_5r5c_lin,vector_5r5c_log,vector_8r8c_lin,vector_8r8c_log,vector_12r12c_lin,vector_12r12c_log,vector_0r4c_lin,vector_2r6c_lin,vector_4r8c_lin
set PREP=raw,dc_hold,freq_trim_0p95,freq_trim_0p9,hf_hold,hf_rolloff_20db_dec

set CHANS=--channel-id Clarity_example_acf20e4a --channel-id Clarity_example_Fitted_55b55a71 --channel-id ntwk2_e1c16499 --channel-id ntwk3_ad74ab42 --channel-id ntwk2_24638a5f --channel-id ntwk3_8f8a2430 --channel-id Ch10_35_5F3N_f4_fc94db99 --channel-id Ch10_35_5F3N_t_d3c7dddc --channel-id Ch3_17_5F3N_f3_c08ef229

if not exist "%STUDY%\logs" mkdir "%STUDY%\logs"

echo ========== 01 vector-fit fitting ==========
py -3.14 -u scripts\run_sparam_vector_fit_campaign.py fit ^
  --study-dir "%STUDY%" ^
  --skrf-target "%SKRF_TARGET%" ^
  --skrf-tests-dir results\sparam_conversion_quality_2026-06-08\inputs\skrf_tests ^
  --extra-touchstone-dir hspice\sparam ^
  --phase-profile phase1 ^
  --candidate-profile expanded ^
  --candidates "%CANDS%" ^
  --preprocess "%PREP%" ^
  %CHANS% ^
  --workers 2 ^
  --resume ^
  --candidate-timeout-s 300 ^
  --passivity-strategy near-pass ^
  --enforce-samples-list 200,2000 ^
  --enforce-fmax-list original,high ^
  --enforce-preserve-dc-list true,false ^
  --dense-samples 301 ^
  --resample-points 201 ^
  --impulse-samples 1024 ^
  > "%STUDY%\logs\01_fit.log" 2>&1

echo ========== 02 ngspice smoke ==========
py -3.14 -u scripts\run_sparam_vector_fit_campaign.py smoke-ngspice ^
  --study-dir "%STUDY%" ^
  --skrf-target "%SKRF_TARGET%" ^
  --ngspice "%NGSPICE%" ^
  --sim-timeout 180 ^
  > "%STUDY%\logs\02_smoke.log" 2>&1

echo ========== 03 hspice audit ==========
py -3.14 -u scripts\run_sparam_vector_fit_campaign.py audit-hspice ^
  --study-dir "%STUDY%" ^
  --skrf-target "%SKRF_TARGET%" ^
  --ngspice "%NGSPICE%" ^
  --hspice "%HSPICE%" ^
  --audit-top-k 3 ^
  --sim-timeout 240 ^
  --audit-stop-ns 35 ^
  --resume ^
  > "%STUDY%\logs\03_audit.log" 2>&1

echo ========== 04 report ==========
py -3.14 -u scripts\run_sparam_vector_fit_campaign.py report ^
  --study-dir "%STUDY%" ^
  > "%STUDY%\logs\04_report.log" 2>&1

echo DONE

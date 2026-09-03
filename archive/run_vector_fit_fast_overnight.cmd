@echo off
setlocal

cd /d C:\Users\sh3qm\code\ibis_comparison

set STUDY=results\sparam_vector_fit_campaign_v1_2026-06-17_fast_overnight_v2
set NGSPICE=\\minerfiles.mst.edu\dfs\users\sh3qm\Downloads\ngspice-46_64\Spice64\bin\ngspice_con.exe
set HSPICE=C:\synopsys\Hspice_T-2022.06\WIN64\hspice.com
set SKRF_TARGET=%TEMP%\ibis_skrf_target
set SKRF_TESTS=results\sparam_conversion_quality_2026-06-08\inputs\skrf_tests
set EXTRA_TOUCHSTONE=hspice\sparam

if not exist "%NGSPICE%" (
  echo Missing NGSPICE: %NGSPICE%
  exit /b 1
)

if not exist "%HSPICE%" (
  echo Missing HSPICE: %HSPICE%
  exit /b 1
)

if not exist "%SKRF_TARGET%" (
  echo Missing scikit-rf target: %SKRF_TARGET%
  exit /b 1
)

if not exist "%SKRF_TESTS%" (
  echo Missing scikit-rf tests: %SKRF_TESTS%
  exit /b 1
)

if not exist "%EXTRA_TOUCHSTONE%" (
  echo Missing Touchstone folder: %EXTRA_TOUCHSTONE%
  exit /b 1
)

mkdir "%STUDY%\logs" 2>nul

echo ========== 01 vector-fit pilot fitting ==========
py -3.14 -u scripts\run_sparam_vector_fit_campaign.py fit ^
  --study-dir "%STUDY%" ^
  --skrf-target "%SKRF_TARGET%" ^
  --skrf-tests-dir "%SKRF_TESTS%" ^
  --extra-touchstone-dir "%EXTRA_TOUCHSTONE%" ^
  --candidate-profile pilot ^
  --preprocess raw,dc_hold ^
  --dense-samples 201 ^
  --max-channels 40 ^
  > "%STUDY%\logs\01_fit.log" 2>&1

if errorlevel 1 (
  echo FIT FAILED. See %STUDY%\logs\01_fit.log
  exit /b 1
)

echo ========== 02 ngspice smoke ==========
py -3.14 -u scripts\run_sparam_vector_fit_campaign.py smoke-ngspice ^
  --study-dir "%STUDY%" ^
  --skrf-target "%SKRF_TARGET%" ^
  --ngspice "%NGSPICE%" ^
  --sim-timeout 180 ^
  > "%STUDY%\logs\02_smoke_ngspice.log" 2>&1

if errorlevel 1 (
  echo NGSPICE SMOKE FAILED. See %STUDY%\logs\02_smoke_ngspice.log
  exit /b 1
)

echo ========== 03 HSPICE audit ==========
py -3.14 -u scripts\run_sparam_vector_fit_campaign.py audit-hspice ^
  --study-dir "%STUDY%" ^
  --skrf-target "%SKRF_TARGET%" ^
  --ngspice "%NGSPICE%" ^
  --hspice "%HSPICE%" ^
  --sim-timeout 240 ^
  --audit-stop-ns 35 ^
  --max-channels 20 ^
  --resume ^
  > "%STUDY%\logs\03_audit_hspice.log" 2>&1

if errorlevel 1 (
  echo HSPICE AUDIT FAILED. See %STUDY%\logs\03_audit_hspice.log
  exit /b 1
)

echo ========== 04 report ==========
py -3.14 -u scripts\run_sparam_vector_fit_campaign.py report ^
  --study-dir "%STUDY%" ^
  --skrf-target "%SKRF_TARGET%" ^
  > "%STUDY%\logs\04_report.log" 2>&1

if errorlevel 1 (
  echo REPORT FAILED. See %STUDY%\logs\04_report.log
  exit /b 1
)

echo DONE.
echo Main report: %STUDY%\README.md
exit /b 0

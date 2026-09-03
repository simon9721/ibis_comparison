# Suggested commands from optimize_ngspice_sparam_flow.py

$target = Join-Path $env:TEMP 'ibis_skrf_target'

# Direct-route channels: run normal vector-fit/ngspice/HSPICE audit.
py -3.14 scripts/run_sparam_conversion_quality_study.py run --skrf-target $target --manifest C:\Users\sh3qm\code\ibis_comparison\results\sparam_ngspice_flow_optimized_2026-06-08\manifest_direct_vector_fit.csv --study-dir C:\Users\sh3qm\code\ibis_comparison\results\sparam_ngspice_flow_optimized_2026-06-08\direct_vector_fit_study --candidates auto_fit,vector_1r1c,vector_2r2c,vector_3r3c,vector_4r4c,vector_5r5c,vector_6r6c,vector_8r8c --smoke-stop-ns 12.0 --audit-stop-ns 12.0

# Delay-aware channels: do not accept direct vector-fit export as final.
# Use the per-channel recommended_audit_stop_ns from manifest_delay_aware_required.csv
# with run_native_hspice_sparam_audit.py and the delay-aware prototype until a delayed macromodel exporter is implemented.

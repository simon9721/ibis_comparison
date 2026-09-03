# Simulated IBIS Files And Models

- Unique IBIS files: `4`
- Unique applicable models: `4`
- Exact duplicate files are suppressed by SHA-256, matching the full-swing and stress campaigns.

| IBIS file | Component | Model | Type | VCC | Full swing | Legacy high/low | Value-match high/low | Gate full high/low | Gate hybrid high/low |
|---|---|---|---|---:|---|---|---|---|---|
| inv_t2b.ibs | invchain | driver3 | Output | 1.8 | COMPLETED | COMPLETED/COMPLETED | COMPLETED/COMPLETED | COMPLETED/COMPLETED | COMPLETED/COMPLETED |
| io_buf.ibs | MCM Driver 1 | driver | I/O | 3.3 | COMPLETED | COMPLETED/COMPLETED | COMPLETED/COMPLETED | COMPLETED/COMPLETED | COMPLETED/COMPLETED |
| sample1(original).ibs | WXY123 | BPOZ2F | 3-state | 3.3 | COMPLETED | COMPLETED/COMPLETED | COMPLETED/COMPLETED | COMPLETED/COMPLETED | COMPLETED/COMPLETED |
| stm32g031_041_ufqfpn32.ibs | stm32g031_041_ufqfpn32 | ioms8p_sudq_ft_lv | I/O | 1.8 | COMPLETED | COMPLETED/COMPLETED | COMPLETED/NGSPICE_TIMEOUT | NGSPICE_TIMEOUT/COMPLETED | COMPLETED/NGSPICE_TIMEOUT |

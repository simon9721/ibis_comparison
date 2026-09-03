# Optimized ngspice S-parameter Flow

## Routing Rules

- Direct vector-fit route when dominant delay < `2.0` ns or delay-bandwidth product < `40.0` cycles.
- Delay-aware route when both thresholds are exceeded.
- Direct-route transient stop stays at `12.0` ns.
- Delay-aware transient stop is `dominant_delay_ns + 20.0` ns, minimum `12.0` ns.

## Summary

- `delay_aware_required`: 150
- `direct_vector_fit`: 31

## Channels

| channel | ports | dominant path | delay (ns) | cycles at fmax | route | action |
|---|---:|---:|---:|---:|---|---|
| `Clarity_example_4669a7eb` | 2 | `S21` | 0.3591 | 0.7182 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch10_35_5F3N_f1_49905299` | 4 | `S42` | 15.53 | 776.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_5F3N_f2_f23c49e2` | 4 | `S13` | 2.867 | 143.3 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_5F3N_f3_81049e25` | 4 | `S13` | 14 | 700 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_5F3N_f4_fc94db99` | 4 | `S13` | 13.94 | 697 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_5F3N_f5_3a904f20` | 4 | `S13` | 10.27 | 513.4 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_5F3N_n1_8e377765` | 4 | `S13` | 1.283 | 64.13 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch10_35_5F3N_n2_b3e24295` | 4 | `S13` | 1.111 | 55.57 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch10_35_5F3N_n3_a9ef8f2b` | 4 | `S13` | 1.237 | 61.83 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch10_35_5F3N_t_d3c7dddc` | 4 | `S31` | 13.98 | 699.2 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_5F3N_f1_8f9c2982` | 4 | `S31` | 2.534 | 126.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_5F3N_f2_47dc69c2` | 4 | `S13` | 2.601 | 130 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_5F3N_f3_ab427591` | 4 | `S13` | 2.498 | 124.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_5F3N_f4_dfb4f0b9` | 4 | `S31` | 2.621 | 131.1 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_5F3N_f5_30ca600f` | 4 | `S42` | 2.753 | 137.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_5F3N_n1_9a8781a5` | 4 | `S13` | 1.283 | 64.13 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch1_10_5F3N_n2_a8ccad10` | 4 | `S13` | 1.111 | 55.57 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch1_10_5F3N_n3_3af593d3` | 4 | `S13` | 1.237 | 61.83 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch1_10_5F3N_t_9f42119e` | 4 | `S31` | 2.436 | 121.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_5F3N_f1_3378b0a3` | 4 | `S31` | 3.056 | 152.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_5F3N_f2_d795f530` | 4 | `S31` | 3.063 | 153.2 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_5F3N_f3_c4aa62ca` | 4 | `S42` | 3.021 | 151 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_5F3N_f4_5d940b85` | 4 | `S31` | 3.111 | 155.6 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_5F3N_f5_f42d0440` | 4 | `S13` | 3.278 | 163.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_5F3N_n1_a8c804cf` | 4 | `S13` | 1.283 | 64.13 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch2_12_5F3N_n2_7df3d449` | 4 | `S13` | 1.111 | 55.57 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch2_12_5F3N_n3_0722c1a4` | 4 | `S13` | 1.237 | 61.83 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch2_12_5F3N_t_6b0325a2` | 4 | `S42` | 2.96 | 148 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_5F3N_f1_ea073bed` | 4 | `S42` | 4.537 | 226.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_5F3N_f2_88fcb92b` | 4 | `S24` | 4.466 | 223.3 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_5F3N_f3_c08ef229` | 4 | `S13` | 4.507 | 225.3 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_5F3N_f4_efc6aab7` | 4 | `S31` | 4.571 | 228.5 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_5F3N_f5_2005253f` | 4 | `S24` | 4.676 | 233.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_5F3N_n1_154e3882` | 4 | `S13` | 1.283 | 64.13 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch3_17_5F3N_n2_6af9a3d7` | 4 | `S13` | 1.111 | 55.57 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch3_17_5F3N_n3_7c2c38b4` | 4 | `S13` | 1.237 | 61.83 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch3_17_5F3N_t_b5beac5f` | 4 | `S31` | 4.455 | 222.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_5F3N_f1_3d23614b` | 4 | `S42` | 9.052 | 452.6 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_5F3N_f2_82231e3b` | 4 | `S42` | 9.02 | 451 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_5F3N_f3_f9f1e38c` | 4 | `S31` | 9.064 | 453.2 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_5F3N_f4_b2aeb782` | 4 | `S31` | 9.057 | 452.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_5F3N_f5_fb83e9a3` | 4 | `S13` | 9.093 | 454.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_5F3N_n1_18bbe129` | 4 | `S13` | 1.283 | 64.13 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch4_20_5F3N_n2_63b78e89` | 4 | `S13` | 1.111 | 55.57 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch4_20_5F3N_n3_3aef7b19` | 4 | `S13` | 1.237 | 61.83 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch4_20_5F3N_t_78b3548c` | 4 | `S31` | 8.994 | 449.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_5F3N_f1_ceb18ce3` | 4 | `S42` | 6.054 | 302.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_5F3N_f2_46ed874c` | 4 | `S24` | 5.938 | 296.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_5F3N_f3_8c03a4fd` | 4 | `S13` | 5.982 | 299.1 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_5F3N_f4_23652cf6` | 4 | `S13` | 6.014 | 300.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_5F3N_f5_45e65429` | 4 | `S13` | 5.98 | 299 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_5F3N_n1_5e444e53` | 4 | `S13` | 1.283 | 64.13 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch5_22_5F3N_n2_62fabfed` | 4 | `S13` | 1.111 | 55.57 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch5_22_5F3N_n3_b15f7e50` | 4 | `S13` | 1.237 | 61.83 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch5_22_5F3N_t_cd60ff78` | 4 | `S31` | 5.941 | 297 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_5F3N_f1_fbd74da8` | 4 | `S24` | 9.598 | 479.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_5F3N_f2_607adf50` | 4 | `S24` | 9.533 | 476.6 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_5F3N_f3_bcc9d6b5` | 4 | `S13` | 9.588 | 479.4 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_5F3N_f4_ade4d318` | 4 | `S13` | 9.51 | 475.5 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_5F3N_f5_259b77ba` | 4 | `S13` | 9.555 | 477.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_5F3N_n1_b477e2ca` | 4 | `S13` | 1.283 | 64.13 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch6_25_5F3N_n2_1d1f7481` | 4 | `S13` | 1.111 | 55.57 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch6_25_5F3N_n3_96915930` | 4 | `S13` | 1.237 | 61.83 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch6_25_5F3N_t_99b0e890` | 4 | `S24` | 9.524 | 476.2 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_5F3N_f1_2f68e976` | 4 | `S42` | 9 | 450 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_5F3N_f2_541c3113` | 4 | `S13` | 6.845 | 342.3 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_5F3N_f3_f196ef7a` | 4 | `S31` | 7.47 | 373.5 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_5F3N_f4_517f55f7` | 4 | `S31` | 7.501 | 375.1 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_5F3N_f5_62411d5d` | 4 | `S42` | 6.873 | 343.6 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_5F3N_n1_9c8e023c` | 4 | `S13` | 1.283 | 64.13 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch7_28_5F3N_n2_411f3ca5` | 4 | `S13` | 1.111 | 55.57 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch7_28_5F3N_n3_ec85f61c` | 4 | `S13` | 1.237 | 61.83 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch7_28_5F3N_t_14e90129` | 4 | `S31` | 7.431 | 371.6 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_5F3N_f1_3d07c21c` | 4 | `S42` | 12.9 | 644.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_5F3N_f2_b656654c` | 4 | `S13` | 11.62 | 580.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_5F3N_f3_5fb04c7e` | 4 | `S13` | 12.54 | 626.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_5F3N_f4_6538e16f` | 4 | `S13` | 12.43 | 621.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_5F3N_f5_e1730a3a` | 4 | `S13` | 12.3 | 614.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_5F3N_n1_e33ebec6` | 4 | `S13` | 1.283 | 64.13 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch8_30_5F3N_n2_a4161197` | 4 | `S13` | 1.111 | 55.57 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch8_30_5F3N_n3_2787bd7a` | 4 | `S13` | 1.237 | 61.83 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch8_30_5F3N_t_21ef6343` | 4 | `S31` | 12.49 | 624.4 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_5F3N_f1_15c78eab` | 4 | `S13` | 13.98 | 699 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_5F3N_f2_727163b3` | 4 | `S24` | 12.55 | 627.4 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_5F3N_f3_e6d09091` | 4 | `S31` | 12.54 | 626.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_5F3N_f4_dd88a4a4` | 4 | `S13` | 12.39 | 619.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_5F3N_f5_fe9a0410` | 4 | `S13` | 12.3 | 615.1 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_5F3N_n1_c06daa3b` | 4 | `S13` | 1.283 | 64.13 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch9_33_5F3N_n2_873a1ec3` | 4 | `S13` | 1.111 | 55.57 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch9_33_5F3N_n3_152db7f8` | 4 | `S13` | 1.237 | 61.83 | `direct_vector_fit` | run direct vector-fit candidate search, ngspice smoke, then HSPICE audit |
| `Ch9_33_5F3N_t_cbf9057d` | 4 | `S31` | 12.5 | 624.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_8F_f1_a4cc4b4d` | 4 | `S42` | 15.53 | 776.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_8F_f2_bf896f64` | 4 | `S13` | 2.867 | 143.3 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_8F_f3_e315413e` | 4 | `S13` | 14 | 700 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_8F_f4_71660fc2` | 4 | `S13` | 13.94 | 697 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_8F_f5_14667ac0` | 4 | `S13` | 10.27 | 513.4 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_8F_f6_122f3a53` | 4 | `S13` | 2.867 | 143.3 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_8F_f7_086b91fb` | 4 | `S13` | 14 | 700 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_8F_f8_95b91b5e` | 4 | `S13` | 10.27 | 513.4 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch10_35_8F_t_99349b74` | 4 | `S31` | 13.98 | 699.2 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_8F_f1_2b7329d0` | 4 | `S31` | 2.534 | 126.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_8F_f2_35a4bf64` | 4 | `S13` | 2.601 | 130 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_8F_f3_db4ce1de` | 4 | `S13` | 2.498 | 124.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_8F_f4_70717a00` | 4 | `S31` | 2.621 | 131.1 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_8F_f5_27613e57` | 4 | `S42` | 2.753 | 137.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_8F_f6_76527a26` | 4 | `S13` | 2.601 | 130 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_8F_f7_47d970d1` | 4 | `S13` | 2.498 | 124.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_8F_f8_d512bcd9` | 4 | `S42` | 2.753 | 137.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch1_10_8F_t_73ade4ae` | 4 | `S31` | 2.436 | 121.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_8F_f1_12d491be` | 4 | `S31` | 3.056 | 152.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_8F_f2_449c19aa` | 4 | `S31` | 3.063 | 153.2 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_8F_f3_516feefe` | 4 | `S42` | 3.021 | 151 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_8F_f4_6e22223a` | 4 | `S31` | 3.111 | 155.6 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_8F_f5_eaec6e10` | 4 | `S13` | 3.278 | 163.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_8F_f6_28686e56` | 4 | `S31` | 3.063 | 153.2 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_8F_f7_70f22531` | 4 | `S42` | 3.021 | 151 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_8F_f8_d80c8546` | 4 | `S13` | 3.278 | 163.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch2_12_8F_t_d9ac8524` | 4 | `S42` | 2.96 | 148 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_8F_f1_c6a11f17` | 4 | `S42` | 4.537 | 226.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_8F_f2_0ab1651f` | 4 | `S24` | 4.466 | 223.3 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_8F_f3_00c873e8` | 4 | `S13` | 4.507 | 225.3 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_8F_f4_817c067b` | 4 | `S31` | 4.571 | 228.5 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_8F_f5_ed043d75` | 4 | `S24` | 4.676 | 233.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_8F_f6_73c71a2e` | 4 | `S24` | 4.466 | 223.3 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_8F_f7_49b5a47c` | 4 | `S13` | 4.507 | 225.3 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_8F_f8_7fecdbaf` | 4 | `S24` | 4.676 | 233.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch3_17_8F_t_1063b4ed` | 4 | `S31` | 4.455 | 222.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_8F_f1_b4666d63` | 4 | `S42` | 9.052 | 452.6 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_8F_f2_a9f640a6` | 4 | `S42` | 9.02 | 451 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_8F_f3_05e85a7b` | 4 | `S31` | 9.064 | 453.2 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_8F_f4_3e8e60e2` | 4 | `S31` | 9.057 | 452.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_8F_f5_9f06750c` | 4 | `S13` | 9.093 | 454.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_8F_f6_43432bd4` | 4 | `S42` | 9.02 | 451 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_8F_f7_32ac290e` | 4 | `S31` | 9.064 | 453.2 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_8F_f8_28b2932d` | 4 | `S13` | 9.093 | 454.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch4_20_8F_t_afb27bdd` | 4 | `S31` | 8.994 | 449.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_8F_f1_f48fcabb` | 4 | `S42` | 6.054 | 302.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_8F_f2_37d9c944` | 4 | `S24` | 5.938 | 296.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_8F_f3_16ba5f55` | 4 | `S13` | 5.982 | 299.1 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_8F_f4_1658149d` | 4 | `S13` | 6.014 | 300.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_8F_f5_60d2b16e` | 4 | `S13` | 5.98 | 299 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_8F_f6_827cd43f` | 4 | `S24` | 5.938 | 296.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_8F_f7_66c0a870` | 4 | `S13` | 5.982 | 299.1 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_8F_f8_f6ad5bf7` | 4 | `S13` | 5.98 | 299 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch5_22_8F_t_afe82982` | 4 | `S31` | 5.941 | 297 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_8F_f1_7bb184a9` | 4 | `S24` | 9.598 | 479.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_8F_f2_26d81958` | 4 | `S24` | 9.533 | 476.6 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_8F_f3_a24fa548` | 4 | `S13` | 9.588 | 479.4 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_8F_f4_3a0e4c5a` | 4 | `S13` | 9.51 | 475.5 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_8F_f5_3f5f43c2` | 4 | `S13` | 9.555 | 477.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_8F_f6_a9565afb` | 4 | `S24` | 9.533 | 476.6 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_8F_f7_5904ffa7` | 4 | `S13` | 9.588 | 479.4 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_8F_f8_4aee51f6` | 4 | `S13` | 9.555 | 477.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch6_25_8F_t_eb3aefd3` | 4 | `S24` | 9.524 | 476.2 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_8F_f1_9117014c` | 4 | `S42` | 9 | 450 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_8F_f2_41c1a6bc` | 4 | `S13` | 6.845 | 342.3 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_8F_f3_25caab78` | 4 | `S31` | 7.47 | 373.5 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_8F_f4_0141b7df` | 4 | `S31` | 7.501 | 375.1 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_8F_f5_3fcf7d73` | 4 | `S42` | 6.873 | 343.6 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_8F_f6_113f3e8b` | 4 | `S13` | 6.845 | 342.3 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_8F_f7_5aadab9c` | 4 | `S31` | 7.47 | 373.5 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_8F_f8_298ab5d4` | 4 | `S42` | 6.873 | 343.6 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch7_28_8F_t_b6a7aed0` | 4 | `S31` | 7.431 | 371.6 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_8F_f1_1edcc859` | 4 | `S42` | 12.9 | 644.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_8F_f2_234ba6e8` | 4 | `S13` | 11.62 | 580.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_8F_f3_9c3ef384` | 4 | `S13` | 12.54 | 626.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_8F_f4_755c037e` | 4 | `S13` | 12.43 | 621.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_8F_f5_412a0962` | 4 | `S13` | 12.3 | 614.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_8F_f6_7608a147` | 4 | `S13` | 11.62 | 580.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_8F_f7_dca3d683` | 4 | `S13` | 12.54 | 626.9 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_8F_f8_ee54f19c` | 4 | `S13` | 12.3 | 614.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch8_30_8F_t_887ed30d` | 4 | `S31` | 12.49 | 624.4 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_8F_f1_f73e8bf0` | 4 | `S13` | 13.98 | 699 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_8F_f2_8b42f408` | 4 | `S24` | 12.55 | 627.4 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_8F_f3_b9d9e2c5` | 4 | `S31` | 12.54 | 626.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_8F_f4_a831b05b` | 4 | `S13` | 12.39 | 619.7 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_8F_f5_537052d4` | 4 | `S13` | 12.3 | 615.1 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_8F_f6_715f8c77` | 4 | `S24` | 12.55 | 627.4 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_8F_f7_50933ff5` | 4 | `S31` | 12.54 | 626.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_8F_f8_c5ee0f55` | 4 | `S13` | 12.3 | 615.1 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |
| `Ch9_33_8F_t_dbdad530` | 4 | `S31` | 12.5 | 624.8 | `delay_aware_required` | skip direct vector-fit as final; run delay-aware residual/prototype and HSPICE audit |

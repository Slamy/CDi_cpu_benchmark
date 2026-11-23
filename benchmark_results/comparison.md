# Real CD-i versus measurement

Only terminated benchmark cycles are included: `-----` ends a cycle;

Real CD-i: 621 complete cycles; 0 trailing measurements excluded. MiSTer: 884 complete cycles; 13 trailing measurements excluded.

Means are arithmetic means. Variance is sample variance (denominator n−1); SD is its square root. Variance has squared units. Change = 100 × (MiSTer mean / VMPEG mean − 1).

DA=0 and DA=1 refer to the display-active register bit tested by src/main.c. Operation rows count loop iterations in each phase; positive changes mean more operations per phase. Phase duration differences also affect operation counts, so the percentages are not isolated CPU speedups.

Benchmarks are matched by code location and label;

MiSTer change: 🔴 **negative** · 🟢 positive · ⚪ zero. Negative changes indicate lower throughput per phase.

## DA=0

| Location | Benchmark | VMPEG mean ± SD | VMPEG variance | MiSTer mean ± SD | MiSTer variance | MiSTer change |
|---|---|---:|---:|---:|---:|---:|
| VIDEO1 | getime | 7.41 ± 0.49 | 0.242 | 9.00 ± 0.00 | 0.000 | 🟢 +21.5% |
| VIDEO1 | getpid | 10.00 ± 0.00 | 0.000 | 11.00 ± 0.00 | 0.000 | 🟢 +10.0% |
| VIDEO1 | pt_coord | 3.02 ± 0.14 | 0.019 | 4.29 ± 0.46 | 0.207 | 🟢 +42.1% |
| VIDEO1 | dm_wrpix | 3.00 ± 0.00 | 0.000 | 3.00 ± 0.00 | 0.000 | ⚪ +0.0% |
| VIDEO1 | dr_circ | 1.00 ± 0.00 | 0.000 | 1.00 ± 0.00 | 0.000 | ⚪ +0.0% |
| VIDEO1 | gc_ptn | 4.00 ± 0.00 | 0.000 | 4.00 ± 0.00 | 0.000 | ⚪ +0.0% |
| VIDEO1 | dc_wrli | 3.00 ± 0.00 | 0.000 | 3.00 ± 0.00 | 0.000 | ⚪ +0.0% |
| VIDEO1 | Multi | 39.00 ± 0.00 | 0.000 | 61.00 ± 0.00 | 0.000 | 🟢 +56.4% |
| VIDEO1 | Add | 128.98 ± 0.13 | 0.016 | 138.52 ± 0.50 | 0.250 | 🟢 +7.4% |
| VIDEO1 | Div | 33.47 ± 0.50 | 0.250 | 40.00 ± 0.00 | 0.000 | 🟢 +19.5% |
| VIDEO1 | Copy VRAM to VRAM | 113.00 ± 0.06 | 0.003 | 117.93 ± 0.26 | 0.069 | 🟢 +4.4% |
| VIDEO1 | Copy VRAM to SYSRAM | 112.98 ± 0.15 | 0.022 | 117.60 ± 0.49 | 0.240 | 🟢 +4.1% |
| VIDEO1 | Copy SYSRAM to VRAM | 113.95 ± 0.21 | 0.043 | 118.00 ± 0.00 | 0.000 | 🟢 +3.5% |
| VIDEO1 | Copy SYSROM to SYSRAM | 113.96 ± 0.19 | 0.037 | 117.61 ± 0.49 | 0.238 | 🟢 +3.2% |
| VIDEO1 | Copy DVCROM to SYSRAM | 113.01 ± 0.08 | 0.006 | 117.14 ± 0.35 | 0.121 | 🟢 +3.7% |
| SYSRAM | getime | 8.00 ± 0.00 | 0.000 | 9.00 ± 0.00 | 0.000 | 🟢 +12.5% |
| SYSRAM | getpid | 10.11 ± 0.31 | 0.098 | 11.00 ± 0.00 | 0.000 | 🟢 +8.8% |
| SYSRAM | pt_coord | 3.00 ± 0.00 | 0.000 | 4.26 ± 0.44 | 0.197 | 🟢 +42.0% |
| SYSRAM | dm_wrpix | 3.00 ± 0.00 | 0.000 | 3.00 ± 0.00 | 0.000 | ⚪ +0.0% |
| SYSRAM | dr_circ | 1.00 ± 0.00 | 0.000 | 1.00 ± 0.00 | 0.000 | ⚪ +0.0% |
| SYSRAM | gc_ptn | 4.00 ± 0.00 | 0.000 | 4.00 ± 0.00 | 0.000 | ⚪ +0.0% |
| SYSRAM | dc_wrli | 3.00 ± 0.00 | 0.000 | 3.00 ± 0.00 | 0.000 | ⚪ +0.0% |
| SYSRAM | Multi | 41.80 ± 0.40 | 0.162 | 65.05 ± 0.21 | 0.045 | 🟢 +55.6% |
| SYSRAM | Add | 141.00 ± 0.06 | 0.003 | 150.03 ± 0.17 | 0.029 | 🟢 +6.4% |
| SYSRAM | Div | 36.00 ± 0.00 | 0.000 | 43.34 ± 0.47 | 0.223 | 🟢 +20.4% |
| SYSRAM | Copy VRAM to VRAM | 123.69 ± 0.46 | 0.213 | 127.07 ± 0.25 | 0.062 | 🟢 +2.7% |
| SYSRAM | Copy VRAM to SYSRAM | 123.00 ± 0.00 | 0.000 | 127.27 ± 0.45 | 0.200 | 🟢 +3.5% |
| SYSRAM | Copy SYSRAM to VRAM | 124.03 ± 0.16 | 0.025 | 128.00 ± 0.00 | 0.000 | 🟢 +3.2% |
| SYSRAM | Copy SYSROM to SYSRAM | 124.02 ± 0.13 | 0.016 | 127.00 ± 0.00 | 0.000 | 🟢 +2.4% |
| SYSRAM | Copy DVCROM to SYSRAM | 123.91 ± 0.29 | 0.085 | 127.00 ± 0.00 | 0.000 | 🟢 +2.5% |

## DA=1

| Location | Benchmark | VMPEG mean ± SD | VMPEG variance | MiSTer mean ± SD | MiSTer variance | MiSTer change |
|---|---|---:|---:|---:|---:|---:|
| VIDEO1 | getime | 57.59 ± 0.49 | 0.242 | 70.00 ± 0.00 | 0.000 | 🟢 +21.5% |
| VIDEO1 | getpid | 82.00 ± 0.00 | 0.000 | 86.00 ± 0.00 | 0.000 | 🟢 +4.9% |
| VIDEO1 | pt_coord | 29.05 ± 0.32 | 0.103 | 36.70 ± 0.48 | 0.229 | 🟢 +26.3% |
| VIDEO1 | dm_wrpix | 23.00 ± 0.00 | 0.000 | 25.00 ± 0.00 | 0.000 | 🟢 +8.7% |
| VIDEO1 | dr_circ | 7.00 ± 0.00 | 0.000 | 8.00 ± 0.00 | 0.000 | 🟢 +14.3% |
| VIDEO1 | gc_ptn | 26.00 ± 0.06 | 0.003 | 28.00 ± 0.00 | 0.000 | 🟢 +7.7% |
| VIDEO1 | dc_wrli | 23.00 ± 0.00 | 0.000 | 25.00 ± 0.00 | 0.000 | 🟢 +8.7% |
| VIDEO1 | Multi | 286.71 ± 0.45 | 0.206 | 420.00 ± 0.00 | 0.000 | 🟢 +46.5% |
| VIDEO1 | Add | 904.24 ± 0.45 | 0.205 | 979.48 ± 0.50 | 0.250 | 🟢 +8.3% |
| VIDEO1 | Div | 225.58 ± 0.52 | 0.271 | 280.00 ± 0.00 | 0.000 | 🟢 +24.1% |
| VIDEO1 | Copy VRAM to VRAM | 760.23 ± 0.42 | 0.178 | 865.07 ± 0.26 | 0.069 | 🟢 +13.8% |
| VIDEO1 | Copy VRAM to SYSRAM | 760.10 ± 0.30 | 0.087 | 865.40 ± 0.49 | 0.240 | 🟢 +13.9% |
| VIDEO1 | Copy SYSRAM to VRAM | 760.04 ± 0.21 | 0.044 | 871.00 ± 0.00 | 0.000 | 🟢 +14.6% |
| VIDEO1 | Copy SYSROM to SYSRAM | 777.06 ± 0.36 | 0.131 | 871.00 ± 0.00 | 0.000 | 🟢 +12.1% |
| VIDEO1 | Copy DVCROM to SYSRAM | 760.18 ± 0.38 | 0.146 | 871.00 ± 0.00 | 0.000 | 🟢 +14.6% |
| SYSRAM | getime | 61.00 ± 0.00 | 0.000 | 73.00 ± 0.00 | 0.000 | 🟢 +19.7% |
| SYSRAM | getpid | 86.43 ± 0.55 | 0.298 | 89.00 ± 0.00 | 0.000 | 🟢 +3.0% |
| SYSRAM | pt_coord | 29.98 ± 0.20 | 0.038 | 37.72 ± 0.49 | 0.238 | 🟢 +25.8% |
| SYSRAM | dm_wrpix | 23.94 ± 0.23 | 0.055 | 25.00 ± 0.00 | 0.000 | 🟢 +4.4% |
| SYSRAM | dr_circ | 7.00 ± 0.00 | 0.000 | 8.00 ± 0.00 | 0.000 | 🟢 +14.3% |
| SYSRAM | gc_ptn | 28.00 ± 0.00 | 0.000 | 29.00 ± 0.00 | 0.000 | 🟢 +3.6% |
| SYSRAM | dc_wrli | 24.00 ± 0.00 | 0.000 | 25.00 ± 0.00 | 0.000 | 🟢 +4.2% |
| SYSRAM | Multi | 360.20 ± 0.40 | 0.162 | 534.95 ± 0.21 | 0.045 | 🟢 +48.5% |
| SYSRAM | Add | 1232.47 ± 0.50 | 0.250 | 1287.97 ± 0.17 | 0.029 | 🟢 +4.5% |
| SYSRAM | Div | 311.00 ± 0.00 | 0.000 | 361.66 ± 0.47 | 0.223 | 🟢 +16.3% |
| SYSRAM | Copy VRAM to VRAM | 1067.26 ± 0.46 | 0.208 | 1088.93 ± 0.25 | 0.062 | 🟢 +2.0% |
| SYSRAM | Copy VRAM to SYSRAM | 1066.06 ± 0.23 | 0.055 | 1088.73 ± 0.45 | 0.200 | 🟢 +2.1% |
| SYSRAM | Copy SYSRAM to VRAM | 1087.48 ± 0.50 | 0.251 | 1120.00 ± 0.00 | 0.000 | 🟢 +3.0% |
| SYSRAM | Copy SYSROM to SYSRAM | 1087.01 ± 0.20 | 0.039 | 1120.00 ± 0.00 | 0.000 | 🟢 +3.0% |
| SYSRAM | Copy DVCROM to SYSRAM | 1081.09 ± 0.29 | 0.085 | 1120.00 ± 0.00 | 0.000 | 🟢 +3.6% |

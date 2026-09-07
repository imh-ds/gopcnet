# Stage 5h Four-Way Signal-Strength Sweep Report

**Recall check: Recall stayed at 1.0 (within floor tolerance) for all four methods in every cell -- no method's own precision behavior under this manipulation is purchased by missing true edges.**

**Replication check against D-050: Largest |precision difference| between this charter's own fresh N=1500 draw and D-050's own archived N=1500 rows, across both shared methods and all tested strengths: 0.0096. Different seed streams (see docs/stage5h_charter.md's own Seeding section), so exact agreement is not expected -- this checks whether the qualitative pattern (EBICglasso declining, GOPC-original flat, as strength increases) replicates, not whether the rows match.**

Descriptive result, not a validation gate -- see `docs/stage5h_charter.md`'s own decision structure. Precision trend classified per (dgp, method, N) series across ascending strength.

## Precision trend by (dgp, method, N)

| DGP shape | method | N | trend |
|---|---|---|---|
| chain_fork_hub | ebicglasso | 750 | decreasing |
| chain_fork_hub | ebicglasso | 1000 | decreasing |
| chain_fork_hub | ebicglasso | 1500 | decreasing |
| chain_fork_hub | ebicglasso | 1750 | decreasing |
| chain_fork_hub | pc | 750 | increasing |
| chain_fork_hub | pc | 1000 | increasing |
| chain_fork_hub | pc | 1500 | increasing |
| chain_fork_hub | pc | 1750 | increasing |
| chain_fork_hub | mint | 750 | non-monotonic |
| chain_fork_hub | mint | 1000 | decreasing |
| chain_fork_hub | mint | 1500 | decreasing |
| chain_fork_hub | mint | 1750 | decreasing |
| chain_fork_hub | gopc_growing_subset | 750 | decreasing |
| chain_fork_hub | gopc_growing_subset | 1000 | decreasing |
| chain_fork_hub | gopc_growing_subset | 1500 | decreasing |
| chain_fork_hub | gopc_growing_subset | 1750 | decreasing |
| overlap | ebicglasso | 750 | decreasing |
| overlap | ebicglasso | 1000 | decreasing |
| overlap | ebicglasso | 1500 | decreasing |
| overlap | ebicglasso | 1750 | decreasing |
| overlap | pc | 750 | increasing |
| overlap | pc | 1000 | flat |
| overlap | pc | 1500 | flat |
| overlap | pc | 1750 | increasing |
| overlap | mint | 750 | decreasing |
| overlap | mint | 1000 | decreasing |
| overlap | mint | 1500 | decreasing |
| overlap | mint | 1750 | decreasing |
| overlap | gopc_growing_subset | 750 | decreasing |
| overlap | gopc_growing_subset | 1000 | decreasing |
| overlap | gopc_growing_subset | 1500 | flat |
| overlap | gopc_growing_subset | 1750 | flat |

## Replication check detail (N=1500 only)

| DGP shape | method | strength | Stage 5h precision | D-050 precision | difference |
|---|---|---|---|---|---|
| chain_fork_hub | mint | 0.3 | 0.9616 | 0.9623 | -0.0007 |
| chain_fork_hub | mint | 0.5 | 0.9327 | 0.9319 | 0.0008 |
| chain_fork_hub | mint | 0.7 | 0.9361 | 0.9336 | 0.0025 |
| chain_fork_hub | ebicglasso | 0.3 | 0.8987 | 0.8974 | 0.0013 |
| chain_fork_hub | ebicglasso | 0.5 | 0.7367 | 0.7279 | 0.0087 |
| chain_fork_hub | ebicglasso | 0.7 | 0.5109 | 0.5120 | -0.0010 |
| overlap | mint | 0.3 | 0.9229 | 0.9241 | -0.0011 |
| overlap | mint | 0.5 | 0.9126 | 0.9072 | 0.0054 |
| overlap | mint | 0.7 | 0.9161 | 0.9147 | 0.0013 |
| overlap | ebicglasso | 0.3 | 0.8587 | 0.8639 | -0.0051 |
| overlap | ebicglasso | 0.5 | 0.7941 | 0.7846 | 0.0096 |
| overlap | ebicglasso | 0.7 | 0.6667 | 0.6580 | 0.0087 |

## chain_fork_hub

| N | strength | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|---|
| 750 | 0.3 | ebicglasso | 0.8811 | 1.0000 | 0.9324 | 0.9500 | 1.8135 | 0 |
| 750 | 0.3 | pc | 0.9226 | 1.0000 | 0.9572 | 0.5770 | 0.0348 | 0 |
| 750 | 0.3 | mint | 0.9532 | 1.0000 | 0.9743 | 0.3440 | 0.0080 | 0 |
| 750 | 0.3 | gopc_growing_subset | 0.9544 | 1.0000 | 0.9750 | 0.3320 | 0.0110 | 0 |
| 750 | 0.5 | ebicglasso | 0.7334 | 1.0000 | 0.8399 | 2.4440 | 2.8226 | 0 |
| 750 | 0.5 | pc | 0.9476 | 1.0000 | 0.9713 | 0.3830 | 0.0379 | 0 |
| 750 | 0.5 | mint | 0.9107 | 1.0000 | 0.9498 | 0.6930 | 0.0107 | 0 |
| 750 | 0.5 | gopc_growing_subset | 0.9224 | 1.0000 | 0.9574 | 0.5690 | 0.0122 | 0 |
| 750 | 0.7 | ebicglasso | 0.5189 | 1.0000 | 0.6778 | 5.9980 | 2.1627 | 0 |
| 750 | 0.7 | pc | 0.9645 | 1.0000 | 0.9807 | 0.2540 | 0.0283 | 0 |
| 750 | 0.7 | mint | 0.9225 | 1.0000 | 0.9565 | 0.6010 | 0.0079 | 0 |
| 750 | 0.7 | gopc_growing_subset | 0.9315 | 1.0000 | 0.9623 | 0.5030 | 0.0088 | 0 |
| 1000 | 0.3 | ebicglasso | 0.8885 | 1.0000 | 0.9369 | 0.8780 | 1.6749 | 0 |
| 1000 | 0.3 | pc | 0.9267 | 1.0000 | 0.9595 | 0.5460 | 0.0372 | 0 |
| 1000 | 0.3 | mint | 0.9597 | 1.0000 | 0.9779 | 0.2940 | 0.0085 | 0 |
| 1000 | 0.3 | gopc_growing_subset | 0.9615 | 1.0000 | 0.9791 | 0.2760 | 0.0112 | 0 |
| 1000 | 0.5 | ebicglasso | 0.7410 | 1.0000 | 0.8447 | 2.3630 | 2.7556 | 0 |
| 1000 | 0.5 | pc | 0.9475 | 1.0000 | 0.9712 | 0.3850 | 0.0392 | 0 |
| 1000 | 0.5 | mint | 0.9256 | 1.0000 | 0.9582 | 0.5760 | 0.0109 | 0 |
| 1000 | 0.5 | gopc_growing_subset | 0.9347 | 1.0000 | 0.9641 | 0.4790 | 0.0131 | 0 |
| 1000 | 0.7 | ebicglasso | 0.5121 | 1.0000 | 0.6722 | 6.1320 | 1.6818 | 0 |
| 1000 | 0.7 | pc | 0.9622 | 1.0000 | 0.9793 | 0.2740 | 0.0224 | 0 |
| 1000 | 0.7 | mint | 0.9264 | 1.0000 | 0.9588 | 0.5660 | 0.0063 | 0 |
| 1000 | 0.7 | gopc_growing_subset | 0.9348 | 1.0000 | 0.9642 | 0.4780 | 0.0067 | 0 |
| 1500 | 0.3 | ebicglasso | 0.8987 | 1.0000 | 0.9429 | 0.7900 | 1.0404 | 0 |
| 1500 | 0.3 | pc | 0.9307 | 1.0000 | 0.9617 | 0.5160 | 0.0245 | 0 |
| 1500 | 0.3 | mint | 0.9616 | 1.0000 | 0.9786 | 0.2910 | 0.0059 | 0 |
| 1500 | 0.3 | gopc_growing_subset | 0.9671 | 1.0000 | 0.9821 | 0.2360 | 0.0076 | 0 |
| 1500 | 0.5 | ebicglasso | 0.7367 | 1.0000 | 0.8426 | 2.3840 | 1.5656 | 0 |
| 1500 | 0.5 | pc | 0.9473 | 1.0000 | 0.9711 | 0.3850 | 0.0245 | 0 |
| 1500 | 0.5 | mint | 0.9327 | 1.0000 | 0.9624 | 0.5160 | 0.0065 | 0 |
| 1500 | 0.5 | gopc_growing_subset | 0.9414 | 1.0000 | 0.9679 | 0.4270 | 0.0072 | 0 |
| 1500 | 0.7 | ebicglasso | 0.5109 | 1.0000 | 0.6710 | 6.1780 | 2.7808 | 0 |
| 1500 | 0.7 | pc | 0.9629 | 1.0000 | 0.9798 | 0.2670 | 0.0415 | 0 |
| 1500 | 0.7 | mint | 0.9361 | 1.0000 | 0.9642 | 0.4930 | 0.0113 | 0 |
| 1500 | 0.7 | gopc_growing_subset | 0.9450 | 1.0000 | 0.9699 | 0.4000 | 0.0127 | 0 |
| 1750 | 0.3 | ebicglasso | 0.8904 | 1.0000 | 0.9381 | 0.8620 | 1.7542 | 0 |
| 1750 | 0.3 | pc | 0.9218 | 1.0000 | 0.9566 | 0.5870 | 0.0425 | 0 |
| 1750 | 0.3 | mint | 0.9577 | 1.0000 | 0.9762 | 0.3290 | 0.0102 | 0 |
| 1750 | 0.3 | gopc_growing_subset | 0.9661 | 1.0000 | 0.9815 | 0.2440 | 0.0126 | 0 |
| 1750 | 0.5 | ebicglasso | 0.7247 | 1.0000 | 0.8343 | 2.5340 | 2.7206 | 0 |
| 1750 | 0.5 | pc | 0.9451 | 1.0000 | 0.9698 | 0.4030 | 0.0426 | 0 |
| 1750 | 0.5 | mint | 0.9328 | 1.0000 | 0.9622 | 0.5210 | 0.0113 | 0 |
| 1750 | 0.5 | gopc_growing_subset | 0.9422 | 1.0000 | 0.9683 | 0.4210 | 0.0130 | 0 |
| 1750 | 0.7 | ebicglasso | 0.5105 | 1.0000 | 0.6705 | 6.1890 | 2.0929 | 0 |
| 1750 | 0.7 | pc | 0.9670 | 1.0000 | 0.9819 | 0.2400 | 0.0320 | 0 |
| 1750 | 0.7 | mint | 0.9420 | 1.0000 | 0.9676 | 0.4450 | 0.0085 | 0 |
| 1750 | 0.7 | gopc_growing_subset | 0.9500 | 1.0000 | 0.9726 | 0.3630 | 0.0092 | 0 |

## overlap

| N | strength | method | precision | recall | F1 | SHD | mean runtime (s) | errors |
|---|---|---|---|---|---|---|---|---|
| 750 | 0.3 | ebicglasso | 0.8629 | 1.0000 | 0.9234 | 1.7470 | 0.6818 | 0 |
| 750 | 0.3 | pc | 0.9636 | 1.0000 | 0.9807 | 0.4130 | 0.0280 | 0 |
| 750 | 0.3 | mint | 0.8496 | 1.0000 | 0.9160 | 1.9090 | 0.0042 | 0 |
| 750 | 0.3 | gopc_growing_subset | 0.9613 | 1.0000 | 0.9794 | 0.4400 | 0.0168 | 0 |
| 750 | 0.5 | ebicglasso | 0.7987 | 1.0000 | 0.8844 | 2.7350 | 1.8411 | 0 |
| 750 | 0.5 | pc | 0.9758 | 1.0000 | 0.9872 | 0.2720 | 0.0606 | 0 |
| 750 | 0.5 | mint | 0.8384 | 1.0000 | 0.9090 | 2.0890 | 0.0109 | 0 |
| 750 | 0.5 | gopc_growing_subset | 0.9511 | 1.0000 | 0.9740 | 0.5570 | 0.0346 | 0 |
| 750 | 0.7 | ebicglasso | 0.6707 | 1.0000 | 0.7987 | 5.2500 | 1.2308 | 0 |
| 750 | 0.7 | pc | 0.9802 | 1.0000 | 0.9895 | 0.2220 | 0.0350 | 0 |
| 750 | 0.7 | mint | 0.8340 | 1.0000 | 0.9065 | 2.1550 | 0.0061 | 0 |
| 750 | 0.7 | gopc_growing_subset | 0.9495 | 1.0000 | 0.9731 | 0.5750 | 0.0219 | 0 |
| 1000 | 0.3 | ebicglasso | 0.8600 | 1.0000 | 0.9215 | 1.7980 | 0.9787 | 0 |
| 1000 | 0.3 | pc | 0.9659 | 1.0000 | 0.9819 | 0.3870 | 0.0474 | 0 |
| 1000 | 0.3 | mint | 0.8740 | 1.0000 | 0.9291 | 1.6310 | 0.0078 | 0 |
| 1000 | 0.3 | gopc_growing_subset | 0.9652 | 1.0000 | 0.9815 | 0.3960 | 0.0286 | 0 |
| 1000 | 0.5 | ebicglasso | 0.7957 | 1.0000 | 0.8825 | 2.7880 | 1.0092 | 0 |
| 1000 | 0.5 | pc | 0.9746 | 1.0000 | 0.9866 | 0.2850 | 0.0378 | 0 |
| 1000 | 0.5 | mint | 0.8562 | 1.0000 | 0.9185 | 1.8910 | 0.0070 | 0 |
| 1000 | 0.5 | gopc_growing_subset | 0.9535 | 1.0000 | 0.9753 | 0.5290 | 0.0228 | 0 |
| 1000 | 0.7 | ebicglasso | 0.6669 | 1.0000 | 0.7963 | 5.3100 | 1.9789 | 0 |
| 1000 | 0.7 | pc | 0.9814 | 1.0000 | 0.9902 | 0.2080 | 0.0622 | 0 |
| 1000 | 0.7 | mint | 0.8611 | 1.0000 | 0.9216 | 1.8080 | 0.0119 | 0 |
| 1000 | 0.7 | gopc_growing_subset | 0.9576 | 1.0000 | 0.9774 | 0.4840 | 0.0361 | 0 |
| 1500 | 0.3 | ebicglasso | 0.8587 | 1.0000 | 0.9208 | 1.8150 | 1.1108 | 0 |
| 1500 | 0.3 | pc | 0.9667 | 1.0000 | 0.9823 | 0.3770 | 0.0669 | 0 |
| 1500 | 0.3 | mint | 0.9229 | 1.0000 | 0.9571 | 0.9770 | 0.0128 | 0 |
| 1500 | 0.3 | gopc_growing_subset | 0.9709 | 1.0000 | 0.9846 | 0.3260 | 0.0378 | 0 |
| 1500 | 0.5 | ebicglasso | 0.7941 | 1.0000 | 0.8818 | 2.7980 | 0.7915 | 0 |
| 1500 | 0.5 | pc | 0.9728 | 1.0000 | 0.9856 | 0.3080 | 0.0365 | 0 |
| 1500 | 0.5 | mint | 0.9126 | 1.0000 | 0.9509 | 1.1310 | 0.0076 | 0 |
| 1500 | 0.5 | gopc_growing_subset | 0.9614 | 1.0000 | 0.9795 | 0.4380 | 0.0225 | 0 |
| 1500 | 0.7 | ebicglasso | 0.6667 | 1.0000 | 0.7962 | 5.3120 | 1.8732 | 0 |
| 1500 | 0.7 | pc | 0.9816 | 1.0000 | 0.9903 | 0.2060 | 0.0680 | 0 |
| 1500 | 0.7 | mint | 0.9161 | 1.0000 | 0.9531 | 1.0740 | 0.0141 | 0 |
| 1500 | 0.7 | gopc_growing_subset | 0.9632 | 1.0000 | 0.9805 | 0.4150 | 0.0426 | 0 |
| 1750 | 0.3 | ebicglasso | 0.8530 | 1.0000 | 0.9174 | 1.9020 | 1.1300 | 0 |
| 1750 | 0.3 | pc | 0.9628 | 1.0000 | 0.9802 | 0.4230 | 0.0726 | 0 |
| 1750 | 0.3 | mint | 0.9339 | 1.0000 | 0.9632 | 0.8380 | 0.0140 | 0 |
| 1750 | 0.3 | gopc_growing_subset | 0.9722 | 1.0000 | 0.9852 | 0.3150 | 0.0444 | 0 |
| 1750 | 0.5 | ebicglasso | 0.7913 | 1.0000 | 0.8800 | 2.8500 | 0.8462 | 0 |
| 1750 | 0.5 | pc | 0.9736 | 1.0000 | 0.9861 | 0.2960 | 0.0428 | 0 |
| 1750 | 0.5 | mint | 0.9236 | 1.0000 | 0.9574 | 0.9760 | 0.0088 | 0 |
| 1750 | 0.5 | gopc_growing_subset | 0.9649 | 1.0000 | 0.9814 | 0.3950 | 0.0275 | 0 |
| 1750 | 0.7 | ebicglasso | 0.6661 | 1.0000 | 0.7957 | 5.3330 | 0.7236 | 0 |
| 1750 | 0.7 | pc | 0.9805 | 1.0000 | 0.9898 | 0.2160 | 0.0283 | 0 |
| 1750 | 0.7 | mint | 0.9254 | 1.0000 | 0.9586 | 0.9440 | 0.0059 | 0 |
| 1750 | 0.7 | gopc_growing_subset | 0.9663 | 1.0000 | 0.9822 | 0.3790 | 0.0170 | 0 |

See `raw_metrics.csv`, `report.json`, `resolved_config.yaml`, and `precision_by_strength.png` for complete evidence.

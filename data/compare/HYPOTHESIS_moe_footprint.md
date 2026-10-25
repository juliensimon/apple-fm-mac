# Hypothesis H4, written 2026-10-25 before any result

Question: does a per-token mixture-of-experts open model of Core Advanced's class (Gemma 4 26B A4B, 25.2B total, 3.8B active, Google's model card)
need its whole weight set resident in memory on this Mac, where Apple's design keeps its 20B in flash?

Build: mlx-community/gemma-4-26b-a4b-it-4bit (4-bit MLX), behind mlx_lm.server, measured with memory_protocol.py exactly as the six 4B builds
(download done before the run, so it is outside every reading).

H4: the server's footprint two seconds after the long request is at least 12 GiB.
Holds if: footprint_after >= 12 GiB. Fails if: footprint_after < 8 GiB (which would mean MLX keeps most experts out of memory).
Between 8 and 12 GiB: reported as is, no verdict.
My threshold, not a standard: 25.2B weights at 4 bits plus group scales come to roughly 13-15 GB if all are resident.

## Result, 2026-10-25 (memory_protocol.json, last row; log run_moe_footprint.log)
Footprint of the mlx_lm.server process, as `footprint` prints it (whole GB at this size): started 7.8 GiB, idle 14.0, during the
4,922-token prompt 16.0 (also the peak, 49 readings), two seconds after 15.0, ten seconds later 15.0. H4 HOLDS (15.0 >= 12 GiB).
Apple's two processes at the same moment: 2.0 GiB (note on Apple's snapshots). The model was already in the Hugging Face cache, so no download fell inside the run.

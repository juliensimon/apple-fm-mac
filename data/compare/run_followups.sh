#!/bin/bash
# The two root measurements the story meeting asked for (2026-10-25): a third cadence trace, then the 4-bit energy set.
# Run:   sudo bash run_followups.sh      Takes: about 20 minutes. Keep the Mac otherwise idle.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
if [ "$(id -u)" -ne 0 ]; then echo "run with sudo"; exit 1; fi
bash "$HERE/inspect_ifp_cadence.sh" || echo "cadence trace failed; continuing with the energy set"
sleep 20
ENERGY_TAG=_4bit bash "$HERE/run_energy.sh"

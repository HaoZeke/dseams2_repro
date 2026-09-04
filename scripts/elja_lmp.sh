#!/usr/bin/env bash
# Host LAMMPS on Elja: foss/2021b + LAMMPS 23Jun2022-kokkos (PLUMED, TIP4P, SW).
# Use as SEAMS_LMP so pixi run does not pick conda-forge lmp.
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=elja_host_env.sh
. "$SCRIPT_DIR/elja_host_env.sh"
elja_host_env
exec lmp "$@"

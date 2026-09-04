#!/usr/bin/env bash
# EasyBuild toolchain + LAMMPS on Elja (Rocky 8, glibc 2.28).
# conda-forge lammps 2025.07 needs GLIBC_2.29/2.34 and does not run here.
# /etc/profile.d/lmod.sh returns immediately under Slurm; init Lmod from
# the OpenHPC prefix instead.
#
# Source this file and call elja_host_env. It prepends the host lmp and
# PLUMED 2.7.3 (the kernel LAMMPS 23Jun2022 looks up via PLUMED_KERNEL).
elja_host_env() {
  # Lmod init reads FPATH; foss puts a Python 3.9 SciPy-bundle on
  # PYTHONPATH. Both break a `set -u` pixi 3.12 process.
  local nounset=0
  case $- in *u*) nounset=1; set +u;; esac
  if ! type module >/dev/null 2>&1; then
    if [ -f /opt/ohpc/admin/lmod/lmod/init/bash ]; then
      # shellcheck disable=SC1091
      . /opt/ohpc/admin/lmod/lmod/init/bash
    elif [ -f /usr/share/lmod/lmod/init/bash ]; then
      # shellcheck disable=SC1091
      . /usr/share/lmod/lmod/init/bash
    else
      echo "elja_host_env: no Lmod init on this node" >&2
      [ "$nounset" = 1 ] && set -u
      return 1
    fi
  fi
  if [ -z "${MODULEPATH:-}" ]; then
    export MODULEPATH=/opt/ohpc/pub/modulefiles:/hpcapps/lib-edda/modules/all/Core
  fi
  module load foss/2021b
  # Hidden modules: leading-dot versions on the hierarchical MPI path.
  module load PLUMED/.2.7.3
  module load LAMMPS/.23Jun2022-kokkos
  unset PYTHONPATH PYTHONHOME
  local eb_plumed=/hpcapps/lib-edda/easybuild/software/PLUMED/2.7.3-foss-2021b
  if [ -z "${SEAMS_PLUMED_KERNEL:-}" ] && [ -f "$eb_plumed/lib/libplumedKernel.so" ]; then
    export PLUMED_KERNEL="$eb_plumed/lib/libplumedKernel.so"
  elif [ -n "${SEAMS_PLUMED_KERNEL:-}" ]; then
    export PLUMED_KERNEL="$SEAMS_PLUMED_KERNEL"
  fi
  [ "$nounset" = 1 ] && set -u
  if ! command -v lmp >/dev/null 2>&1; then
    echo "elja_host_env: lmp not on PATH after module load" >&2
    return 1
  fi
}

#!/usr/bin/env bash
# Reproducibility campaign driver for an IRHPC-style Slurm cluster.
#
#   scripts/elja_submit.sh prep     # login node: env, sources, wraps, data, hq
#   scripts/elja_submit.sh submit   # sbatch the exclusive campaign
#   scripts/elja_submit.sh run      # the sbatch body (hq server + snakemake)
#
# Environment:
#   ELJA_ACCOUNT    Slurm account for submit (default chem-ui)
#   ELJA_PARTITION  partition (default 64cpu_256mem)
#   ELJA_TIME       walltime (default 08:00:00)
#   CONFIG          workflow config (default config/config.yaml)
#   HQ_VERSION      HyperQueue release to fetch (default v0.19.0)
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(dirname "$SCRIPT_DIR")
CONFIG=${CONFIG:-config/config.yaml}
SOURCE_ROOT=${DSEAMS_SOURCE_ROOT:-$ROOT/sources}
HQ_VERSION=${HQ_VERSION:-v0.19.0}
export PATH=$HOME/.pixi/bin:$ROOT/bin:$PATH
export DSEAMS_SOURCE_ROOT=$SOURCE_ROOT

case "${1:-}" in
prep)
  cd "$ROOT"
  pixi install
  # Every component of config/ecosystem-lock.json, the engine and its
  # baseline included, at its immutable revision
  pixi run -- python scripts/ecosystem_sources.py fetch --root "$SOURCE_ROOT"
  pixi run -- python scripts/ecosystem_sources.py wire --root "$SOURCE_ROOT"
  # Meson wraps for both engine trees need the network
  (cd "$SOURCE_ROOT/seams-core" && pixi run --manifest-path "$ROOT/pixi.toml" -- meson subprojects download)
  (cd "$SOURCE_ROOT/seams-base" && pixi run --manifest-path "$ROOT/pixi.toml" -- meson subprojects download)
  # Compute nodes are offline; the public trajectories download here
  pixi run -- python scripts/figshare_demos.py fetch data/figshare
  pixi run -- python scripts/public_ice.py fetch data/public-ice
  # HyperQueue is a single static binary
  if ! command -v hq > /dev/null; then
    mkdir -p bin
    curl -sL "https://github.com/It4innovations/hyperqueue/releases/download/${HQ_VERSION}/hq-${HQ_VERSION}-linux-x64.tar.gz" |
      tar -xz -C bin
  fi
  pixi run -- snakemake -s workflow/Snakefile --configfile "$CONFIG" --dry-run --cores 1 > /dev/null
  echo "prep done: core $(git -C "$SOURCE_ROOT/seams-core" rev-parse --short HEAD), base $(git -C "$SOURCE_ROOT/seams-base" rev-parse --short HEAD), hq $(hq --version)"
  ;;
submit)
  : "${ELJA_ACCOUNT:=chem-ui}"
  cd "$ROOT"
  mkdir -p results
  sbatch --partition="${ELJA_PARTITION:-64cpu_256mem}" --exclusive \
    --ntasks=1 --cpus-per-task=32 --hint=nomultithread --time="${ELJA_TIME:-08:00:00}" \
    --mem=32G --account="$ELJA_ACCOUNT" --job-name=dseams2-repro \
    --output=results/repro-%j.out --wrap "CONFIG=$CONFIG $ROOT/scripts/elja_submit.sh run"
  ;;
run)
  cd "$ROOT"
  mkdir -p results
  # One HyperQueue server and one worker own the allocation; Snakemake
  # submits every heavy rule through it
  export HQ_SERVER_DIR=$ROOT/results/hq-server
  mkdir -p "$HQ_SERVER_DIR"
  hq server start > results/hq-server.log 2>&1 &
  HQ_SERVER_PID=$!
  sleep 3
  # Tasks inherit the worker environment, so the worker starts inside the
  # pixi environment; meson, ninja and python resolve there
  pixi run -- hq worker start --cpus "${SLURM_CPUS_PER_TASK:-32}" \
    > results/hq-worker.log 2>&1 &
  HQ_WORKER_PID=$!
  sleep 2
  trap 'hq server stop > /dev/null 2>&1 || true; kill $HQ_WORKER_PID $HQ_SERVER_PID 2> /dev/null || true' EXIT

  # Node-local build root: the cluster NFS clock skews against the nodes,
  # which meson refuses at configure time
  export SEAMS_BUILD_ROOT=/tmp/dseams2-repro-${SLURM_JOB_ID:-manual}
  mkdir -p "$SEAMS_BUILD_ROOT"
  echo "loadavg_before_workflow: $(cut -d' ' -f1 /proc/loadavg)"
  pixi run -- snakemake -s workflow/Snakefile --configfile "$CONFIG" --cores all --printshellcmds
  echo "manifest: results/paper_manifest.json"
  ;;
*)
  echo "usage: $0 {prep|submit|run}" >&2
  exit 2
  ;;
esac

#!/usr/bin/env bash
# Seeding campaign on Elja: one exclusive node per temperature.
#   scripts/elja_production.sh prep      # login node: env, module, data
#   scripts/elja_production.sh submit    # one sbatch per temperature
#   scripts/elja_production.sh submit-brine  # ice/brine front, one job per temperature
#   scripts/elja_production.sh smoke     # tiny matrix, one short job (not paper numbers)
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(dirname "$SCRIPT_DIR")
CONFIG=${CONFIG:-config/production.yaml}
export PATH=$HOME/.pixi/bin:$PATH
# shellcheck source=elja_host_env.sh
. "$SCRIPT_DIR/elja_host_env.sh"
export SEAMS_LMP=${SEAMS_LMP:-$SCRIPT_DIR/elja_lmp.sh}
cd "$ROOT"

# pixi run prepends conda lmp; load the host stack inside that env so
# EasyBuild lmp/plumed sit in front and genice2/python stay from pixi.
production_snakemake() {
  pixi run -e production -- bash -c '
    set -euo pipefail
    . "$1"
    elja_host_env
    export SEAMS_LMP="$2"
    shift 2
    exec snakemake -s workflow/production.smk "$@"
  ' bash "$SCRIPT_DIR/elja_host_env.sh" "$SEAMS_LMP" "$@"
}

case "${1:-}" in
prep)
  pixi install -e production
  if ! pixi run -e production -- command -v genice2 >/dev/null; then
    echo "prep: genice2 missing from the production env" >&2
    exit 1
  fi
  elja_host_env
  if ! command -v lmp >/dev/null 2>&1; then
    echo "prep: host lmp not on PATH after elja_host_env" >&2
    exit 1
  fi
  echo "prep: host lmp=$(command -v lmp)"
  echo "prep: PLUMED_KERNEL=${PLUMED_KERNEL:-unset}"
  # The previous conda-plumed module cannot LOAD into EasyBuild PLUMED 2.7.3
  rm -f build-plumed/libdseams_plumed.so
  production_snakemake --configfile "$CONFIG" --cores 4 -- build_module
  production_snakemake --configfile "$CONFIG" --dry-run --cores 1 > /dev/null
  echo "prep done: SEAMS_LMP=$SEAMS_LMP genice2=$(pixi run -e production -- command -v genice2)"
  ;;
submit)
  : "${ELJA_ACCOUNT:=chem-ui}"
  mkdir -p results/production
  for T in $(pixi run -e production -- python -c "import yaml,sys;print(*yaml.safe_load(open('$CONFIG'))['temperatures'])"); do
    sbatch --partition="${ELJA_PARTITION:-64cpu_256mem}" --exclusive --ntasks=1 --cpus-per-task=32 \
      --time="${ELJA_TIME:-24:00:00}" --mem=32G --account="$ELJA_ACCOUNT" --job-name="seed-T$T" \
      --output=results/production/seed-T$T-%j.out \
      --wrap "CONFIG=$CONFIG $ROOT/scripts/elja_production.sh run --configfile $CONFIG --config temperatures=[$T] --cores 32 --keep-going"
  done
  ;;
submit-brine)
  : "${ELJA_ACCOUNT:=chem-ui}"
  mkdir -p results/brine
  for T in $(pixi run -e production -- python -c "import yaml;print(*yaml.safe_load(open('$CONFIG'))['brine']['temperatures'])"); do
    TARGETS=$(pixi run -e production -- python -c "
import yaml,itertools
b=yaml.safe_load(open('$CONFIG'))['brine']
print(*[f'results/brine/T{$T}_m{m}_r{r}/BRINE' for m,r in itertools.product(b['pairs'],range(b['replicas']))])")
    sbatch --partition="${ELJA_PARTITION:-64cpu_256mem}" --exclusive --ntasks=1 --cpus-per-task=32 \
      --time="${ELJA_TIME:-48:00:00}" --mem=32G --account="$ELJA_ACCOUNT" --job-name="brine-T$T" \
      --output=results/brine/brine-T$T-%j.out \
      --wrap "CONFIG=$CONFIG $ROOT/scripts/elja_production.sh run --configfile $CONFIG --cores 32 --keep-going -- $TARGETS"
  done
  ;;
smoke)
  : "${ELJA_ACCOUNT:=chem-ui}"
  mkdir -p results/production results/brine
  sbatch --partition="${ELJA_PARTITION:-64cpu_256mem}" --ntasks=1 --cpus-per-task=8 \
    --time="${ELJA_SMOKE_TIME:-00:30:00}" --mem=16G --account="$ELJA_ACCOUNT" --job-name="prod-smoke" \
    --output=results/production/smoke-%j.out \
    --wrap "CONFIG=config/production-smoke.yaml $ROOT/scripts/elja_production.sh run --configfile config/production-smoke.yaml --cores 8 --keep-going"
  ;;
run)
  shift
  production_snakemake "$@"
  ;;
*)
  echo "usage: $0 {prep|submit|submit-brine|smoke|run}" >&2; exit 2;;
esac

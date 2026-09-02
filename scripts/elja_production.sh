#!/usr/bin/env bash
# Seeding campaign on Elja: one exclusive node per temperature.
#   scripts/elja_production.sh prep      # login node: env, module, data
#   scripts/elja_production.sh submit    # one sbatch per temperature
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(dirname "$SCRIPT_DIR")
CONFIG=${CONFIG:-config/production.yaml}
export PATH=$HOME/.pixi/bin:$PATH
cd "$ROOT"
case "${1:-}" in
prep)
  pixi install -e production
  pixi run -e production -- snakemake -s workflow/production.smk --configfile "$CONFIG" --cores 4 -- build_module
  pixi run -e production -- snakemake -s workflow/production.smk --configfile "$CONFIG" --dry-run --cores 1 > /dev/null
  echo "prep done"
  ;;
submit)
  : "${ELJA_ACCOUNT:=chem-ui}"
  mkdir -p results/production
  for T in $(python -c "import yaml,sys;print(*yaml.safe_load(open('$CONFIG'))['temperatures'])"); do
    sbatch --partition="${ELJA_PARTITION:-64cpu_256mem}" --exclusive --ntasks=1 --cpus-per-task=32 \
      --time="${ELJA_TIME:-24:00:00}" --mem=32G --account="$ELJA_ACCOUNT" --job-name="seed-T$T" \
      --output=results/production/seed-T$T-%j.out \
      --wrap "cd $ROOT; export PATH=\$HOME/.pixi/bin:\$PATH; pixi run -e production -- snakemake -s workflow/production.smk --configfile $CONFIG --config temperatures=[$T] --cores 32 --keep-going"
  done
  ;;
*)
  echo "usage: $0 {prep|submit}" >&2; exit 2;;
esac

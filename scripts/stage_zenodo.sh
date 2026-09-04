#!/usr/bin/env bash
# Copy campaign outputs into zenodo/payload/. No manuscript.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
# Live results/ after elja_submit.sh, else the exclusive-node campaign the
# paper tables read.
if [ -f "$ROOT/results/paper_manifest.json" ]; then
  SRC=$ROOT/results
else
  SRC=${CAMPAIGN:-$ROOT/results/reference/elja-1798666}
fi
DST=$ROOT/zenodo/payload
test -f "$SRC/paper_manifest.json" || {
  echo "missing $SRC/paper_manifest.json; run the campaign first" >&2
  exit 1
}
if [ -e "$DST" ]; then
  BACKUP=$DST.previous.$(date -u +%Y%m%dT%H%M%SZ)
  test ! -e "$BACKUP" || {
    echo "backup path exists: $BACKUP" >&2
    exit 1
  }
  mv "$DST" "$BACKUP"
  echo "preserved existing payload at $BACKUP"
fi
mkdir -p "$DST"
cp -a "$SRC/paper_manifest.json" "$DST/"
cp -a "$SRC/source-manifest.json" "$DST/"
cp -a "$SRC/workflow-parity.json" "$DST/"
cp -a "$SRC/conditions.txt" "$DST/"
for f in "$SRC"/tip-*.txt "$SRC"/base-*.txt "$SRC"/trajectory-incremental.txt \
         "$SRC"/ql-*.txt "$SRC"/figshare-incremental.json; do
  [ -f "$f" ] && cp -a "$f" "$DST/"
done
cp -a "$ROOT/config/config.yaml" "$DST/"
cp -a "$ROOT/config/ecosystem-lock.json" "$DST/"
cp -a "$ROOT/workflow/Snakefile" "$DST/"
if [ -d "$SRC/figshare-demos" ]; then
  mkdir -p "$DST/figshare-demos"
  cp -a "$SRC/figshare-demos/"*.json "$DST/figshare-demos/" 2>/dev/null || true
fi
# Exclusive-node identity for GPU and v1 bars the paper cites
for f in \
  "$ROOT/results/reference/gpu-conditions-elja-1787449.txt" \
  "$ROOT/results/reference/tip-gpu-batch-elja-1787449.txt" \
  "$ROOT/results/reference/conditions-elja-1785712.txt"
do
  [ -f "$f" ] && cp -a "$f" "$DST/"
done
# Seeding committor / cubicity and the ice/brine summary
if [ -d "$ROOT/results/reference/elja-production" ]; then
  mkdir -p "$DST/production"
  for f in committor.txt committor.tex committor-table.tex \
           cubicity.txt cubicity.tex cubicity-table.tex \
           msm_features.csv msm_features.tex ml_labels.csv \
           brine_summary.txt brine.tex brine_conditions.txt conditions.txt; do
    [ -f "$ROOT/results/reference/elja-production/$f" ] && \
      cp -a "$ROOT/results/reference/elja-production/$f" "$DST/production/"
  done
fi
if [ -f "$ROOT/results/brine/summary.txt" ]; then
  mkdir -p "$DST/brine"
  for f in summary.txt brine.tex status.txt conditions.txt; do
    [ -f "$ROOT/results/brine/$f" ] && cp -a "$ROOT/results/brine/$f" "$DST/brine/"
  done
fi
if [ -f "$ROOT/results/production/committor.txt" ]; then
  mkdir -p "$DST/production"
  [ -f "$DST/production/committor.txt" ] || \
    cp -a "$ROOT/results/production/committor.txt" "$DST/production/"
  [ -f "$ROOT/results/production/conditions.txt" ] && \
    cp -a "$ROOT/results/production/conditions.txt" "$DST/production/"
fi
if [ -f "$ROOT/zenodo/RELEASE" ]; then
  cp -a "$ROOT/zenodo/RELEASE" "$DST/"
fi
# Refuse a manuscript if one was dropped in by accident
for bad in rg_main.org rg_main.pdf cover.pdf cover_letter.pdf highlights.pdf \
           highlights.docx; do
  if [ -e "$DST/$bad" ] || [ -e "$DST/production/$bad" ]; then
    echo "manuscript file $bad must not enter the payload" >&2
    exit 1
  fi
done
MANIFEST_TMP=$(mktemp /tmp/dseams-manifest.XXXXXX)
(cd "$DST" && find . -type f ! -name MANIFEST | sed 's|^\./||' | sort) > "$MANIFEST_TMP"
mv "$MANIFEST_TMP" "$DST/MANIFEST"
echo "staged $DST ($(wc -l < "$DST/MANIFEST") files)"

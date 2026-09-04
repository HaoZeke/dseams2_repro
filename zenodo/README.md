# Reproducibility deposit (Zenodo)

The deposit records the measurement campaign. Keep `rg_main.org`, the
Computer Physics Communications (CPC) PDF, the cover letter, and the
highlights out of this payload. Pin the software to a release tag.

## Payload

`paper_manifest.json` records parsed timings, identity checks, the
source graph, parity evidence and conditions.
`source-manifest.json` records the exact revisions used by the
campaign. `workflow-parity.json` is the CLI/Python/Lua agreement
report. `conditions.txt` records host, job, revisions, CPU and load.
`tip-*.txt` and `base-*.txt` are raw bench stdout.
`tip-incremental-*.txt` compares the hop-bound updater to a rebuild.
`tip-pipeline.txt` and `tip-stages-*.txt` break the ring, cage and
affiliation times. `config.yaml` and `ecosystem-lock.json` pin sizes
and source revisions. `Snakefile` is the directed acyclic graph (DAG)
that produced the files. `figshare-demos/` and
`figshare-incremental.json` cover the five v1 deposits.

`scripts/stage_zenodo.sh` fills `payload/` from `results/` after
`scripts/elja_submit.sh run` exits 0, or from
`results/reference/elja-1798666` when the live `results/` tree has no
manifest. Pin each software record to the paper release tag. Check that
each locked revision belongs to that tag. `zenodo/RELEASE` names the
tag and the locked engine.

The campaign archive tarball also carries `results/reference/` (GenIce
atlas, ion atlas, liquid-null sweep, polymorph library) and, when those
directories exist, `results/production/` and `results/brine/` from
`scripts/elja_production.sh`. Those campaign directories travel with
the payload at the same release tag. Trajectory dumps stay out of the
archive; the COLVAR files (`ICE`, `BRINE`) are the observables.

The exclusive-node campaign that the paper's timing figures read is
this record. The tagged release of seams-core / PydSEAMSlib /
yodaStruct is the CPC-library software tarball.

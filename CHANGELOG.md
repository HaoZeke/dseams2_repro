# Changelog

All notable changes to this project are documented in this file.

The format is [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Unreleased notes live in [`changelog.d/`](changelog.d/) and are assembled
by [towncrier](https://towncrier.readthedocs.io/).

<!-- towncrier release notes start -->

## [2.7.0] - 2026-09-04

### Added

- Elja ice/brine direct-coexistence campaign (24 finished BRINE
  files) and the seeding committor (216 ICE files) are interned
  with summary.txt, brine.tex and conditions. One Zenodo draft
  is staged from that tag.
- Rule genice_atlas (scripts/genice_atlas.py) labels Ice I, dense
  polymorphs, empty hydrate frameworks, porous ices and continuous
  random networks at rest and under positional noise.
- Rule ion_atlas (scripts/ion_atlas.py) places substitutional Na and Cl
  in ice Ih, Ic and the sI framework. The ions stay off the graph.
- Rule polymorph_library (scripts/polymorph_library.py) stores three-hop
  topology keys on the mutual four-nearest graph, with a two-hop
  fallback that records the depth that named each molecule.
- Snakemake emits pgfplots figures and a latex table from committor.txt
  and from the brine summary, so the Applications plots are campaign
  products rather than hand-edited coordinates.
- Snakemake products for cubicity, hydrate occupancy, Niu-pair
  features, frame-level ML labels, and dated notes when a shear,
  INP or brine dump is absent.
- The sota_sweep liquid null is the 512-molecule mW liquid at 215 K in
  data/mW_liquid_T215_512.data, reported as system=liquid in
  sota_compare.txt.
- scripts/elja_production.sh prep, submit and submit-brine drive the
  mW seeding campaign and the ice/brine direct-coexistence campaign
  on the production DAG.

### Changed

- CHANGELOG.md follows Keep a Changelog. Unreleased notes are
  changelog.d fragments assembled by towncrier.

### Fixed

- Elja production uses EasyBuild LAMMPS 23Jun2022 and ships genice2 in the
  production environment, so the seed and brine jobs run on glibc 2.28.

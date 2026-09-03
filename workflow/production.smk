# mW seeding campaign (Elja production). Run from the repository root:
#   pixi run -e production -- snakemake -s workflow/production.smk --configfile config/production.yaml --cores all
# The PLUMED module comes from dseams-plumed built in the production env
# (rule build_module); LAMMPS with PLUMED from conda-forge.
import itertools
import json
import os

configfile: "config/production.yaml"

R = "results/production"
MODULE = os.path.abspath(config.get("module", "build-plumed/libdseams_plumed.so"))
PLUMED_SRC = config.get("plumed_source", "sources/dseams-plumed")
RUNS = [
    f"T{T}_s{s}_{p}_r{r}"
    for T, s, p, r in itertools.product(
        config["temperatures"], config["seed_sizes"], config["polymorphs"], range(config["replicas"])
    )
]


def run_meta(wc):
    T, s, p, r = wc.run.split("_")
    return dict(temperature=int(T[1:]), seed_size=int(s[1:]), polymorph=p, replica=int(r[1:]))


rule all:
    input:
        R + "/committor.txt",


rule module_source:
    # The action's source at its current revision; the module rebuilds when
    # the revision changes, so a stale build cannot run with old engine
    # semantics (the first smoke did exactly that)
    output:
        PLUMED_SRC + "/.revision",
    params:
        src=PLUMED_SRC,
    shell:
        r"""
        if [ -d {params.src}/.git ]; then git -C {params.src} pull -q --ff-only; \
        else git clone -q https://github.com/d-SEAMS/dseams-plumed.git {params.src}; fi
        git -C {params.src} rev-parse HEAD > {output}
        """


rule build_module:
    input:
        PLUMED_SRC + "/.revision",
    output:
        MODULE,
    params:
        src=PLUMED_SRC,
    shell:
        r"""
        export RUSTFLAGS="${{SEAMS_RUSTFLAGS:-}}"
        # Build on node-local disk: cluster fileservers can run ahead of the
        # login node clock, and meson aborts on build files with mtimes in
        # the future. The engine is linked statically into the module so the
        # single .so is the whole artifact.
        BLOCAL="${{TMPDIR:-/tmp}}/${{USER}}-dseams-plumed-build"
        rm -rf "$BLOCAL" "$BLOCAL-src"
        cp -r {params.src} "$BLOCAL-src"
        # the wrap revision moves with the module; a cached engine checkout
        # would otherwise be reused at its old revision (the redirect wraps
        # need the directory to exist, so reset rather than delete)
        meson subprojects update --reset --sourcedir "$BLOCAL-src" seams-core
        find "$BLOCAL-src" -exec touch {{}} +
        meson setup "$BLOCAL" "$BLOCAL-src" --buildtype=release -Dseams-core:default_library=static
        meson compile -C "$BLOCAL"
        install -D "$BLOCAL/libdseams_plumed.so" {output}
        """


rule packing:
    output:
        R + "/liquid/T{T}/packing.data",
    params:
        n=config["n_liquid"],
    shell:
        "python scripts/seed_ice.py --n-liquid {params.n} --no-seed --rng {wildcards.T} --out {output}"


rule liquid:
    # Melt the packing hot, settle at T and P: the liquid every seed of this
    # temperature is cut into
    input:
        R + "/liquid/T{T}/packing.data",
    output:
        R + "/liquid/T{T}/liquid.data",
    params:
        P=config["pressure_bar"],
        melt=config.get("liquid_melt_steps", 20000),
        eq=config.get("liquid_eq_steps", 20000),
    threads: config["lammps_threads"]
    shell:
        r"""
        d=$(dirname {output}); cp templates/mW.sw $d/; cd $d
        OMP_NUM_THREADS={threads} lmp -sf omp -log log.liquid -in ../../../../templates/in.liquid.lammps           -var data packing.data -var T {wildcards.T} -var P {params.P}           -var steps_melt {params.melt} -var steps_eq {params.eq} -var seed 7{wildcards.T}           -var out liquid.data > lammps.out 2>&1
        test -s liquid.data
        """


rule seed:
    input:
        lambda wc: R + "/liquid/T%d/liquid.data" % run_meta(wc)["temperature"],
    output:
        data=R + "/{run}/seeded.data",
        meta=R + "/{run}/run.json",
    params:
        m=run_meta,
        n=config["n_liquid"],
    run:
        m = params.m
        shell(
            "python scripts/seed_ice.py --n-liquid {params.n} --seed-size %d --polymorph %s "
            "--liquid-data {input} --rng %d --out {output.data}" % (m["seed_size"], m["polymorph"], 1000 + m["replica"])
        )
        with open(output.meta, "w") as fh:
            json.dump(m, fh)


rule plumed_input:
    input:
        data=R + "/{run}/seeded.data",
        module=MODULE,
    output:
        R + "/{run}/plumed.dat",
    params:
        m=run_meta,
        stride=config["plumed_stride"],
        melt=config["melt_basin"],
        grow=config["grow_factor"],
    run:
        natoms = int(next(l.split()[0] for l in open(input.data) if l.strip().endswith("atoms")))
        text = open("templates/plumed_seed.dat").read()
        text = (text.replace("@MODULE@", input.module).replace("@NATOMS@", str(natoms))
                .replace("@STRIDE@", str(params.stride)).replace("@MELT@", str(params.melt))
                .replace("@GROW@", str(int(params.grow * params.m["seed_size"]))))
        open(output[0], "w").write(text)


rule run:
    input:
        data=R + "/{run}/seeded.data",
        plumed=R + "/{run}/plumed.dat",
    output:
        ice=R + "/{run}/ICE",
        log=R + "/{run}/log.lammps",
    params:
        m=run_meta,
        steps=config["steps"],
        dump=config["dump_every"],
        P=config["pressure_bar"],
    threads: config["lammps_threads"]
    shell:
        r"""
        d=$(dirname {output.ice}); cp templates/mW.sw $d/; cd $d
        OMP_NUM_THREADS={threads} lmp -sf omp -log log.lammps -in ../../../templates/in.seed.lammps \
          -var data seeded.data -var T {params.m[temperature]} -var P {params.P} \
          -var steps {params.steps} -var dumpevery {params.dump} -var seed {params.m[replica]}1 \
          -var plumed plumed.dat -var dump traj.lammpstrj > lammps.out 2>&1 || true
        # COMMITTOR stops the run early; an ICE file is the result either way
        test -s ICE
        """


rule committor:
    input:
        expand(R + "/{run}/ICE", run=RUNS),
    output:
        R + "/committor.txt",
    params:
        melt=config["melt_basin"],
    shell:
        "python scripts/committor.py " + R + " --melt {params.melt} > {output}"

# --- Ice/brine direct coexistence: TIP4P/2005 water, Madrid 2019 NaCl ---
BRINE = config.get("brine", {})
BRINE_RUNS = [
    f"T{T}_m{m}_r{r}"
    for T, m, r in itertools.product(
        BRINE.get("temperatures", []), BRINE.get("pairs", []), range(BRINE.get("replicas", 0))
    )
]
RB = "results/brine"


def brine_meta(wc):
    T, m, r = wc.brun.split("_")
    return dict(temperature=int(T[1:]), pairs=int(m[1:]), replica=int(r[1:]))


rule brine_build:
    # GenIce ice Ih with TIP4P geometry, upper half marked liquid, NaCl pairs
    # drawn among its molecules
    output:
        data=RB + "/{brun}/brine.data",
        groups=RB + "/{brun}/groups.lmp",
    params:
        m=brine_meta,
        rep=" ".join(str(x) for x in BRINE.get("rep", [4, 4, 6])),
    shell:
        "python scripts/brine_system.py --rep {params.rep} --pairs {params.m[pairs]} "
        "--seed {params.m[replica]} --data {output.data} --groups {output.groups} "
        "> $(dirname {output.data})/build.txt"


rule brine_plumed:
    input:
        data=RB + "/{brun}/brine.data",
        module=MODULE,
    output:
        RB + "/{brun}/plumed.dat",
    params:
        stride=BRINE.get("plumed_stride", 500),
    run:
        oxygens, ions = [], []
        with open(input.data) as fh:
            in_atoms = False
            for line in fh:
                if line.startswith("Atoms"):
                    in_atoms = True
                    continue
                if in_atoms:
                    if line.startswith(("Bonds", "Angles", "Velocities")):
                        break
                    cols = line.split()
                    if len(cols) >= 7:
                        aid, typ = int(cols[0]), int(cols[2])
                        if typ == 1:
                            oxygens.append(aid)
                        elif typ in (3, 4):
                            ions.append(aid)

        def ranges(ids):
            ids = sorted(ids)
            out, start, prev = [], ids[0], ids[0]
            for x in ids[1:]:
                if x != prev + 1:
                    out.append(f"{start}-{prev}" if start != prev else f"{start}")
                    start = x
                prev = x
            out.append(f"{start}-{prev}" if start != prev else f"{start}")
            return ",".join(out)

        text = open("templates/plumed_brine.dat").read()
        text = (text.replace("@MODULE@", input.module).replace("@OXYGENS@", ranges(oxygens))
                .replace("@IONS@", ranges(ions)).replace("@STRIDE@", str(params.stride)))
        open(output[0], "w").write(text)


rule brine_run:
    input:
        data=RB + "/{brun}/brine.data",
        groups=RB + "/{brun}/groups.lmp",
        plumed=RB + "/{brun}/plumed.dat",
    output:
        RB + "/{brun}/BRINE",
    params:
        m=brine_meta,
        P=config["pressure_bar"],
        melt=BRINE.get("melt_steps", 50000),
        steps=BRINE.get("steps", 2500000),
        dump=BRINE.get("dump_every", 25000),
    threads: config["lammps_threads"]
    shell:
        r"""
        cd $(dirname {output})
        OMP_NUM_THREADS={threads} lmp -sf omp -log log.lammps -in ../../../templates/in.brine.lammps           -var data brine.data -var groups groups.lmp -var T {params.m[temperature]} -var P {params.P}           -var steps_melt {params.melt} -var steps {params.steps} -var dumpevery {params.dump}           -var seed {params.m[replica]}3 -var plumed plumed.dat -var dump traj.lammpstrj > lammps.out 2>&1
        test -s BRINE
        """


rule brine_all:
    input:
        expand(RB + "/{brun}/BRINE", brun=BRINE_RUNS),
    output:
        RB + "/summary.txt",
    shell:
        "python scripts/brine_summary.py " + RB + " > {output}"

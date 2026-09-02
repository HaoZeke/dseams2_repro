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
        else git clone -q https://github.com/HaoZeke/dseams-plumed.git {params.src}; fi
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

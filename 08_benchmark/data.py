"""data.py — DFT database and MLIP inference result loading."""
import csv
import json
import os
from collections import defaultdict
from ase.db import connect

BASE_DIR     = "/DATA/user_scratch/jsh9967/12_sensor/0_benchmark"
RESULTS_DIR  = os.path.join(BASE_DIR, "results")
CURATED_DIR  = os.path.join(BASE_DIR, "curated")

# Canonical DFT database paths
ALL_DB      = os.path.join(CURATED_DIR, "all.db")       # 1167 entries, all metals
PD_DB       = os.path.join(CURATED_DIR, "Pd.db")        # 39 entries  (B1-B3)
SNO2_DB     = os.path.join(CURATED_DIR, "SnO2_only.db") # 36 entries  (B1-B3)
LOCAL_DB    = os.path.join(BASE_DIR, "sensor_bench", "dft_raw_data.db")  # local copy


# ── DFT data ───────────────────────────────────────────────────────────────

def load_dft(scope="all"):
    """
    Load DFT energies into a nested dict:
      groups[(metal, config)][calc] = {E, syms, formula, natoms, source}

    scope="all"  → all.db (1167 structures, B4-B7 and full B1-B3 via Pd/SnO2 filter)
    scope="b123" → Pd.db + SnO2_only.db (75 structures, legacy B1-B3 source)
    """
    groups = defaultdict(dict)

    if scope == "b123":
        # Legacy: load from separate Pd.db + SnO2_only.db
        sources = [("Pd", PD_DB), ("SnO2", SNO2_DB)]
        for db_tag, db_path in sources:
            if not os.path.exists(db_path):
                continue
            db = connect(db_path)
            for r in db.select():
                metal = r.get("SAC_metal", db_tag)
                cfg   = r.get("configuration", "")
                calc  = r.get("calculation",   "")
                groups[(metal, cfg)][calc] = {
                    "E":      r.data["final_energy"],
                    "syms":   list(r.toatoms().get_chemical_symbols()),
                    "formula": r.formula,
                    "natoms": r.natoms,
                    "source": r.get("source_db", db_tag),
                }
    else:
        # Primary: all.db
        db_path = ALL_DB if os.path.exists(ALL_DB) else LOCAL_DB
        db = connect(db_path)
        for r in db.select():
            metal = r.get("SAC_metal", "SnO2")
            cfg   = r.get("configuration", "")
            calc  = r.get("calculation",   "")
            groups[(metal, cfg)][calc] = {
                "E":      r.data["final_energy"],
                "syms":   list(r.toatoms().get_chemical_symbols()),
                "formula": r.formula,
                "natoms": r.natoms,
                "source": r.get("source_db", ""),
            }
    return groups


def load_mlip(model, scope="all"):
    """
    Load MLIP inference results.
      scope="all"  → results/{model}_all_raw_energies.csv
      scope="b123" → results/{model}_raw_energies.csv

    Returns dict: (metal, config, calc) → energy (float) | None
    Returns None if the file does not exist.
    """
    if scope == "b123":
        path = os.path.join(RESULTS_DIR, f"{model}_raw_energies.csv")
    else:
        path = os.path.join(RESULTS_DIR, f"{model}_all_raw_energies.csv")

    if not os.path.exists(path):
        return None

    out = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            metal  = row.get("SAC_metal") or row.get("db", "")
            config = row.get("config", row.get("configuration", ""))
            calc   = row.get("calculation", "")
            e_str  = row.get("mlip_energy", "")
            out[(metal, config, calc)] = float(e_str) if e_str else None
    return out


def load_mu_metals():
    """
    Load DFT bulk metal chemical potentials from results/mu_metals.csv.
      Returns dict: metal → μ (eV/atom) | None
    """
    path = os.path.join(RESULTS_DIR, "mu_metals.csv")
    mu = {}
    if not os.path.exists(path):
        return mu
    with open(path) as f:
        for row in csv.DictReader(f):
            val = row.get("mu_eV_per_atom", "")
            mu[row["metal"]] = float(val) if val else None
    return mu


def load_dft_refs():
    """
    Full DFT reference set for computing e_dft with correct DFT corrections.

    Combines:
      - Gas-phase refs: H, O, H2, H2O, Sn (from refs.DFT_GAS_REFS)
      - Bulk metal μ: all 29 SAC metals from results/mu_metals.csv

    Returns dict: element → μ (eV/atom)
    """
    from sensor_bench.refs import DFT_GAS_REFS
    refs = dict(DFT_GAS_REFS)
    for metal, mu in load_mu_metals().items():
        if mu is not None:
            refs[metal] = mu
    return refs


# ── Legacy helpers (kept for backward compat) ──────────────────────────────

def build_db(src=None, out_db="dft_raw_data.db", out_json="index.json"):
    """Copy curated ASE DB → out_db and write index.json."""
    if src is None:
        src = ALL_DB
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source DB not found: {src}")
    db_in  = connect(src)
    db_out = connect(out_db, append=False)
    index  = {}
    for r in db_in.select():
        metal = r.get("SAC_metal", "SnO2")
        cfg   = r.get("configuration", "")
        calc  = r.get("calculation",   "")
        row_id = db_out.write(
            r.toatoms(),
            SAC_metal=metal, configuration=cfg, calculation=calc,
            source_db=r.get("source_db", ""),
            data={"final_energy": r.data["final_energy"]},
        )
        index[f"{metal}|{cfg}|{calc}"] = row_id
    with open(out_json, "w") as f:
        json.dump(index, f, indent=2)
    print(f"Built {out_db}: {len(index)} entries  →  {out_json}")


def load_groups(db_path=None):
    """Return groups[(metal, cfg)][calc] = {E, syms, formula, source, natoms}"""
    if db_path is None:
        db_path = ALL_DB if os.path.exists(ALL_DB) else LOCAL_DB
    return load_dft(scope="all")


def load_atoms_iter(db_path=None):
    """Yield (metal, cfg, calc, atoms) for inference."""
    if db_path is None:
        db_path = ALL_DB if os.path.exists(ALL_DB) else LOCAL_DB
    db = connect(db_path)
    for r in db.select():
        yield (
            r.get("SAC_metal", "SnO2"),
            r.get("configuration", ""),
            r.get("calculation",   ""),
            r.toatoms(),
        )

"""refs.py — Model-specific reference energy loading. NO DFT fallback."""
import csv
import math
import os
from collections import Counter

BASE_DIR      = "/DATA/user_scratch/jsh9967/12_sensor/0_benchmark"
MLIP_REFS_DIR = os.path.join(BASE_DIR, "results", "mlip_refs")

# DFT RPBE references (VASP gas_phase_calc/ on login node + slab-derived Sn)
# These are used for computing e_dft with the correct DFT correction.
_H2_DFT  = -6.98891882     # eV, total E(H2)
_H2O_DFT = -14.14778058    # eV, total E(H2O)
DFT_GAS_REFS = {
    "H2":  _H2_DFT,
    "H2O": _H2O_DFT,
    "H":   _H2_DFT / 2,              # μ_H = E(H2)/2 = -3.4945 eV/atom
    "O":   _H2O_DFT - _H2_DFT,      # μ_O = E(H2O) - E(H2) = -7.1587 eV
    "Sn":  -2.836,                    # slab-derived μ_Sn (avg 100f:-2.852, 110f:-2.821)
}


def load_model_refs(model):
    """
    Load self-consistent refs from results/mlip_refs/{model}_refs.csv.

    Returns dict with:
      "H2", "H2O"  — total energies (eV)
      "H", "O"     — per-atom chemical potentials (eV/atom)
      "Ag", "Au", ..., "Zr", "Sn", "Pd", ...  — per-atom μ_M (eV/atom)
      nan entries preserved for metals whose calculation failed.

    Returns None if the refs CSV does not exist yet (model not yet computed).
    NO DFT fallback — caller must handle None as n/a.
    """
    csv_path = os.path.join(MLIP_REFS_DIR, f"{model}_refs.csv")
    if not os.path.exists(csv_path):
        return None

    raw = {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            tag = row["tag"]
            try:
                e = float(row["energy"])
            except (ValueError, KeyError):
                e = float("nan")
            n = int(row["natoms"])
            raw[tag] = (e, n)   # (total_energy, natoms)

    result = {}

    # Gas references
    if "H2" in raw:
        e_h2, n = raw["H2"]
        result["H2"] = e_h2
        result["H"]  = e_h2 / n          # μ_H = E(H2)/2
    if "H2O" in raw and "H2" in raw:
        e_h2o, _ = raw["H2O"]
        result["H2O"] = e_h2o
        result["O"]   = e_h2o - result["H2"]   # μ_O = E(H2O) - E(H2)

    # Metal bulk per-atom μ
    for tag, (e, n) in raw.items():
        if tag not in ("H2", "H2O"):
            result[tag] = e / n           # μ_M = E_bulk / n_atoms (nan preserved)

    return result


def che_correction(ref_syms, ads_syms, refs):
    """
    CHE stoichiometry correction using model-specific refs:
      corr = dO * μ_O + dH * μ_H
    where μ_O = H2O - H2, μ_H = H2/2 (already in refs).

    Returns (corr, dO, dH). corr is nan if H/O refs are nan.
    """
    s  = Counter(ref_syms)
    a  = Counter(ads_syms)
    dO = a.get("O", 0) - s.get("O", 0)
    dH = a.get("H", 0) - s.get("H", 0)
    mu_O = refs.get("O", float("nan"))
    mu_H = refs.get("H", float("nan"))
    corr = dO * mu_O + dH * mu_H
    return corr, dO, dH


def mu_ok(refs, *keys):
    """Return True if all keys exist in refs and are finite (not nan)."""
    for k in keys:
        v = refs.get(k, float("nan"))
        if v is None or math.isnan(v):
            return False
    return True

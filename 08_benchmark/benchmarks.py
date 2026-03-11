"""benchmarks.py — B1-B7 benchmark computations.

All functions signature:
    b*(groups_dft, mlip, model_refs, ...)
    → list of result dicts

model_refs: output of refs.load_model_refs(model)
  Required keys vary by benchmark (see docstrings).
  nan values → that entry skipped (n/a), NOT replaced by DFT refs.
"""
import math
from collections import Counter, defaultdict
from sensor_bench.refs import che_correction, mu_ok
from sensor_bench.metrics import stats, spearman, pearson

OER_ADS = ["O", "OH", "OOH"]
LOM_ADS = ["LOM-H"]

EXCLUDE_METALS = {"Sc", "Hg"}   # unphysical / excluded from B4/B7


# ── B1: Pd OER adsorption (25 OER + 2 LOM-H pairs) ───────────────────────
def b1_oer(groups, mlip, model_refs, dft_refs=None):
    """Pd-only OER adsorption energies.

    e_dft uses dft_refs (DFT RPBE gas-phase μ_H, μ_O) for the CHE correction.
    e_ml  uses model_refs (model-specific μ_H, μ_O).
    Required model_refs: H, O (derived from H2, H2O).
    """
    return _adsorption(groups, mlip, model_refs, metals=["Pd"], label="B1",
                       dft_refs=dft_refs)


# ── B5: All-metal OER + LOM adsorption (809 pairs) ────────────────────────
def b5_oer_all(groups, mlip, model_refs, dft_refs=None):
    """All SAC metals, OER surface→O/OH/OOH + LOM O-vac→LOM-H."""
    return _adsorption(groups, mlip, model_refs, metals=None, label="B5",
                       dft_refs=dft_refs)


# ── B6: All-metal OER only (no LOM-H, ~701 pairs) ─────────────────────────
def b6_oer_filtered(groups, mlip, model_refs, dft_refs=None):
    """All SAC metals, OER surface→O/OH/OOH only (no LOM-H)."""
    return _adsorption(groups, mlip, model_refs, metals=None, label="B6",
                       include_lom=False, dft_refs=dft_refs)


def _adsorption(groups, mlip, model_refs, metals, label, include_lom=True,
                dft_refs=None):
    """Core OER/LOM adsorption computation.

    e_dft: DFT raw energies corrected with dft_refs μ_H/μ_O (physically correct).
    e_ml:  MLIP raw energies corrected with model_refs μ_H/μ_O (model-consistent).
    If dft_refs is None, falls back to model_refs for e_dft (backward compat).
    """
    if not mu_ok(model_refs, "H", "O"):
        return []   # can't compute e_ml without H/O model refs

    _dft = dft_refs if dft_refs is not None else model_refs

    results = []
    for (metal, cfg), calcs in sorted(groups.items()):
        if metals and metal not in metals:
            continue
        if metal in EXCLUDE_METALS:
            continue

        # OER: surface → O*, OH*, OOH*
        slab = calcs.get("surface")
        if slab:
            for ads in OER_ADS:
                if ads not in calcs:
                    continue
                adslab = calcs[ads]
                corr_ml, dO, dH = che_correction(slab["syms"], adslab["syms"], model_refs)
                if math.isnan(corr_ml):
                    continue
                # e_dft uses DFT gas-phase μ (avoids applying model energy scale to DFT)
                corr_dft = dO * _dft.get("O", float("nan")) + dH * _dft.get("H", float("nan"))
                e_dft = adslab["E"] - slab["E"] - corr_dft
                em_s  = mlip.get((metal, cfg, "surface")) if mlip else None
                em_a  = mlip.get((metal, cfg, ads))       if mlip else None
                e_ml  = (em_a - em_s - corr_ml) if (em_s is not None and em_a is not None) else None
                results.append(dict(bench=label, metal=metal, config=cfg,
                                    ref="surface", ads=ads, dO=dO, dH=dH,
                                    e_dft=e_dft, e_ml=e_ml,
                                    err=(e_ml - e_dft) if e_ml is not None else None))

        # LOM: O-vac → LOM-H
        if include_lom:
            ovac = calcs.get("O-vac")
            if ovac:
                for ads in LOM_ADS:
                    if ads not in calcs:
                        continue
                    adslab = calcs[ads]
                    corr_ml, dO, dH = che_correction(ovac["syms"], adslab["syms"], model_refs)
                    if math.isnan(corr_ml):
                        continue
                    corr_dft = dO * _dft.get("O", float("nan")) + dH * _dft.get("H", float("nan"))
                    e_dft = adslab["E"] - ovac["E"] - corr_dft
                    em_o  = mlip.get((metal, cfg, "O-vac")) if mlip else None
                    em_a  = mlip.get((metal, cfg, ads))     if mlip else None
                    e_ml  = (em_a - em_o - corr_ml) if (em_o is not None and em_a is not None) else None
                    results.append(dict(bench=label, metal=metal, config=cfg,
                                        ref="O-vac", ads=ads, dO=dO, dH=dH,
                                        e_dft=e_dft, e_ml=e_ml,
                                        err=(e_ml - e_dft) if e_ml is not None else None))
    return results


# ── B2: Formation energy — Pd+SnO2 (75 structures) ────────────────────────
def b2_formation(groups, mlip, model_refs, dft_refs=None):
    """Formation energies for Pd+SnO2 subset.

    e_f_dft uses dft_refs μ (DFT RPBE); e_f_ml uses model_refs μ.
    """
    return _formation(groups, mlip, model_refs, metals=["Pd", "SnO2"], label="B2",
                      dft_refs=dft_refs)


# ── B4: Formation energy — all 1167 structures ────────────────────────────
def b4_formation_all(groups, mlip, model_refs, dft_refs=None):
    """Formation energies for all metals.

    e_f_dft uses dft_refs μ (DFT RPBE + bulk metals from mu_metals.csv).
    e_f_ml  uses model_refs μ (model-consistent references).
    """
    return _formation(groups, mlip, model_refs, metals=None, label="B4",
                      dft_refs=dft_refs)


def _formation(groups, mlip, model_refs, metals, label, dft_refs=None):
    """Core formation energy computation.

    E_f = [E_total - Σ n_i * μ_i] / N_atoms

    e_f_dft: uses dft_refs μ (DFT correction) → physically correct DFT E_f.
    e_f_ml:  uses model_refs μ (model correction) → model E_f relative to model refs.
    If dft_refs is None, falls back to model_refs for e_f_dft (backward compat).
    Entries where required μ is missing → skipped.
    """
    _dft = dft_refs if dft_refs is not None else model_refs
    results = []
    missing_dft_logged = set()
    missing_ml_logged  = set()

    for (metal, cfg), calcs in sorted(groups.items()):
        if metals and metal not in metals:
            continue
        if metal in EXCLUDE_METALS:
            continue

        for calc, info in calcs.items():
            syms = Counter(info["syms"])
            nat  = info["natoms"]

            # DFT μ for e_f_dft
            mu_dft_el = {}
            skip_dft = False
            for el in syms:
                val = _dft.get(el, float("nan"))
                if val is None or math.isnan(val):
                    if el not in missing_dft_logged:
                        missing_dft_logged.add(el)
                    skip_dft = True
                    break
                mu_dft_el[el] = val

            if skip_dft:
                continue   # can't compute e_f_dft → skip entire entry

            # Model μ for e_f_ml
            mu_ml_el = {}
            skip_ml = False
            for el in syms:
                val = model_refs.get(el, float("nan"))
                if val is None or math.isnan(val):
                    if el not in missing_ml_logged:
                        missing_ml_logged.add(el)
                    skip_ml = True
                    break
                mu_ml_el[el] = val

            ref_e_dft = sum(syms[el] * mu_dft_el[el] for el in syms)
            e_f_dft   = (info["E"] - ref_e_dft) / nat

            e_ml_r = mlip.get((metal, cfg, calc)) if mlip else None
            if e_ml_r is not None and not skip_ml:
                ref_e_ml = sum(syms[el] * mu_ml_el[el] for el in syms)
                e_f_ml   = (e_ml_r - ref_e_ml) / nat
            else:
                e_f_ml = None

            results.append(dict(bench=label, metal=metal, config=cfg,
                                calculation=calc, formula=info["formula"],
                                natoms=nat, e_f_dft=e_f_dft, e_f_ml=e_f_ml,
                                err=(e_f_ml - e_f_dft) if e_f_ml is not None else None))

    if missing_dft_logged:
        print(f"  [{label}] skipped (missing DFT μ): {sorted(missing_dft_logged)}")
    if missing_ml_logged:
        print(f"  [{label}] e_f_ml=None (missing model μ): {sorted(missing_ml_logged)}")
    return results


# ── B3: Pd@SnO2 anchor + substitution ─────────────────────────────────────
def b3_anchor(groups, mlip, model_refs, dft_refs=None):
    """Pd@SnO2 anchoring (adatom) and substitution energies.

    e_dft uses dft_refs μ_Pd, μ_Sn (DFT RPBE).
    e_ml  uses model_refs μ_Pd, μ_Sn (model-specific).
    Anchor:       E = E(M/SnO2) - E(SnO2) - μ_M
    Substitution: E = E(M/SnO2) - E(SnO2) + μ_Sn - μ_M
    """
    return _anchor(groups, mlip, model_refs, metals=["Pd"], label="B3",
                   dft_refs=dft_refs)


# ── B7: All-metal anchor + substitution ───────────────────────────────────
def b7_anchor_all(groups, mlip, model_refs, dft_refs=None):
    """Anchor and substitution energies for all SAC metals.

    Same formula as B3 but applied to all 29 metals.
    e_dft uses dft_refs; e_ml uses model_refs.
    """
    return _anchor(groups, mlip, model_refs, metals=None, label="B7",
                   dft_refs=dft_refs)


def _anchor(groups, mlip, model_refs, metals, label, dft_refs=None):
    """Core anchor/substitution computation.

    e_dft: uses dft_refs μ_M and μ_Sn → physically correct DFT anchor/sub energy.
    e_ml:  uses model_refs μ_M and μ_Sn → model-consistent anchor/sub energy.
    If dft_refs is None, falls back to model_refs for e_dft (backward compat).
    """
    _dft = dft_refs if dft_refs is not None else model_refs

    # μ_Sn from DFT refs (for e_dft) and model refs (for e_ml)
    mu_Sn_dft = _dft.get("Sn", float("nan"))
    mu_Sn_ml  = model_refs.get("Sn", float("nan"))

    if math.isnan(mu_Sn_dft):
        print(f"  [{label}] skipped: μ_Sn not in dft_refs")
        return []

    # Collect SnO2-only surface references
    sno2_surfs = []
    for (metal, cfg), calcs in groups.items():
        if metal == "SnO2" and "surface" in calcs:
            facet = cfg.split("-")[0]
            sno2_surfs.append(dict(config=cfg, facet=facet,
                                   natoms=calcs["surface"]["natoms"],
                                   E=calcs["surface"]["E"]))

    def find_ref(cfg, nat, facet, is_adatom):
        target = nat - 1 if is_adatom else nat
        for s in sno2_surfs:
            if s["config"] == cfg and s["natoms"] == target:
                return s, "exact"
        cands = [s for s in sno2_surfs if s["facet"] == facet and s["natoms"] == target]
        if not cands:
            return None, None
        med_E = sorted(s["E"] for s in cands)[len(cands) // 2]
        best  = min(cands, key=lambda s: abs(s["E"] - med_E))
        return best, f"fallback({best['config']})"

    results = []
    for (metal, cfg), calcs in sorted(groups.items()):
        if metals and metal not in metals:
            continue
        if metal in EXCLUDE_METALS or metal == "SnO2":
            continue
        if "surface" not in calcs:
            continue

        # DFT μ_M for e_dft
        mu_M_dft = _dft.get(metal, float("nan"))
        if mu_M_dft is None or math.isnan(mu_M_dft):
            continue   # DFT metal ref missing → skip

        info      = calcs["surface"]
        facet     = cfg.split("-")[0]
        is_adatom = "adatom" in cfg
        ref, match = find_ref(cfg, info["natoms"], facet, is_adatom)
        if ref is None:
            continue

        dE_dft = info["E"] - ref["E"]
        e_dft  = (dE_dft - mu_M_dft) if is_adatom else (dE_dft + mu_Sn_dft - mu_M_dft)

        # Model μ_M for e_ml
        mu_M_ml = model_refs.get(metal, float("nan"))
        em_M   = mlip.get((metal,   cfg,          "surface")) if mlip else None
        em_Sn2 = mlip.get(("SnO2",  ref["config"], "surface")) if mlip else None
        if em_M is not None and em_Sn2 is not None and not math.isnan(mu_M_ml) and not math.isnan(mu_Sn_ml):
            dE_ml = em_M - em_Sn2
            e_ml  = (dE_ml - mu_M_ml) if is_adatom else (dE_ml + mu_Sn_ml - mu_M_ml)
            err   = e_ml - e_dft
        else:
            e_ml = err = None

        btype = f"{label}_anchor" if is_adatom else f"{label}_sub"
        results.append(dict(bench=btype, metal=metal, config=cfg,
                            e_dft=e_dft, e_ml=e_ml, err=err,
                            ref_config=ref["config"], match=match))
    return results


# ── Summary statistics helpers ─────────────────────────────────────────────

def summarize_ads(results, label):
    """Return summary dict for adsorption benchmark results.

    Includes overall OER/LOM stats AND per-adsorbate (O, OH, OOH, LOM-H) breakdown.
    """
    oer = [r for r in results if r["ref"] == "surface"]
    lom = [r for r in results if r["ref"] == "O-vac"]
    all_ = results

    def _rho(rs):
        pairs = [(r["e_dft"], r["e_ml"]) for r in rs if r["e_ml"] is not None]
        if len(pairs) < 2: return float("nan")
        xs, ys = zip(*pairs)
        return spearman(xs, ys)

    def _r(rs):
        pairs = [(r["e_dft"], r["e_ml"]) for r in rs if r["e_ml"] is not None]
        if len(pairs) < 2: return float("nan")
        xs, ys = zip(*pairs)
        return pearson(xs, ys)

    p = label.lower()
    s_oer = stats([r["err"] for r in oer])
    s_lom = stats([r["err"] for r in lom])
    s_all = stats([r["err"] for r in all_])
    out = {
        f"{p}_oer_n":    s_oer["n"],   f"{p}_oer_mae":  s_oer["mae"],
        f"{p}_oer_rmse": s_oer["rmse"],f"{p}_oer_bias": s_oer["bias"],
        f"{p}_oer_r":    _r(oer),       f"{p}_oer_rho":  _rho(oer),
        f"{p}_lom_n":    s_lom["n"],   f"{p}_lom_mae":  s_lom["mae"],
        f"{p}_lom_rmse": s_lom["rmse"],f"{p}_lom_bias": s_lom["bias"],
        f"{p}_n":        s_all["n"],   f"{p}_mae":      s_all["mae"],
        f"{p}_rmse":     s_all["rmse"],f"{p}_bias":     s_all["bias"],
        f"{p}_r":        _r(all_),      f"{p}_rho":      _rho(all_),
    }
    # Per-adsorbate breakdown (for figures 3 & 4)
    for ads in ["O", "OH", "OOH"]:
        rs = [r for r in oer if r["ads"] == ads]
        s  = stats([r["err"] for r in rs])
        out[f"{p}_{ads}_mae"] = s["mae"]
        out[f"{p}_{ads}_rho"] = _rho(rs)
    # LOM-H per-adsorbate
    rs = [r for r in lom if r["ads"] == "LOM-H"]
    s  = stats([r["err"] for r in rs])
    out[f"{p}_LOM_mae"] = s["mae"]
    out[f"{p}_LOM_rho"] = _rho(rs)
    return out


def summarize_formation(results, label):
    """Return summary dict for formation energy benchmark results."""
    p = label.lower()
    s = stats([r["err"] for r in results])
    # Spearman ρ over metal-averaged E_f
    metals = defaultdict(lambda: {"dft": [], "ml": []})
    for r in results:
        if r["e_f_ml"] is not None:
            metals[r["metal"]]["dft"].append(r["e_f_dft"])
            metals[r["metal"]]["ml"].append(r["e_f_ml"])
    avg_dft = [sum(v["dft"]) / len(v["dft"]) for v in metals.values()]
    avg_ml  = [sum(v["ml"])  / len(v["ml"])  for v in metals.values()]
    rho = spearman(avg_dft, avg_ml)
    r   = pearson(avg_dft, avg_ml)
    return {
        f"{p}_n":    s["n"],  f"{p}_mae":  s["mae"],
        f"{p}_rmse": s["rmse"], f"{p}_bias": s["bias"],
        f"{p}_r":    r,         f"{p}_rho":  rho,
    }


def summarize_anchor(results, label):
    """Return summary dict for anchor/substitution benchmark results."""
    p = label.lower()
    anc = [r for r in results if r["bench"].endswith("_anchor")]
    sub = [r for r in results if r["bench"].endswith("_sub")]

    def _rho(rs):
        pairs = [(r["e_dft"], r["e_ml"]) for r in rs if r["e_ml"] is not None]
        if len(pairs) < 2: return float("nan")
        xs, ys = zip(*pairs)
        return spearman(xs, ys)

    sa = stats([r["err"] for r in anc])
    ss = stats([r["err"] for r in sub])
    return {
        f"{p}_anc_n":    sa["n"],   f"{p}_anc_mae":  sa["mae"],
        f"{p}_anc_rmse": sa["rmse"],f"{p}_anc_bias": sa["bias"],
        f"{p}_anc_rho":  _rho(anc),
        f"{p}_sub_n":    ss["n"],   f"{p}_sub_mae":  ss["mae"],
        f"{p}_sub_rmse": ss["rmse"],f"{p}_sub_bias": ss["bias"],
        f"{p}_sub_rho":  _rho(sub),
    }

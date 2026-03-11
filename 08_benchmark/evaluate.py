#!/usr/bin/env python3
"""
evaluate.py — MACE inference + B1-B5 benchmarks on SnO2 SAC OER dataset.

Requires:
    dft_raw_data.db   (build with: python evaluate.py --build-db)
    index.json        (built alongside dft_raw_data.db)
    mu_metals.csv     (optional; for B4 all-metal formation energy)

Usage:
    # One-time: build the merged DB from curated source files
    python evaluate.py --build-db

    # Run inference + benchmarks
    python evaluate.py --model mace_mh1_omat
    python evaluate.py --model mace_mh1_oc20
    python evaluate.py --model mace_omat0

    # Use CPU
    python evaluate.py --model mace_omat0 --device cpu

    # Skip B4/B5 (fast, only 75 structures)
    python evaluate.py --model mace_omat0 --b123-only
"""
import argparse
import csv
import os
import sys
import time

# ── Paths ──────────────────────────────────────────────────────────────────
HERE      = os.path.dirname(os.path.abspath(__file__))
CKPT      = "/DATA/user_scratch/jsh9967/12_sensor/checkpoints"
DB_PATH   = os.path.join(HERE, "dft_raw_data.db")
MU_CSV    = os.path.join(HERE, "mu_metals.csv")
OUT_DIR   = os.path.join(HERE, "results")

sys.path.insert(0, HERE)
from data       import build_db, load_groups, load_atoms_iter
from refs       import load_mu_metals
from benchmarks import (benchmark1, benchmark2, benchmark3,
                        benchmark4, benchmark5, print_summary)


# ── MACE calculators ───────────────────────────────────────────────────────
def get_calculator(model, device="cuda"):
    from mace.calculators import MACECalculator
    if model == "mace_mh1_omat":
        return MACECalculator(
            model_paths=f"{CKPT}/MACE/mace-mh-1.model",
            device=device, default_dtype="float32", head="omat_pbe")
    elif model == "mace_mh1_oc20":
        return MACECalculator(
            model_paths=f"{CKPT}/MACE/mace-mh-1.model",
            device=device, default_dtype="float32", head="oc20_usemppbe")
    elif model == "mace_omat0":
        return MACECalculator(
            model_paths=f"{CKPT}/MACE/mace-omat-0-medium.model",
            device=device, default_dtype="float32")
    else:
        raise ValueError(f"Unknown model: {model}  "
                         f"(choose: mace_mh1_omat | mace_mh1_oc20 | mace_omat0)")


# ── Inference ──────────────────────────────────────────────────────────────
def run_inference(calc, b123_only=False):
    """Run MACE on all (or 75) structures. Returns mlip dict + raw rows."""
    mlip = {}
    rows = []
    structures = list(load_atoms_iter(DB_PATH))
    total = len(structures)

    # Filter to Pd+SnO2 only if b123_only
    if b123_only:
        structures = [(m, cfg, c, at) for m, cfg, c, at in structures
                      if m in ("Pd", "SnO2")]
        print(f"  b123_only: {len(structures)}/{total} structures")

    n_ok = 0
    for i, (metal, cfg, c, atoms) in enumerate(structures):
        atoms.calc = calc
        t0 = time.time()
        try:
            e = atoms.get_potential_energy()
            status = "OK"
            n_ok += 1
        except Exception as ex:
            e = None
            status = f"ERR:{ex}"
        dt = time.time() - t0

        mlip[(metal, cfg, c)] = e
        rows.append(dict(metal=metal, config=cfg, calculation=c,
                         mlip_energy=e, status=status, elapsed=f"{dt:.1f}"))

        if (i + 1) % 50 == 0 or i == 0:
            tag  = f"{metal}/{cfg}/{c}"
            estr = f"{e:.4f}" if e is not None else "ERR"
            print(f"  [{i+1:4d}/{len(structures)}] {tag:<45} E={estr}  ({dt:.1f}s)")

    print(f"\n  Done: {n_ok}/{len(structures)} OK")
    return mlip, rows


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model",     default="mace_mh1_omat",
                        help="mace_mh1_omat | mace_mh1_oc20 | mace_omat0")
    parser.add_argument("--device",    default="cuda", help="cuda or cpu")
    parser.add_argument("--b123-only", action="store_true",
                        help="Only run B1-B3 (75 Pd+SnO2 structures, fast)")
    parser.add_argument("--build-db",  action="store_true",
                        help="Build dft_raw_data.db + index.json then exit")
    args = parser.parse_args()

    if args.build_db:
        build_db(out_db=DB_PATH, out_json=os.path.join(HERE, "index.json"))
        return

    if not os.path.exists(DB_PATH):
        print(f"ERROR: {DB_PATH} not found. Run: python evaluate.py --build-db")
        sys.exit(1)

    print(f"\n{'='*65}")
    print(f"Model : {args.model}")
    print(f"Device: {args.device}")
    print(f"DB    : {DB_PATH}")
    print(f"{'='*65}")

    # Load DFT groups
    print("\nLoading DFT groups...")
    groups = load_groups(DB_PATH)
    print(f"  {len(groups)} (metal, config) groups loaded")

    # Load μ_metal (optional; needed for B4)
    mu_extra = load_mu_metals(MU_CSV)
    if mu_extra:
        print(f"  μ_metal loaded: {len(mu_extra)} metals")
    else:
        print(f"  μ_metals.csv not found — B4 limited to Pd+SnO2+H+O+Sn")

    # Load MACE calculator
    print(f"\nLoading {args.model}...")
    t0   = time.time()
    calc = get_calculator(args.model, args.device)
    print(f"  ready in {time.time()-t0:.1f}s")

    # Run inference
    print(f"\nRunning inference...")
    mlip, raw_rows = run_inference(calc, b123_only=args.b123_only)

    # Save raw energies
    os.makedirs(OUT_DIR, exist_ok=True)
    raw_path = os.path.join(OUT_DIR, f"{args.model}_raw_energies.csv")
    with open(raw_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["metal","config","calculation",
                                          "mlip_energy","status","elapsed"])
        w.writeheader()
        w.writerows(raw_rows)
    print(f"  Raw energies: {raw_path}")

    # Run benchmarks
    print(f"\nRunning benchmarks...")
    b1 = benchmark1(groups, mlip)
    b2 = benchmark2(groups, mlip)
    b3 = benchmark3(groups, mlip)
    b4 = benchmark4(groups, mlip, mu_extra=mu_extra) if not args.b123_only else []
    b5 = benchmark5(groups, mlip)                    if not args.b123_only else []

    # Print summary
    print_summary(args.model, b1, b2, b3, b4, b5)

    # Save benchmark CSV
    all_rows = b1 + b2 + b3 + b4 + b5
    bench_path = os.path.join(OUT_DIR, f"{args.model}_benchmark.csv")
    all_keys   = set()
    for r in all_rows:
        all_keys.update(r.keys())
    fields = ["bench", "metal", "config"] + sorted(all_keys - {"bench", "metal", "config"})
    with open(bench_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)
    print(f"\n  Benchmark CSV: {bench_path}")


if __name__ == "__main__":
    main()

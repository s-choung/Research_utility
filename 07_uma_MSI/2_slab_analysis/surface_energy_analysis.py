#!/usr/bin/env python3
"""
Surface Energy Analysis for Metal Oxide Slabs
==============================================
Analyzes slab structures and calculates surface energies to identify
the most stable surfaces for each material.

Surface Energy Formula:
γ = (E_slab - N * E_bulk) / (2 * A)

where:
- γ = surface energy (eV/Å²)
- E_slab = total energy of the slab
- N = number of formula units in the slab
- E_bulk = energy per formula unit in bulk
- A = surface area
- Factor of 2 accounts for two surfaces (top and bottom)
"""

import os
import json
import numpy as np
from pathlib import Path
from ase.io import read
from collections import defaultdict


# Bulk reference energies (eV per formula unit)
# These should be calculated from fully relaxed bulk structures
# For now, using estimated values - MUST BE REPLACED with actual bulk calculations
BULK_ENERGIES = {
    'MgO': -6.59,      # per MgO formula unit
    'CaO': -7.18,      # per CaO formula unit
    'CeO2': -12.65,    # per CeO2 formula unit
    'TiO2': -9.87,     # per TiO2 formula unit (rutile)
    'SnO2': -7.21,     # per SnO2 formula unit
    'ZnO': -3.85,      # per ZnO formula unit
    'Al2O3': -20.54,   # per Al2O3 formula unit
    'ZrO2': -11.21,    # per ZrO2 formula unit
    'SiO2': -7.26,     # per SiO2 formula unit
}


class SlabAnalyzer:
    """Analyzer for slab surface energies"""

    def __init__(self, slab_dir, restarted_dir, output_dir, log_dir):
        self.slab_dir = Path(slab_dir)
        self.restarted_dir = Path(restarted_dir)
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        self.results = defaultdict(list)
        self.energy_from_logs = {}  # Store energies parsed from logs

        # Parse energies from log files
        self.parse_log_energies()

    def parse_log_energies(self):
        """Parse energies from evaluation log files"""
        import re

        print("\n📄 Parsing energies from log files...")

        for log_file in sorted(self.log_dir.glob("energy_evaluation_chunk*.log")):
            with open(log_file, 'r') as f:
                content = f.read()

            # Parse each material section
            # Pattern: Material Miller (x, y, z) (N terminations):
            material_pattern = r'(\w+(?:_\w+)?)\s+Miller\s+\((\d+),\s*(\d+),\s*(\d+)\)\s+\((\d+)\s+terminations?\):'

            for match in re.finditer(material_pattern, content):
                material = match.group(1)
                miller = (int(match.group(2)), int(match.group(3)), int(match.group(4)))
                n_terms = int(match.group(5))

                # Find the termination data after this match
                start_pos = match.end()
                # Find next material or end of file
                next_match = re.search(material_pattern, content[start_pos:])
                if next_match:
                    end_pos = start_pos + next_match.start()
                else:
                    end_pos = len(content)

                section = content[start_pos:end_pos]

                # Parse each termination
                term_matches = list(re.finditer(r'Termination (\d+)/\d+:', section))
                for i, term_match in enumerate(term_matches):
                    term_num = int(term_match.group(1))

                    # Get the section for this termination
                    term_start = term_match.end()
                    if i + 1 < len(term_matches):
                        term_end = term_matches[i + 1].start()
                    else:
                        term_end = len(section)

                    term_section = section[term_start:term_end]

                    # Extract final energy
                    energy_match = re.search(r'Final energy:\s+([+-]?\d+\.\d+)\s+eV', term_section)
                    if energy_match:
                        energy = float(energy_match.group(1))

                        # Create key for lookup
                        key = (material, miller, term_num - 1)  # 0-indexed termination
                        self.energy_from_logs[key] = energy

        print(f"  Parsed {len(self.energy_from_logs)} energies from logs")

    def get_formula_unit_count(self, atoms, material):
        """Calculate number of formula units in the slab"""
        formula_map = {
            'MgO': {'Mg': 1, 'O': 1},
            'CaO': {'Ca': 1, 'O': 1},
            'CeO2': {'Ce': 1, 'O': 2},
            'TiO2': {'Ti': 1, 'O': 2},
            'SnO2': {'Sn': 1, 'O': 2},
            'ZnO': {'Zn': 1, 'O': 1},
            'Al2O3': {'Al': 2, 'O': 3},
            'ZrO2': {'Zr': 1, 'O': 2},
            'SiO2': {'Si': 1, 'O': 2},
        }

        if material not in formula_map:
            raise ValueError(f"Unknown material: {material}")

        formula = formula_map[material]
        symbols = atoms.get_chemical_symbols()

        # Count atoms
        counts = {}
        for symbol in set(symbols):
            counts[symbol] = symbols.count(symbol)

        # Calculate number of formula units
        # Use the cation count divided by its formula coefficient
        cation = [k for k in formula.keys() if k != 'O'][0]
        n_formula_units = counts[cation] / formula[cation]

        return n_formula_units

    def calculate_surface_area(self, atoms):
        """Calculate surface area from cell vectors"""
        cell = atoms.get_cell()
        # Surface area is the area of the a-b plane
        a = cell[0]
        b = cell[1]
        # Area = |a × b|
        cross_product = np.cross(a, b)
        area = np.linalg.norm(cross_product)
        return area

    def calculate_surface_energy(self, atoms, material, miller, termination):
        """
        Calculate surface energy for a slab

        Returns:
            dict: Contains surface energy and related parameters
        """
        # Get energies - try trajectory first, then logs
        E_slab = None
        try:
            E_slab = atoms.get_potential_energy()
        except:
            # Try to get energy from parsed logs
            # Need to match material name in logs
            log_material = material.replace('TiO2_anatase', 'TiO2_anatase').replace('TiO2_rutile', 'TiO2_rutile')
            key = (log_material, miller, termination)
            if key in self.energy_from_logs:
                E_slab = self.energy_from_logs[key]

        if E_slab is None:
            return None

        E_bulk = BULK_ENERGIES.get(material)
        if E_bulk is None:
            print(f"Warning: No bulk energy for {material}")
            return None

        # Get structural parameters
        N = self.get_formula_unit_count(atoms, material)
        A = self.calculate_surface_area(atoms)

        # Calculate surface energy (eV/Å²)
        # Factor of 2 for two surfaces
        gamma = (E_slab - N * E_bulk) / (2 * A)

        return {
            'surface_energy': gamma,
            'slab_energy': E_slab,
            'n_formula_units': N,
            'surface_area': A,
            'n_atoms': len(atoms),
            'cell_volume': atoms.get_volume(),
        }

    def parse_filename(self, filename):
        """
        Parse slab filename to extract material, miller index, and termination

        Examples:
            CaO_111_4x4_relaxed.traj -> material=CaO, miller=(1,1,1)
            ZrO2_miller111_term2_restarted.traj -> material=ZrO2, miller=(1,1,1), term=2
        """
        stem = filename.stem  # Remove .traj extension

        # Handle restarted files
        if 'restarted' in stem:
            # Format: Material_millerXYZ_termN_restarted
            # Example: TiO2_rutile_miller101_term0_restarted
            parts = stem.replace('_restarted', '').split('_')

            # Handle materials with polymorph (e.g., TiO2_rutile)
            if len(parts) >= 4 and parts[1] in ['rutile', 'anatase']:
                material = f"{parts[0]}_{parts[1]}"
                miller_str = parts[2].replace('miller', '')
                term_str = parts[3].replace('term', '')
            else:
                material = parts[0]
                miller_str = parts[1].replace('miller', '')
                term_str = parts[2].replace('term', '')

            # Extract miller indices
            miller = tuple(int(d) for d in miller_str)

            # Extract termination number
            termination = int(term_str)

            return material, miller, termination, 'restarted'

        else:
            # Format: Material_XYZ_NxM_relaxed
            parts = stem.replace('_relaxed', '').split('_')

            # Handle special cases like TiO2_rutile, TiO2_anatase
            if parts[0] in ['TiO2'] and len(parts) > 2:
                material = f"{parts[0]}_{parts[1]}"
                miller_str = parts[2]
                supercell = parts[3] if len(parts) > 3 else None
            else:
                material = parts[0]
                miller_str = parts[1]
                supercell = parts[2] if len(parts) > 2 else None

            # Parse miller indices
            miller = tuple(int(d) for d in miller_str)

            return material, miller, 0, 'original'

    def analyze_slab(self, filepath):
        """Analyze a single slab file - handles multiple terminations"""
        try:
            # Read ALL frames (terminations) from trajectory file
            all_atoms = read(str(filepath), index=':')
            if not isinstance(all_atoms, list):
                all_atoms = [all_atoms]

            # Parse filename
            material, miller, termination, source = self.parse_filename(filepath)

            # For TiO2, keep rutile and anatase separate as different materials
            if 'rutile' in material.lower() or 'anatase' in material.lower():
                base_material = 'TiO2'
                polymorph = material.split('_')[1]
                analysis_material = material  # Keep TiO2_rutile or TiO2_anatase as separate material
            else:
                base_material = material
                polymorph = None
                analysis_material = material

            # Process each termination/frame
            for frame_idx, atoms in enumerate(all_atoms):
                # For files with multiple frames, frame_idx is the termination number
                current_term = termination if len(all_atoms) == 1 else frame_idx

                # Calculate surface energy
                result = self.calculate_surface_energy(atoms, base_material, miller, current_term)

                if result is None:
                    continue

                # Store results
                result_entry = {
                    'filename': filepath.name,
                    'material': material,
                    'base_material': base_material,
                    'polymorph': polymorph,
                    'miller_index': miller,
                    'termination': current_term,
                    'source': source,
                    **result
                }

                # Store under analysis_material (keeps rutile/anatase separate)
                self.results[analysis_material].append(result_entry)

                term_label = f" (term {current_term})" if len(all_atoms) > 1 else ""
                print(f"✓ {filepath.name}{term_label}: γ = {result['surface_energy']:.4f} eV/Å²")

        except Exception as e:
            print(f"Error analyzing {filepath.name}: {e}")

    def analyze_all_slabs(self):
        """Analyze all slab structures"""
        print("=" * 80)
        print("ANALYZING SLAB SURFACE ENERGIES")
        print("=" * 80)

        # Analyze original slabs
        print("\n📁 Analyzing original slabs...")
        for traj_file in sorted(self.slab_dir.glob("*_relaxed.traj")):
            self.analyze_slab(traj_file)

        # Analyze restarted slabs
        if self.restarted_dir.exists():
            print("\n📁 Analyzing restarted slabs...")
            for traj_file in sorted(self.restarted_dir.glob("*_restarted.traj")):
                self.analyze_slab(traj_file)

        print("\n" + "=" * 80)
        print(f"Total materials analyzed: {len(self.results)}")
        print("=" * 80)

    def find_best_surfaces(self):
        """Identify the most stable surface for each material

        For each Miller index with multiple terminations, selects the
        termination with minimum surface energy.
        """
        best_surfaces = {}

        for material, slabs in self.results.items():
            if not slabs:
                continue

            # Group by Miller index
            by_miller = defaultdict(list)
            for slab in slabs:
                miller_key = slab['miller_index']
                by_miller[miller_key].append(slab)

            # For each Miller index, select the best (minimum energy) termination
            best_per_miller = []
            for miller, miller_slabs in by_miller.items():
                # Sort terminations by surface energy
                sorted_terms = sorted(miller_slabs, key=lambda x: x['surface_energy'])
                best_term = sorted_terms[0]

                # Mark if multiple terminations were compared
                if len(sorted_terms) > 1:
                    best_term['n_terminations'] = len(sorted_terms)
                    best_term['other_terminations'] = sorted_terms[1:]

                best_per_miller.append(best_term)

            # Sort all Miller indices by surface energy
            sorted_slabs = sorted(best_per_miller, key=lambda x: x['surface_energy'])

            best_surfaces[material] = {
                'best': sorted_slabs[0],
                'all_surfaces': sorted_slabs
            }

        return best_surfaces

    def generate_report(self):
        """Generate comprehensive analysis report"""
        best_surfaces = self.find_best_surfaces()

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("SURFACE ENERGY ANALYSIS REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append("NOTE: Bulk reference energies are estimates.")
        report_lines.append("      For accurate results, calculate bulk energies with the same method.")
        report_lines.append("")

        # Summary table
        report_lines.append("\n" + "=" * 80)
        report_lines.append("BEST SURFACE FOR EACH MATERIAL")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"{'Material':<15} {'Miller':<10} {'Term':<6} {'γ (eV/Å²)':<12} {'File':<40}")
        report_lines.append("-" * 80)

        for material in sorted(best_surfaces.keys()):
            best = best_surfaces[material]['best']
            miller_str = f"({','.join(map(str, best['miller_index']))})"
            report_lines.append(
                f"{best['material']:<15} {miller_str:<10} {best['termination']:<6} "
                f"{best['surface_energy']:<12.4f} {best['filename']:<40}"
            )

        # Detailed analysis for each material
        report_lines.append("\n\n" + "=" * 80)
        report_lines.append("DETAILED SURFACE ENERGY COMPARISON")
        report_lines.append("=" * 80)

        for material in sorted(best_surfaces.keys()):
            report_lines.append(f"\n\n{material}")
            report_lines.append("-" * 80)
            report_lines.append(
                f"{'Miller':<12} {'Term':<6} {'γ (eV/Å²)':<12} {'Area (Ų)':<12} "
                f"{'N atoms':<10} {'Source':<12} {'File':<30}"
            )
            report_lines.append("-" * 80)

            for slab in best_surfaces[material]['all_surfaces']:
                miller_str = f"({','.join(map(str, slab['miller_index']))})"

                # Add note if multiple terminations were compared
                term_note = ""
                if slab.get('n_terminations', 1) > 1:
                    term_note = f" (best of {slab['n_terminations']})"

                report_lines.append(
                    f"{miller_str:<12} {slab['termination']:<6} "
                    f"{slab['surface_energy']:<12.4f} {slab['surface_area']:<12.2f} "
                    f"{slab['n_atoms']:<10} {slab['source']:<12} {slab['filename']:<30}{term_note}"
                )

            # Add recommendation
            best = best_surfaces[material]['all_surfaces'][0]
            report_lines.append("")
            report_lines.append(f"✓ RECOMMENDED: {best['filename']}")
            report_lines.append(f"  Surface energy: {best['surface_energy']:.4f} eV/Ų")
            report_lines.append(f"  Miller index: {best['miller_index']}")
            report_lines.append(f"  Termination: {best['termination']}")
            if best.get('n_terminations', 1) > 1:
                report_lines.append(f"  Note: Best of {best['n_terminations']} terminations")

        # Write report
        report_file = self.output_dir / "surface_energy_report.txt"
        with open(report_file, 'w') as f:
            f.write('\n'.join(report_lines))

        print(f"\n📄 Report saved to: {report_file}")

        # Also print to console
        print('\n'.join(report_lines))

    def save_json_results(self):
        """Save results as JSON for further analysis"""
        best_surfaces = self.find_best_surfaces()

        # Convert numpy types to Python types for JSON serialization
        def convert_types(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(item) for item in obj]
            else:
                return obj

        json_data = convert_types(best_surfaces)

        json_file = self.output_dir / "surface_energies.json"
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)

        print(f"📄 JSON data saved to: {json_file}")

    def create_best_slab_paths(self):
        """Create a file with paths to the best slab structures"""
        best_surfaces = self.find_best_surfaces()

        paths_file = self.output_dir / "best_slab_paths.txt"

        with open(paths_file, 'w') as f:
            f.write("# Best Surface Slab Structures\n")
            f.write("# Format: Material | Miller | Surface Energy | Path\n")
            f.write("#" + "=" * 78 + "\n\n")

            for material in sorted(best_surfaces.keys()):
                best = best_surfaces[material]['best']
                miller_str = f"({','.join(map(str, best['miller_index']))})"

                # Determine full path
                if best['source'] == 'restarted':
                    full_path = self.restarted_dir / best['filename']
                else:
                    full_path = self.slab_dir / best['filename']

                f.write(f"{material:<15} | {miller_str:<10} | "
                       f"{best['surface_energy']:>8.4f} eV/Ų | {full_path}\n")

        print(f"📄 Best slab paths saved to: {paths_file}")

        return paths_file


def main():
    """Main analysis workflow"""
    # Directory setup
    base_dir = Path("/DATA/user_scratch/jsh9967/5_uma_MSI")
    slab_dir = base_dir / "1_slab_gen" / "slabs"
    restarted_dir = base_dir / "1_slab_gen" / "slabs_restarted"
    log_dir = base_dir / "1_slab_gen"
    output_dir = base_dir / "2_slab_analysis"

    # Create analyzer
    analyzer = SlabAnalyzer(slab_dir, restarted_dir, output_dir, log_dir)

    # Run analysis
    analyzer.analyze_all_slabs()
    analyzer.generate_report()
    analyzer.save_json_results()
    paths_file = analyzer.create_best_slab_paths()

    print("\n" + "=" * 80)
    print("✓ ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nResults saved in: {output_dir}")
    print(f"  - surface_energy_report.txt  : Detailed analysis report")
    print(f"  - surface_energies.json      : Machine-readable results")
    print(f"  - best_slab_paths.txt        : Paths to recommended structures")
    print("\n⚠️  IMPORTANT: Update BULK_ENERGIES with actual calculated values")
    print("    for accurate surface energy predictions!")


if __name__ == "__main__":
    main()

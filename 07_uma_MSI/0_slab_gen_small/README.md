# Small Slab Generation (0_slab_gen_small)

**Purpose**: Generate smaller slab models for single GPU runs without chunking.

## Key Differences from 1_slab_gen

### Slab Dimensions

**Lateral Size (x, y axes):**
- **Target**: < 20 Å (2 nm) in both x and z directions
- **Original**: 19-25 Å (some exceeded 2nm limit)
- **Modified**: 14-20 Å (all under 2nm)

**Slab Thickness:**
- **Original**: 12-20 Å (4-6 atomic layers)
- **Modified**: 8-12 Å (3-5 atomic layers)

**Z-Cell Height:**
- **Original**: `slab_thickness + 17.0` Å
- **Modified**: `slab_thickness + 20.0` Å (as requested: zmax-zmin+20)

### Supercell Modifications

| Material | Original | Modified | Lateral Size |
|----------|----------|----------|--------------|
| MgO | 5×5 | 4×4 | 16.8 Å |
| CaO | 4×4 | 3×3 | 14.4 Å |
| CeO2 | 4×4 | 3×3 | 16.2 Å |
| TiO2_rutile | 5×4 | 4×3 | 18.4×13.8 Å |
| SnO2 | 5×4 | 4×3 | 19.0×14.2 Å |
| TiO2_anatase | 6×5 | 5×4 | 18.9×15.1 Å |
| ZnO | 6×6 | 5×5 | 16.3 Å |
| Al2O3 | 5×5 | 4×4 | 19.0 Å |
| ZrO2 | 4×4 | 3×3 | 15.6 Å |
| SiO2 | 5×5 | 4×4 | 19.7 Å |

### Advantages

1. **Single GPU**: No chunking needed - all models fit in single GPU memory
2. **Faster Testing**: Smaller models = faster calculations and relaxations
3. **Lower Memory**: Reduced memory footprint for development/testing
4. **Same Facets**: Still covers all 31 important facets (10 materials)

### Files

- `generate_slabs.py`: Modified slab generation script
- `run_small_slabgen.sh`: SLURM submission script (single GPU, 24h)
- `FACET_SELECTION.md`: Reference documentation (unchanged)

### Usage

```bash
# Submit job
sbatch run_small_slabgen.sh

# Or run directly
python generate_slabs.py
```

### Output

Generated files will be in `./slabs/` directory:
- Initial structures: `{material}_{miller}_{supercell}.traj`
- Relaxed structures: `{material}_{miller}_{supercell}_relaxed.traj`
- Summary: `slab_generation_summary.txt`
- Energy log: `energy_evaluation.log`

## Notes

- All slabs have < 2nm lateral dimensions as requested
- Z-cell follows requested formula: zmax-zmin+20
- Thinner slabs (3-5 layers) still capture essential surface chemistry
- Suitable for rapid prototyping and single GPU testing

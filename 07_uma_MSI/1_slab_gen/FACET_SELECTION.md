# Metal Oxide Facet Selection - Final Selection for GA

Best terminations selected based on UMA surface energy calculations.
These slabs will be enlarged to ≥50×50 Å for genetic algorithm with M200 clusters.

---

## Selected Slabs for GA (Lowest Surface Energy)

| Material     | Miller  | Term | γ (eV/Å²) | Source File                       | Current xy | Target xy |
|--------------|---------|------|-----------|-----------------------------------|------------|-----------|
| Al2O3        | (0,0,1) | 0    | 0.1130    | Al2O3_001_4x4_relaxed.traj        | 19×19 Å    | 57×57 Å   |
| CaO          | (1,0,0) | 0    | 0.0267    | CaO_100_5x5_relaxed.traj          | 17×17 Å    | 51×51 Å   |
| CeO2         | (1,1,1) | 1    | 0.0273    | CeO2_111_5x5_relaxed.traj         | 19×19 Å    | 57×57 Å   |
| MgO          | (1,0,0) | 0    | 0.0146    | MgO_100_5x5_relaxed.traj          | 15×15 Å    | 60×60 Å   |
| SiO2         | (1,0,1) | 3    | 0.1199    | SiO2_101_4x4_relaxed.traj         | 20×29 Å    | 60×58 Å   |
| SnO2         | (1,0,0) | 1    | 0.0421    | SnO2_100_5x4_relaxed.traj         | 24×13 Å    | 48×52 Å   |
| TiO2_anatase | (0,0,1) | 1    | -0.0303   | TiO2_anatase_001_5x4_relaxed.traj | 19×15 Å    | 57×60 Å   |
| TiO2_rutile  | (1,0,0) | 1    | 0.0204    | TiO2_rutile_100_5x4_relaxed.traj  | 23×12 Å    | 46×60 Å   |
| ZnO          | (1,0,0) | 0    | 0.0474    | ZnO_100_5x5_relaxed.traj          | 16×26 Å    | 64×52 Å   |
| ZrO2         | (1,0,0) | 1    | 0.1015    | ZrO2_100_4x4_relaxed.traj         | 21×21 Å    | 63×63 Å   |

---

## Supercell Scaling

| Material     | Base Supercell | Scale (nx×ny) | Final Supercell |
|--------------|----------------|---------------|-----------------|
| Al2O3        | 4×4            | 3×3           | 12×12           |
| CaO          | 5×5            | 3×3           | 15×15           |
| CeO2         | 5×5            | 3×3           | 15×15           |
| MgO          | 5×5            | 4×4           | 20×20           |
| SiO2         | 4×4            | 3×2           | 12×8            |
| SnO2         | 5×4            | 2×4           | 10×16           |
| TiO2_anatase | 5×4            | 3×4           | 15×16           |
| TiO2_rutile  | 5×4            | 2×5           | 10×20           |
| ZnO          | 5×5            | 4×2           | 20×10           |
| ZrO2         | 4×4            | 3×3           | 12×12           |

---

## Target Slab Dimensions

- **xy size**: ≥50 Å in both directions (for M200 with ~50% coverage)
- **z size**: ~10-15 Å slab thickness + 15 Å vacuum = 25-30 Å total
- **Atoms**: Minimize while maintaining surface stability

---

## References

1. Tasker, P.W. (1979) "The stability of ionic crystal surfaces" J. Phys. C: Solid State Phys. 12, 4977
2. Noguera, C. (1996) "Physics and Chemistry at Oxide Surfaces" Cambridge University Press
3. Diebold, U. (2003) "The surface science of titanium dioxide" Surf. Sci. Rep. 48, 53-229
4. Henrich, V.E. & Cox, P.A. (1994) "The Surface Science of Metal Oxides" Cambridge University Press

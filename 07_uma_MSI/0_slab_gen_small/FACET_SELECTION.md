# Metal Oxide Facet Selection

This document explains the selection of important low-index facets for each metal oxide system.

## Selection Criteria

1. **Experimental prevalence**: Facets commonly observed in experiments
2. **Thermodynamic stability**: Low surface energy facets
3. **Catalytic relevance**: Facets with important catalytic properties
4. **Literature consensus**: Well-studied surfaces in computational/experimental literature

---

## Rock Salt Structures (Cubic, Fm-3m)

### MgO - Magnesium Oxide
**Selected facets**: (100), (110), (111)

- **(100)**: Most stable, cleaves along Mg-O planes, most studied surface
- **(110)**: Moderate stability, mixed termination, important for reactivity
- **(111)**: Polar surface, requires reconstruction, high reactivity

**Reference**: MgO(100) is the textbook surface for oxide surface science

### CaO - Calcium Oxide
**Selected facets**: (100), (110), (111)

- Same reasoning as MgO (isostructural)
- (100) most stable and common
- (110) and (111) important for understanding structure-reactivity

---

## Fluorite Structure (Cubic, Fm-3m)

### CeO₂ - Cerium Oxide
**Selected facets**: (111), (110), (100)

- **(111)**: Most stable, oxygen-terminated, dominant in nanoparticles
- **(110)**: Second most stable, mixed termination, catalytically active
- **(100)**: Higher energy but catalytically important for redox reactions

**Reference**: CeO₂(111) is standard for oxygen storage/release studies

---

## Rutile Structure (Tetragonal, P4₂/mnm)

### TiO₂ - Titanium Oxide (Rutile)
**Selected facets**: (110), (100), (101), (001)

- **(110)**: Most stable, ~90% of natural rutile surfaces, bridging oxygen rows
- **(100)**: Second most stable, Ti-O-Ti ridge structure
- **(101)**: Important for photocatalysis
- **(001)**: High energy but highly reactive, important for catalysis

**Reference**: Rutile TiO₂(110) is the most studied oxide surface in surface science

### SnO₂ - Tin Oxide
**Selected facets**: (110), (101), (100)

- **(110)**: Most stable (isostructural with rutile TiO₂)
- **(101)**: Important for gas sensing applications
- **(100)**: Catalytically relevant for oxidation reactions

---

## Anatase Structure (Tetragonal, I4₁/amd)

### TiO₂ - Titanium Oxide (Anatase)
**Selected facets**: (101), (001), (100)

- **(101)**: Most stable, dominant in anatase nanoparticles (~94%)
- **(001)**: Highly reactive despite higher surface energy, excellent for photocatalysis
- **(100)**: Less common but stable, important for understanding facet effects

**Reference**: Anatase (101) vs (001) is key for photocatalytic studies

---

## Wurtzite Structure (Hexagonal, P6₃mc)

### ZnO - Zinc Oxide
**Selected facets**: (0001), (10-10), (11-20)

- **(0001)**: Zn-terminated polar surface (also O-terminated (000-1)), most common
- **(10-10)**: Non-polar, most stable, alternating Zn-O rows
- **(11-20)**: Non-polar, important for understanding surface chemistry

**Note**: Miller-Bravais notation (hkil) converted to 3-index for code:
- (10-10) → (100)
- (11-20) → (110)

**Reference**: ZnO polar vs non-polar surfaces crucial for piezoelectric/sensing

---

## Corundum Structure (Hexagonal, R-3c)

### Al₂O₃ - Aluminum Oxide (Alpha-alumina)
**Selected facets**: (0001), (10-10), (11-20)

- **(0001)**: Most stable, Al or O terminated, most studied
- **(10-10)**: R-plane, important for catalysis support
- **(11-20)**: A-plane, less common but catalytically active

**Conversion**: Same as ZnO
- (10-10) → (100)
- (11-20) → (110)

**Reference**: α-Al₂O₃(0001) is standard catalyst support surface

---

## Monoclinic Structure (P2₁/c)

### ZrO₂ - Zirconium Oxide
**Selected facets**: (111), (101), (100)

- **(111)**: Most stable for monoclinic phase
- **(101)**: Important cleavage plane, catalytically relevant
- **(100)**: Common in thin films

**Note**: Monoclinic ZrO₂ is complex; cubic/tetragonal phases may be more relevant at high temperature

---

## Trigonal Structure (Hexagonal, P3₂21)

### SiO₂ - Silicon Oxide (α-Quartz)
**Selected facets**: (0001), (10-10), (10-11)

- **(0001)**: Basal plane, most stable, controls crystal growth
- **(10-10)**: Prism plane, important for surface chemistry
- **(10-11)**: Common in natural quartz crystals

**Conversion**:
- (10-10) → (100)
- (10-11) → (101)

**Reference**: Quartz surfaces important for geochemistry and mineral processing

---

## Summary Statistics

| Material | Structure | # Facets | Primary Facet | Applications |
|----------|-----------|----------|---------------|--------------|
| MgO | Rock salt | 3 | (100) | Model system, catalysis support |
| CaO | Rock salt | 3 | (100) | CO₂ capture, catalysis |
| CeO₂ | Fluorite | 3 | (111) | Oxygen storage, catalysis |
| TiO₂ (rutile) | Rutile | 4 | (110) | Photocatalysis, surface science |
| TiO₂ (anatase) | Anatase | 3 | (101) | Photocatalysis |
| SnO₂ | Rutile | 3 | (110) | Gas sensing, catalysis |
| ZnO | Wurtzite | 3 | (10-10) | Piezoelectric, photocatalysis |
| Al₂O₃ | Corundum | 3 | (0001) | Catalyst support, corrosion |
| ZrO₂ | Monoclinic | 3 | (111) | Solid electrolyte, catalysis |
| SiO₂ | α-Quartz | 3 | (0001) | Electronics, geochemistry |

**Total**: 10 materials, 31 facets (down from 260+ for all Miller indices with max=1)

---

## Computational Benefits

**Before** (all Miller indices with max=1):
- 26 unique Miller indices per material
- 10 materials × 26 facets = 260+ slabs
- Multiple terminations per facet → ~400-600 total structures

**After** (important facets only):
- 3-4 facets per material (based on experimental relevance)
- 10 materials × 3.1 avg = 31 slabs
- Multiple terminations → ~60-100 total structures

**Reduction**: ~85% fewer calculations, focusing on scientifically relevant surfaces

---

## References

1. Tasker, P.W. (1979) "The stability of ionic crystal surfaces" J. Phys. C: Solid State Phys. 12, 4977
2. Noguera, C. (1996) "Physics and Chemistry at Oxide Surfaces" Cambridge University Press
3. Diebold, U. (2003) "The surface science of titanium dioxide" Surf. Sci. Rep. 48, 53-229
4. Henrich, V.E. & Cox, P.A. (1994) "The Surface Science of Metal Oxides" Cambridge University Press

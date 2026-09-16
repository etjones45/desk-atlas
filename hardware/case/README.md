# Desk Atlas — Orange Pi Zero 2W + Whisplay HAT case

Printable two-piece clamshell for **Ethan’s desk Atlas** stack:

- Bottom: Orange Pi Zero 2W  
- Top: PiSugar Whisplay HAT (1.69″ LCD, dual mics, speaker, RGB LED, click button)  
- Interconnect: 40-pin GPIO header  

This is a **custom Orange Pi** case (Mini-HDMI + 2× USB-C + microSD). It is **not** a Raspberry Pi Zero case (those use Micro-USB).

## Files

| File | Description |
|------|-------------|
| `atlas-whisplay-case.scad` | OpenSCAD source (edit dims here) |
| `atlas-whisplay-case-bottom.stl` | Bottom shell, print as-oriented |
| `atlas-whisplay-case-top.stl` | Top lid, already flipped (outer face on bed) |
| `atlas-whisplay-case.stl` | Both parts laid flat on one plate |
| `dims.json` | Numeric assumptions used for this revision |
| `README.md` | This file |

## Key dimensions

| Item | Value |
|------|-------|
| PCB footprint | 65 × 30 × 1.2 mm, corner R≈3 |
| Mounting holes | Ø≈2.8, centers (3.5,3.5), (61.5,3.5), (3.5,26.5), (61.5,26.5) |
| Outer case | **69.6 × 34.6 × 27.6 mm** (bottom 15.8 + lid walls into 1.2 lip) |
| Wall / floor / lid | 1.8 mm |
| Under-PCB standoffs | 2.0 mm |
| Internal cavity (standoff tops → lid lip) | **22 mm** |
| Screen window | 36 × 29 mm open aperture over 37 × 30 mm glass zone (PCB X=28…65) |

### Coordinate system

- **X=0** microSD short edge → **X=65** screen / RGB end  
- **Y=0** port long edge (Mini-HDMI, USB-C, USB-C) → **Y=30** GPIO / header edge  

## Print settings

- **Material:** PLA or PETG (PETG preferred if the desk is warm / near a lamp)  
- **Layer height:** 0.2 mm  
- **Nozzle:** 0.4 mm  
- **Infill:** 20–30% gyroid/grid  
- **Perimeters:** ≥3  
- **Supports:** none required (45°-friendly; lid prints outer-face down)  
- **Bed adhesion:** brim optional on lid (thin walls)  
- **Tolerance:** first print may need 0.2–0.5 mm port tweaks — cutouts are intentionally generous  

## Assembly

1. Drop Orange Pi Zero 2W into the bottom shell on the four standoffs (ports toward the long cutout wall; microSD toward the short slot).  
2. Seat Whisplay HAT on the 40-pin header (button side toward the USB-C / HDMI edge per PiSugar).  
3. Route the U.FL antenna pigtail through the small notch on the port wall (do not pinch).  
4. Fit the lid; screen glass should sit in the thin underside recess / show through the window.  
5. Fasten with **4× M2.5** screws **from the bottom** into the lid posts (self-tap in plastic, or set `use_heatset=true` in the SCAD for brass inserts).  
6. Optional: PH2.0 external speaker cable through the mid-wall opening between the boards.

Screen-end posts (under the glass zone) are **braced to the walls** so they stay attached even though the window removes top-slab material over those holes.

## Assumptions (read before printing)

1. **Stack height:** photos suggest ~16–20 mm total. Assumed header gap ≈11 mm + display raise ≈2.5 mm. Cavity is **22 mm** from standoff tops for clearance so the lid does not crush the glass.  
2. **Port centers:** Mini-HDMI ≈X=12.5, USB-C ≈X=40.5 / 53.5 on the Y=0 edge — approximated from Ethan’s photos and Zero-form-factor layout, **not** an official OPi mechanical drawing. Cutouts are oversized; measure your board and edit the SCAD if a plug binds.  
3. **Whisplay face holes:** mic / speaker / button / LED positions are approximate (photos + typical HAT face). PiSugar’s FDM chatbot case and Printables “Ground Zero” were used only as HAT-face references — **their RPi port cutouts were not used**.  
4. **No published OPi Zero 2W + Whisplay STL** was found; this design is original for Atlas.

## Regenerating STLs

```bash
sudo apt-get install -y openscad   # if needed
cd /workspace/desk-atlas/case
openscad -o atlas-whisplay-case-bottom.stl --export-format binstl -D 'part="bottom"' atlas-whisplay-case.scad
openscad -o atlas-whisplay-case-top.stl    --export-format binstl -D 'part="top"'    atlas-whisplay-case.scad
openscad -o atlas-whisplay-case.stl        --export-format binstl -D 'part="both"'   atlas-whisplay-case.scad
```

Preview assembly in OpenSCAD with `part="assembly"`.

## Revision

- 2026-09-14 — Initial OpenSCAD clamshell for Atlas (OPi Zero 2W ports + Whisplay face).


## Printable STLs

Binary `.stl` files are large for the GitHub text API. Source of truth for prints:

- Google Drive folder: [Desk Atlas case](https://drive.google.com/drive/folders/1oPI9PROn44mxh8NkbhoVGv0CYGK3a-l1)
- In-repo: OpenSCAD source + `dims.json` (edit dims here, regenerate STLs)

Files on Drive / local seed: `atlas-whisplay-case-bottom.stl`, `atlas-whisplay-case-top.stl`, `atlas-whisplay-case.stl` (combined plate).

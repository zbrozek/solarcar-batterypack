# XINGLIGHT XL-3528RGBW-HM 3D model

`XL-3528RGBW-HM.step` is a colored STEP AP214 file in millimeters. Five solids
represent the molded body and four contacts. The flat black bezel and opaque
white diffuser are colored faces of the body, so they add no thickness or
extra solids. This is the unlit appearance. Hidden dies, bond wires and
internal leadframe geometry are omitted.

## Altium placement

The model matches the origin and pin orientation of `LED_RGB_SMD3528-4P` in
`led_rgb_smd3528-4p.PcbLib`. Use X=0, Y=0, Z=0, rotations=0, scale=1.
The contact undersides are at **Z=0**, with the top at **Z=1.90 mm**.
Looking down from +Z with +Y upward, the marked pin-1 corner is lower right.

| Pin | Function | Existing pad center X | Existing pad center Y |
| --- | --- | ---: | ---: |
| 1 | Red cathode | +1.35 | -0.75 |
| 2 | Common anode | -1.35 | -0.75 |
| 3 | Green cathode | +1.35 | +0.75 |
| 4 | Blue cathode | -1.35 | +0.75 |

Pads are 0.90 x 0.90 mm. The four contacts fit entirely inside their matching
pad outlines. Their envelope centers are X=+/-1.39 mm and Y=+/-0.75 mm.

## Dimensions and sources

The repository's [XINGLIGHT datasheet](../../../../bms/documentation/xinglight/XL-3528RGBW-HM.pdf),
page 9, supplies the dimensions and pinout. Page 1 supplies the exterior
reference illustration. Public manufacturer references are the
[product page](https://www.xinglight.cn/index.php?c=show&id=3412) and its
[datasheet](https://www.xinglight.cn/uploadfile/202511/505682b0e27017b.pdf).

| Feature | Model dimension (mm) |
| --- | ---: |
| Overall X, including contacts | 3.50 |
| Body maximum X | 3.20 |
| Body Y | 2.80 |
| Overall height | 1.90 |
| Contact width along Y | 0.70 |
| Contact pitch along Y | 1.50 |
| Contact rise above seating plane | 1.10 |
| Underside contact envelope length along X | 0.72 |

The drawing also labels the underside contact gap as 2.0 mm. That differs
from 3.50 - 2 x 0.72 = 2.06 mm. The model preserves the stated overall width
and contact length, giving a 2.06 mm gap. The 0.06 mm difference is within
the drawing's general +/-0.25 mm tolerance. Nominal dimensions are modeled;
this is not a maximum-tolerance clearance envelope.

The following undimensioned details are approximate: 2.40 mm diffuser
diameter, 0.20 mm contact-foot thickness and housing standoff, 0.05 mm side
draft in X, 0.04 mm contact bend radius, and the roughly 0.6 mm polarity
corner ending 0.3 mm below the top. The circular diffuser is flush and opaque,
consistent with the mist-white material and reference illustration. Colors
are approximate. Fine underside molding relief is simplified.

The old footprint extrusion is a 3.2 x 3.2 mm square. This model follows the
datasheet's 3.2 x 2.8 mm molded body. The PcbLib has not been modified.

## Validation and regeneration

The exported file was re-imported into FreeCAD/Open CASCADE and checked for
five valid solids, preserved face colors, contact surfaces at Z=0, contact
alignment within the existing pads, and the 3.50 x 2.80 x 1.90 mm overall
envelope. No solids overlap in volume. Isometric, top and bottom renders of
the re-imported STEP were inspected. Import into Altium itself was not tested.

The generator is `../../scripts/build_xl3528_step.py`. From the repository root:

```powershell
& 'C:\Program Files\FreeCAD 1.0\bin\python.exe' altium_library\scripts\build_xl3528_step.py --render --qa-dir tmp\xl3528
```

FreeCAD 1.0 was used. VTK is required only for the optional preview render.
The generator needs no network access or additional asset files.

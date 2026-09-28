"""Generate a colored exterior-only XL-3528RGBW-HM STEP with FreeCAD.

Units: mm. Origin: package center in XY, contact undersides at Z=0.
Orientation matches LED_RGB_SMD3528-4P: pin 1 at +X,-Y in top view.
Tested with the Python bundled in FreeCAD 1.0 / Open CASCADE 7.8.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import FreeCAD as App
import Import
import Part

V = App.Vector
PART_NAME = "XL-3528RGBW-HM"
BODY_X, BODY_Y, HEIGHT = 3.20, 2.80, 1.90
LEAD_SPAN, LEAD_WIDTH, LEAD_FOOT = 3.50, 0.70, 0.72
LEAD_TOP, LEAD_THICKNESS = 1.10, 0.20
LENS_RADIUS = 1.20  # Undimensioned; approximate diameter from the outline drawing.
HOUSING_COLOR = (0.82, 0.83, 0.80)
BEZEL_COLOR = (0.055, 0.058, 0.060)
DIFFUSER_COLOR = (0.95, 0.95, 0.92)
CONTACT_COLOR = (0.68, 0.71, 0.74)
# Pin number, side sign, Y center, electrical function.
PINS = [(1, 1, -0.75, "Red cathode"), (2, -1, -0.75, "Common anode"),
        (3, 1, 0.75, "Green cathode"), (4, -1, 0.75, "Blue cathode")]


def polygon_face(points):
    return Part.Face(Part.makePolygon(points + [points[0]]))


def make_housing():
    # The molded housing has a slight draft in X, visible in the datasheet.
    # Its maximum body width is 3.2 at the lead shoulder. Draft and underside
    # standoff are visual approximations; the specified envelope is retained.
    y = -BODY_Y / 2
    points = [V(-1.55, y, LEAD_THICKNESS), V(1.55, y, LEAD_THICKNESS),
              V(1.60, y, LEAD_TOP), V(1.55, y, HEIGHT),
              V(-1.55, y, HEIGHT), V(-1.60, y, LEAD_TOP)]
    body = polygon_face(points).extrude(V(0, BODY_Y, 0))
    # Top-only polarity corner, beside pin 1. The drawing shows this corner
    # ending below the upper face; its 0.6 leg / 0.3 depth are approximate.
    notch = polygon_face([V(1.0, -1.4, 1.6), V(1.8, -1.4, 1.6),
                          V(1.8, -0.6, 1.6)]).extrude(V(0, 0, 0.5))
    body = body.cut(notch)
    lens = Part.Face(Part.Wire(Part.makeCircle(LENS_RADIUS, V(0, 0, HEIGHT))))
    split, _ = body.generalFuse([lens])
    assert len(split.Solids) == 1
    body = split.Solids[0]
    colors = []
    for face in body.Faces:
        if abs(face.BoundBox.ZMin - HEIGHT) < 1e-7:
            is_lens = face.common(lens).Area > 0.99 * face.Area
            colors.append(DIFFUSER_COLOR if is_lens else BEZEL_COLOR)
        else:
            colors.append(HOUSING_COLOR)
    assert colors.count(DIFFUSER_COLOR) == 1
    assert colors.count(BEZEL_COLOR) == 1
    return body, colors


def make_contact(side, center_y):
    # Underfolded PLCC terminal: visible upright side and horizontal foot.
    # 3.50 overall span and 0.72 foot imply a 2.06 underside gap. The drawing
    # also says 2.0; the small discrepancy is documented, not hidden.
    outer = LEAD_SPAN / 2
    inner = outer - LEAD_FOOT
    y = center_y - LEAD_WIDTH / 2
    r = 0.04  # Approximate exterior bend radius.
    a, b = V(inner, y, 0), V(outer - r, y, 0)
    mid = V(outer - r + r / math.sqrt(2), y, r - r / math.sqrt(2))
    c, d = V(outer, y, r), V(outer, y, LEAD_TOP)
    e, f = V(1.60, y, LEAD_TOP), V(1.55, y, LEAD_THICKNESS)
    g = V(inner, y, LEAD_THICKNESS)
    edges = [Part.makeLine(a, b), Part.Arc(b, mid, c).toShape(),
             Part.makeLine(c, d), Part.makeLine(d, e), Part.makeLine(e, f),
             Part.makeLine(f, g), Part.makeLine(g, a)]
    contact = Part.Face(Part.Wire(edges)).extrude(V(0, LEAD_WIDTH, 0))
    if side < 0:
        contact = contact.mirror(V(), V(1, 0, 0))
    # Bake cap placements to avoid OCCT face-color aliasing on extrusion caps.
    return contact.transformGeometry(App.Matrix())


def shape_bounds(shape):
    bounds = shape.BoundBox
    return {key: round(getattr(bounds, key), 7) for key in
            ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax",
             "XLength", "YLength", "ZLength")}


def render_preview(parts, path, view="iso"):
    """Render re-imported STEP geometry and colors with optional VTK."""
    import vtk

    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0.96, 0.97, 0.98)
    renderer.SetBackground2(0.82, 0.86, 0.91)
    renderer.GradientBackgroundOn()
    for shape, colors in parts:
        for face, color in zip(shape.Faces, colors):
            vertices, triangles = face.tessellate(0.007)
            points = vtk.vtkPoints()
            for vertex in vertices:
                points.InsertNextPoint(vertex.x, vertex.y, vertex.z)
            cells = vtk.vtkCellArray()
            for triangle in triangles:
                cells.InsertNextCell(3)
                for index in triangle:
                    cells.InsertCellPoint(index)
            data = vtk.vtkPolyData()
            data.SetPoints(points)
            data.SetPolys(cells)
            normals = vtk.vtkPolyDataNormals()
            normals.SetInputData(data)
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(normals.GetOutputPort())
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            prop = actor.GetProperty()
            prop.SetColor(*color[:3])
            prop.SetAmbient(0.28)
            prop.SetDiffuse(0.72)
            is_metal = abs(color[0] - CONTACT_COLOR[0]) < 1e-5
            prop.SetSpecular(0.45 if is_metal else 0.04)
            prop.SetSpecularPower(35)
            renderer.AddActor(actor)
    camera = renderer.GetActiveCamera()
    camera.SetFocalPoint(0, 0, HEIGHT / 2)
    if view == "iso":
        camera.SetPosition(6.8, -9.5, 8)
        camera.SetViewUp(0, 0, 1)
        scale = 2.55
    else:
        camera.SetPosition(0, 0, 15 if view == "top" else -15)
        camera.SetViewUp(0, 1, 0)
        scale = 1.9
    camera.ParallelProjectionOn()
    camera.SetParallelScale(scale)
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(1400, 1100)
    window.SetMultiSamples(8)
    window.AddRenderer(renderer)
    window.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.ReadFrontBufferOff()
    capture.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(path))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()
    window.Finalize()


def build(output_dir, qa_dir=None, render=False):
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = App.newDocument("XL_3528RGBW_HM")
    shape, colors = make_housing()
    body = doc.addObject("Part::Feature", "Housing")
    body.Label = PART_NAME + " housing and opaque diffuser"
    body.Shape = shape
    export_data = [(body, colors)]
    for number, side, y, function in PINS:
        obj = doc.addObject("Part::Feature", f"Pin{number}")
        obj.Label = f"Pin {number} - {function}"
        obj.Shape = make_contact(side, y)
        export_data.append((obj, [CONTACT_COLOR] * len(obj.Shape.Faces)))
    doc.recompute()
    for obj, _ in export_data:
        assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1
    for i, (obj, _) in enumerate(export_data):
        for other, _ in export_data[i + 1:]:
            assert obj.Shape.common(other.Shape).Volume < 1e-8
    path = output_dir / (PART_NAME + ".step")
    App.ParamGet("User parameter:BaseApp/Preferences/Mod/Part/STEP").SetString(
        "Scheme", "AP214IS")
    Import.export(export_data, str(path))
    check_doc = App.newDocument("STEP_validation")
    imported = Import.insert(str(path), check_doc.Name)
    assert imported and len(imported) == 5
    originals = {obj.Label: (obj.Shape, colors) for obj, colors in export_data}
    verified = []
    report = {"file": path.name, "units": "mm", "parts": []}
    for obj, colors in imported:
        expected_shape, expected_colors = originals[obj.Label]
        assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1
        assert abs(obj.Shape.Volume - expected_shape.Volume) < 1e-7
        assert len(colors) == len(obj.Shape.Faces)
        for color in colors:
            assert any(max(abs(color[k] - e[k]) for k in range(3)) < 1e-5
                       for e in expected_colors), (obj.Label, color)
        if obj.Label.startswith("Pin "):
            bounds = obj.Shape.BoundBox
            assert abs(bounds.ZMin) < 1e-7 and abs(bounds.ZMax - LEAD_TOP) < 1e-7
            pin = next(pin for pin in PINS if obj.Label.startswith(f"Pin {pin[0]} "))
            _, side, y, _ = pin
            pad_x = side * 1.35
            assert bounds.XMin >= pad_x - 0.45 - 1e-7
            assert bounds.XMax <= pad_x + 0.45 + 1e-7
            assert bounds.YMin >= y - 0.45 - 1e-7
            assert bounds.YMax <= y + 0.45 + 1e-7
            planar_bottom = [f for f in obj.Shape.Faces
                             if abs(f.BoundBox.ZMin) < 1e-7
                             and abs(f.BoundBox.ZMax) < 1e-7]
            assert len(planar_bottom) == 1 and planar_bottom[0].Area > 0.4
        report["parts"].append({"name": obj.Label, "valid": True,
                                 "solids": 1, "faces": len(obj.Shape.Faces),
                                 "bounds": shape_bounds(obj.Shape)})
        verified.append((obj.Shape, colors))
    whole = Part.makeCompound([shape for shape, _ in verified])
    b = whole.BoundBox
    for actual, expected in [(b.XLength, LEAD_SPAN), (b.YLength, BODY_Y),
                             (b.ZMin, 0), (b.ZMax, HEIGHT)]:
        assert abs(actual - expected) < 1e-6
    report.update({"overall_bounds": shape_bounds(whole),
                   "solid_count": len(whole.Solids), "step_bytes": path.stat().st_size,
                   "format": "STEP AP214 with face colors"})
    contents = path.read_text()
    assert "AUTOMOTIVE_DESIGN" in contents and "COLOUR_RGB" in contents
    assert "SI_UNIT(.MILLI.,.METRE.)" in contents
    if qa_dir:
        qa_dir.mkdir(parents=True, exist_ok=True)
        (qa_dir / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    if render:
        render_preview(verified, output_dir / (PART_NAME + ".png"))
        if qa_dir:
            render_preview(verified, qa_dir / "top.png", "top")
            render_preview(verified, qa_dir / "bottom.png", "bottom")
    print(json.dumps(report, indent=2))
    App.closeDocument(check_doc.Name)
    App.closeDocument(doc.Name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "footprints" / "common")
    parser.add_argument("--qa-dir", type=Path)
    parser.add_argument("--render", action="store_true", help="Requires VTK")
    args = parser.parse_args()
    build(args.output_dir, args.qa_dir, args.render)

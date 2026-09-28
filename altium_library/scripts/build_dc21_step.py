"""Build a lightweight, colored HALO DC21-V0505SLF STEP using FreeCAD.

Run with FreeCAD's bundled Python (FreeCAD 1.0 / Open CASCADE 7.8 tested).
The model uses millimeters and matches the existing HALO_DC21 footprint.
Only the six exterior solids are exported. The logo is a face imprint,
so it adds neither raised geometry nor extra solids.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import FreeCAD as App
import Import
import Part


BODY_LENGTH = 12.70
BODY_WIDTH = 11.20
TOP_Z = 7.25
BODY_BOTTOM = 0.30  # Inferred from the datasheet end view and lead thickness.
LEAD_SPAN = 11.40
LEAD_LENGTH = 1.00
LEAD_WIDTH = 0.60
LEAD_THICKNESS = 0.30
BODY_COLOR = (0.115, 0.120, 0.110)
INK_COLOR = (0.85, 0.85, 0.80)
METAL_COLOR = (0.72, 0.74, 0.76)
# Pin centers along the original datasheet horizontal axis, and row sign.
PINS = [(1, -3.81, -1), (2, -1.27, -1), (4, 3.81, -1),
        (5, 3.81, 1), (8, -3.81, 1)]
V = App.Vector


def align_to_footprint(shape):
    """Datasheet (u,v,z) -> footprint (v,-u,z); pin 1 upper left."""
    shape.rotate(V(), V(0, 0, 1), -90)
    return shape


def make_logo(font_file):
    letters = Part.makeWireString("HALO", str(font_file.parent) + "/",
                                  font_file.name, 2.15, 0)
    faces = [Part.makeFace(wires, "Part::FaceMakerBullseye") for wires in letters]
    # A small elliptical halo above the A, as in HALO's official family photo.
    a_bounds = faces[1].BoundBox
    center = V((a_bounds.XMin + a_bounds.XMax) / 2, a_bounds.YMax + 0.31, 0)
    outer = Part.Wire(Part.Ellipse(center, 0.66, 0.19).toShape())
    inner = Part.Wire(Part.Ellipse(center, 0.57, 0.11).toShape())
    faces.append(Part.makeFace([outer, inner], "Part::FaceMakerBullseye"))
    logo = Part.makeCompound(faces)
    bounds = logo.BoundBox
    logo.translate(V(-(bounds.XMin + bounds.XMax) / 2,
                     -(bounds.YMin + bounds.YMax) / 2 + 0.65, TOP_Z))
    return logo


def make_body(font_file):
    body = Part.makeBox(BODY_LENGTH, BODY_WIDTH, TOP_Z - BODY_BOTTOM,
                        V(-BODY_LENGTH / 2, -BODY_WIDTH / 2, BODY_BOTTOM))
    # These small cosmetic radii and the shallow pin-1 dimple are photo-based.
    body = body.makeFillet(0.08, body.Edges)
    dimple_depth, dimple_radius = 0.08, 0.32
    sphere_radius = (dimple_radius ** 2 + dimple_depth ** 2) / (2 * dimple_depth)
    dimple = Part.makeSphere(sphere_radius,
                            V(-4.8, -4.2, TOP_Z + sphere_radius - dimple_depth))
    body = body.cut(dimple)
    logo = make_logo(font_file)
    split, _ = body.generalFuse(logo.Faces)
    assert len(split.Solids) == 1
    body = split.Solids[0]
    colors = []
    for face in body.Faces:
        is_top = abs(face.BoundBox.ZMin - TOP_Z) < 1e-6
        ink_area = face.common(logo).Area if is_top else 0.0
        colors.append(INK_COLOR if ink_area > face.Area * 0.99 else BODY_COLOR)
    assert sum(color == INK_COLOR for color in colors) == 5
    return align_to_footprint(body), colors


def make_lead(u, row):
    # Cross-section of the negative-v contact. The inward lower corner is
    # rounded, matching the underfold in the drawing. The bend radius is
    # cosmetic; the specified span, foot length and thickness are retained.
    outer = -LEAD_SPAN / 2
    inner = outer + LEAD_LENGTH
    radius = 0.12
    x = u - LEAD_WIDTH / 2
    p0 = V(x, outer, 0)
    p1 = V(x, inner - radius, 0)
    pm = V(x, inner - radius + radius / math.sqrt(2),
           radius - radius / math.sqrt(2))
    p2 = V(x, inner, radius)
    p3 = V(x, inner, LEAD_THICKNESS)
    p4 = V(x, outer, LEAD_THICKNESS)
    edges = [Part.makeLine(p0, p1), Part.Arc(p1, pm, p2).toShape(),
             Part.makeLine(p2, p3), Part.makeLine(p3, p4), Part.makeLine(p4, p0)]
    lead = Part.Face(Part.Wire(edges)).extrude(V(LEAD_WIDTH, 0, 0))
    if row > 0:
        lead = lead.mirror(V(), V(0, 1, 0))
    # Bake face placements to give the two extrusion caps distinct geometry;
    # this also avoids an OCCT face-color alias when exporting translated caps.
    lead = lead.transformGeometry(App.Matrix())
    return align_to_footprint(lead)


def bounds_dict(shape):
    b = shape.BoundBox
    return {key: round(getattr(b, key), 7) for key in
            ("XMin", "XMax", "YMin", "YMax", "ZMin", "ZMax",
             "XLength", "YLength", "ZLength")}


def render_preview(colored_shapes, output_path, view="iso"):
    """Render the re-imported STEP faces, rather than a separate mockup."""
    import vtk

    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0.96, 0.97, 0.98)
    renderer.SetBackground2(0.84, 0.87, 0.91)
    renderer.GradientBackgroundOn()
    for shape, colors in colored_shapes:
        for face, color in zip(shape.Faces, colors):
            vertices, triangles = face.tessellate(0.035)
            points = vtk.vtkPoints()
            for v in vertices:
                points.InsertNextPoint(v.x, v.y, v.z)
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
            normals.SetFeatureAngle(45)
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(normals.GetOutputPort())
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            prop = actor.GetProperty()
            prop.SetColor(*color[:3])
            prop.SetAmbient(0.32)
            prop.SetDiffuse(0.68)
            prop.SetSpecular(0.28 if color[0] > 0.6 else 0.08)
            prop.SetSpecularPower(35)
            renderer.AddActor(actor)
    camera = renderer.GetActiveCamera()
    if view == "iso":
        camera.SetPosition(-25, -19, 24)
        camera.SetFocalPoint(0, 0, 3.5)
        camera.SetViewUp(0, 0, 1)
        scale = 10.3
    else:
        camera.SetPosition(0, 0, 40 if view == "top" else -40)
        camera.SetFocalPoint(0, 0, 3.5)
        camera.SetViewUp(0, 1, 0)
        scale = 8.2
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
    writer.SetFileName(str(output_path))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()
    window.Finalize()


def build(output_dir, font_file, qa_dir=None, render=False):
    output_dir.mkdir(parents=True, exist_ok=True)
    doc = App.newDocument("HALO_DC21_V0505SLF")
    shape, colors = make_body(font_file)
    body = doc.addObject("Part::Feature", "Housing")
    body.Label = "HALO DC21-V0505SLF housing"
    body.Shape = shape
    export_data = [(body, colors)]
    for number, u, row in PINS:
        obj = doc.addObject("Part::Feature", f"Pin{number}")
        obj.Label = f"Pin {number}"
        obj.Shape = make_lead(u, row)
        # Supply a color for every face; a single-item list only colors one
        # face with the headless exporter in FreeCAD 1.0.
        export_data.append((obj, [METAL_COLOR] * len(obj.Shape.Faces)))
    doc.recompute()
    for obj, _ in export_data:
        assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1
    path = output_dir / "DC21-V0505SLF.step"
    # AP214 carries face colors and millimeter units for Altium's STEP import.
    App.ParamGet("User parameter:BaseApp/Preferences/Mod/Part/STEP").SetString(
        "Scheme", "AP214IS")
    Import.export(export_data, str(path))

    # Read the actual deliverable back and check geometry and face colors.
    check_doc = App.newDocument("STEP_validation")
    imported = Import.insert(str(path), check_doc.Name)
    assert imported and len(imported) == 6
    original = {obj.Label: (obj.Shape, colors) for obj, colors in export_data}
    verified = []
    report = {"file": path.name, "units": "mm", "parts": []}
    for obj, actual_colors in imported:
        expected_shape, expected_colors = original[obj.Label]
        assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1
        assert abs(obj.Shape.Volume - expected_shape.Volume) < 1e-6
        assert len(actual_colors) == len(obj.Shape.Faces)
        for c in actual_colors:
            assert any(max(abs(c[i] - e[i]) for i in range(3)) < 1e-5
                       for e in expected_colors), (obj.Label, c)
        if obj.Label.startswith("Pin "):
            assert abs(obj.Shape.BoundBox.ZMin) < 1e-7
            assert abs(obj.Shape.BoundBox.ZMax - LEAD_THICKNESS) < 1e-7
        report["parts"].append({"name": obj.Label, "valid": True,
                                 "solids": 1, "faces": len(obj.Shape.Faces),
                                 "bounds": bounds_dict(obj.Shape)})
        verified.append((obj.Shape, actual_colors))
    combined = Part.makeCompound([s for s, _ in verified])
    bounds = combined.BoundBox
    for actual, expected in [(bounds.XLength, 11.40), (bounds.YLength, 12.70),
                             (bounds.ZMin, 0), (bounds.ZMax, 7.25)]:
        assert abs(actual - expected) < 1e-6
    report["overall_bounds"] = bounds_dict(combined)
    report["solid_count"] = len(combined.Solids)
    report["step_bytes"] = path.stat().st_size
    step_text = path.read_text()
    assert "AUTOMOTIVE_DESIGN" in step_text and "COLOUR_RGB" in step_text
    report["format"] = "STEP AP214 with per-face colors"
    if qa_dir:
        qa_dir.mkdir(parents=True, exist_ok=True)
        (qa_dir / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    if render:
        render_preview(verified, output_dir / "DC21-V0505SLF.png")
        if qa_dir:
            render_preview(verified, qa_dir / "top.png", "top")
            render_preview(verified, qa_dir / "bottom.png", "bottom")
    print(json.dumps(report, indent=2))
    App.closeDocument(check_doc.Name)
    App.closeDocument(doc.Name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "footprints" / "halo")
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/arial.ttf"))
    parser.add_argument("--qa-dir", type=Path)
    parser.add_argument("--render", action="store_true", help="Requires VTK")
    args = parser.parse_args()
    build(args.output_dir, args.font, args.qa_dir, args.render)

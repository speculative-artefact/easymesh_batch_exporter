"""Tests for export format functionality.

This module tests that the addon correctly exports meshes in all supported
formats: FBX, OBJ, glTF (GLB and JSON), USD, and STL.
"""

import bpy
import pytest
from conftest import (
    verify_file_exists,
    verify_exported_files,
    get_scene_props,
)


pytestmark = pytest.mark.export_format


def reimport_fbx_dimensions(fbx_path):
    """Import an FBX file and return the bounding-box dimensions of its mesh.

    Imported objects are removed afterwards so the scene is left untouched.

    Args:
        fbx_path (Path): Path to the FBX file to import.

    Returns:
        tuple[float, float, float]: The (x, y, z) dimensions of the first
        imported mesh object.
    """
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(fbx_path))
    new_objects = [obj for obj in bpy.data.objects if obj not in before]
    meshes = [obj for obj in new_objects if obj.type == "MESH"]
    assert meshes, f"No mesh object imported from {fbx_path}"
    dimensions = tuple(meshes[0].dimensions)

    # Clean up everything the importer created
    for obj in new_objects:
        bpy.data.objects.remove(obj, do_unlink=True)

    return dimensions


class TestFBXExport:
    """Tests for FBX export format."""

    def test_fbx_single_object_export(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Test exporting a single cube to FBX format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        # Select the cube
        create_cube.select_set(True)
        bpy.context.view_layer.objects.active = create_cube

        # Export
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export should complete successfully"

        # Verify FBX file was created
        expected_file = temp_export_dir / "TestCube.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            f"FBX file should exist at {expected_file}"
        )

    def test_fbx_multiple_objects_export(
        self, create_cube, create_sphere, temp_export_dir, reset_settings
    ):
        """Test exporting multiple objects to FBX format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        # Select both objects
        create_cube.select_set(True)
        create_sphere.select_set(True)

        # Export
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export should complete successfully"

        # Verify both FBX files were created
        assert verify_exported_files(
            temp_export_dir, ["TestCube", "TestSphere"], "fbx"
        ), "Both FBX files should be exported"

    def test_fbx_with_smoothing(self, create_sphere, temp_export_dir, reset_settings):
        """Test FBX export with different smoothing modes."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_naming_enabled = True
        props.mesh_export_naming_convention = "UNREAL"
        props.mesh_export_format = "FBX"
        create_sphere.select_set(True)

        for smoothing_mode in ["OFF", "FACE", "EDGE", "SMOOTH_GROUP"]:
            props.mesh_export_smoothing = smoothing_mode
            props.mesh_export_suffix = f"_{smoothing_mode.lower()}"

            result = bpy.ops.mesh.batch_export()
            assert result == {"FINISHED"}, (
                f"Export with smoothing={smoothing_mode} should succeed"
            )

            expected_file = temp_export_dir / f"TestSphere_{smoothing_mode.lower()}.fbx"
            assert verify_file_exists(expected_file, "fbx"), (
                f"FBX with smoothing={smoothing_mode} should be exported"
            )


class TestOBJExport:
    """Tests for OBJ export format."""

    def test_obj_single_object_export(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Test exporting a single cube to OBJ format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "OBJ"

        create_cube.select_set(True)
        bpy.context.view_layer.objects.active = create_cube

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export should complete successfully"

        expected_file = temp_export_dir / "TestCube.obj"
        assert verify_file_exists(expected_file, "obj"), (
            f"OBJ file should exist at {expected_file}"
        )

    def test_obj_with_material_file(
        self, create_sphere, temp_export_dir, reset_settings
    ):
        """Test that OBJ export creates accompanying MTL material file."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "OBJ"

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export should complete successfully"

        # OBJ export typically creates .mtl file alongside .obj
        obj_file = temp_export_dir / "TestSphere.obj"
        assert verify_file_exists(obj_file, "obj"), "OBJ file should exist"


class TestGLTFExport:
    """Tests for glTF export format (both GLB and JSON)."""

    def test_gltf_glb_export(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting to binary glTF (GLB) format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export should complete successfully"

        expected_file = temp_export_dir / "TestCube.glb"
        assert verify_file_exists(expected_file, "glb"), "GLB file should exist"

    def test_gltf_json_export(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting to JSON glTF format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLTF_SEPARATE"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export should complete successfully"

        expected_file = temp_export_dir / "TestCube.gltf"
        assert verify_file_exists(expected_file, "gltf"), "GLTF file should exist"

    def test_gltf_draco_compression(
        self, create_sphere, temp_export_dir, reset_settings
    ):
        """Test glTF export with Draco compression enabled."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_use_draco_compression = True

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with Draco should complete successfully"

        expected_file = temp_export_dir / "TestSphere.glb"
        assert verify_file_exists(expected_file, "glb"), "GLB with Draco should exist"

    def test_gltf_material_export_modes(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Test different glTF material export modes."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_naming_enabled = True
        props.mesh_export_naming_convention = "UNREAL"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        create_cube.select_set(True)

        for material_mode in ["EXPORT", "PLACEHOLDER", "NONE"]:
            props.mesh_export_gltf_materials = material_mode
            props.mesh_export_suffix = f"_{material_mode.lower()}"

            result = bpy.ops.mesh.batch_export()
            assert result == {"FINISHED"}, (
                f"Export with materials={material_mode} should succeed"
            )

            expected_file = temp_export_dir / f"TestCube_{material_mode.lower()}.glb"
            assert verify_file_exists(expected_file, "glb"), (
                f"GLB with materials={material_mode} should exist"
            )


class TestUSDExport:
    """Tests for USD export format."""

    def test_usd_single_object_export(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Test exporting a single cube to USD format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "USD"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "USD export should complete successfully"

        expected_file = temp_export_dir / "TestCube.usd"
        assert verify_file_exists(expected_file, "usd"), "USD file should exist"

    def test_usd_multiple_objects_export(
        self, create_cube, create_sphere, temp_export_dir, reset_settings
    ):
        """Test exporting multiple objects to USD format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "USD"

        create_cube.select_set(True)
        create_sphere.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "USD export should complete successfully"

        assert verify_exported_files(
            temp_export_dir, ["TestCube", "TestSphere"], "usd"
        ), "Both USD files should be exported"


class TestSTLExport:
    """Tests for STL export format."""

    def test_stl_single_object_export(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Test exporting a single cube to STL format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "STL"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "STL export should complete successfully"

        expected_file = temp_export_dir / "TestCube.stl"
        assert verify_file_exists(expected_file, "stl"), "STL file should exist"

    def test_stl_triangulation(self, create_cube, temp_export_dir, reset_settings):
        """Test that STL export properly triangulates meshes.

        STL format requires triangulated meshes. This test verifies
        triangulation is applied during export.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "STL"
        props.mesh_export_tri = True  # Ensure triangulation is enabled

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "STL export with triangulation should succeed"

        expected_file = temp_export_dir / "TestCube.stl"
        assert verify_file_exists(expected_file, "stl"), "Triangulated STL should exist"


class TestCoordinateSystem:
    """Tests for coordinate system and axis configuration."""

    def test_different_up_axes(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting with different up axis configurations."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_naming_enabled = True
        props.mesh_export_naming_convention = "UNREAL"
        props.mesh_export_format = "FBX"
        create_cube.select_set(True)

        for up_axis in ["X", "Y", "Z", "-X", "-Y", "-Z"]:
            props.mesh_export_coord_up = up_axis
            props.mesh_export_suffix = f"_up{up_axis.replace('-', 'neg')}"

            result = bpy.ops.mesh.batch_export()
            assert result == {"FINISHED"}, f"Export with up={up_axis} should succeed"

            suffix = up_axis.replace("-", "neg")
            expected_file = temp_export_dir / f"TestCube_up{suffix}.fbx"
            assert verify_file_exists(expected_file, "fbx"), (
                f"Export with up={up_axis} should create file"
            )

    def test_different_forward_axes(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting with different forward axis configurations."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_naming_enabled = True
        props.mesh_export_naming_convention = "UNREAL"
        props.mesh_export_format = "FBX"
        create_cube.select_set(True)

        for forward_axis in ["X", "Y", "Z", "-X", "-Y", "-Z"]:
            props.mesh_export_coord_forward = forward_axis
            props.mesh_export_suffix = f"_fwd{forward_axis.replace('-', 'neg')}"

            result = bpy.ops.mesh.batch_export()
            assert result == {"FINISHED"}, (
                f"Export with forward={forward_axis} should succeed"
            )

            suffix = forward_axis.replace("-", "neg")
            expected_file = temp_export_dir / f"TestCube_fwd{suffix}.fbx"
            assert verify_file_exists(expected_file, "fbx"), (
                f"Export with forward={forward_axis} should create file"
            )


class TestUnitsAndScale:
    """Tests for units and scale settings."""

    def test_meters_export(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting with metres as the unit."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_units = "METERS"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with metres should succeed"

    def test_centimeters_export(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting with centimetres as the unit."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_units = "CENTIMETERS"

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with centimetres should succeed"

    def test_custom_scale_factor(self, create_cube, temp_export_dir, reset_settings):
        """Test exporting with custom scale factors."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_naming_enabled = True
        props.mesh_export_naming_convention = "UNREAL"
        props.mesh_export_format = "FBX"
        create_cube.select_set(True)

        for scale in [0.5, 1.0, 2.0, 10.0]:
            props.mesh_export_scale = scale
            props.mesh_export_suffix = f"_scale{int(scale * 10)}"

            result = bpy.ops.mesh.batch_export()
            assert result == {"FINISHED"}, f"Export with scale={scale} should succeed"

            expected_file = temp_export_dir / f"TestCube_scale{int(scale * 10)}.fbx"
            assert verify_file_exists(expected_file, "fbx"), (
                f"Export with scale={scale} should create file"
            )

    def test_centimeters_geometry_is_100x_meters(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """Centimetre exports should bake 100x the geometry of metre exports.

        Regression test for issue #9: scale must be baked into the FBX geometry
        (not just the file's UnitScaleFactor header, which Unreal ignores).
        Comparing two exports re-imported with identical settings isolates the
        baked-geometry difference from any importer-side unit handling.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_naming_enabled = True
        props.mesh_export_naming_convention = "UNREAL"
        props.mesh_export_format = "FBX"
        props.mesh_export_scale = 1.0

        props.mesh_export_units = "METERS"
        props.mesh_export_suffix = "_m"
        create_cube.select_set(True)
        bpy.context.view_layer.objects.active = create_cube
        assert bpy.ops.mesh.batch_export() == {"FINISHED"}

        props.mesh_export_units = "CENTIMETERS"
        props.mesh_export_suffix = "_cm"
        create_cube.select_set(True)
        bpy.context.view_layer.objects.active = create_cube
        assert bpy.ops.mesh.batch_export() == {"FINISHED"}

        m_dims = reimport_fbx_dimensions(temp_export_dir / "TestCube_m.fbx")
        cm_dims = reimport_fbx_dimensions(temp_export_dir / "TestCube_cm.fbx")

        for axis, (m_val, cm_val) in enumerate(zip(m_dims, cm_dims)):
            assert m_val > 0, f"Metre dimension on axis {axis} should be non-zero"
            assert cm_val == pytest.approx(m_val * 100.0, rel=1e-3), (
                f"Centimetre geometry on axis {axis} should be 100x metres "
                f"(got {cm_val} vs {m_val})"
            )

    def test_scale_factor_bakes_into_geometry(
        self, create_cube, temp_export_dir, reset_settings
    ):
        """A 2x scale factor should produce 2x the re-imported dimensions."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_naming_enabled = True
        props.mesh_export_naming_convention = "UNREAL"
        props.mesh_export_format = "FBX"
        props.mesh_export_units = "METERS"

        props.mesh_export_scale = 1.0
        props.mesh_export_suffix = "_s1"
        create_cube.select_set(True)
        bpy.context.view_layer.objects.active = create_cube
        assert bpy.ops.mesh.batch_export() == {"FINISHED"}

        props.mesh_export_scale = 2.0
        props.mesh_export_suffix = "_s2"
        create_cube.select_set(True)
        bpy.context.view_layer.objects.active = create_cube
        assert bpy.ops.mesh.batch_export() == {"FINISHED"}

        s1_dims = reimport_fbx_dimensions(temp_export_dir / "TestCube_s1.fbx")
        s2_dims = reimport_fbx_dimensions(temp_export_dir / "TestCube_s2.fbx")

        for axis, (s1_val, s2_val) in enumerate(zip(s1_dims, s2_dims)):
            assert s1_val > 0, f"Scale-1 dimension on axis {axis} should be non-zero"
            assert s2_val == pytest.approx(s1_val * 2.0, rel=1e-3), (
                f"Scale 2.0 geometry on axis {axis} should be 2x scale 1.0 "
                f"(got {s2_val} vs {s1_val})"
            )

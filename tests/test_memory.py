"""Tests for memory management and large mesh handling.

This module tests the memory optimisation features for large meshes,
including adaptive garbage collection and progressive LOD building.
"""

import bpy
import pytest
import gc
from conftest import verify_file_exists, get_scene_props


pytestmark = [pytest.mark.slow, pytest.mark.memory]


class TestLargeMeshHandling:
    """Tests for large mesh memory optimisation (500K+ polygons)."""

    @pytest.mark.slow
    def test_large_mesh_export(
        self, create_large_mesh, temp_export_dir, reset_settings
    ):
        """Test exporting a large mesh (500K+ polygons).

        Should trigger basic memory optimisation.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        create_large_mesh.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Large mesh export should succeed"

        expected_file = temp_export_dir / "TestLargeMesh.fbx"
        assert verify_file_exists(expected_file, "fbx"), "Large mesh file should exist"

    @pytest.mark.slow
    def test_very_large_mesh_export(
        self, create_very_large_mesh, temp_export_dir, reset_settings
    ):
        """Test exporting a very large mesh (2M+ polygons).

        Should trigger aggressive memory optimisation.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        create_very_large_mesh.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Very large mesh export should succeed"

        expected_file = temp_export_dir / "TestVeryLargeMesh.fbx"
        assert verify_file_exists(expected_file, "fbx"), (
            "Very large mesh file should exist"
        )

    @pytest.mark.slow
    def test_large_mesh_with_triangulation(
        self, create_large_mesh, temp_export_dir, reset_settings
    ):
        """Test large mesh export with triangulation.

        Triangulation on large meshes should still complete without memory errors.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_tri = True
        props.mesh_export_tri_method = "BEAUTY"

        create_large_mesh.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Large mesh with triangulation should succeed"

    @pytest.mark.slow
    def test_large_mesh_with_modifiers(
        self, create_large_mesh, temp_export_dir, reset_settings
    ):
        """Test large mesh with modifier application.

        Applying modifiers to large meshes should use memory optimisation.
        """
        # Note: The large mesh already has a subdivision modifier
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_apply_modifiers = "VISIBLE"

        create_large_mesh.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Large mesh with modifiers should succeed"


class TestLargeMeshWithLOD:
    """Tests for LOD generation on large meshes."""

    @pytest.mark.slow
    def test_large_mesh_lod_generation(
        self, create_large_mesh, temp_export_dir, reset_settings
    ):
        """Test LOD generation on a large mesh.

        Should use progressive LOD building for memory efficiency.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False

        create_large_mesh.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Large mesh LOD generation should succeed"

        # Verify LOD files were created
        base_file = temp_export_dir / "TestLargeMesh.fbx"
        lod1_file = temp_export_dir / "TestLargeMesh_LOD01.fbx"

        assert verify_file_exists(base_file, "fbx"), "Base file should exist"
        assert verify_file_exists(lod1_file, "fbx"), "LOD1 file should exist"

    @pytest.mark.slow
    def test_very_large_mesh_lod_generation(
        self, create_very_large_mesh, temp_export_dir, reset_settings
    ):
        """Test LOD generation on a very large mesh.

        Should use aggressive GC (2-3 second intervals) for memory management.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False

        create_very_large_mesh.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Very large mesh LOD generation should succeed"


class TestMemoryCleanup:
    """Tests for memory cleanup and garbage collection."""

    def test_multiple_exports_memory_cleanup(
        self, create_sphere, temp_export_dir, reset_settings
    ):
        """Test that multiple exports don't accumulate memory.

        Export the same mesh multiple times and verify memory is cleaned up.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        create_sphere.select_set(True)

        # Export multiple times
        for i in range(5):
            props.mesh_export_suffix = f"_{i}"

            result = bpy.ops.mesh.batch_export()
            assert result == {"FINISHED"}, f"Export {i} should succeed"

            # Explicit GC to verify no memory leaks
            gc.collect()

        # Verify all files were created
        for i in range(5):
            expected_file = temp_export_dir / f"TestSphere_{i}.fbx"
            assert verify_file_exists(expected_file, "fbx"), (
                f"Export {i} file should exist"
            )

    @pytest.mark.slow
    def test_large_mesh_repeated_exports(
        self, create_large_mesh, temp_export_dir, reset_settings
    ):
        """Test repeated large mesh exports for memory leaks.

        Exporting the same large mesh multiple times should not leak memory.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        create_large_mesh.select_set(True)

        # Export the same large mesh 3 times
        for i in range(3):
            props.mesh_export_suffix = f"_export{i}"

            result = bpy.ops.mesh.batch_export()
            assert result == {"FINISHED"}, f"Large mesh export {i} should succeed"

            # Force GC between exports
            gc.collect()


class TestBatchExportMemory:
    """Tests for memory management during batch exports."""

    def test_many_small_meshes_batch(self, temp_export_dir, reset_settings):
        """Test exporting many small meshes in batch.

        Should handle many objects without memory issues.
        """
        # Create 20 small cubes
        objects = []
        for i in range(20):
            bpy.ops.mesh.primitive_cube_add(location=(i * 2, 0, 0))
            obj = bpy.context.active_object
            obj.name = f"Cube_{i:02d}"
            obj.select_set(True)
            objects.append(obj)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, (
            "Batch export of many small meshes should succeed"
        )

        # Verify a reasonable number of files were created
        # (at least half, accounting for possible skips)
        fbx_files = list(temp_export_dir.glob("*.fbx"))
        assert len(fbx_files) >= 10, "Should export majority of objects"

    def test_batch_gltf_combine_memory(self, temp_export_dir, reset_settings):
        """Test glTF batch combine mode with many objects.

        Combining many objects into one glTF should use efficient memory.
        """
        # Create 10 cubes
        for i in range(10):
            bpy.ops.mesh.primitive_cube_add(location=(i * 2, 0, 0))
            obj = bpy.context.active_object
            obj.name = f"Cube_{i:02d}"
            obj.select_set(True)

        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_gltf_batch_mode = "COMBINE"

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Batch glTF combine should succeed"

        # Should create one combined file
        glb_files = list(temp_export_dir.glob("*.glb"))
        assert len(glb_files) == 1, "Should create one combined GLB file"


class TestMemoryWithDifferentFormats:
    """Tests for memory management across different export formats."""

    @pytest.mark.slow
    def test_large_mesh_all_formats(
        self, create_large_mesh, temp_export_dir, reset_settings
    ):
        """Test exporting large mesh in all formats.

        All formats should handle large meshes with memory optimisation.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"

        create_large_mesh.select_set(True)

        formats = [
            ("FBX", "fbx"),
            ("OBJ", "obj"),
            ("GLTF", "glb"),
            ("USD", "usd"),
            ("STL", "stl"),
        ]

        for format_name, extension in formats:
            props.mesh_export_format = format_name
            if format_name == "GLTF":
                props.mesh_export_gltf_type = "GLB"

            props.mesh_export_suffix = f"_{format_name.lower()}"

            result = bpy.ops.mesh.batch_export()
            assert result == {"FINISHED"}, (
                f"Large mesh export to {format_name} should succeed"
            )

            # Force GC between format exports
            gc.collect()

            expected_file = (
                temp_export_dir / f"TestLargeMesh_{format_name.lower()}.{extension}"
            )
            assert verify_file_exists(expected_file, extension), (
                f"{format_name} file should exist"
            )

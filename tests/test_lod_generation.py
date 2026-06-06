"""Tests for LOD (Level of Detail) generation.

This module tests LOD generation, LOD ratios, LOD hierarchies,
and texture resizing for LOD levels.
"""

import bpy
import pytest
from conftest import (
    verify_file_exists,
    count_exported_files,
    get_scene_props,
)


pytestmark = pytest.mark.slow  # LOD tests can be slower


class TestBasicLODGeneration:
    """Tests for basic LOD generation functionality."""

    def test_lod_generation_enabled(
        self, create_sphere, temp_export_dir, reset_settings
    ):
        """Test that LOD generation creates additional LOD files."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2  # Generate LOD1 and LOD2
        props.mesh_export_lod_hierarchy = False  # Individual files

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "LOD generation should succeed"

        # Should have: TestSphere.fbx, TestSphere_LOD01.fbx, TestSphere_LOD02.fbx
        base_file = temp_export_dir / "TestSphere.fbx"
        lod1_file = temp_export_dir / "TestSphere_LOD01.fbx"
        lod2_file = temp_export_dir / "TestSphere_LOD02.fbx"

        assert verify_file_exists(base_file, "fbx"), "Base LOD file should exist"
        assert verify_file_exists(lod1_file, "fbx"), "LOD1 file should exist"
        assert verify_file_exists(lod2_file, "fbx"), "LOD2 file should exist"

    def test_lod_generation_disabled(
        self, create_sphere, temp_export_dir, reset_settings
    ):
        """Test that disabling LOD only exports base mesh."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = False

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export without LOD should succeed"

        # Should only have TestSphere.fbx
        fbx_count = count_exported_files(temp_export_dir, "fbx")
        assert fbx_count == 1, "Should only export one file without LOD"

    def test_lod_count_variation(self, create_sphere, temp_export_dir, reset_settings):
        """Test generating different numbers of LOD levels."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_hierarchy = False

        for lod_count in [1, 2, 3, 4]:
            # Clear previous exports
            for file in temp_export_dir.glob("*.fbx"):
                file.unlink()

            props.mesh_export_lod_count = lod_count

            create_sphere.select_set(True)
            result = bpy.ops.mesh.batch_export()
            assert result == {"FINISHED"}, (
                f"Export with {lod_count} LODs should succeed"
            )

            # Should have 1 base + lod_count additional LOD files
            fbx_count = count_exported_files(temp_export_dir, "fbx")
            expected_count = 1 + lod_count
            assert fbx_count == expected_count, (
                f"Should have {expected_count} files (1 base + {lod_count} LODs)"
            )


class TestLODRatios:
    """Tests for LOD ratio configuration."""

    def test_custom_lod_ratios(self, create_sphere, temp_export_dir, reset_settings):
        """Test setting custom LOD decimation ratios."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 3
        props.mesh_export_lod_hierarchy = False

        # Set custom ratios
        props.mesh_export_lod_ratio_01 = 0.8  # 80% of original
        props.mesh_export_lod_ratio_02 = 0.5  # 50% of original
        props.mesh_export_lod_ratio_03 = 0.2  # 20% of original

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with custom LOD ratios should succeed"

        # Verify all LOD files were created
        base_file = temp_export_dir / "TestSphere.fbx"
        lod1_file = temp_export_dir / "TestSphere_LOD01.fbx"
        lod2_file = temp_export_dir / "TestSphere_LOD02.fbx"
        lod3_file = temp_export_dir / "TestSphere_LOD03.fbx"

        assert verify_file_exists(base_file, "fbx"), "Base file should exist"
        assert verify_file_exists(lod1_file, "fbx"), "LOD1 file should exist"
        assert verify_file_exists(lod2_file, "fbx"), "LOD2 file should exist"
        assert verify_file_exists(lod3_file, "fbx"), "LOD3 file should exist"

    def test_extreme_lod_ratios(self, create_cube, temp_export_dir, reset_settings):
        """Test LOD generation with very low ratio (high decimation)."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 1
        props.mesh_export_lod_hierarchy = False

        # Very aggressive decimation
        props.mesh_export_lod_ratio_01 = 0.1  # Only 10% of original

        create_cube.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "Export with extreme LOD ratio should succeed"


class TestLODHierarchy:
    """Tests for LOD hierarchy export (game engine workflow)."""

    def test_lod_hierarchy_export(self, create_sphere, temp_export_dir, reset_settings):
        """Test exporting LODs as a hierarchy in a single FBX file."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = True  # Export as hierarchy

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "LOD hierarchy export should succeed"

        # Should create a single _LODGroup.fbx file
        hierarchy_file = temp_export_dir / "TestSphere_LODGroup.fbx"
        assert verify_file_exists(hierarchy_file, "fbx"), (
            "LOD hierarchy file should exist"
        )

        # Should NOT create individual LOD files
        lod1_file = temp_export_dir / "TestSphere_LOD01.fbx"
        assert not lod1_file.exists(), (
            "Individual LOD1 file should not exist in hierarchy mode"
        )

    def test_lod_hierarchy_multiple_objects(
        self, create_cube, create_sphere, temp_export_dir, reset_settings
    ):
        """Test LOD hierarchy export with multiple objects.

        Each object should get its own LOD hierarchy file.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = True

        create_cube.select_set(True)
        create_sphere.select_set(True)

        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, (
            "Multiple object LOD hierarchy export should succeed"
        )

        # Should create two _LODGroup.fbx files
        cube_hierarchy = temp_export_dir / "TestCube_LODGroup.fbx"
        sphere_hierarchy = temp_export_dir / "TestSphere_LODGroup.fbx"

        assert verify_file_exists(cube_hierarchy, "fbx"), (
            "Cube LOD hierarchy should exist"
        )
        assert verify_file_exists(sphere_hierarchy, "fbx"), (
            "Sphere LOD hierarchy should exist"
        )

    def test_lod_hierarchy_writes_lodgroup_node(
        self, create_sphere, temp_export_dir, reset_settings
    ):
        """The exported FBX must contain an FBX LodGroup node (issue #12).

        Unreal only imports the LODs as a single Static Mesh when the parent
        empty is written as a ``LodGroup`` node, which Blender does only when
        the empty carries ``fbx_type = "LodGroup"``. Verify by (a) scanning the
        binary FBX for the LodGroup marker and (b) re-importing and checking the
        round-tripped empty/hierarchy.
        """
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2  # LOD0 + LOD1 + LOD2 = 3 meshes
        props.mesh_export_lod_hierarchy = True

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "LOD hierarchy export should succeed"

        hierarchy_file = temp_export_dir / "TestSphere_LODGroup.fbx"
        assert verify_file_exists(hierarchy_file, "fbx"), (
            "LOD hierarchy file should exist"
        )

        # (a) The LodGroup node attribute must be present in the binary FBX.
        raw = hierarchy_file.read_bytes()
        assert b"LodGroup" in raw, (
            "Exported FBX must contain a LodGroup node so Unreal imports the "
            "LODs as one mesh"
        )

        # (b) Re-import and confirm the hierarchy is intact: a single root empty
        # parenting all LOD meshes. (Blender's importer collapses the LodGroup
        # node back to a plain empty and does not restore the fbx_type custom
        # property, so we check structure rather than the marker here.)
        existing = set(bpy.data.objects.keys())
        bpy.ops.import_scene.fbx(filepath=str(hierarchy_file))
        imported = [o for o in bpy.data.objects if o.name not in existing]

        root_empties = [
            o for o in imported if o.type == "EMPTY" and o.parent is None
        ]
        assert len(root_empties) == 1, (
            "Re-imported FBX should contain exactly one root empty (the LOD "
            f"group), found {len(root_empties)}"
        )

        mesh_children = [
            o
            for o in imported
            if o.type == "MESH" and o.parent is root_empties[0]
        ]
        assert len(mesh_children) == 3, (
            "LOD group should parent LOD0 + 2 LODs (3 meshes), "
            f"found {len(mesh_children)}"
        )


class TestLODSymmetry:
    """Tests for LOD symmetry settings."""

    def test_lod_symmetry_enabled(self, create_sphere, temp_export_dir, reset_settings):
        """Test LOD generation with symmetry enabled."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False
        props.mesh_export_lod_symmetry = True
        props.mesh_export_lod_symmetry_axis = "X"

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "LOD generation with symmetry should succeed"

    def test_lod_symmetry_axes(self, create_sphere, temp_export_dir, reset_settings):
        """Test LOD symmetry on different axes."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 1
        props.mesh_export_lod_hierarchy = False
        props.mesh_export_lod_symmetry = True

        for axis in ["X", "Y", "Z"]:
            # Clear previous exports
            for file in temp_export_dir.glob("*.fbx"):
                file.unlink()

            props.mesh_export_lod_symmetry_axis = axis
            props.mesh_export_suffix = f"_sym{axis}"

            create_sphere.select_set(True)
            result = bpy.ops.mesh.batch_export()
            assert result == {"FINISHED"}, (
                f"LOD with symmetry on {axis} axis should succeed"
            )


class TestLODTextureResizing:
    """Tests for automatic texture resizing in LOD levels."""

    def test_lod_texture_resizing_enabled(
        self, create_sphere, temp_export_dir, reset_settings
    ):
        """Test LOD generation with automatic texture resizing."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False
        props.mesh_export_resize_textures = True

        # Set texture sizes for LODs
        props.mesh_export_lod1_texture_size = "2048"
        props.mesh_export_lod2_texture_size = "1024"

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "LOD with texture resizing should succeed"

    def test_lod_texture_resizing_disabled(
        self, create_sphere, temp_export_dir, reset_settings
    ):
        """Test LOD generation without texture resizing."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False
        props.mesh_export_resize_textures = False

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "LOD without texture resizing should succeed"

    def test_normal_map_preservation(
        self, create_sphere, temp_export_dir, reset_settings
    ):
        """Test that normal map quality is preserved at higher resolution."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False
        props.mesh_export_resize_textures = True
        props.mesh_export_preserve_normal_maps = True

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "LOD with normal map preservation should succeed"


class TestLODWithFormats:
    """Tests for LOD generation with different export formats."""

    def test_lod_with_gltf(self, create_sphere, temp_export_dir, reset_settings):
        """Test LOD generation with glTF format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "GLTF"
        props.mesh_export_gltf_type = "GLB"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "LOD generation with glTF should succeed"

        # Verify LOD files with glb extension
        base_file = temp_export_dir / "TestSphere.glb"
        lod1_file = temp_export_dir / "TestSphere_LOD01.glb"
        lod2_file = temp_export_dir / "TestSphere_LOD02.glb"

        assert verify_file_exists(base_file, "glb"), "Base glTF file should exist"
        assert verify_file_exists(lod1_file, "glb"), "LOD1 glTF file should exist"
        assert verify_file_exists(lod2_file, "glb"), "LOD2 glTF file should exist"

    def test_lod_with_obj(self, create_sphere, temp_export_dir, reset_settings):
        """Test LOD generation with OBJ format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "OBJ"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "LOD generation with OBJ should succeed"

    def test_lod_with_stl(self, create_sphere, temp_export_dir, reset_settings):
        """Test LOD generation with STL format."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "STL"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False

        create_sphere.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "LOD generation with STL should succeed"


@pytest.mark.slow
class TestLODWithLargeMeshes:
    """Tests for LOD generation with large meshes (memory intensive)."""

    def test_lod_with_large_mesh(
        self, create_large_mesh, temp_export_dir, reset_settings
    ):
        """Test LOD generation on a large mesh (500K+ polygons)."""
        props = get_scene_props()
        props.mesh_export_path = str(temp_export_dir) + "/"
        props.mesh_export_format = "FBX"
        props.mesh_export_lod = True
        props.mesh_export_lod_count = 2
        props.mesh_export_lod_hierarchy = False

        create_large_mesh.select_set(True)
        result = bpy.ops.mesh.batch_export()
        assert result == {"FINISHED"}, "LOD generation on large mesh should succeed"

        # Verify files were created
        base_file = temp_export_dir / "TestLargeMesh.fbx"
        assert verify_file_exists(base_file, "fbx"), "Large mesh base file should exist"

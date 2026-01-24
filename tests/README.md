# EasyMesh Batch Exporter Test Suite

Comprehensive automated testing for the EasyMesh Batch Exporter addon using pytest-blender.

## Quick Start

```bash
# From the project root
./run_tests.sh
```

## Test Files Overview

### `test_export_formats.py` - Export Format Testing

Tests all supported export formats and their specific features:

- **FBX Export:** Single/multiple objects, smoothing modes
- **OBJ Export:** Basic export, material files
- **glTF Export:** GLB vs JSON, Draco compression, material modes
- **USD Export:** Single/multiple objects
- **STL Export:** Triangulation requirements
- **Coordinate Systems:** Up/Forward axis configurations
- **Units & Scale:** Metres vs centimetres, custom scale factors

**Test Count:** ~30 tests
**Run Time:** ~2-3 minutes
**Markers:** `export_format`

### `test_object_types.py` - Object Type Handling

Tests different Blender object types and their conversion:

- **Mesh Objects:** Cube, sphere, cylinder, torus primitives
- **Curve Objects:** Bezier, NURBS, bevelled curves
- **Metaball Objects:** Ball, capsule, smooth shading
- **Mixed Selections:** Multiple object types together
- **Transforms:** Zero location, rotation, scaling

**Test Count:** ~20 tests
**Run Time:** ~1-2 minutes

### `test_lod_generation.py` - LOD System Testing

Tests Level of Detail generation and configuration:

- **Basic LOD:** Enable/disable, varying LOD counts (1-4)
- **LOD Ratios:** Custom decimation ratios, extreme values
- **LOD Hierarchies:** Game engine LOD group export
- **LOD Symmetry:** X/Y/Z axis symmetry preservation
- **Texture Resizing:** Automatic downscaling per LOD level
- **Format Compatibility:** LOD with different export formats
- **Large Mesh LODs:** Memory optimisation for LOD generation

**Test Count:** ~25 tests
**Run Time:** ~5-10 minutes (includes slow tests)
**Markers:** `slow`

### `test_batch_modes.py` - Batch Export Testing

Tests glTF batch mode functionality:

- **Batch Combine:** Multiple objects into single glTF file
- **Batch Individual:** Separate files per object
- **Collection Naming:** Using collection name for combined files
- **Batch + LOD:** Combining batch mode with LOD generation
- **Format Specificity:** Batch mode only applies to glTF
- **Naming Conventions:** Batch mode with custom naming

**Test Count:** ~15 tests
**Run Time:** ~1-2 minutes

### `test_naming.py` - Naming Convention Testing

Tests filename generation and sanitisation:

- **Naming Conventions:** Default, Godot (snake_case), Unity (Capitalised_Words), Unreal (PascalCase)
- **Prefix/Suffix:** Adding custom text to filenames
- **Unreal Prefixes:** SM_, SK_, BP_ prefix preservation
- **Filename Sanitisation:** Special characters, Unicode, slashes
- **Length Truncation:** Very long filename handling (>100 chars)
- **LOD Naming:** Naming conventions applied to LOD files

**Test Count:** ~20 tests
**Run Time:** ~1-2 minutes

### `test_modifiers.py` - Modifier Application Testing

Tests modifier handling during export:

- **Application Modes:** None, Visible, Render
- **Specific Modifiers:** Subdivision Surface, Bevel, Mirror, Array
- **Multiple Modifiers:** Modifier stacks, mixed visibility
- **Triangulation:** Interaction with modifier application
- **LOD + Modifiers:** Modifiers applied before LOD decimation

**Test Count:** ~15 tests
**Run Time:** ~2-3 minutes

### `test_memory.py` - Memory Management Testing

Tests large mesh handling and memory optimisation:

- **Large Meshes:** 500K+ polygon handling
- **Very Large Meshes:** 2M+ polygon handling with aggressive GC
- **Triangulation:** Large mesh triangulation
- **Modifiers:** Large mesh modifier application
- **LOD Generation:** Progressive LOD building on large meshes
- **Memory Cleanup:** Multiple export memory leak testing
- **Batch Exports:** Many objects, glTF combine mode
- **All Formats:** Large mesh export across all formats

**Test Count:** ~15 tests
**Run Time:** ~10-20 minutes (very slow)
**Markers:** `slow`, `memory`

### `test_edge_cases.py` - Error Handling Testing

Tests edge cases and error recovery:

- **Empty Selections:** No objects selected, empty scene
- **Invalid Paths:** Non-existent directories, relative paths
- **Unsupported Objects:** Camera, light, empty objects
- **Mixed Selections:** Valid + invalid objects together
- **Zero Polygon Meshes:** Vertices without faces
- **Collection Instances:** Should be skipped gracefully
- **Special Characters:** Unicode, dots, illegal characters
- **Extreme Settings:** Zero LOD ratios, extreme scales

**Test Count:** ~25 tests
**Run Time:** ~2-3 minutes

## Running Specific Test Subsets

### Run only fast tests (skip slow memory tests)

```bash
./run_tests.sh -m "not slow and not memory"
```

### Run only export format tests

```bash
./run_tests.sh tests/test_export_formats.py
```

### Run only LOD tests

```bash
./run_tests.sh tests/test_lod_generation.py
```

### Run specific test class

```bash
./run_tests.sh tests/test_export_formats.py::TestFBXExport
```

### Run specific test method

```bash
./run_tests.sh tests/test_export_formats.py::TestFBXExport::test_fbx_single_object_export
```

### Run all tests matching a pattern

```bash
./run_tests.sh -k "gltf"  # All glTF-related tests
./run_tests.sh -k "lod"   # All LOD-related tests
./run_tests.sh -k "naming"  # All naming tests
```

## Test Markers

Tests use pytest markers to categorise and filter:

- `@pytest.mark.slow` - Tests that take significant time (>30s)
- `@pytest.mark.memory` - Memory-intensive tests requiring large meshes
- `@pytest.mark.export_format` - Tests for specific export formats
- `@pytest.mark.integration` - Integration tests (multiple components)
- `@pytest.mark.unit` - Unit tests (single functions)

## Fixtures (conftest.py)

### Object Creation Fixtures

- `create_cube` - Simple cube mesh
- `create_sphere` - UV sphere mesh
- `create_curve` - Bezier curve
- `create_large_mesh` - 500K+ polygon mesh
- `create_very_large_mesh` - 2M+ polygon mesh
- `create_collection` - Collection with multiple objects

### Utility Fixtures

- `clean_scene` - Auto-cleans scene before each test
- `temp_export_dir` - Temporary directory for exports
- `reset_settings` - Resets all export settings to defaults
- `enable_addon` - Ensures addon is enabled (session scope)

### Helper Functions

- `verify_file_exists(path, format)` - Check if exported file exists
- `verify_exported_files(dir, files, format)` - Verify multiple files
- `count_exported_files(dir, format)` - Count files of specific format
- `get_scene_props()` - Get addon property group
- `reset_export_settings()` - Reset all settings programmatically

## Expected Test Results

**Total Tests:** ~180 tests
**Fast Tests Only:** ~120 tests (~10-15 minutes)
**All Tests:** ~180 tests (~25-35 minutes)

### Success Criteria

- All tests pass (green)
- No memory leaks reported
- Exported files created correctly
- Error conditions handled gracefully

### Common Test Failures

1. **Blender version mismatch** - Ensure Blender 4.2+ is installed
2. **Addon not enabled** - Run tests from project root with addon installed
3. **Missing dependencies** - Install test-requirements.txt into Blender Python
4. **Permission errors** - Ensure write access to temp directories

## Adding New Tests

When adding new features:

1. **Create test file** (if testing new major feature area)
2. **Add test class** organising related tests
3. **Use fixtures** from conftest.py for setup
4. **Add markers** for slow/memory intensive tests
5. **Verify cleanup** - ensure tests don't leak resources
6. **Document coverage** - update this README

### Example Test

```python
def test_my_new_feature(create_cube, temp_export_dir, reset_settings):
    """Test description of what this test validates."""
    props = get_scene_props()
    props.mesh_export_path = str(temp_export_dir) + "/"
    props.mesh_export_format = "FBX"

    create_cube.select_set(True)
    result = bpy.ops.mesh.batch_export_selected()

    assert result == {'FINISHED'}, "Export should succeed"
    assert verify_file_exists(temp_export_dir / "TestCube.fbx", "fbx")
```

## Continuous Integration

The test suite can be integrated into CI/CD:

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: |
          pip install pytest-blender
          blender_python="$(pytest-blender)"
          $blender_python -m pip install -r test-requirements.txt
      - name: Run tests
        run: ./run_tests.sh -m "not slow and not memory"
```

## Troubleshooting

### Tests fail with "addon not found"

- Ensure addon is installed in Blender
- Run from project root directory
- Check addon name matches in conftest.py

### Tests fail with import errors

- Install test dependencies: `pip install -r test-requirements.txt`
- Ensure pytest-blender is installed
- Check Blender Python path

### Memory tests timeout

- Expected for very large mesh tests (2M+ polygons)
- Skip with: `./run_tests.sh -m "not memory"`
- Increase timeout if needed (see pytest.ini)

### Permission denied errors

- Check write permissions for temp directories
- Ensure /tmp or system temp dir is writable
- On Windows, check %TEMP% permissions

## Support

For issues with tests:

1. Check existing test output for error messages
2. Run with verbose flag: `./run_tests.sh -v`
3. Run specific failing test in isolation
4. Check GitHub Issues for similar problems
5. Create new issue with test output and Blender version

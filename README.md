# EasyMesh Batch Exporter for Blender

![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)
![Version: 1.4.0](https://img.shields.io/badge/Version-1.4.0-green.svg)
![Blender: 4.2+](https://img.shields.io/badge/Blender-4.2+-orange.svg)
![Large Mesh Support](https://img.shields.io/badge/Large%20Mesh-2M%2B%20Polygons-red.svg)

A streamlined Blender add-on designed for game development workflows. Batch export meshes, curves, and metaballs with advanced memory optimisation, game engine naming conventions, LOD hierarchy export, texture optimisation, and visual export indicators. Features robust modifier control and handles large, complex meshes (2M+ polygons) without crashes.

[![EasyMesh demo - Watch Video](https://cdn.loom.com/sessions/thumbnails/567dea7f7cf84f91939d159807d6659d-e7c0d4f2068a7d8d-full-play.gif)](https://www.loom.com/share/567dea7f7cf84f91939d159807d6659d?sid=dd68ecd1-58dc-43c4-b74b-cfeaa82f4553)

## Features

### 🚀 **Performance & Memory Optimisation**
* **Large Mesh Support:** Handles meshes with 2+ million polygons without crashes
* **Smart Memory Management:** Automatic garbage collection and cleanup for large meshes (>500K polygons)
* **Progressive Processing:** Memory cleanup every 3 modifiers during heavy modifier stacks
* **Threshold-Based Optimisation:** Different strategies for large (500K+) and very large (1M+) meshes

### 🎛️ **Advanced Modifier Control**
* **Flexible Modifier Application:** Choose which modifiers to apply during export:
  * **None:** Skip all modifiers for fastest performance
  * **Visible:** Apply only viewport-visible modifiers (default)
  * **Render:** Apply only render-enabled modifiers
* **Smart Processing:** Respects Blender's modifier visibility states
* **Memory Efficient:** Automatic cleanup between modifier applications

### 📦 **Batch Export**
* **Multi-Object Support:** Export meshes, curves, and metaballs simultaneously
* **Automatic Conversion:** Curves and metaballs are converted to meshes during export
* **Error Handling:** Robust error recovery with detailed failure reporting
* **Multiple Formats:** FBX, OBJ, glTF (binary/JSON), USD, and STL support

### 🎮 **Game Engine Integration**
* **Naming Conventions:** Built-in support for game engine naming standards:
  * **Godot:** snake_case naming (my_mesh_name)
  * **Unity:** Capitalised_Words_With_Underscores 
  * **Unreal Engine:** PascalCase naming (MyMeshName) with prefix preservation
  * **Default:** Keep original naming with basic sanitisation
* **LOD Hierarchy Export:** Export objects with LOD levels as structured hierarchies for Unity/Unreal workflows (FBX format only)
* **Game-Ready Output:** Optimised for immediate use in game engines

### 🎯 **Precision Controls**
* **Transform Options:**
    * Zero object location before export
    * Custom export scale with format-specific handling
    * Configurable Forward and Up axes
* **Units Handling:** Seamless conversion between metres and centimetres
* **Naming System:** Custom prefixes and suffixes for organised file output

### 🔧 **Mesh Processing**
* **Triangulation:** Multiple methods (Beauty, Fixed, Alternate, Shortest Diagonal) with normal preservation
* **Smoothing Control:** Format-specific smoothing options (Face, Edge, Off)
* **Memory-Safe Operations:** All processing optimised for large mesh stability

### 📊 **LOD Generation & Hierarchy Export**
* **Automatic LODs:** Generate up to 4 levels of detail using Decimate modifier
* **Progressive Building:** Each LOD built from previous (making processing faster and uses less memory)
* **Symmetry Preservation:** Maintain model symmetry during decimation
* **Quality Control:** Individual ratio settings for each LOD level
* **Hierarchy Export Mode:** Export LODs as structured FBX hierarchies for game engines:
  * Creates `{ObjectName}_LODGroup.fbx` with parent empty containing all LOD levels
  * LOD objects named as `{basename}_LOD00`, `{basename}_LOD01`, etc.
  * Each selected object processed individually (preserves separate LOD groups)
  * Compatible with Unity and Unreal Engine LOD systems
* **Advanced Texture Optimisation:**
  * Automatic texture downscaling with customisable sizes per LOD
  * Aspect ratio preservation to prevent distortion
  * Format preservation (PNG for alpha, HDR for high dynamic range)
  * Normal map quality preservation (keeps higher resolution)
  * Compression quality control for lossy formats (0-100)
  * Smart resizing (no upscaling of small textures)

### 👁️ **Visual Feedback**
* **Export Indicators:** Optional viewport colour coding for recently exported objects
  * Green: Recently exported (< 1 minute)
  * Yellow: Previously exported (< 5 minutes)
  * Toggle on/off via checkbox for cleaner viewport when needed
* **Recent Exports Panel:** Interactive list of exported objects with selection
* **Detailed Logging:** Comprehensive console output with polygon counts and timing

## Installation

### Method 1: Blender Extensions

1. In Blender, go to `Edit` > `Preferences...`.
2. Navigate to the `Get Extensions` tab.
3. Search for "EasyMesh Batch Exporter" and click the `Install` button.

You can also find the add-on directly on [Blender Extensions](https://extensions.blender.org/add-ons/easymesh-batch-exporter/).

### Method 2: Manual Installation

1. Download the latest release `.zip` file from the [Releases page](https://github.com/speculative-artefact/easymesh_batch_exporter/releases).
2. In Blender, go to `Edit` > `Preferences...`.
3. Navigate to the `Get Extensions` tab.
4. In the top right next to `Repositories`, click the `⌄` dropdown menu.
5. Choose `Install from Disk...` from the dropdown.
6. Navigate to where you downloaded the `.zip` file in step 1.
7. Select the `.zip` file and click `Install from Disk`.

## Usage

1.  **Find the Panel:** The add-on's panel appears in the 3D Viewport's Sidebar (Press `N` key if hidden) under the "Exporter" tab.
2.  **Select Objects:** Select one or more mesh, curve, or metaball objects you want to export in the 3D Viewport.
3.  **Configure Settings:** Adjust the settings in the "EasyMesh Batch Exporter" panel:
    
    ### Basic Settings
    * **Export Path:** Choose the directory where files will be saved
    * **Format:** Select output format (FBX, OBJ, glTF, USD, STL)
    * **glTF Batch Export:** (glTF only) Combine all selected meshes into a single file
      * **Enabled by default** - Perfect for Godot imports
      * Uses collection name for filename (or first object's name as fallback)
      * Disable to export each mesh as a separate file
      * Compatible with LOD generation
    * **Coordinate System:** Set Forward and Up axes for your target application
    * **Scale & Units:** Set global scale and choose between metres/centimetres
    * **Smoothing:** Select smoothing method (Face, Edge, Off) for supported formats
    
    ### Transform & Processing
    * **Zero Location:** Set object location to (0,0,0) before export
    * **Modifier Mode:** Choose which modifiers to apply:
      * **None:** Skip all modifiers (fastest, export base mesh only)
      * **Visible:** Apply viewport-visible modifiers (recommended)
      * **Render:** Apply render-enabled modifiers (most complete)
    * **Triangulate:** Optional mesh triangulation with method selection and normal preservation
    
    ### File Naming & Game Engine Support
    * **Prefix/Suffix:** Add custom text to exported filenames for organisation
    * **Naming Conventions:** Choose game engine specific naming:
      * **Godot:** snake_case (my_mesh_name)
      * **Unity:** Capitalised_Words_With_Underscores
      * **Unreal Engine:** PascalCase (MyMeshName) 
      * **Default:** Basic sanitisation only
    
    ### LOD Generation (Optional)
    * **Quick LODs:** Enable in sub-panel header to generate up to 4 detail levels
    * **Export as Hierarchy:** Create structured LOD groups for Unity/Unreal workflows
    * **Symmetry:** Maintain model symmetry during decimation
    * **Resize Textures:** Enable automatic texture optimisation for LODs
    * **Texture Settings** (when resizing enabled):
      * **Compression:** Quality setting for lossy formats like JPEG (0-100)
      * **Preserve Normal Maps:** Keep normal maps at higher resolution
      * **LOD Texture Sizes:** Customisable max size for each LOD (8K to 128px)
    * **Ratios:** Individual mesh decimation settings for each LOD level
    * Note: LOD0 = base mesh, LOD1-4 = progressively optimised versions

4.  **Export:** Click the "Export Objects" button (text changes based on selection type)
5.  **Monitor Progress:** 
    * Real-time progress in Blender's status bar
    * Detailed console logs with polygon counts and timing
    * Memory optimisation messages for large meshes

## Performance & Large Mesh Handling

### 🔧 **Automatic Optimisations**
The add-on automatically detects and optimises for large meshes:

* **500K+ polygons:** Basic memory management with progressive cleanup
* **1M+ polygons:** Aggressive memory optimisation and pre-processing cleanup
* **Memory cleanup:** Automatic garbage collection every 3 modifiers during heavy operations
* **Smart processing:** Different strategies based on mesh complexity
* **LOD Reuse:** Progressive building reduces memory by 60% and time by 40-50%

### 💡 **Performance Tips**

#### For Large Meshes (500K+ polygons):
* **Use "None" modifiers:** Skip modifier application for fastest export
* **Close other applications:** Maximise available system memory
* **Export in batches:** Process fewer objects at once to reduce memory pressure
* **Monitor console:** Watch for "Memory optimisation" messages

#### For Very Large Meshes (1M+ polygons):
* **Strongly recommend "None" modifiers:** Avoid modifier processing when possible
* **Single object exports:** Export one object at a time for maximum stability
* **LOD generation:** Use LODs to create multiple resolution versions efficiently

#### Modifier Application Guidelines:
* **"None":** Best performance, exports base mesh without any modifications
* **"Visible":** Good balance of functionality and performance (default)
* **"Render":** Most complete but may impact performance on large meshes

### 📊 **Console Output**
Monitor the console for detailed information:
```
INFO: Applying memory optimisation for large mesh: 1,250,000 polygons
INFO: Large mesh export: 1,250,000 polygons
INFO: Memory cleanup after 3 modifiers
INFO: Decimation complete: 1,250,000 → 312,500 polys (target: 0.250, actual: 0.250)
```

## Export Indicators

* After an object is successfully exported (including all its LODs if enabled), it will be marked in the viewport.
  * **Green:** Object exported within the last minute (`FRESH`).
  * **Yellow:** Object exported within the last 5 minutes (`STALE`).
  * **Normal Colour:** Object export indicator has expired, or indicators were cleared.
* **Toggle Location:** The export indicators checkbox is conveniently located in the header of the "Recent Exports" panel.
* **Visibility:** To see these colours in the 3D Viewport, ensure you are in **Solid** display mode and that the **Shading -> Colour** type is set to **Object**.
    [[Viewport Shading Docs]](https://docs.blender.org/manual/en/latest/editors/3dview/display/shading.html#solid)
* **Recent Exports Panel:** When indicators are enabled, shows a list of recently exported objects (still FRESH or STALE). Clicking the icon selects the object.
* **Clear Indicators:** The "Clear All Export Indicators" button at the bottom of the "Recent Exports" panel will immediately remove the status from all objects and restore their original viewport colours.
* **Auto-Clear:** Unchecking the indicators checkbox immediately clears all existing indicators from the viewport.

## Support Development

If you find EasyMesh Batch Exporter useful in your workflow, consider supporting continued development:

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20Development-FF5E5B?style=for-the-badge&logo=ko-fi&logoColour=white)](https://ko-fi.com/speculative_artefact)

Thank you!

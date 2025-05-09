# EasyMesh Batch Exporter for Blender

![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)
![Blender: 4.2+](https://img.shields.io/badge/Blender-4.2+-orange.svg)

A Blender add-on for batch exporting multiple selected mesh objects with customisable settings, including LOD generation and viewport indicators for recent exports.

## Features

* **Batch Export:** Export multiple selected mesh objects at once.
* **Multiple Formats:** Supports exporting to FBX, OBJ, glTF (gltf+bin+textures), USD, and STL.
* **Custom Transforms:**
    * Optionally zero the object's location before export.
    * Apply custom export scale (behaviour dependent on exporter).
    * Set custom Forward and Up axes.
* **Units Handling:** Choose between metres and centimetres to match your target application.
* **Naming Options:** Add custom prefixes and suffixes to exported filenames.
* **Mesh Processing:**
    * Apply all existing (visible) modifiers before export.
    * Optionally triangulate meshes using different methods (Beauty, Fixed, Fixed Alternate, Shortest Diagonal).
    * Choose specific smoothing methods for formats that support them (Face, Edge, or Off).
    * Optionally generate Levels of Detail (LODs) using the Decimate modifier (creates `_LOD00`, `_LOD01`, etc. files).
    * Apply symmetry during LOD generation to maintain model symmetry.
* **Advanced Texture Handling:** Automatic downscaling of textures for different LOD levels to optimise file size.
* **Export Indicators:** Provides visual feedback in the viewport for recently exported objects (Green = fresh, Yellow = stale) and lists them in the panel.

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
2.  **Select Objects:** Select one or more mesh objects you want to export in the 3D Viewport.
3.  **Configure Settings:** Adjust the settings in the "Batch Exporter" panel:
    * **Export Path:** Choose the directory where files will be saved.
    * **Format:** Select the desired output file format (FBX, OBJ, etc.).
    * **Coordinate System:** Set the Forward and Up axes according to your target application's needs.
    * **Scale:** Set the global export scale (if supported by the format).
    * **Units:** Choose between metres (Blender default) and centimetres (common in game engines).
    * **Smoothing:** For applicable formats, select the smoothing method (Face, Edge, or Off).
    * **Zero Location:** If checked, object copies will have their location set to (0,0,0) before export.
    * **Triangulate:** If checked, applies triangulation to the exported mesh copy. Choose the desired method and whether to preserve normals.
    * **Rename File:** Add optional Prefix and/or Suffix to the exported filenames.
    * **Quick LODs (Optional):** Check the box in the sub-panel header to enable LOD generation. Configure the number of LODs (1-4), symmetry options, and ratio for each level. Note that LOD0 is the base mesh (after base modifiers/triangulation), and subsequent LODs are generated with increasingly aggressive decimation.
4.  **Export:** Click the "Export Selected Meshes" button.
5.  **Progress:** Monitor the export progress in Blender's bottom status bar. Console output provides detailed logs.

## Export Indicators

* After an object is successfully exported (including all its LODs if enabled), it will be marked in the viewport.
* **Green:** Object exported within the last minute (`FRESH`).
* **Yellow:** Object exported within the last 5 minutes (`STALE`).
* **Normal Colour:** Object export indicator has expired, or indicators were cleared.
* **Visibility:** To see these colours in the 3D Viewport, ensure you are in **Solid** display mode and that the **Shading -> Color** type is set to **Object**.
    [[Viewport Shading Docs]](https://docs.blender.org/manual/en/latest/editors/3dview/display/shading.html#solid)
* **Recent Exports Panel:** A list of recently exported objects (still FRESH or STALE) appears in a sub-panel. Clicking the icon selects the object.
* **Clear Indicators:** The "Clear All Export Indicators" button at the bottom of the "Recent Exports" panel will immediately remove the status from all objects and restore their original viewport colours.

## Support Development

If you find EasyMesh Batch Exporter useful in your workflow, consider supporting continued development:

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support%20Development-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/speculative_artefact)

Your support helps maintain and improve this add-on. Thank you!

# EasyMesh Batch Exporter for Blender

![License: GPL-2.0-or-later](https://img.shields.io/badge/License-GPL--2.0--or--later-blue.svg)
![Blender: 4.2+](https://img.shields.io/badge/Blender-4.2+-orange.svg)

A Blender add-on for batch exporting multiple selected mesh objects with customisable settings, including LOD generation and viewport indicators for recent exports.

## Features

* **Batch Export:** Export multiple selected mesh objects at once.
* **Multiple Formats:** Supports exporting to FBX, OBJ, glTF (gltf+bin+textures), USD, and STL.
* **Custom Transforms:**
    * Optionally zero the object's location before export.
    * Apply custom export scale (behaviour dependent on exporter).
    * Set custom Forward and Up axes.
* **Naming Options:** Add custom prefixes and suffixes to exported filenames.
* **Mesh Processing:**
    * Apply all existing (visible) modifiers before export.
    * Optionally triangulate meshes using different methods.
    * Optionally generate Levels of Detail (LODs) using the Decimate modifier (creates `_LOD00`, `_LOD01`, etc. files).
* **Export Indicators:** Provides visual feedback in the viewport for recently exported objects (Green = fresh, Yellow = stale) and lists them in the panel.
* **Status Bar Progress:** Shows export progress in Blender's status bar for longer operations.

## Installation

1.  Download the latest release `.zip` file from the [Releases page](https://github.com/doommchips/blender_mesh_exporter/releases).
2.  In Blender, go to `Edit` > `Preferences...`.
3.  Navigate to the `Add-ons` tab.
4.  Click `Install...` and select the downloaded `.zip` file.
5.  Find the add-on named "EasyMesh Batch Exporter" in the list (you can search for it).
6.  Enable the add-on by checking the checkbox next to its name.

## Usage

1.  **Find the Panel:** The add-on's panel appears in the 3D Viewport's Sidebar (Press `N` key if hidden) under the "Exporter" tab.
2.  **Select Objects:** Select one or more mesh objects you want to export in the 3D Viewport.
3.  **Configure Settings:** Adjust the settings in the "Batch Exporter" panel:
    * **Export Path:** Choose the directory where files will be saved.
    * **Format:** Select the desired output file format (FBX, OBJ, etc.).
    * **Coordinate System:** Set the Forward and Up axes according to your target application's needs.
    * **Scale:** Set the global export scale (if supported by the format).
    * **Zero Location:** If checked, object copies will have their location set to (0,0,0) before export.
    * **Triangulate:** If checked, applies triangulation to the exported mesh copy. Choose the desired method.
    * **Rename File:** Add optional Prefix and/or Suffix to the exported filenames.
    * **LOD Generation (Optional):** Check the box in the "LOD Generation" sub-panel header to enable it. Configure the number of LODs, Decimation Type, and Ratio/Iterations for each level. Note that LOD0 is the base mesh (after base modifiers/triangulation), and subsequent LODs are generated progressively from fresh copies.
4.  **Export:** Click the "Export Selected Meshes" button.
5.  **Progress:** Monitor the export progress in Blender's bottom status bar. Console output provides detailed logs.

## Export Indicators

* After an object is successfully exported (including all its LODs if enabled), it will be marked in the viewport.
* **Green:** Object exported within the last minute (`FRESH`).
* **Yellow:** Object exported within the last 5 minutes (`STALE`).
* **Normal Color:** Object export indicator has expired, or indicators were cleared.
* **Visibility:** To see these colours in the 3D Viewport, ensure you are in **Solid** display mode and that the **Shading -> Color** type is set to **Object**.
    ![Viewport Shading Object Color](https://docs.blender.org/manual/en/latest/editors/3dview/display/shading.html#solid)
* **Recent Exports Panel:** A list of recently exported objects (still FRESH or STALE) appears in a sub-panel. Clicking the icon selects the object.
* **Clear Indicators:** The "Clear All Export Indicators" button at the bottom of the "Recent Exports" panel will immediately remove the status from all objects and restore their original viewport colors.

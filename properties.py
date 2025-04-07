# properties.py
"""
This module defines properties for exporting meshes in Blender.
It includes properties for export path, format, scale, coordinate system,
triangulation, LOD generation, and more.
"""

import bpy
from bpy.props import (StringProperty, EnumProperty, 
                       FloatProperty, IntProperty, BoolProperty)

def register_properties():
    # Export path property
    # Default to the current blend file directory 
    # with a subfolder "exported_meshes"
    bpy.types.Scene.mesh_export_path = StringProperty(
        name="Export Path",
        description="Path to export meshes",
        default="//exported_meshes/",
        subtype="DIR_PATH"
    )

    # Export format property
    bpy.types.Scene.mesh_export_format = EnumProperty(
        name="Format",
        description="File format to export meshes",
        items=[
             ("FBX", "FBX", "Export as FBX"),
             ("OBJ", "OBJ", "Export as OBJ"),
             ("GLTF", "glTF", "Export as glTF"),
             ("USD", "USD", "Export as USD"),
             ("STL", "STL", "Export as STL"),
        ],
        default="FBX"
    )

    # Scale property
    bpy.types.Scene.mesh_export_scale = FloatProperty(
        name="Scale",
        description="Scale factor for exported meshes",
        default=1.0,
        min=0.001,
        max=1000.0,
        soft_min=0.01,
        soft_max=100.0
    )

    # Coordinate system properties
    bpy.types.Scene.mesh_export_coord_up = EnumProperty(
        name="Up Axis",
        description="Up axis for exported meshes",
        items=[
            ("X", "X", ""),("Y", "Y", ""),("Z", "Z", ""),
            ("-X", "-X", ""),("-Y", "-Y", ""),("-Z", "-Z", "")
        ],
        default="Z"
    )

    bpy.types.Scene.mesh_export_coord_forward = EnumProperty(
        name="Forward Axis",
        description="Forward axis for exported meshes",
        items=[
            ("X", "X", ""),("Y", "Y", ""),("Z", "Z", ""),
            ("-X", "-X", ""),("-Y", "-Y", ""),("-Z", "-Z", "")
        ],
        default="X"
    )

    # Zero location property
    bpy.types.Scene.mesh_export_zero_location = BoolProperty(
        name="Zero Location",
        description="Zero location of the object copy before export",
        default=True
    )

    # Triangulate properties
    bpy.types.Scene.mesh_export_tri = BoolProperty(
        name="Triangulate Faces",
        description="Convert all faces to triangles on the copy",
        default=True
    )

    # Triangulate method property
    bpy.types.Scene.mesh_export_tri_method = EnumProperty(
        name="Method",
        description="Method used for triangulating quads",
        items=[
                ("BEAUTY", "Beauty", 
                 "Triangulate with the best-looking result"),
                ("FIXED", "Fixed", 
                 "Split the quad from the first to third vertices"),
                ("FIXED_ALTERNATE", "Fixed Alternate", 
                 "Split the quad from the second to fourth vertices"),
                ("SHORTEST_DIAGONAL", "Shortest Diagonal", 
                 "Split the quad along the shortest diagonal")
            ],
        default="BEAUTY"
    )

    # Keep normals property
    bpy.types.Scene.mesh_export_keep_normals = BoolProperty(
        name="Keep Normals",
        description="Preserve normal vectors during triangulation",
        default=True
    )

    # Prefix and suffix properties
    bpy.types.Scene.mesh_export_prefix = StringProperty(
        name="Prefix",
        description="Prefix for exported file names",
        default=""
    )

    bpy.types.Scene.mesh_export_suffix = StringProperty(
        name="Suffix",
        description="Suffix for exported file names",
        default=""
    )

    # LOD properties
    bpy.types.Scene.mesh_export_lod = BoolProperty(
        name="Generate LODs",
        description="Generate additional LODs using Decimate (modifies copy)",
        default=False
    )

    # LOD count property
    bpy.types.Scene.mesh_export_lod_count = IntProperty(
        name="Additional LODs",
        description="How many additional LODs to generate (LOD1 to LOD4)",
        default=4, min=1, max=4, # Max 4 due to 4 ratio properties
    )

    # LOD type property
    # Note: I've excluded "UNSUBDIVIDE" and "DISSOLVE"
    bpy.types.Scene.mesh_export_lod_type = EnumProperty(
        name="Decimation Type",
        description="Type of decimation to use for generating LODs",
        items=[
            ("COLLAPSE", "Collapse", "Collapse edges (Ratio)"),
            # ("UNSUBDIVIDE", "Unsubdivide", "Unsubdivide (Iterations)"),
            # ("DISSOLVE", "Planar", "Dissolve planar faces (Angle Limit)")
        ],
        default="COLLAPSE",
    )

    # LOD ratio properties
    bpy.types.Scene.mesh_export_lod_ratio_01 = FloatProperty(
        name="LOD1 Ratio", 
        description="Decimate factor for LOD 1",
        default=0.75, min=0.0, max=1.0, subtype="FACTOR"
    )
    bpy.types.Scene.mesh_export_lod_ratio_02 = FloatProperty(
        name="LOD2 Ratio", 
        description="Decimate factor for LOD 2",
        default=0.50, min=0.0, max=1.0, subtype="FACTOR"
    )
    bpy.types.Scene.mesh_export_lod_ratio_03 = FloatProperty(
        name="LOD3 Ratio", 
        description="Decimate factor for LOD 3",
        default=0.25, min=0.0, max=1.0, subtype="FACTOR"
    )
    bpy.types.Scene.mesh_export_lod_ratio_04 = FloatProperty(
        name="LOD4 Ratio", 
        description="Decimate factor for LOD 4",
        default=0.10, min=0.0, max=1.0, subtype="FACTOR"
    )


def unregister_properties():
    props_to_delete = [
        "mesh_export_path", 
        "mesh_export_format", 
        "mesh_export_scale",
        "mesh_export_coord_up", 
        "mesh_export_coord_forward",
        "mesh_export_zero_location", 
        "mesh_export_tri",
        "mesh_export_tri_method", 
        "mesh_export_keep_normals",
        "mesh_export_prefix", 
        "mesh_export_suffix", 
        "mesh_export_lod",
        "mesh_export_lod_count", 
        "mesh_export_lod_type",
        "mesh_export_lod_ratio_01", 
        "mesh_export_lod_ratio_02",
        "mesh_export_lod_ratio_03", 
        "mesh_export_lod_ratio_04",
    ]
    for prop_name in props_to_delete:
         if hasattr(bpy.types.Scene, prop_name):
              delattr(bpy.types.Scene, prop_name)
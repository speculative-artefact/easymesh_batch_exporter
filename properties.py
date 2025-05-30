# properties.py
"""
This module defines properties for exporting meshes in Blender.
It includes properties for export path, format, scale, coordinate system,
triangulation, LOD generation, and more.
"""

import bpy
from bpy.props import (StringProperty, EnumProperty, 
                      FloatProperty, IntProperty, BoolProperty,
                      PointerProperty)
from bpy.types import PropertyGroup


def clear_indicators_if_disabled(self, context):
    """Callback to clear all indicators when the checkbox is unchecked."""
    if not self.mesh_export_show_indicators:
        # Clear all export indicators
        try:
            bpy.ops.mesh.clear_export_indicators()
        except:
            # Operator might not be registered yet during addon startup
            pass


class MeshExporterSettings(PropertyGroup):
    # Export path property
    # Default to the current blend file directory 
    # with a subfolder "exported_meshes"
    mesh_export_path: StringProperty(
        name="Export Path",
        description="Path to export meshes",
        default="//exported_meshes/",
        subtype="DIR_PATH"
    )

    # Export format property
    mesh_export_format: EnumProperty(
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

    # GLTF type property
    mesh_export_gltf_type: EnumProperty(
        name="glTF type",
        description="Type of glTF to export",
        items=[
            ("GLB", "Binary", "Export as binary glTF (GLB)"),
            ("GLTF_SEPARATE", "JSON", "Export as JSON glTF (GLTF)"),
        ],
        default="GLB"
    )

    #GLTF export materials property
    mesh_export_gltf_materials: EnumProperty(
        name="Export Materials",
        description="Export materials with glTF",
        items=[
            ("EXPORT", "Export", "Export all materials used by included objects"),
            ("PLACEHOLDER", "Placeholder", "Do not export materials, but write multiple primitive groups per mesh, keeping material slot information"),
            ("NONE", "No export", "Do not export materials, and combine mesh primitive groups, losing material slot information"),
        ],
        default="EXPORT"
    )

    # Scale property
    mesh_export_scale: FloatProperty(
        name="Scale",
        description="Scale factor for exported meshes",
        default=1.0,
        min=0.001,
        max=1000.0,
        soft_min=0.01,
        soft_max=100.0
    )
    
    # Units property
    mesh_export_units: EnumProperty(
        name="Units",
        description="Unit system for exported meshes",
        items=[
            ("METERS", "m", "Use meters as export unit"),
            ("CENTIMETERS", "cm", "Use centimeters as export unit"),
        ],
        default="METERS",
    )

    # Coordinate system properties
    mesh_export_coord_up: EnumProperty(
        name="Up Axis",
        description="Up axis for exported meshes",
        items=[
            ("X", "X", ""),("Y", "Y", ""),("Z", "Z", ""),
            ("-X", "-X", ""),("-Y", "-Y", ""),("-Z", "-Z", "")
        ],
        default="Z"
    )

    mesh_export_coord_forward: EnumProperty(
        name="Forward Axis",
        description="Forward axis for exported meshes",
        items=[
            ("X", "X", ""),("Y", "Y", ""),("Z", "Z", ""),
            ("-X", "-X", ""),("-Y", "-Y", ""),("-Z", "-Z", "")
        ],
        default="X"
    )

    mesh_export_smoothing: EnumProperty(
        name="Smoothing",
        description="Smoothing method for exported meshes",
        items=[
            ("OFF", "Off", "Export only normals instead "
            "of writing edge or face smoothing data"),
            ("FACE", "Face", "Write face smoothing"),
            ("EDGE", "Edge", "Write edge smoothing"),
        ],
        default="FACE"
    )

    # Zero location property
    mesh_export_zero_location: BoolProperty(
        name="Zero Location",
        description="Zero location of the object copy before export",
        default=True
    )

    # Triangulate properties
    mesh_export_tri: BoolProperty(
        name="Triangulate Faces",
        description="Convert all faces to triangles on the copy",
        default=True
    )

    # Triangulate method property
    mesh_export_tri_method: EnumProperty(
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
    mesh_export_keep_normals: BoolProperty(
        name="Keep Normals",
        description="Preserve normal vectors during triangulation",
        default=True
    )

    # Modifier application property
    mesh_export_apply_modifiers: EnumProperty(
        name="Modifier Mode",
        description="Which modifiers to apply during export",
        items=[
            ("NONE", "None", "Don't apply any modifiers to the exported copy"),
            ("VISIBLE", "Visible", "Apply only modifiers visible in viewport"),
            ("RENDER", "Render", "Apply only modifiers enabled for rendering"),
        ],
        default="VISIBLE"
    )

    # Prefix and suffix properties
    mesh_export_prefix: StringProperty(
        name="Prefix",
        description="Prefix for exported file names",
        default=""
    )

    mesh_export_suffix: StringProperty(
        name="Suffix",
        description="Suffix for exported file names",
        default=""
    )

    # Export indicators property
    mesh_export_show_indicators: BoolProperty(
        name="Show Export Indicators",
        description="Display colour indicators in viewport for recently exported objects",
        default=True,
        update=lambda self, context: clear_indicators_if_disabled(self, context)
    )

    # LOD properties
    mesh_export_lod: BoolProperty(
        name="Generate LODs",
        description="Generate additional LODs using Decimate (modifies copy)",
        default=False
    )

    # LOD count property
    mesh_export_lod_count: IntProperty(
        name="Additional LODs",
        description="How many additional LODs to generate (LOD1 to LOD4)",
        default=4, min=1, max=4, # Max 4 due to 4 ratio properties
    )

    # LOD symmetry property
    mesh_export_lod_symmetry: BoolProperty(
        name="Symmetry",
        description="Use symmetry for LOD generation",
        default=False
    )

    # LOD symmetry axis property
    mesh_export_lod_symmetry_axis: EnumProperty(
        name="Symmetry Axis",
        description="Axis of symmetry for LOD generation",
        items=[
            ("X", "X", "X axis"),
            ("Y", "Y", "Y axis"),
            ("Z", "Z", "Z axis")
        ],
        default="X"
    )

    # LOD type property
    # Note: I've excluded "UNSUBDIVIDE" and "DISSOLVE"
    mesh_export_lod_type: EnumProperty(
        name="Decimation Type",
        description="Type of decimation to use for generating LODs",
        items=[
            ("COLLAPSE", "Collapse", "Collapse edges (Ratio)"),
            # ("UNSUBDIVIDE", "Unsubdivide", "Unsubdivide (Iterations)"),
            # ("DISSOLVE", "Planar", "Dissolve planar faces (Angle Limit)")
        ],
        default="COLLAPSE",
    )

    # Texture resizing property
    mesh_export_resize_textures: BoolProperty(
        name="Resize Textures for LODs",
        description="Automatically resize textures for LODs",
        default=True
    )
    
    # Texture quality property
    mesh_export_texture_quality: IntProperty(
        name="Texture Compression",
        description="Quality for lossy formats like JPEG (0-100). Does not affect PNG or other lossless formats",
        default=85,
        min=0,
        max=100,
        subtype='PERCENTAGE'
    )
    
    # LOD texture size properties
    mesh_export_lod1_texture_size: EnumProperty(
        name="LOD1 Texture Size",
        description="Maximum texture size for LOD1",
        items=[
            ("8192", "8K", "8192x8192"),
            ("4096", "4K", "4096x4096"),
            ("2048", "2K", "2048x2048"),
            ("1024", "1K", "1024x1024"),
        ],
        default="2048"
    )
    
    mesh_export_lod2_texture_size: EnumProperty(
        name="LOD2 Texture Size",
        description="Maximum texture size for LOD2",
        items=[
            ("4096", "4K", "4096x4096"),
            ("2048", "2K", "2048x2048"),
            ("1024", "1K", "1024x1024"),
            ("512", "512", "512x512"),
        ],
        default="1024"
    )
    
    mesh_export_lod3_texture_size: EnumProperty(
        name="LOD3 Texture Size",
        description="Maximum texture size for LOD3",
        items=[
            ("2048", "2K", "2048x2048"),
            ("1024", "1K", "1024x1024"),
            ("512", "512", "512x512"),
            ("256", "256", "256x256"),
        ],
        default="512"
    )
    
    mesh_export_lod4_texture_size: EnumProperty(
        name="LOD4 Texture Size",
        description="Maximum texture size for LOD4",
        items=[
            ("1024", "1K", "1024x1024"),
            ("512", "512", "512x512"),
            ("256", "256", "256x256"),
            ("128", "128", "128x128"),
        ],
        default="256"
    )
    
    # Normal map handling
    mesh_export_preserve_normal_maps: BoolProperty(
        name="Preserve Normal Map Quality",
        description="Keep normal maps at one LOD level higher resolution",
        default=True
    )
    
    # Texture embedding property
    mesh_export_embed_textures: BoolProperty(
        name="Embed Textures",
        description="Embed textures in the exported file (increases file size)",
        default=False
    )
    

    # LOD ratio properties
    mesh_export_lod_ratio_01: FloatProperty(
        name="LOD1 Ratio", 
        description="Decimate factor for LOD 1",
        default=0.75, min=0.0, max=1.0, subtype="FACTOR"
    )
    mesh_export_lod_ratio_02: FloatProperty(
        name="LOD2 Ratio", 
        description="Decimate factor for LOD 2",
        default=0.50, min=0.0, max=1.0, subtype="FACTOR"
    )
    mesh_export_lod_ratio_03: FloatProperty(
        name="LOD3 Ratio", 
        description="Decimate factor for LOD 3",
        default=0.25, min=0.0, max=1.0, subtype="FACTOR"
    )
    mesh_export_lod_ratio_04: FloatProperty(
        name="LOD4 Ratio", 
        description="Decimate factor for LOD 4",
        default=0.10, min=0.0, max=1.0, subtype="FACTOR"
    )


def register_properties():
    """Register the property group and create the Scene property"""
    try:
        bpy.utils.register_class(MeshExporterSettings)
        bpy.types.Scene.mesh_exporter = PointerProperty(
            type=MeshExporterSettings)
        # Verification
        test = bpy.types.Scene.bl_rna.properties.get("mesh_exporter")
        if test:
            print(f"Successfully registered mesh_exporter: {test}")
        else:
            print("Failed to register mesh_exporter property")
    except Exception as e:
        print(f"Error registering properties: {e}")


def unregister_properties():
    """Unregister the property group and remove the Scene property"""
    if hasattr(bpy.types.Scene, "mesh_exporter"):
        delattr(bpy.types.Scene, "mesh_exporter")
    bpy.utils.unregister_class(MeshExporterSettings)
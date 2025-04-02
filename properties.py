import bpy
from bpy.props import StringProperty, EnumProperty, FloatProperty, IntProperty, BoolProperty

def register_properties():
    bpy.types.Scene.mesh_export_path = StringProperty(
        name="Export Path",
        description="Path to export meshes",
        default="//exported_meshes/",
        subtype="DIR_PATH"
    )
    
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
    
    bpy.types.Scene.mesh_export_scale = FloatProperty(
        name="Scale",
        description="Scale factor for exported meshes",
        default=1.0,
        min=0.001,
        max=1000.0,
        soft_min=0.01,
        soft_max=100.0
    )
    
    bpy.types.Scene.mesh_export_axis_simple = EnumProperty(
        name="Coord Sys",
        description="Coordinate system for exported meshes",
        items=[
            ("Blender", "Blender (Z-up, Y-forward)", ""),
            ("Godot", "Godot (Y-up, Z-forward)", ""),
            ("Unity", "Unity (Y-up, Z-forward)", ""),
            ("Unreal", "Unreal (Z-up, X-forward)", ""),
        ],
        default="Unreal"
    )

    bpy.types.Scene.mesh_export_zero_location = BoolProperty(
        name="Zero Location",
        description="Zero location of the object before export",
        default=True
    )

    bpy.types.Scene.mesh_export_triangulate = BoolProperty(
        name="Triangulate Faces",
        description="Convert all faces to triangles",
        default=True
    )
    
    bpy.types.Scene.mesh_export_triangulate_method = EnumProperty(
        name="Method",
        description="Method used for triangulating quads",
        items=[
            ("BEAUTY", "Beauty", "Triangulate with the best-looking result"),
            ("FIXED", "Fixed", "Split the quad from the first to third vertices"),
            ("FIXED_ALTERNATE", "Fixed Alternate", "Split the quad from the second to fourth vertices"),
            ("SHORTEST_DIAGONAL", "Shortest Diagonal", "Split the quad along the shortest diagonal")
        ],
        default="BEAUTY"
    )
    
    bpy.types.Scene.mesh_export_keep_normals = BoolProperty(
        name="Keep Normals",
        description="Preserve normal vectors during triangulation",
        default=True
    )

    bpy.types.Scene.mesh_export_prefix = StringProperty(
        name="Prefix",
        description="Prefix for exported file names",
    )

    bpy.types.Scene.mesh_export_suffix = StringProperty(
        name="Suffix",
        description="Suffix for exported file names",
    )
    
    bpy.types.Scene.mesh_export_lod = IntProperty(
        name="Additional LODs",
        description="Generate LODs for the exported meshes, these are in addtion to the base mesh",
        default=0,
        min=0,
        max=3
    )

    bpy.types.Scene.mesh_export_lod_01 = FloatProperty(
        name="LOD 01 Ratio",
        description="Decimate factor for LOD 01, lower values mean more decimation",
        default=0.5000,
        min=0.0000,
        max=1.0000,
        subtype="FACTOR"
    )

    bpy.types.Scene.mesh_export_lod_02 = FloatProperty(
        name="LOD 02 Ratio",
        description="Decimate factor for LOD 02, lower values mean more decimation",
        default=0.2500,
        min=0.0000,
        max=1.0000,
        subtype="FACTOR"
    )

    bpy.types.Scene.mesh_export_lod_03 = FloatProperty(
        name="LOD 03 Ratio",
        description="Decimate factor for LOD 03, lower values mean more decimation",
        default=0.1000,
        min=0.0000,
        max=1.0000,
        subtype="FACTOR"
    )

    bpy.types.Scene.mesh_export_in_progress = bpy.props.BoolProperty(
        name="Export in Progress",
        description="Indicates an export is currently running",
        default=False
    )

    bpy.types.Scene.mesh_export_current_object = bpy.props.StringProperty(
        name="Current Object",
        description="Name of the object currently being exported",
        default=""
    )

    bpy.types.Scene.mesh_export_progress = bpy.props.IntProperty(
        name="Export Progress",
        description="Current export progress",
        default=0,
        min=0
    )

    bpy.types.Scene.mesh_export_total = bpy.props.IntProperty(
        name="Export Total",
        description="Total objects to export",
        default=0,
        min=0
    )

def unregister_properties():
    del bpy.types.Scene.mesh_export_path
    del bpy.types.Scene.mesh_export_format
    del bpy.types.Scene.mesh_export_scale
    del bpy.types.Scene.mesh_export_axis_simple
    del bpy.types.Scene.mesh_export_zero_location
    del bpy.types.Scene.mesh_export_prefix
    del bpy.types.Scene.mesh_export_suffix
    del bpy.types.Scene.mesh_export_triangulate
    del bpy.types.Scene.mesh_export_triangulate_method
    del bpy.types.Scene.mesh_export_keep_normals
    del bpy.types.Scene.mesh_export_lod
    del bpy.types.Scene.mesh_export_lod_01
    del bpy.types.Scene.mesh_export_lod_02
    del bpy.types.Scene.mesh_export_lod_03
    del bpy.types.Scene.mesh_export_in_progress
    del bpy.types.Scene.mesh_export_current_object
    del bpy.types.Scene.mesh_export_progress
    del bpy.types.Scene.mesh_export_total

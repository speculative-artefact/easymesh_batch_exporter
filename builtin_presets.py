# builtin_presets.py
"""
Built-in factory presets for common game engines.

This module defines default preset configurations optimised for Godot, Unity,
and Unreal Engine, plus a generic custom template.
"""

# Built-in preset definitions
# Each preset includes metadata and complete settings configuration
BUILTIN_PRESETS = {
    "Godot": {
        "metadata": {
            "description": "Optimised for Godot 4.x (Y-up, Z-forward, meters, snake_case)",
            "icon": "COMMUNITY",  # Blender icon identifier
            "is_builtin": True,
        },
        "settings": {
            # Export format
            "mesh_export_format": "GLTF",
            "mesh_export_gltf_type": "GLB",
            "mesh_export_gltf_materials": "EXPORT",
            "mesh_export_use_draco_compression": False,

            # Coordinate system (Godot uses Y-up, Z-forward)
            "mesh_export_coord_up": "Y",
            "mesh_export_coord_forward": "Z",

            # Scale and units
            "mesh_export_scale": 1.0,
            "mesh_export_units": "METERS",

            # Transform
            "mesh_export_zero_location": True,
            "mesh_export_smoothing": "FACE",

            # Triangulation
            "mesh_export_tri": True,
            "mesh_export_tri_method": "BEAUTY",
            "mesh_export_keep_normals": True,

            # Modifiers
            "mesh_export_apply_modifiers": "VISIBLE",

            # Naming (Godot uses snake_case)
            "mesh_export_prefix": "",
            "mesh_export_suffix": "",
            "mesh_export_naming_convention": "GODOT",

            # Export indicators
            "mesh_export_show_indicators": True,

            # LOD settings
            "mesh_export_lod": False,
            "mesh_export_lod_count": 4,
            "mesh_export_lod_symmetry": False,
            "mesh_export_lod_symmetry_axis": "X",
            "mesh_export_lod_type": "COLLAPSE",
            "mesh_export_lod_hierarchy": True,

            # Texture settings
            "mesh_export_resize_textures": True,
            "mesh_export_texture_quality": 85,
            "mesh_export_lod1_texture_size": "2048",
            "mesh_export_lod2_texture_size": "1024",
            "mesh_export_lod3_texture_size": "512",
            "mesh_export_lod4_texture_size": "256",
            "mesh_export_preserve_normal_maps": True,
            "mesh_export_embed_textures": True,

            # LOD ratios
            "mesh_export_lod_ratio_01": 0.75,
            "mesh_export_lod_ratio_02": 0.50,
            "mesh_export_lod_ratio_03": 0.25,
            "mesh_export_lod_ratio_04": 0.10,
        }
    },

    "Unity": {
        "metadata": {
            "description": "Optimised for Unity (Y-up, -Z-forward, meters, Capitalised_Words)",
            "icon": "CUBE",  # Blender icon identifier
            "is_builtin": True,
        },
        "settings": {
            # Export format (FBX is standard for Unity)
            "mesh_export_format": "FBX",
            "mesh_export_gltf_type": "GLB",
            "mesh_export_gltf_materials": "EXPORT",
            "mesh_export_use_draco_compression": False,

            # Coordinate system (Unity uses Y-up, -Z-forward)
            "mesh_export_coord_up": "Y",
            "mesh_export_coord_forward": "-Z",

            # Scale and units
            "mesh_export_scale": 1.0,
            "mesh_export_units": "METERS",

            # Transform
            "mesh_export_zero_location": True,
            "mesh_export_smoothing": "FACE",

            # Triangulation
            "mesh_export_tri": True,
            "mesh_export_tri_method": "BEAUTY",
            "mesh_export_keep_normals": True,

            # Modifiers
            "mesh_export_apply_modifiers": "VISIBLE",

            # Naming (Unity uses Capitalised_Words)
            "mesh_export_prefix": "",
            "mesh_export_suffix": "",
            "mesh_export_naming_convention": "UNITY",

            # Export indicators
            "mesh_export_show_indicators": True,

            # LOD settings
            "mesh_export_lod": False,
            "mesh_export_lod_count": 4,
            "mesh_export_lod_symmetry": False,
            "mesh_export_lod_symmetry_axis": "X",
            "mesh_export_lod_type": "COLLAPSE",
            "mesh_export_lod_hierarchy": True,

            # Texture settings
            "mesh_export_resize_textures": True,
            "mesh_export_texture_quality": 85,
            "mesh_export_lod1_texture_size": "2048",
            "mesh_export_lod2_texture_size": "1024",
            "mesh_export_lod3_texture_size": "512",
            "mesh_export_lod4_texture_size": "256",
            "mesh_export_preserve_normal_maps": True,
            "mesh_export_embed_textures": True,

            # LOD ratios
            "mesh_export_lod_ratio_01": 0.75,
            "mesh_export_lod_ratio_02": 0.50,
            "mesh_export_lod_ratio_03": 0.25,
            "mesh_export_lod_ratio_04": 0.10,
        }
    },

    "Unreal": {
        "metadata": {
            "description": "Optimised for Unreal Engine (Z-up, X-forward, centimeters, PascalCase)",
            "icon": "OUTLINER_OB_ARMATURE",  # Blender icon identifier
            "is_builtin": True,
        },
        "settings": {
            # Export format (FBX is standard for Unreal)
            "mesh_export_format": "FBX",
            "mesh_export_gltf_type": "GLB",
            "mesh_export_gltf_materials": "EXPORT",
            "mesh_export_use_draco_compression": False,

            # Coordinate system (Unreal uses Z-up, X-forward)
            "mesh_export_coord_up": "Z",
            "mesh_export_coord_forward": "X",

            # Scale and units (Unreal uses centimeters)
            "mesh_export_scale": 1.0,
            "mesh_export_units": "CENTIMETERS",

            # Transform
            "mesh_export_zero_location": True,
            "mesh_export_smoothing": "FACE",

            # Triangulation
            "mesh_export_tri": True,
            "mesh_export_tri_method": "BEAUTY",
            "mesh_export_keep_normals": True,

            # Modifiers
            "mesh_export_apply_modifiers": "VISIBLE",

            # Naming (Unreal uses PascalCase)
            "mesh_export_prefix": "",
            "mesh_export_suffix": "",
            "mesh_export_naming_convention": "UNREAL",

            # Export indicators
            "mesh_export_show_indicators": True,

            # LOD settings
            "mesh_export_lod": False,
            "mesh_export_lod_count": 4,
            "mesh_export_lod_symmetry": False,
            "mesh_export_lod_symmetry_axis": "X",
            "mesh_export_lod_type": "COLLAPSE",
            "mesh_export_lod_hierarchy": True,

            # Texture settings
            "mesh_export_resize_textures": True,
            "mesh_export_texture_quality": 85,
            "mesh_export_lod1_texture_size": "2048",
            "mesh_export_lod2_texture_size": "1024",
            "mesh_export_lod3_texture_size": "512",
            "mesh_export_lod4_texture_size": "256",
            "mesh_export_preserve_normal_maps": True,
            "mesh_export_embed_textures": True,

            # LOD ratios
            "mesh_export_lod_ratio_01": 0.75,
            "mesh_export_lod_ratio_02": 0.50,
            "mesh_export_lod_ratio_03": 0.25,
            "mesh_export_lod_ratio_04": 0.10,
        }
    },
}


def get_builtin_preset_names():
    """Get list of built-in preset names.

    Returns:
        List of built-in preset names in display order

    Example:
        >>> get_builtin_preset_names()
        ['Godot', 'Unity', 'Unreal', 'Custom 01']
    """
    return list(BUILTIN_PRESETS.keys())


def is_builtin_preset(preset_name: str) -> bool:
    """Check if a preset name is a built-in preset.

    Args:
        preset_name: Name of the preset to check

    Returns:
        True if preset is built-in, False otherwise

    Example:
        >>> is_builtin_preset("Godot")
        True
        >>> is_builtin_preset("My Custom Preset")
        False
    """
    return preset_name in BUILTIN_PRESETS


def get_builtin_preset_data(preset_name: str) -> dict:
    """Get the complete data for a built-in preset.

    Args:
        preset_name: Name of the built-in preset

    Returns:
        Dictionary containing metadata and settings

    Raises:
        KeyError: If preset name is not a built-in

    Example:
        >>> data = get_builtin_preset_data("Godot")
        >>> data['metadata']['description']
        'Optimised for Godot 4.x (Y-up, Z-forward, meters, snake_case)'
    """
    return BUILTIN_PRESETS[preset_name]


def get_builtin_preset_icon(preset_name: str) -> str:
    """Get the icon identifier for a built-in preset.

    Args:
        preset_name: Name of the built-in preset

    Returns:
        Blender icon identifier string

    Example:
        >>> get_builtin_preset_icon("Godot")
        'COMMUNITY'
    """
    if preset_name in BUILTIN_PRESETS:
        return BUILTIN_PRESETS[preset_name]['metadata']['icon']
    return 'FILE_3D'  # Default icon for unknown presets


def get_builtin_preset_description(preset_name: str) -> str:
    """Get the description for a built-in preset.

    Args:
        preset_name: Name of the built-in preset

    Returns:
        Description string

    Example:
        >>> get_builtin_preset_description("Unity")
        'Optimised for Unity (Y-up, -Z-forward, meters, Capitalised_Words)'
    """
    if preset_name in BUILTIN_PRESETS:
        return BUILTIN_PRESETS[preset_name]['metadata']['description']
    return ""

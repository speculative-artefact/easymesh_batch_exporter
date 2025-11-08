# panels.py
""" 
EasyMesh Batch Exporter UI Panels
This module contains the UI panels for the EasyMesh Batch Exporter add-on. 
It includes the main exporter panel, LOD settings, and recent exports
"""

import time
import logging
from bpy.types import Panel
from . import export_indicators

# --- Setup Logger ---
logger = logging.getLogger(__name__)
# Clear any existing handlers to prevent accumulation on addon reload
if logger.handlers:
    logger.handlers.clear()
handler = logging.StreamHandler()
formatter = logging.Formatter("%(name)s:%(levelname)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)  # Default level
# Prevent propagation to avoid duplicate logs
logger.propagate = False

# Main UI Panel
class MESH_PT_exporter_panel(Panel):
    bl_label = "EasyMesh Batch Exporter"
    bl_idname = "MESH_PT_exporter_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Exporter" # Match bl_info location

    # Helper functions
    def format_has_scale(self, format):
        """Check if the format is compatible with scale export setting"""
        return format in {"FBX", "OBJ", "STL"}

    def format_has_coordinates(self, format):
        """Check if the format is compatible with coordinate export settings"""
        return format in {"FBX", "OBJ", "USD", "STL"}
    
    def format_has_smoothing(self, format):
        """Check if the format is compatible with smoothing export settings"""
        return format in {"FBX"}


    def draw(self, context):
        layout = self.layout

        # --- Debugging Start ---
        # logger.info("--- Drawing MESH_PT_exporter_panel ---")
        if not hasattr(context.scene, "mesh_exporter"):
            logger.error("context.scene has no 'mesh_exporter' attribute!")
            layout.label(text="Error: Property group not registered?")
            return # Stop drawing if the group isn't there
        
        settings = context.scene.mesh_exporter

        if settings is None:
            logger.error("context.scene.mesh_exporter is None!")
            layout.label(text="Error: Property group is None?")
            return # Stop drawing if the group is None
        
        # logger.info(f"Settings object: {settings}")
        # try:
            # Try accessing a property directly
            # path_value = settings.mesh_export_path
            # logger.info(f"Value of mesh_export_path: {path_value}")
        # except AttributeError:
        #     logger.error("Could not access settings.mesh_export_path!")
        # --- Debugging End ---

        layout.use_property_split = True
        layout.use_property_decorate = False

        # Export path settings
        layout.prop(settings, "mesh_export_path")
        layout.prop(settings, "mesh_export_format")

        # Format-specific settings
        if settings.mesh_export_format == "GLTF":
            # GLTF-specific settings
            col = layout.column(heading="GLTF Type", align=True)
            row = col.row(align=True)
            row.prop(settings, "mesh_export_gltf_type", expand=True)

            col = layout.column(heading="Materials", align=True)
            row = col.row(align=True)
            row.prop(settings, "mesh_export_gltf_materials")
            
            col = layout.column(heading="Compression", align=True)
            col.prop(settings, "mesh_export_use_draco_compression")

        # Coordinate system settings
        if self.format_has_coordinates(settings.mesh_export_format):
            col = layout.column(heading="Coordinate system", align=True)
            row = col.row(align=True)
            row.prop(settings, "mesh_export_coord_up", expand=True)
            row = col.row(align=True)
            row.prop(settings, "mesh_export_coord_forward", expand=True)

        # Scale settings
        if self.format_has_scale(settings.mesh_export_format):
            col = layout.column(heading="Scale", align=True)
            col.prop(settings, "mesh_export_scale")

        # Units settings
        if self.format_has_scale(settings.mesh_export_format):
            col = layout.column(heading="Units", align=True)
            row = col.row(align=True)
            row.prop(settings, "mesh_export_units", expand=True)

        # Smoothing settings
        if self.format_has_smoothing(settings.mesh_export_format):
            # Only show if the format supports smoothing
            col = layout.column(heading="Smoothing", align=True)
            row = col.row(align=True)
            row.prop(settings, "mesh_export_smoothing", expand=True)

        # Zero location settings
        col = layout.column(heading="Transform", align=True)
        col.prop(settings, "mesh_export_zero_location")

        # Modifier application settings
        col = layout.column(heading="Modifier Mode", align=True)
        row = col.row(align=True)
        row.prop(settings, "mesh_export_apply_modifiers", expand=True)

        # Triangulate settings
        col = layout.column(heading="Triangulate", align=True)
        row = col.row(align=True)
        row.prop(settings, "mesh_export_tri", text="")
        sub = row.row(align=True)
        sub.enabled = settings.mesh_export_tri # Enable/disable sub-option
        sub.prop(settings, "mesh_export_tri_method", text="")
        row = col.row(align=True)
        row.enabled = settings.mesh_export_tri # Enable/disable sub-option
        row.prop(settings, "mesh_export_keep_normals")

        # Rename file settings
        col = layout.column(heading="Rename file", align=True)
        col.prop(settings, "mesh_export_prefix")
        col.prop(settings, "mesh_export_suffix")
        col.prop(settings, "mesh_export_naming_convention", text="Convention")

        # Texture embedding option (for formats that support it)
        if settings.mesh_export_format in {"FBX", "USD"}:
            col = layout.column(heading="Textures", align=True)
            col.prop(settings, "mesh_export_embed_textures")
        # Show format-specific texture info for GLTF
        elif settings.mesh_export_format == "GLTF":
            col = layout.column(heading="Textures", align=True)
            if settings.mesh_export_gltf_type == "GLTF_SEPARATE":
                col.label(text="JSON format exports textures separately", icon='INFO')
            elif settings.mesh_export_gltf_type == "GLB":
                col.label(text="GLB format always embeds textures", icon='INFO')

        layout.separator()

        # Export Button 
        exportable_objects = [obj for obj in context.selected_objects if obj.type in ["MESH", "CURVE", "META"]]
        exportable_count = len(exportable_objects)
        
        # Check if all selected objects are the same type
        unique_types = set(obj.type for obj in exportable_objects)
        
        # Export button
        row = layout.row()
        # Generate the button text based on object types
        if exportable_count == 0:
            button_text = "Export Objects"
        elif len(unique_types) == 1:
            # All objects are the same type
            obj_type = list(unique_types)[0]
            if obj_type == "MESH":
                button_text = f"Export Meshes ({exportable_count})"
            elif obj_type == "CURVE":
                button_text = f"Export Curves ({exportable_count})"
            elif obj_type == "META":
                button_text = f"Export Metaballs ({exportable_count})"
        else:
            # Mixed types
            button_text = f"Export Objects ({exportable_count})"
        
        # Pass the generated text to the "text" parameter
        row.operator("mesh.batch_export", text=button_text, icon="EXPORT")


# LOD Panel
class MESH_PT_exporter_panel_lod(Panel):
    bl_label = "Quick LODs"
    bl_idname = "MESH_PT_exporter_panel_lod"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI" 
    bl_category = "Exporter" 
    bl_parent_id = "MESH_PT_exporter_panel" 
    bl_options = {"DEFAULT_CLOSED"} # Optional: Start closed

    @classmethod
    def poll(cls, context):
        # Show only if the main panel exists and path is set
        settings = context.scene.mesh_exporter
        # Check if the path property itself exists and is not None/empty
        return (settings 
                and settings.mesh_export_path 
                is not None 
                and settings.mesh_export_path != "")

    def draw_header(self, context):
        layout = self.layout
        settings = context.scene.mesh_exporter
        layout.prop(settings, "mesh_export_lod", text="") # Checkbox in header

    def draw(self, context):
        layout = self.layout
        settings = context.scene.mesh_exporter

        layout.use_property_split = True
        layout.use_property_decorate = False

        # Enable/disable based on the header checkbox
        layout.enabled = settings.mesh_export_lod

        # Show LOD hierarchy option only for FBX format
        if settings.mesh_export_format == "FBX":
            col = layout.column(heading="LOD Hierarchy", align=True)
            col.prop(settings, "mesh_export_lod_hierarchy")

        col = layout.column(align=True)
        col.prop(settings, "mesh_export_lod_count")
        # Hide the decimate type bc I'm not sure if it's needed yet
        # col.prop(settings, "mesh_export_lod_type")

        # Symmetry
        col = layout.column(heading="Symmetry", align=True)
        row = col.row(align=True)
        # Add the symmetry checkbox to the row
        row.prop(settings, "mesh_export_lod_symmetry", text="")
        # Create a sub-row for the axis enum that can be disabled
        sub = row.row(align=True)
        # Disable the sub-row (and its contents) if symmetry is off
        sub.enabled = settings.mesh_export_lod_symmetry
        # Add the axis enum property to the sub-row
        sub.prop(settings, "mesh_export_lod_symmetry_axis", expand=True)
        
        col = layout.column(heading="Textures", align=True)
        
        # Texture resizing option
        row = col.row(align=True)
        row.prop(settings, "mesh_export_resize_textures", text="Resize for LODs")
        
        # Texture compression quality
        row = col.row(align=True)
        row.prop(settings, "mesh_export_texture_quality", text="Compression")
        row.enabled = settings.mesh_export_resize_textures # Enable/disable sub-option

        # Normal map preservation
        row = col.row(align=True)
        row.prop(settings, "mesh_export_preserve_normal_maps")
        row.enabled = settings.mesh_export_resize_textures # Enable/disable sub-option

        # LOD decimation ratios
        box = layout.box()
        col = box.column(align=True)

        col.label(text="LOD Decimation Ratios:")
        row = col.row(align=True)
        row.prop(settings, "mesh_export_lod_ratio_01", text="LOD1")
        row = col.row(align=True)
        row.prop(settings, "mesh_export_lod_ratio_02", text="LOD2")
        if settings.mesh_export_lod_count < 2:
            row.enabled = False # Disable if LOD2 not used
        row = col.row(align=True)
        row.prop(settings, "mesh_export_lod_ratio_03", text="LOD3")
        if settings.mesh_export_lod_count < 3:
            row.enabled = False # Disable if LOD3 not used
        row = col.row(align=True)
        row.prop(settings, "mesh_export_lod_ratio_04", text="LOD4")
        if settings.mesh_export_lod_count < 4:
            row.enabled = False # Disable if LOD4 not used
        
        # Show texture quality and LOD size settings if resizing is enabled
        if settings.mesh_export_resize_textures:
            box = layout.box()
            col = box.column(align=True)
            
            # LOD texture sizes
            col.label(text="LOD Texture Sizes:")
            row = col.row(align=True)
            row.prop(settings, "mesh_export_lod1_texture_size", text="LOD1")
            row = col.row(align=True)
            row.prop(settings, "mesh_export_lod2_texture_size", text="LOD2")
            if settings.mesh_export_lod_count < 2:
                row.enabled = False # Disable if LOD2 not used
            row = col.row(align=True)
            row.prop(settings, "mesh_export_lod3_texture_size", text="LOD3")
            if settings.mesh_export_lod_count < 3:
                row.enabled = False # Disable if LOD3 not used
            row = col.row(align=True)
            row.prop(settings, "mesh_export_lod4_texture_size", text="LOD4")
            if settings.mesh_export_lod_count < 4:
                row.enabled = False # Disable if LOD4 not used

# Recent Exports Panel
class MESH_EXPORT_PT_recent_exports(Panel):
    bl_label = "Recent Exports"
    bl_idname = "MESH_EXPORT_PT_recent_exports"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Exporter"
    bl_parent_id = "MESH_PT_exporter_panel"
    bl_options = {"DEFAULT_CLOSED"} # Optional: Start closed

    @classmethod
    def poll(cls, context):
        # Check if the indicator system is running and has data
        # Also check if indicators are enabled
        if not hasattr(export_indicators, "get_recently_exported_objects"):
            return False
            
        return True
    
    def draw_header(self, context):
        layout = self.layout
        settings = context.scene.mesh_exporter
        layout.prop(settings, "mesh_export_show_indicators", text="") # Checkbox in header

    def draw(self, context):
        layout = self.layout
        settings = context.scene.mesh_exporter
        
        # Only show content if indicators are enabled
        if not settings.mesh_export_show_indicators:
            layout.label(text="Export indicators disabled.")
            return

        try:
            # Use the function from the export_indicators module
            recently_exported = (
                export_indicators.get_recently_exported_objects()
            )
        except AttributeError:
            layout.label(text="Indicator system not fully loaded.")
            return

        if not recently_exported:
            layout.label(text="No recent mesh exports.")
            return

        # Keep as single combined list for now
        # Can separate into fresh/stale based on status if needed
        box = layout.box()
        col = box.column(align=True)

        max_items = 10 # Limit display length
        for i, (obj, export_time) in enumerate(recently_exported):
            if i >= max_items:
                row = col.row()
                row.label(text=f"... and "
                          f"{len(recently_exported) - max_items} more")
                break

            if not obj: 
                continue # Skip if object deleted

            row = col.row(align=True)
            icon = "HIDE_OFF" # Default icon

            # Button to select object
            # Get the operator instance
            op = row.operator(
                "object.select_by_name", 
                text="", 
                icon=icon
            )
            # Set the property on the returned operator instance
            op.object_name = obj.name 

            row.label(text=obj.name)

            # Time since export
            time_diff = time.time() - export_time
            if time_diff < 60:
                time_str = f"{int(time_diff)}s ago"
            elif time_diff < 3600:
                time_str = f"{int(time_diff/60)}m ago"
            else:
                time_str = f"{int(time_diff/3600)}h ago"
            row.label(text=time_str)

        # Clear Indicators button if indicators are present
        if hasattr(export_indicators, "MESH_OT_clear_all_indicators"):
            layout.operator(
                export_indicators.MESH_OT_clear_all_indicators.bl_idname, 
                icon="TRASH"
            )



# Texture Info Panel
class MESH_EXPORT_PT_texture_info(Panel):
    bl_label = "Texture Export Preview"
    bl_idname = "MESH_EXPORT_PT_texture_info"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Exporter"
    bl_parent_id = "MESH_PT_exporter_panel"
    bl_options = {"DEFAULT_CLOSED"} # Start closed
    
    @classmethod
    def poll(cls, context):
        # Only show if texture resizing and LODs are enabled
        settings = context.scene.mesh_exporter
        return (settings and 
                settings.mesh_export_resize_textures and 
                settings.mesh_export_lod and
                any(obj.type == "MESH" for obj in context.selected_objects))
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.mesh_exporter
        
        # Count unique textures in selected meshes
        texture_info = []  # List of (image, has_alpha) tuples
        
        for obj in context.selected_objects:
            if obj.type == "MESH" and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and mat.node_tree:
                        for node in mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                img = node.image
                                if not any(info[0] == img for info in texture_info):
                                    # Check if image has alpha
                                    has_alpha = False
                                    if hasattr(img, 'depth'):
                                        has_alpha = img.depth == 32  # RGBA
                                    elif hasattr(img, 'channels'):
                                        has_alpha = img.channels == 4
                                    texture_info.append((img, has_alpha))
        
        if not texture_info:
            layout.label(text="No textures found in selection.")
            return
        
        col = layout.column(align=True)
        col.label(text=f"Unique textures: {len(texture_info)}", icon='TEXTURE')
        
        # Calculate original size (uncompressed in memory)
        total_uncompressed = 0
        for img, has_alpha in texture_info:
            if hasattr(img, 'size'):
                pixel_count = img.size[0] * img.size[1]
                total_uncompressed += pixel_count * 4
        
        size_mb_uncompressed = total_uncompressed / (1024 * 1024)
        col.label(text=f"Uncompressed: ~{size_mb_uncompressed:.1f} MB")
        
        # Estimate compressed sizes for each LOD
        if settings.mesh_export_lod_count >= 1:
            col.separator()
            col.label(text="Estimated compressed sizes:")
            
            # Get compression quality
            jpeg_quality = settings.mesh_export_texture_quality / 100.0
            
            # JPEG compression ratios based on quality (empirical approximations)
            # At 85% quality, JPEG typically achieves 10:1 to 20:1 compression
            # Lower quality = higher compression
            jpeg_compression_ratio = 0.05 + (0.15 * (jpeg_quality ** 2))  # 5-20% of original
            
            # Calculate LOD sizes
            lod_sizes = [
                int(settings.mesh_export_lod1_texture_size),
                int(settings.mesh_export_lod2_texture_size),
                int(settings.mesh_export_lod3_texture_size),
                int(settings.mesh_export_lod4_texture_size)
            ]
            
            box = layout.box()
            col = box.column(align=True)
            
            for i in range(settings.mesh_export_lod_count):
                total_size_kb = 0
                
                for img, has_alpha in texture_info:
                    if hasattr(img, 'size'):
                        # Calculate resized dimensions
                        orig_w, orig_h = img.size
                        target_size = lod_sizes[i]
                        
                        # Calculate actual dimensions after resize (preserving aspect ratio)
                        if orig_w > orig_h:
                            new_w = min(orig_w, target_size)
                            new_h = int(new_w * (orig_h / orig_w))
                        else:
                            new_h = min(orig_h, target_size)
                            new_w = int(new_h * (orig_w / orig_h))
                        
                        # Calculate pixel count
                        pixel_count = new_w * new_h
                        
                        # Estimate compressed size
                        if has_alpha:
                            # PNG compression (typically 50-70% of uncompressed)
                            compressed_bytes = pixel_count * 4 * 0.6
                        else:
                            # JPEG compression
                            compressed_bytes = pixel_count * 3 * jpeg_compression_ratio
                        
                        total_size_kb += compressed_bytes / 1024
                
                # Display in KB or MB depending on size
                if total_size_kb < 1024:
                    col.label(text=f"LOD{i+1}: ~{total_size_kb:.0f} KB")
                else:
                    col.label(text=f"LOD{i+1}: ~{total_size_kb/1024:.1f} MB")
                
            # Add note about estimates
            col.separator()
            col.label(text=f"Based on {int(jpeg_quality * 100)}% compression", icon='INFO')


# Registration
classes = (
    MESH_PT_exporter_panel,
    MESH_PT_exporter_panel_lod,
    MESH_EXPORT_PT_texture_info,
    MESH_EXPORT_PT_recent_exports,
)

# register/unregister functions handled by __init__.py
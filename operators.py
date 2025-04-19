# operators.py
"""
Contains Blender operators for the Mesh Exporter add-on.
Handles batch export of selected mesh objects, including LOD generation,
texture compression, and cleanup of temporary objects.
"""

import bpy
import os
import time
import contextlib
import re
import math
import logging
from bpy.types import Operator
from bpy.props import StringProperty
from . import export_indicators

# --- Setup Logger ---
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(name)s:%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)  # Default level

# --- Constants ---
EXPORT_TIME_PROP = "mesh_export_timestamp"
EXPORT_STATUS_PROP = "mesh_export_status"


# --- Core Functions ---


@contextlib.contextmanager
def temp_selection_context(context, active_object=None, selected_objects=None):
    """
    Temporarily set the active object and selection using direct API.
    
    Args:
        context (bpy.context): The current Blender context.
        active_object (bpy.types.Object, optional): 
            The object to set as active.
        selected_objects (list, optional): List of objects to select.
    
    Returns:
        None
    """
    # Store original state
    original_active = context.view_layer.objects.active
    original_selected = [obj for obj in context.scene.objects 
                         if obj.select_get()]
    
    try:
        # Deselect all objects directly
        for obj in context.scene.objects:
            if obj.select_get():
                obj.select_set(False)
        
        # Select requested objects directly
        if selected_objects:
            if not isinstance(selected_objects, list):
                selected_objects = [selected_objects]
            
            for obj in selected_objects:
                if obj and obj.name in context.scene.objects:
                    try:
                        obj.select_set(True)
                    except ReferenceError:
                        logger.warning(f"Could not select '{obj.name}' "
                                       f"- object reference invalid.")
        
        # Set active object directly
        if active_object and active_object.name in context.scene.objects:
            context.view_layer.objects.active = active_object
        elif selected_objects:
            for obj in selected_objects:
                if obj and obj.name in context.scene.objects:
                    context.view_layer.objects.active = obj
                    break
        
        yield
    
    finally:
        # Restore original state directly
        for obj in context.scene.objects:
            obj.select_set(False)
            
        for obj in original_selected:
            if obj and obj.name in context.scene.objects:
                try:
                    obj.select_set(True)
                except ReferenceError:
                    pass
        
        if original_active and original_active.name in context.scene.objects:
            try:
                context.view_layer.objects.active = original_active
            except ReferenceError:
                pass


def create_export_copy(original_obj, context):
    """
    Creates a linked copy of the object and its data without mode switching.
    
    Args:
        original_obj (bpy.types.Object): The original object to copy.
        context (bpy.context): The current Blender context.
        
    Returns:
        bpy.types.Object: The copied object.
    """
    if not original_obj or original_obj.type != "MESH":
        raise ValueError("Invalid object provided for copying.")
        
    logger.info(f"Attempting to duplicate '{original_obj.name}' using operator...")
    
    # Use the context manager to handle selection and active object
    with temp_selection_context(context, 
                                active_object=original_obj, 
                                selected_objects=[original_obj]):
        try:
            # Duplicate the active object (linked)
            # more direct and conventional way to perform a non-interactive 
            # linked duplication than bpy.ops.object.duplicate(linked=True)
            bpy.ops.object.duplicate_move_linked(
                OBJECT_OT_duplicate={"linked":True, "mode":'TRANSLATION'}, 
                TRANSFORM_OT_translate={"value":(0, 0, 0)} # No actual move
            ) 
            
            # The new duplicate becomes the active object 
            # after the operator runs
            copy_obj = context.view_layer.objects.active
            logger.info(f"Successfully created duplicate "
                        f"'{copy_obj.name}' via operator.")
            
            # Make Mesh Data Single User
            if copy_obj and copy_obj.data and copy_obj.data.users > 1:
                logger.info(f"Making mesh data single user for "
                            f"'{copy_obj.name}'")
                copy_obj.data = copy_obj.data.copy()

            return copy_obj
            
        except Exception as e:
            logger.error(f"Error using duplicate_move_linked operator for "
                         f"'{original_obj.name}': {e}", exc_info=True)
            # Attempt cleanup if copy_obj was created but failed later
            copy_obj_ref = None
            try:
                copy_obj_ref = context.view_layer.objects.active 
                if copy_obj_ref and copy_obj_ref != original_obj:
                    logger.info(f"Attempting cleanup of partially created "
                                f"copy: {copy_obj_ref.name}")
                    bpy.data.objects.remove(copy_obj_ref, do_unlink=True)
            except Exception as cleanup_e:
                 logger.warning(f"Issue during cleanup after copy "
                                f"failure: {cleanup_e}")

            raise RuntimeError(
                f"Failed to create operator copy of {original_obj.name}: {e}"
            ) from e


def sanitise_filename(name):
    """
    Remove characters that are problematic in filenames.
    
    Args:
        name (str): The name to sanitise.
    
    Returns:
        str: The sanitised name.
    """
    # Replace invalid characters with underscores
    sanitised = re.sub(r'[\\/:*?"<>|.]', '_', name)
    return sanitised


def setup_export_object(obj, original_obj_name, scene_props, lod_level=None):
    """
    Renames object, applies prefix/suffix/LOD naming, zeros location.
    
    Args:
        obj (bpy.types.Object): The object to set up for export.
        original_obj_name (str): The original name of the object.
        scene_props (bpy.types.PropertyGroup): Scene properties for export.
        lod_level (int, optional): LOD level for naming. Defaults to None.
    
    Returns:
        tuple: The final name and base name of the object.
    """
    if not obj:
        return None, None
    try:
        # Sanitise the original object name
        original_obj_name = sanitise_filename(original_obj_name)
        base_name = (
            scene_props.mesh_export_prefix +
            original_obj_name +
            scene_props.mesh_export_suffix
        )
        # Truncate if name too long (conservatively 100 chars)
        max_base_length = 100
        if len(base_name) > max_base_length:
            truncated = base_name[:max_base_length-3] + "..."
            logger.warning(
                f"Name too long, truncating: {base_name} → {truncated}"
            )
            base_name = truncated
        final_name = (
            f"{base_name}_LOD{lod_level:02d}"
            if lod_level is not None
            else base_name
        )
        obj.name = final_name
        logger.info(f"Renamed to: {obj.name}")

        # Check if object's scale is already 1.0
        if obj.scale != (1.0, 1.0, 1.0):
            # Apply scale transform if not 1.0
            logger.info(f"Object scale is not 1.0: {obj.scale}, applying...")
            with bpy.context.temp_override(
                selected_editable_objects=[obj], 
                selected_objects=[obj], active_object=obj): 
                bpy.ops.object.transform_apply(location=False, 
                                            rotation=False, 
                                            scale=True)

        # Zero location if specified in scene properties
        if scene_props.mesh_export_zero_location:
            obj.location = (0.0, 0.0, 0.0)
            logger.info(f"Zeroed location for {obj.name}")

        # Calculate final scale factor
        final_scale_factor = scene_props.mesh_export_scale
        if scene_props.mesh_export_units == "CENTIMETERS":
            # Apply 100x scale for Meters (Blender default) 
            # to Centimeters (UE default)
            final_scale_factor *= 100.0 
            logger.info("Applying M to CM scale factor (x100)")

        # Set the object's scale
        if abs(final_scale_factor - 1.0) > 1e-6: # Check if scaling is needed
            obj.scale = (final_scale_factor, 
                         final_scale_factor, 
                         final_scale_factor)
            logger.info(f"Set object scale to {final_scale_factor:.2f}")
        else:
            logger.info(f"Final scale factor is 1.0. No scaling needed.")

        # Apply the calculated scale transform using temp_override
        with bpy.context.temp_override(
            selected_editable_objects=[obj], 
            selected_objects=[obj], active_object=obj): 
            bpy.ops.object.transform_apply(location=False, 
                                           rotation=True, 
                                           scale=True)
            logger.info(f"Applied final scale transform for {obj.name}")

        return obj.name, base_name
    except Exception as e:
        raise RuntimeError(
            f"Failed to setup (rename/zero) {obj.name}: {e}"
        ) from e


def apply_mesh_modifiers(obj):
    """
    Apply all VISIBLE modifiers on a mesh object.
    
    Args:
        obj (bpy.types.Object): The object whose modifiers to apply.
        
    Returns:
        None
    """
    if not obj or obj.type != "MESH":
        return
    logger.info(f"Applying base modifiers for {obj.name}...")
    current_mode = obj.mode
    if current_mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    override = bpy.context.copy()
    override["object"] = obj
    override["active_object"] = obj
    override["selected_objects"] = [obj]
    override["selected_editable_objects"] = [obj]
    applied_modifiers = []

    try:
        for modifier in obj.modifiers[:]:  # Iterate over a copy
            if modifier.show_viewport:
                mod_name = modifier.name
                logger.info(f"Applying modifier: {mod_name}")
                try:
                    with bpy.context.temp_override(**override):
                        bpy.ops.object.modifier_apply(modifier=mod_name)
                    applied_modifiers.append(mod_name)
                except (RuntimeError, ReferenceError) as e:
                    logger.warning(
                        f"Could not apply modifier '{mod_name}' "
                        f"on {obj.name}: {e}"
                    )
            else:
                logger.info(f"Skipping disabled modifier: {modifier.name}")
    finally:
        if obj.mode != current_mode:
            bpy.ops.object.mode_set(mode=current_mode)
    logger.info(
        f"Finished applying modifiers. Applied: {applied_modifiers}"
    )


def compress_textures(obj, ratio):
    """
    Compresses textures based on decimation ratio with no user input required.
    
    Args:
        obj:    The mesh object whose textures should be compressed
        ratio:  The decimation ratio 
                1.0 = full quality, 0.01 = heavy decimation
        
    Returns:
        List of modified image names for reporting
    """
    if not obj or obj.type != "MESH":
        return []
    
    logger.info(f"Compressing textures for {obj.name} "
                f"(decimation ratio: {ratio:.3f})...")
    
    # Get all materials on the object
    materials = obj.data.materials
    if not materials:
        logger.info(f"No materials found on {obj.name}, "
                    f"skipping texture compression")
        return []
    
    modified_images = []
    
    # First pass - collect all unique images and nodes using them
    image_nodes = {}  # {image: [nodes using this image]}
    for mat in materials:
        if not mat or not mat.node_tree:
            continue
            
        # Find all image texture nodes in the material
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                if node.image not in image_nodes:
                    image_nodes[node.image] = []
                image_nodes[node.image].append((mat, node))
    
    # Nothing to do if no images found
    if not image_nodes:
        logger.info(f"No texture images found on {obj.name}")
        return []
        
    # Calculate compression amount based on decimation ratio
    compression_factor = max(ratio**0.9, 0.05)  # Limit max compression to 1/20
    min_dimension = 64  # Minimum texture size
    
    # Process each image
    for orig_img, nodes_using_img in image_nodes.items():
        # Skip already compressed or size-zero images
        if (not orig_img.has_data 
            or orig_img.size[0] == 0 
            or orig_img.size[1] == 0):
            continue
            
        # Calculate new resolution
        orig_width, orig_height = orig_img.size
        is_power_of_2 = ((orig_width & (orig_width - 1) == 0) 
                         and (orig_height & (orig_height - 1) == 0))
        
        new_width = max(int(orig_width * compression_factor), min_dimension)
        new_height = max(int(orig_height * compression_factor), min_dimension)
        
        # Round to power of 2 if original was power of 2
        if is_power_of_2:
            new_width = 2 ** (new_width - 1).bit_length()
            new_height = 2 ** (new_height - 1).bit_length()
            
        # Skip if size hasn't changed
        if (new_width, new_height) == (orig_width, orig_height):
            continue
        
        # Create a copy of the original image
        copy_name = f"{orig_img.name}_LOD"
        
        # Check if copy already exists, reuse if it does
        copied_img = bpy.data.images.get(copy_name)
        if copied_img:
            # If dimensions don't match our target, recreate it
            if (copied_img.size[0] != new_width 
                or copied_img.size[1] != new_height):
                bpy.data.images.remove(copied_img)
                copied_img = None
        
        if not copied_img:
            # Create new image with proper dimensions
            copied_img = bpy.data.images.new(
                name=copy_name,
                width=new_width,
                height=new_height
            )
            
            # Copy pixel data from original and resize
            if orig_img.has_data and orig_img.pixels:
                try:
                    # Make a copy of the original at the lower resolution
                    # First match original size
                    copied_img.scale(orig_width, orig_height)  
                    # Copy pixels
                    copied_img.pixels = orig_img.pixels[:]     
                    # Then resize to target
                    copied_img.scale(new_width, new_height)    
                    
                    # Copy other relevant properties
                    copied_img.colourspace_settings.name = (
                        orig_img.colourspace_settings.name
                    )
                    if orig_img.filepath:
                        # For export reference
                        copied_img.filepath = orig_img.filepath  
                    
                except Exception as e:
                    logger.warning(f"Error copying pixels for "
                                   f"{orig_img.name}: {e}")
                    
            logger.info(f"Created compressed copy of '{orig_img.name}' "
                        f"at {new_width}x{new_height}")
        
        # Update material nodes to use the copied image
        for mat, node in nodes_using_img:
            node.image = copied_img
        
        modified_images.append(f"{orig_img.name} ({orig_width}x{orig_height} "
                               f"→ {new_width}x{new_height})")
        
        # Store original image reference on the object for restoration
        if "original_textures" not in obj:
            obj["original_textures"] = {}
        
        obj["original_textures"][copy_name] = orig_img.name
    
    return modified_images


def restore_original_textures(obj):
    """
    Restores original textures after exportby replacing 
    compressed copies with originals.
    
    Args:
        obj (bpy.types.Object): The object whose textures to restore.
    
    Returns:
        None
    """
    if not obj or obj.type != "MESH" or "original_textures" not in obj:
        return
    
    texture_map = obj.get("original_textures", {})
    if not texture_map:
        return
    
    logger.info(f"Restoring original textures for {obj.name}...")
    
    # Get all materials on the object
    materials = obj.data.materials
    if not materials:
        return
    
    # Find all image texture nodes and restore originals
    for mat in materials:
        if not mat or not mat.node_tree:
            continue
            
        for node in mat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                # Check if this is an LOD image that needs restoration
                if node.image.name in texture_map:
                    original_name = texture_map[node.image.name]
                    original_img = bpy.data.images.get(original_name)
                    
                    if original_img:
                        logger.info(f"Restoring {node.image.name} "
                                    f"→ {original_name}")
                        node.image = original_img
    
    # Clean up the mapping
    del obj["original_textures"]
    
    # Delete any unused LOD textures
    for img in bpy.data.images:
        if img.name.endswith("_LOD") and not img.users:
            bpy.data.images.remove(img)


def apply_decimate_modifier(obj, ratio, decimate_type, 
                            sym_axis="X", sym=False):
    """
    Adds, configures, and applies a Decimate modifier.
    
    Args:
        obj (bpy.types.Object): The object to apply the modifier to.
        ratio (float): The decimation ratio (0.0 to 1.0).
        decimate_type (str): The type of decimation to apply.
        sym_axis (str): The symmetry axis for decimation.
        sym (bool): Whether to apply symmetry.

    Returns:
        None
    """
    if not obj or obj.type != "MESH":
        return
    
    # Get initial poly count for logging
    initial_poly_count = len(obj.data.polygons)
    logger.info(
        f"Applying Decimate to mesh with {initial_poly_count} polygons "
        f"(Ratio: {ratio:.3f}, Type: {decimate_type})..."
    )

    current_mode = obj.mode
    if current_mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    # Compress textures based on ratio - no UI elements needed
    # compressed_textures = compress_textures(obj, ratio)
    # if compressed_textures:
    #     logger.info(f"Compressed {len(compressed_textures)} textures")

    # Create and apply decimate modifier
    mod_name = "TempDecimate"
    dec_mod = obj.modifiers.new(name=mod_name, type="DECIMATE")
    dec_mod.decimate_type = decimate_type.upper()

    # Right now it only supports COLLAPSE
    if dec_mod.decimate_type == "COLLAPSE":
        dec_mod.ratio = ratio
        # Set use_symmetry first
        dec_mod.use_symmetry = sym
        # Only set the axis if symmetry is enabled
        if sym:
            # Ensure axis is valid before setting
            axis_upper = sym_axis.upper()
            if axis_upper not in {'X', 'Y', 'Z'}:
                 logger.error(f"Invalid symmetry axis value received: "
                              f"{sym_axis}. Aborting modifier application.")
                 obj.modifiers.remove(dec_mod) # Clean up modifier
                 raise ValueError(f"Invalid symmetry axis: {sym_axis}")

            dec_mod.symmetry_axis = axis_upper
            logger.info(
                f"Using symmetry axis: {axis_upper}"
            )

    override = bpy.context.copy()
    override["object"] = obj
    override["active_object"] = obj
    override["selected_objects"] = [obj]
    override["selected_editable_objects"] = [obj]

    try:
        with bpy.context.temp_override(**override):
            bpy.ops.object.modifier_apply(modifier=mod_name)
        
        # Log final results
        final_poly_count = len(obj.data.polygons)
        actual_ratio = (final_poly_count / initial_poly_count 
                        if initial_poly_count > 0 else 0)
        logger.info(
            f"Decimation complete: {initial_poly_count} "
            f"→ {final_poly_count} polys "
            f"(target: {ratio:.3f}, actual: {actual_ratio:.3f})"
        )
        
        # if compressed_textures:
        #     logger.info(f"Texture compression details: "
        #                 f"{', '.join(compressed_textures)}")
            
    except Exception as e:
        logger.error(f"Failed to apply Decimate modifier: {e}")
        if mod_name in obj.modifiers:
            try:
                obj.modifiers.remove(dec_mod)
            except (ReferenceError, RuntimeError):
                 pass # Modifier already gone or object invalid
        raise RuntimeError(f"Failed to apply Decimate modifier: {e}") from e
    finally:
        if obj.mode != current_mode:
            bpy.ops.object.mode_set(mode=current_mode)


def triangulate_mesh(obj, method="BEAUTY", keep_normals=True):
    """
    Add and apply a triangulate modifier.
    
    Args:
        obj (bpy.types.Object): The object to triangulate.
        method (str): The triangulation method to use.
        keep_normals (bool): Whether to keep custom normals.
    
    Returns:
        None
    """
    if not obj or obj.type != "MESH":
        return
    logger.info(f"Triangulating {obj.name}...")
    current_mode = obj.mode
    if current_mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    mod_name = "TempTriangulate"
    tri_mod = obj.modifiers.new(name=mod_name, type="TRIANGULATE")
    tri_mod.quad_method = method
    tri_mod.keep_custom_normals = keep_normals

    override = bpy.context.copy()
    override["object"] = obj
    override["active_object"] = obj
    override["selected_objects"] = [obj]
    override["selected_editable_objects"] = [obj]

    try:
        with bpy.context.temp_override(**override):
            bpy.ops.object.modifier_apply(modifier=mod_name)
        logger.info("Successfully triangulated.")
    except Exception as e:
        logger.warning(
            f"Could not apply triangulation modifier on {obj.name}: {e}"
        )
    finally:
        if obj.mode != current_mode:
            bpy.ops.object.mode_set(mode=current_mode)


def export_object(obj, file_path, scene_props):
    """
    Exports a single object using scene properties.
    
    Args:
        obj (bpy.types.Object): The object to export.
        file_path (str): The file path for the export.
        scene_props (bpy.types.PropertyGroup): Scene properties for export.
    
    Returns:
        bool: True if export was successful, False otherwise.
    """
    fmt = scene_props.mesh_export_format
    success = False
    # base_file_path = os.path.splitext(file_path)[0] # Ensure no extension yet
    base_file_path = file_path
    export_filepath = f"{base_file_path}.{fmt.lower()}"

    temp_lod_lvl = obj.name.split("_")[-1]

    if temp_lod_lvl == "LOD01":
        export_quality = math.ceil(scene_props.mesh_export_lod_ratio_01 * 100)
        downscale_size = "2048"
    elif temp_lod_lvl == "LOD02":
        export_quality = math.ceil(scene_props.mesh_export_lod_ratio_02 * 100)
        downscale_size = "1024"
    elif temp_lod_lvl == "LOD03":
        export_quality = math.ceil(scene_props.mesh_export_lod_ratio_03 * 100)
        downscale_size = "512"
    elif temp_lod_lvl == "LOD04":
        export_quality = math.ceil(scene_props.mesh_export_lod_ratio_04 * 100)
        downscale_size = "256"
    else:
        export_quality = 100
        downscale_size = "KEEP"

    # logger.info(f"[[quality: {export_quality}]]")
    # logger.info(f"[[downscale: {downscale_size}]]")
    
    # logger.info(f"File path: {file_path}")
    logger.info(
        f"Exporting {os.path.basename(export_filepath)} ({fmt})..."
    )

    with temp_selection_context(bpy.context, active_object=obj,
                                selected_objects=[obj]):
        try:
            if fmt == "FBX":
                bpy.ops.export_scene.fbx(
                    filepath=export_filepath,
                    use_selection=True,
                    global_scale=1.0, # Scale applied setup_export_object
                    axis_forward=scene_props.mesh_export_coord_forward,
                    axis_up=scene_props.mesh_export_coord_up,
                    apply_unit_scale=False,
                    apply_scale_options="FBX_SCALE_ALL",
                    object_types={"MESH"},
                    path_mode="COPY",
                    embed_textures=True,
                    use_mesh_modifiers=False, # Handled by apply_mesh_modifiers
                    use_triangles=False,      # Handled by triangulate_mesh
                )
            elif fmt == "OBJ":
                bpy.ops.wm.obj_export(
                    filepath=export_filepath,
                    export_selected_objects=True,
                    global_scale=1.0, # Scale applied setup_export_object
                    forward_axis=scene_props.mesh_export_coord_forward,
                    up_axis=scene_props.mesh_export_coord_up,
                    export_materials=True,
                    path_mode="COPY",
                    apply_modifiers=False, # Handled by apply_mesh_modifiers
                    export_triangulated_mesh=False, # Handled triangulate_mesh
                )
            elif fmt == "GLTF":
                bpy.ops.export_scene.gltf(
                    filepath=export_filepath,
                    use_selection=True,
                    export_format="GLTF_SEPARATE", # or GLB
                    export_apply=False, # Transforms/Mods applied manually
                    export_attributes=True,
                    export_extras=True,
                    export_yup=(scene_props.mesh_export_coord_up == "Y"),
                    # Need to add a prop to track material quality
                    export_jpeg_quality=export_quality,
                    export_image_quality=export_quality,
                )
            elif fmt == "USD":
                bpy.ops.wm.usd_export(
                    filepath=export_filepath,
                    selected_objects_only=True,
                    export_global_forward_selection=(
                        scene_props.mesh_export_coord_forward),
                    export_global_up_selection=(
                        scene_props.mesh_export_coord_up),
                    export_meshes=True,
                    export_materials=True,
                    generate_preview_surface=False,
                    use_instancing=False,
                    evaluation_mode="RENDER",
                    triangulate_meshes=False, # Handled by triangulate_mesh
                    # Need to add a prop to track material quality
                    usdz_downscale_size=downscale_size,
                    export_textures=True,
                    export_textures_mode="NEW",
                    overwrite_textures=True,
                )
            elif fmt == "STL":
                bpy.ops.wm.stl_export(
                    filepath=export_filepath,
                    export_selected_objects=True,
                    global_scale=1.0, # Scale applied setup_export_object
                    forward_axis=scene_props.mesh_export_coord_forward,
                    up_axis=scene_props.mesh_export_coord_up,
                    apply_modifiers=False, # Handled by apply_mesh_modifiers
                )
            else:
                logger.error(f"Unsupported export format '{fmt}'")
                return False

            logger.info(
                f"Successfully exported {os.path.basename(export_filepath)}"
            )
            success = True
        except Exception as e:
            logger.error(
                f"Failed exporting {obj.name} as {fmt}: {e}", exc_info=True
            )
            success = False
    return success


def cleanup_object(obj, obj_name_for_log):
    """
    Removes the specified object, handling potential errors.
    
    Args:
        obj (bpy.types.Object): The object to clean up.
        obj_name_for_log (str): The name to log for the object.
    
    Returns:
        None
    """
    if not obj:
        return
    log_name = obj_name_for_log if obj_name_for_log else "unnamed object"
    logger.info(f"Attempting cleanup for: {log_name}")
    
    # First restore original textures if they were compressed
    # try:
    #     restore_original_textures(obj)
    # except Exception as tex_e:
    #     logger.warning(
    #       f"Error restoring original textures for {log_name}: {tex_e}"
    #     )
    
    # Then remove the object
    try:
        mesh_data = obj.data # Store reference before removing object
        num_users = mesh_data.users
        bpy.data.objects.remove(obj, do_unlink=True)
        logger.info(f"Cleaned up object: {log_name}")
        # If the mesh data had only this object as a user, remove it too
        if num_users == 1 and mesh_data:
             try:
                 bpy.data.meshes.remove(mesh_data)
                 logger.info(f"Cleaned up orphaned mesh data for: {log_name}")
             except (ReferenceError, Exception) as mesh_remove_e:
                 logger.warning(f"Issue removing mesh data for {log_name}: "
                                f"{mesh_remove_e}")

    except (ReferenceError, Exception) as remove_e:
        logger.warning(f"Issue during cleanup of {log_name}: {remove_e}")


# --- Operators ---

class MESH_OT_batch_export(Operator):
    """Exports selected mesh objects sequentially with status bar progress."""
    bl_idname = "mesh.batch_export"
    bl_label = "Export Selected Meshes"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        """Enable only if mesh objects are selected."""
        return any(obj.type == "MESH" for obj in context.selected_objects)

    def execute(self, context):
        """Runs the batch export process."""
        scene = context.scene
        scene_props = scene.mesh_exporter
        wm = context.window_manager
        start_time = time.time()

        objects_to_export = [
            obj for obj in context.selected_objects if obj.type == "MESH"
        ]
        total_objects = len(objects_to_export)

        if not objects_to_export:
            self.report({"WARNING"}, "No mesh objects selected.")
            logger.warning("Export cancelled: No mesh objects selected.")
            return {"CANCELLED"}

        # Validate export path
        export_base_path = bpy.path.abspath(scene_props.mesh_export_path)
        if not os.path.isdir(export_base_path):
            try:
                os.makedirs(export_base_path)
                logger.info(f"Created export directory: {export_base_path}")
            except Exception as e:
                err_msg = (
                    f"Export path invalid/couldn't be created: "
                    f"{export_base_path}. Error: {e}"
                )
                self.report({"ERROR"}, err_msg)
                logger.error(err_msg)
                return {"CANCELLED"}

        successful_exports = 0
        failed_exports = []
        overall_success = True

        logger.info(
            f"Starting batch export for {total_objects} "
            f"objects to {export_base_path}"
        )
        wm.progress_begin(0, total_objects)
        try:
            # --- Main Export Loop ---
            for index, original_obj in enumerate(objects_to_export):
                wm.progress_update(index + 1)
                logger.info(
                    f"Processing ({index + 1}/{total_objects}): "
                    f"{original_obj.name}"
                )
                object_processed_successfully = True

                try:
                    # --- Process One Original Object ---
                    if scene_props.mesh_export_lod:
                        # --- LOD Branch ---
                        logger.info(
                            f"Generating "
                            f"{scene_props.mesh_export_lod_count + 1} "
                            f"LOD levels..."
                        )
                        lod_ratios_prop = [
                            scene_props.mesh_export_lod_ratio_01,
                            scene_props.mesh_export_lod_ratio_02,
                            scene_props.mesh_export_lod_ratio_03,
                            scene_props.mesh_export_lod_ratio_04,
                        ]
                        ratios = (
                            [1.0] 
                            + lod_ratios_prop[
                                :scene_props.mesh_export_lod_count
                            ]
                        )

                        for lod_level, ratio in enumerate(ratios):
                            lod_obj = None
                            lod_obj_name = None
                            try:
                                logger.info(f"Preparing LOD{lod_level}...")
                                lod_obj = create_export_copy(
                                    original_obj, 
                                    context
                                )
                                (lod_obj_name, _) = setup_export_object(
                                    lod_obj, original_obj.name,
                                    scene_props, lod_level
                                )
                                apply_mesh_modifiers(lod_obj) # Base modifiers
                                if lod_level > 0:
                                    apply_decimate_modifier(
                                        lod_obj, ratio,
                                        scene_props.mesh_export_lod_type,
                                        scene_props.mesh_export_lod_symmetry_axis,
                                        scene_props.mesh_export_lod_symmetry,
                                    )
                                if scene_props.mesh_export_tri:
                                    # Trying to avoid long line
                                    method=scene_props.mesh_export_tri_method
                                    k_nrms=scene_props.mesh_export_keep_normals
                                    triangulate_mesh(lod_obj, method, k_nrms)

                                lod_file_path = os.path.join(export_base_path,
                                                             lod_obj_name)
                                if export_object(lod_obj, lod_file_path,
                                                 scene_props):
                                    successful_exports += 1
                                else:
                                    raise RuntimeError("Export func failed")

                            except Exception as lod_e:
                                object_processed_successfully = False
                                log_name = (
                                    lod_obj_name if lod_obj_name else
                                    f"{original_obj.name}_LOD{lod_level:02d}"
                                    )
                                logger.error(
                                    f"Failed processing {log_name}: {lod_e}"
                                )
                                failed_exports.append(
                                    f"{original_obj.name} (LOD{lod_level:02d})"
                                )
                            finally:
                                cleanup_object(lod_obj, lod_obj_name)
                        # --- End LOD Level Loop ---

                    else:
                        # --- Non-LOD Branch ---
                        export_obj = None
                        export_obj_name = None
                        try:
                            logger.info("Processing single export (no LODs)..")
                            export_obj = create_export_copy(
                                original_obj, 
                                context
                            )
                            (export_obj_name, base_name) = setup_export_object(
                                export_obj, original_obj.name, scene_props
                            )
                            apply_mesh_modifiers(export_obj)
                            if scene_props.mesh_export_tri:
                                triangulate_mesh(
                                    export_obj,
                                    scene_props.mesh_export_tri_method,
                                    scene_props.mesh_export_keep_normals
                                )

                            file_path = os.path.join(
                                export_base_path, base_name)
                            if export_object(
                                export_obj, file_path, scene_props):
                                successful_exports += 1
                            else:
                                object_processed_successfully = False
                                failed_exports.append(original_obj.name)

                        except Exception as e:
                            object_processed_successfully = False
                            log_name = (export_obj_name if export_obj_name else
                                        original_obj.name)
                            logger.error(f"Failed processing {log_name}: {e}")
                            failed_exports.append(
                                f"{original_obj.name} (Processing Error)"
                            )
                        finally:
                            cleanup_object(export_obj, export_obj_name)
                    # --- End Non-LOD Branch ---

                except Exception as outer_e:
                    logger.error(
                        f"Unexpected outer error during processing of "
                        f"{original_obj.name}: {outer_e}",
                        exc_info=True
                    )
                    object_processed_successfully = False
                    failed_exports.append(f"{original_obj.name} (Outer Error)")
                finally:
                    # Mark Original Object
                    if original_obj and object_processed_successfully:
                        export_indicators.mark_object_as_exported(original_obj)
                        logger.info(
                            f"Marked original {original_obj.name} as exported."
                        )
                    elif original_obj:
                        logger.info(
                            f"Skipped marking original {original_obj.name} "
                            f"due to errors."
                        )
                        overall_success = False
            # --- End Main Object Loop ---
        finally:
            wm.progress_end()

        # --- Final Report ---
        end_time = time.time()
        elapsed_time = end_time - start_time
        log_level = logging.INFO if overall_success else logging.WARNING
        message = (
            f"Export finished in {elapsed_time:.2f}s. "
            f"Exported {successful_exports} files."
        )
        if failed_exports:
            unique_fails = sorted(list(set(f.split(' (')[0]
                                            for f in failed_exports)))
            fail_summary = (
                f"Failed exports logged for: {len(unique_fails)} original "
                f"objects ({', '.join(unique_fails[:5])}"
                f"{'...' if len(unique_fails)>5 else ''}). Check console/log."
            )
            message += f" {fail_summary}"
            logger.warning(f"Failures occurred for: {', '.join(unique_fails)}")

        logger.log(log_level, message)
        report_type = {"INFO"} if overall_success else {"WARNING"}
        self.report(report_type, message)

        # --- Trigger redraw ---
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()

        return {"FINISHED"}


class OBJECT_OT_select_by_name(Operator):
    """Selects and focuses on the specified object."""
    bl_idname = "object.select_by_name"
    bl_label = "Select Object by Name"
    bl_description = "Selects and focuses on the specified object"
    bl_options = {"REGISTER", "INTERNAL"}

    object_name: StringProperty()

    def execute(self, context):
        """Executes the selection using direct API."""
        target_obj = bpy.data.objects.get(self.object_name)
        if not target_obj:
            logger.warning(f"Object '{self.object_name}' "
                           f"not found for selection.")
            return {"CANCELLED"}
        
        # Deselect all objects directly
        for obj in context.scene.objects:
            if obj.select_get():
                obj.select_set(False)
                
        # Select target and make it active
        target_obj.select_set(True)
        context.view_layer.objects.active = target_obj

        # No need to change modes just for selection
        
        return {"FINISHED"}


# --- Registration ---
classes = (
    MESH_OT_batch_export,
    OBJECT_OT_select_by_name,
)


def register():
    """Registers operator classes."""
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            logger.warning(f"Class {cls.__name__} already registered.")
            pass  # Already registered


def unregister():
    """Unregisters operator classes."""
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            logger.warning(f"Class {cls.__name__} already unregistered.")
            pass  # Already unregistered
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

# Large mesh thresholds
LARGE_MESH_THRESHOLD = 500000  # 500K polygons
VERY_LARGE_MESH_THRESHOLD = 1000000  # 1M polygons


# --- Memory Optimisation Functions ---

def optimise_for_large_mesh(obj):
    """
    Memory optimisation for large meshes.
    
    Args:
        obj (bpy.types.Object): The mesh object to optimise.
        
    Returns:
        bool: True if optimisation was applied, False otherwise.
    """
    if not obj or obj.type != "MESH" or not obj.data:
        return False
        
    poly_count = len(obj.data.polygons)
    if poly_count > LARGE_MESH_THRESHOLD:
        logger.info(f"Applying memory optimisation for large mesh: {poly_count} polygons")
        obj.data.update()
        import gc
        gc.collect()
        return True
    return False


@contextlib.contextmanager
def safe_large_mesh_operation(obj, operation_name):
    """
    Context manager for operations on large meshes with memory management.
    
    Args:
        obj (bpy.types.Object): The mesh object.
        operation_name (str): Name of the operation for logging.
    """
    poly_count = len(obj.data.polygons) if obj and obj.data else 0
    is_large = poly_count > LARGE_MESH_THRESHOLD
    
    if is_large:
        logger.info(f"Starting large mesh operation: {operation_name} on {poly_count:,} polygons")
        # Pre-operation cleanup
        obj.data.update()
        import gc
        gc.collect()
        
    try:
        yield
    finally:
        if is_large:
            # Post-operation cleanup
            obj.data.update()
            import gc
            gc.collect()
            logger.info(f"Completed large mesh operation: {operation_name}")


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
        
    logger.info(f"Attempting to duplicate '{original_obj.name}' "
                f"using operator...")
    
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
                
                # Optimise memory for large meshes after making single user
                optimise_for_large_mesh(copy_obj)

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
        
        # Remove any existing LOD suffix if re-processing the same object
        if "_LOD" in original_obj_name:
            original_obj_name = original_obj_name.split("_LOD")[0]
            
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
        scale_epsilon = 1e-6
        if (abs(obj.scale[0] - 1.0) > scale_epsilon or 
            abs(obj.scale[1] - 1.0) > scale_epsilon or 
            abs(obj.scale[2] - 1.0) > scale_epsilon):
            # Apply scale transform if not 1.0
            logger.info(f"Object scale is not 1.0: {obj.scale}, applying...")
            apply_transforms(obj, apply_scale=True)

        # Zero location if specified in scene properties
        if scene_props.mesh_export_zero_location:
            obj.location = (0.0, 0.0, 0.0)
            logger.info(f"Zeroed location for {obj.name}")

        # Calculate final scale factor
        if (scene_props.mesh_export_format != "GLTF" 
            or scene_props.mesh_export_format != "USD"):
            # For GLTF, we don't want to apply scale here
            final_scale_factor = scene_props.mesh_export_scale
            if scene_props.mesh_export_units == "CENTIMETERS":
                # Apply 100x scale for Meters (Blender default) 
                # to Centimeters (UE default)
                final_scale_factor *= 100.0 
                logger.info("Applying M to CM scale factor (x100)")

            # Set the object's scale
            if abs(final_scale_factor - 1.0) > 1e-6: # Check if scaling is need
                obj.scale = (final_scale_factor, 
                            final_scale_factor, 
                            final_scale_factor)
                logger.info(f"Set object scale to {final_scale_factor:.2f}")
            else:
                logger.info("Final scale factor is 1.0. No scaling needed.")

            # Apply the calculated scale and rotation transforms using the help
            # We always want to apply rotation and scale at the end here.
            apply_transforms(obj, apply_rotation=True, apply_scale=True)

        return obj.name, base_name
    except Exception as e:
        raise RuntimeError(
            f"Failed to setup (rename/zero) {obj.name}: {e}"
        ) from e
    

def apply_transforms(obj, apply_location=False, 
                     apply_rotation=False, apply_scale=False):
    """
    Applies specified transforms to the object.

    Args:
        obj (bpy.types.Object): The object to apply transforms to.
        apply_location (bool): Whether to apply location transforms.
        apply_rotation (bool): Whether to apply rotation transforms.
        apply_scale (bool): Whether to apply scale transforms.

    Returns:
        None
    """
    if not obj:
        logger.warning("Attempted to apply transforms to an invalid object.")
        return
    if not (apply_location or apply_rotation or apply_scale):
        logger.info(f"No transforms requested for {obj.name}. Skipping apply.")
        return

    transforms_to_apply = []
    if apply_location: 
        transforms_to_apply.append("location")
    if apply_rotation: 
        transforms_to_apply.append("rotation")
    if apply_scale: 
        transforms_to_apply.append("scale")

    logger.info(f"Applying {', '.join(transforms_to_apply)} "
                f"transforms for {obj.name}...")
    try:
        with bpy.context.temp_override(
            selected_editable_objects=[obj],
            selected_objects=[obj], active_object=obj):
            bpy.ops.object.transform_apply(location=apply_location,
                                           rotation=apply_rotation,
                                           scale=apply_scale)
        logger.info(f"Successfully applied {', '.join(transforms_to_apply)} "
                    f"for {obj.name}")
    except Exception as e:
        logger.error(f"Failed to apply transforms for {obj.name}: {e}")
        raise


def apply_mesh_modifiers(obj, modifier_mode="VISIBLE"):
    """
    Apply modifiers on a mesh object based on the specified mode.
    
    Args:
        obj (bpy.types.Object): The object whose modifiers to apply.
        modifier_mode (str): Which modifiers to apply ("NONE", "VISIBLE", "RENDER").
        
    Returns:
        None
    """
    if not obj or obj.type != "MESH":
        return
    
    # Skip all modifier application if mode is NONE
    if modifier_mode == "NONE":
        logger.info(f"Skipping modifier application for {obj.name} (mode: NONE)")
        return
        
    logger.info(f"Applying {modifier_mode.lower()} modifiers for {obj.name}...")
    current_mode = obj.mode
    if current_mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    override = bpy.context.copy()
    override["object"] = obj
    override["active_object"] = obj
    override["selected_objects"] = [obj]
    override["selected_editable_objects"] = [obj]
    applied_modifiers = []
    poly_count = len(obj.data.polygons)
    is_large_mesh = poly_count > LARGE_MESH_THRESHOLD

    try:
        for modifier in obj.modifiers[:]:  # Iterate over a copy
            should_apply = False
            
            # Determine if we should apply this modifier based on mode
            if modifier_mode == "VISIBLE":
                should_apply = modifier.show_viewport
            elif modifier_mode == "RENDER":
                should_apply = modifier.show_render
                
            if should_apply:
                mod_name = modifier.name
                logger.info(f"Applying modifier: {mod_name} ({modifier_mode.lower()})")
                try:
                    with bpy.context.temp_override(**override):
                        bpy.ops.object.modifier_apply(modifier=mod_name)
                    applied_modifiers.append(mod_name)
                    
                    # Memory cleanup for large meshes after every 3 modifiers
                    if is_large_mesh and len(applied_modifiers) % 3 == 0:
                        obj.data.update()
                        import gc
                        gc.collect()
                        logger.info(f"Memory cleanup after {len(applied_modifiers)} modifiers")
                        
                except (RuntimeError, ReferenceError) as e:
                    logger.warning(
                        f"Could not apply modifier '{mod_name}' "
                        f"on {obj.name}: {e}"
                    )
            else:
                status = "viewport disabled" if modifier_mode == "VISIBLE" else "render disabled"
                logger.info(f"Skipping modifier '{modifier.name}': {status}")
    finally:
        if obj.mode != current_mode:
            bpy.ops.object.mode_set(mode=current_mode)
    logger.info(
        f"Finished applying modifiers. Applied: {applied_modifiers}"
    )


def compress_textures(obj, ratio, export_path=None, save_compressed=True):
    """
    Compresses textures based on decimation ratio with no user input required.
    
    Args:
        obj:    The mesh object whose textures should be compressed
        ratio:  The decimation ratio 
                1.0 = full quality, 0.01 = heavy decimation
        export_path: Directory to save compressed textures to
        save_compressed: Whether to save compressed textures to disk
        
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
    
    logger.info(f"Found {len(materials)} materials on {obj.name}")
    
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
    
    logger.info(f"Found {len(image_nodes)} unique texture images to compress")
        
    # Calculate compression amount based on decimation ratio
    compression_factor = max(ratio**0.9, 0.05)  # Limit max compression to 1/20
    min_dimension = 64  # Minimum texture size
    
    # Process each image
    for orig_img, nodes_using_img in image_nodes.items():
        try:
            # Skip packed, or invalid images
            if (not orig_img.has_data 
                or orig_img.size[0] == 0 
                or orig_img.size[1] == 0):
                logger.debug(f"Skipping {orig_img.name}: invalid or no data")
                continue
                
            # Skip already compressed images (but allow recompression if different ratio)
            if orig_img.name.endswith("_LOD"):
                logger.debug(f"Skipping {orig_img.name}: already compressed")
                continue
                
            # Calculate new resolution
            orig_width, orig_height = orig_img.size
            is_power_of_2 = ((orig_width & (orig_width - 1) == 0) 
                             and (orig_height & (orig_height - 1) == 0))
            
            new_width = max(int(orig_width * compression_factor), min_dimension)
            new_height = max(int(orig_height * compression_factor), min_dimension)
            
            # Round to power of 2 if original was power of 2
            if is_power_of_2:
                new_width = 2 ** max(0, (new_width - 1).bit_length())
                new_height = 2 ** max(0, (new_height - 1).bit_length())
                
            # Skip if size hasn't changed
            if (new_width, new_height) == (orig_width, orig_height):
                continue
            
            # Create a copy of the original image with unique name based on ratio
            ratio_suffix = f"{int(ratio * 100):02d}"  # Convert 0.75 to "75"
            copy_name = f"{orig_img.name}_LOD{ratio_suffix}"
            
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
                    height=new_height,
                    alpha=True if hasattr(orig_img, 'alpha') and orig_img.alpha else False,
                    float_buffer=orig_img.is_float if hasattr(orig_img, 'is_float') else False
                )
                
                # Copy pixel data from original and resize using a more reliable method
                if orig_img.has_data and len(orig_img.pixels) > 0:
                    try:
                        # Ensure original image is loaded and packed
                        if not orig_img.packed_file and orig_img.filepath:
                            orig_img.reload()
                        
                        # Use a different approach: create at target size and use GPU for scaling
                        # First, save original to a temporary location if it has a filepath
                        import tempfile
                        temp_file = None
                        
                        if orig_img.filepath and os.path.exists(bpy.path.abspath(orig_img.filepath)):
                            # Use the existing file
                            source_path = bpy.path.abspath(orig_img.filepath)
                        else:
                            # Image is procedural or packed, save it temporarily
                            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                            temp_file.close()
                            
                            # Save the original image to temp file
                            orig_img.filepath_raw = temp_file.name
                            orig_img.file_format = 'PNG'
                            orig_img.save()
                            source_path = temp_file.name
                        
                        # Load the image into the new image and scale it
                        copied_img.filepath_raw = source_path
                        copied_img.reload()
                        
                        # Now scale to target size
                        copied_img.scale(new_width, new_height)
                        
                        # Clean up temp file if created
                        if temp_file and os.path.exists(temp_file.name):
                            try:
                                os.unlink(temp_file.name)
                            except:
                                pass
                        
                        # Copy other relevant properties
                        copied_img.colorspace_settings.name = (
                            orig_img.colorspace_settings.name
                        )
                        
                    except Exception as e:
                        logger.warning(f"Error copying pixels for "
                                       f"{orig_img.name}: {e}")
                        # Clean up failed copy
                        if copied_img:
                            bpy.data.images.remove(copied_img)
                        continue
                        
                logger.info(f"Created compressed copy of '{orig_img.name}' "
                            f"at {new_width}x{new_height} "
                            f"(compression factor: {compression_factor:.2f})")
                
                # Save compressed texture to disk if requested
                if save_compressed and export_path:
                    try:
                        # Determine file extension from original
                        orig_ext = ".jpg"  # Default
                        if orig_img.filepath:
                            orig_ext = os.path.splitext(orig_img.filepath)[1] or ".jpg"
                        elif "." in orig_img.name:
                            orig_ext = "." + orig_img.name.split(".")[-1]
                        
                        # Create compressed texture filename
                        base_name = os.path.splitext(orig_img.name)[0]
                        compressed_filename = f"{base_name}_LOD{ratio_suffix}{orig_ext}"
                        compressed_filepath = os.path.join(export_path, compressed_filename)
                        
                        # Save the compressed texture
                        copied_img.filepath_raw = compressed_filepath
                        copied_img.file_format = 'JPEG' if orig_ext.lower() in ['.jpg', '.jpeg'] else 'PNG'
                        copied_img.save()
                        
                        logger.info(f"Saved compressed texture: {compressed_filename}")
                        
                    except Exception as save_e:
                        logger.warning(f"Failed to save compressed texture {copy_name}: {save_e}")
            
            # Update material nodes to use the copied image
            for mat, node in nodes_using_img:
                node.image = copied_img
                logger.debug(f"Updated node '{node.name}' in material '{mat.name}' to use compressed image")
            
            modified_images.append(f"{orig_img.name} ({orig_width}x{orig_height} "
                                   f"→ {new_width}x{new_height})")
            
            # Store original image reference on the object for restoration
            if "original_textures" not in obj:
                obj["original_textures"] = {}
            
            obj["original_textures"][copy_name] = orig_img.name
            
        except Exception as e:
            logger.error(f"Error processing texture {orig_img.name}: {e}", exc_info=True)
            continue
    
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
    try:
        for img in list(bpy.data.images):  # Use list to avoid iteration issues
            if "_LOD" in img.name and img.users == 0:
                logger.debug(f"Removing unused LOD texture: {img.name}")
                bpy.data.images.remove(img)
    except Exception as e:
        logger.warning(f"Error cleaning up LOD textures: {e}")


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
        f"Applying Decimate to mesh with {initial_poly_count:,} polygons "
        f"(Ratio: {ratio:.3f}, Type: {decimate_type})..."
    )
    
    # Memory optimisation for very large meshes before decimation
    if initial_poly_count > VERY_LARGE_MESH_THRESHOLD:
        logger.info("Very large mesh detected, enabling memory optimisation")
        obj.data.update()
        import gc
        gc.collect()

    current_mode = obj.mode
    if current_mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    # Skip the old texture compression system - we now use simple external texture saving
    compressed_texture_list = []
    # Texture compression disabled - using simple external texture saving instead
    logger.debug("Skipping texture compression - using external texture saving")

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
        
        # No texture compression details to log
        pass
            
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
    
    poly_count = len(obj.data.polygons)
    logger.info(f"Triangulating {obj.name} with {poly_count:,} polygons...")
    
    # Memory optimisation for large meshes before triangulation
    if poly_count > LARGE_MESH_THRESHOLD:
        obj.data.update()
        import gc
        gc.collect()
    
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


def is_normal_map(node, img):
    """
    Detect if a texture is likely a normal map based on various indicators.
    
    Args:
        node: The image texture node
        img: The image data
    
    Returns:
        bool: True if likely a normal map
    """
    # Check node name
    node_name_lower = node.name.lower()
    if any(term in node_name_lower for term in ['normal', 'norm', 'nrm', 'bump']):
        return True
    
    # Check image name
    img_name_lower = img.name.lower()
    if any(term in img_name_lower for term in ['normal', 'norm', 'nrm', 'bump', '_n.', '_n_']):
        return True
    
    # Check if connected to Normal input
    for output in node.outputs:
        for link in output.links:
            if link.to_socket.name.lower() in ['normal', 'normal map']:
                return True
    
    # Check colorspace - normal maps are usually Non-Color
    if hasattr(img.colorspace_settings, 'name'):
        if img.colorspace_settings.name in ['Non-Color', 'Linear', 'Raw']:
            # Additional check - if it's connected to Base Color, it's not a normal map
            for output in node.outputs:
                for link in output.links:
                    if link.to_socket.name in ['Base Color', 'Color']:
                        return False
            return True
    
    return False


def get_texture_format_info(img):
    """
    Determine the best format to save a texture based on its properties.
    
    Args:
        img: The image data
    
    Returns:
        tuple: (format_string, has_alpha, is_hdr)
    """
    has_alpha = False
    is_hdr = False
    format_string = 'JPEG'
    
    # Check if image has alpha
    if hasattr(img, 'depth'):
        has_alpha = img.depth == 32  # RGBA
    elif hasattr(img, 'channels'):
        has_alpha = img.channels == 4
    
    # Check if HDR
    if hasattr(img, 'is_float'):
        is_hdr = img.is_float
    
    # Determine format based on properties
    if is_hdr:
        format_string = 'HDR'
    elif has_alpha:
        format_string = 'PNG'
    else:
        # Check original format
        if img.filepath:
            ext = os.path.splitext(img.filepath)[1].lower()
            if ext in ['.png']:
                format_string = 'PNG'
            elif ext in ['.tga', '.targa']:
                format_string = 'TARGA'
            elif ext in ['.exr']:
                format_string = 'OPEN_EXR'
    
    return format_string, has_alpha, is_hdr


def save_external_textures(obj, export_dir, lod_suffix="", resize_textures=True, scene_props=None):
    """
    Save textures used by the object to external files with LOD-appropriate sizes.
    Also updates material nodes to reference the external files for proper FBX export.
    
    Args:
        obj: The mesh object
        export_dir: Directory to save textures to
        lod_suffix: Suffix to add to texture names (e.g., "_LOD01")
        resize_textures: Whether to resize textures for LODs
        scene_props: Scene properties for texture settings
    
    Returns:
        Tuple: (List of saved texture filenames, Dict of original node references for restoration)
    """
    if not obj or obj.type != "MESH":
        return [], {}
    
    saved_textures = []
    original_references = {}  # Store original image references for restoration
    materials = obj.data.materials
    
    if not materials:
        return saved_textures, original_references
    
    # Determine target texture size based on LOD level (only if resizing is enabled)
    target_size = None
    if resize_textures and scene_props:
        if "LOD00" in lod_suffix:
            target_size = None  # Original size
        elif "LOD01" in lod_suffix:
            target_size = int(scene_props.mesh_export_lod1_texture_size)
        elif "LOD02" in lod_suffix:
            target_size = int(scene_props.mesh_export_lod2_texture_size)
        elif "LOD03" in lod_suffix:
            target_size = int(scene_props.mesh_export_lod3_texture_size)
        elif "LOD04" in lod_suffix:
            target_size = int(scene_props.mesh_export_lod4_texture_size)
        else:
            target_size = None  # Default to original
    
    logger.info(f"Target texture size for {lod_suffix}: {target_size or 'original'}")
    
    for mat in materials:
        if not mat or not mat.node_tree:
            continue
            
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                img = node.image
                
                # Skip if no data
                if not img.has_data:
                    continue
                
                # Detect texture type
                is_normal = is_normal_map(node, img)
                
                # Get format info
                format_string, has_alpha, is_hdr = get_texture_format_info(img)
                
                # Determine file extension based on format
                ext_map = {
                    'JPEG': '.jpg',
                    'PNG': '.png',
                    'TARGA': '.tga',
                    'HDR': '.hdr',
                    'OPEN_EXR': '.exr'
                }
                ext = ext_map.get(format_string, '.jpg')
                
                # Create external filename
                base_name = os.path.splitext(img.name)[0]
                external_filename = f"{base_name}{lod_suffix}{ext}"
                external_path = os.path.join(export_dir, external_filename)
                
                try:
                    # Ensure the image has data loaded
                    if not img.has_data and img.filepath:
                        img.reload()
                    
                    # Save a copy of the image (with resizing if needed)
                    if img.has_data:
                        img_to_save = img
                        temp_img = None
                        
                        # Check if we need to resize
                        orig_width, orig_height = img.size
                        
                        # Adjust target size for normal maps if preservation is enabled
                        adjusted_target_size = target_size
                        if is_normal and scene_props and scene_props.mesh_export_preserve_normal_maps and target_size:
                            # Keep normal maps at one LOD level higher
                            if "LOD02" in lod_suffix:
                                adjusted_target_size = int(scene_props.mesh_export_lod1_texture_size)
                            elif "LOD03" in lod_suffix:
                                adjusted_target_size = int(scene_props.mesh_export_lod2_texture_size)
                            elif "LOD04" in lod_suffix:
                                adjusted_target_size = int(scene_props.mesh_export_lod3_texture_size)
                            logger.info(f"Preserving normal map quality: {target_size} → {adjusted_target_size}")
                        
                        # Only resize if image is larger than target (no upscaling)
                        needs_resize = (adjusted_target_size is not None and 
                                      (orig_width > adjusted_target_size or orig_height > adjusted_target_size))
                        
                        if needs_resize:
                            # Calculate new dimensions preserving aspect ratio
                            aspect_ratio = orig_width / orig_height
                            
                            if orig_width > orig_height:
                                new_width = adjusted_target_size
                                new_height = int(adjusted_target_size / aspect_ratio)
                            else:
                                new_height = adjusted_target_size
                                new_width = int(adjusted_target_size * aspect_ratio)
                            
                            # Ensure dimensions are at least 1
                            new_width = max(1, new_width)
                            new_height = max(1, new_height)
                            
                            logger.info(f"Resizing {img.name} from {orig_width}x{orig_height} to {new_width}x{new_height}")
                            
                            # Create a temporary resized copy
                            temp_img = img.copy()
                            temp_img.name = f"{img.name}_temp_resize"
                            
                            # Scale the temporary image
                            temp_img.scale(new_width, new_height)
                            img_to_save = temp_img
                        else:
                            if adjusted_target_size is not None:
                                logger.info(f"Skipping resize for {img.name} ({orig_width}x{orig_height}) - already smaller than target")
                        
                        # Set the save path and format
                        original_filepath = img_to_save.filepath_raw
                        img_to_save.filepath_raw = external_path
                        img_to_save.file_format = format_string
                        
                        # Set JPEG quality if applicable
                        if format_string == 'JPEG' and scene_props:
                            # Note: Blender's save_render settings affect image saving
                            scene = bpy.context.scene
                            original_quality = scene.render.image_settings.quality
                            scene.render.image_settings.quality = scene_props.mesh_export_texture_quality
                        
                        # Save the image
                        img_to_save.save()
                        
                        # Restore JPEG quality
                        if format_string == 'JPEG' and scene_props:
                            scene.render.image_settings.quality = original_quality
                        
                        # Restore original filepath to avoid affecting the scene
                        img_to_save.filepath_raw = original_filepath
                        
                        # Clean up temporary image
                        if temp_img:
                            bpy.data.images.remove(temp_img)
                        
                        # Create a new image that references the external file
                        external_img = bpy.data.images.load(external_path)
                        external_img.name = f"{img.name}_external"
                        
                        # Preserve colorspace settings
                        if hasattr(img, 'colorspace_settings'):
                            external_img.colorspace_settings.name = img.colorspace_settings.name
                        
                        # Store original reference for restoration
                        original_references[node] = img
                        
                        # Update the material node to use the external image
                        node.image = external_img
                        
                        saved_textures.append(external_filename)
                        size_info = f"{orig_width}x{orig_height}"
                        if needs_resize:
                            size_info += f" → {new_width}x{new_height}"
                        texture_type = "normal map" if is_normal else "texture"
                        logger.info(f"Saved external {texture_type}: {external_filename} ({size_info}, {format_string})")
                    else:
                        logger.warning(f"Image {img.name} has no data to save")
                    
                except Exception as e:
                    logger.warning(f"Failed to save texture {img.name}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
    
    return saved_textures, original_references


def restore_material_references(original_references):
    """
    Restore original material node references and clean up external image references.
    
    Args:
        original_references: Dict mapping nodes to their original images
    """
    for node, original_img in original_references.items():
        try:
            # Get the external image we created
            external_img = node.image
            
            # Restore original image reference
            node.image = original_img
            
            # Remove the external image from Blender data
            if external_img and external_img.name.endswith("_external"):
                try:
                    bpy.data.images.remove(external_img)
                    logger.debug(f"Cleaned up external image reference: {external_img.name}")
                except ReferenceError:
                    # Image was already removed, which is fine
                    logger.debug(f"External image already cleaned up: {external_img.name}")
                
        except (ReferenceError, AttributeError):
            # Node or image was already removed, which can happen during cleanup
            logger.debug("Material reference already cleaned up")
        except Exception as e:
            logger.warning(f"Error restoring material reference: {e}")


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
    
    # Handle GLTF format extensions
    if fmt == "GLTF":
        if scene_props.mesh_export_gltf_type == "GLB":
            export_filepath = f"{base_file_path}.glb"
        else:
            export_filepath = f"{base_file_path}.gltf"
    else:
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

    # Check mesh size and optimise if needed
    mesh_size = len(obj.data.polygons) if obj.data else 0
    if mesh_size > LARGE_MESH_THRESHOLD:
        logger.info(f"Large mesh export: {mesh_size:,} polygons")
        obj.data.update()
        bpy.context.view_layer.update()
        import gc
        gc.collect()
    
    # Save external textures if not embedding
    external_textures = []
    original_references = {}
    if not scene_props.mesh_export_embed_textures:
        export_dir = os.path.dirname(export_filepath)
        lod_suffix = ""
        
        # Extract LOD suffix from object name if present
        if "_LOD" in obj.name:
            lod_part = obj.name.split("_LOD")[-1]
            if len(lod_part) == 2 and lod_part.isdigit():
                lod_suffix = f"_LOD{lod_part}"
        
        external_textures, original_references = save_external_textures(obj, export_dir, lod_suffix, scene_props.mesh_export_resize_textures, scene_props)
    
    logger.info(
        f"Exporting {os.path.basename(export_filepath)} ({fmt}) - {mesh_size:,} polygons..."
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
                    path_mode="STRIP" if not scene_props.mesh_export_embed_textures else "COPY",
                    embed_textures=scene_props.mesh_export_embed_textures,
                    mesh_smooth_type=scene_props.mesh_export_smoothing,
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
                    path_mode="STRIP",  # OBJ doesn't embed textures
                    export_normals=True,
                    export_smooth_groups=True,
                    apply_modifiers=False, # Handled by apply_mesh_modifiers
                    export_triangulated_mesh=False, # Handled triangulate_mesh
                )
            elif fmt == "GLTF":
                # For GLTF, textures are always embedded in GLB or copied with GLTF
                bpy.ops.export_scene.gltf(
                    filepath=export_filepath,
                    use_selection=True,
                    export_format=scene_props.mesh_export_gltf_type,
                    export_apply=False, # Transforms/Mods applied manually
                    export_texcoords=True, # Explicitly export UVs
                    export_normals=True,
                    export_tangents=False, 
                    export_materials=scene_props.mesh_export_gltf_materials, 
                    export_vertex_color="MATERIAL", 
                    export_cameras=False,
                    export_lights=False,
                    export_skins=False,  # Disable skin export to reduce size
                    export_animations=False,  # Disable animation export to reduce size
                    export_extras=False,  # Disable extras to reduce size
                    export_yup=True, # Use Y-Up coordinate system
                    # Texture settings
                    export_texture_dir="",  # Export textures to same directory as GLTF
                    export_jpeg_quality=export_quality,
                    export_image_quality=export_quality,
                    export_def_bones=False, # Don't export bones
                    # Enable Draco compression for geometry
                    export_draco_mesh_compression_enable=True,
                    export_draco_mesh_compression_level=6,
                    export_draco_position_quantization=14,
                    export_draco_normal_quantization=10,
                    export_draco_texcoord_quantization=12,
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
                    export_normals=True,
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

            # Get file size
            file_size = os.path.getsize(export_filepath)
            file_size_mb = file_size / (1024 * 1024)
            
            # Calculate approximate size breakdown for GLTF/GLB
            size_info = f"Size: {file_size_mb:.2f} MB"
            
            # Add external texture info if any were saved
            if external_textures:
                export_dir = os.path.dirname(export_filepath)
                total_texture_size = 0
                
                for tex_filename in external_textures:
                    tex_path = os.path.join(export_dir, tex_filename)
                    try:
                        total_texture_size += os.path.getsize(tex_path)
                    except:
                        pass
                
                if total_texture_size > 0:
                    texture_size_mb = total_texture_size / (1024 * 1024)
                    size_info += f" + {len(external_textures)} texture(s): {texture_size_mb:.2f} MB"
                    size_info += f" (Total: {file_size_mb + texture_size_mb:.2f} MB)"
            
            # For GLTF JSON format, also check for other texture files
            elif fmt == "GLTF" and scene_props.mesh_export_gltf_type == "GLTF_SEPARATE":
                export_dir = os.path.dirname(export_filepath)
                texture_files = []
                total_texture_size = 0
                
                # Look for common image formats in the same directory
                for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    pattern = os.path.join(export_dir, f"*{ext}")
                    import glob
                    texture_files.extend(glob.glob(pattern))
                
                if texture_files:
                    for tex_file in texture_files:
                        try:
                            total_texture_size += os.path.getsize(tex_file)
                        except:
                            pass
                    
                    texture_size_mb = total_texture_size / (1024 * 1024)
                    size_info += f" + {len(texture_files)} texture(s): {texture_size_mb:.2f} MB"
                    size_info += f" (Total: {file_size_mb + texture_size_mb:.2f} MB)"
            
            elif fmt == "GLTF" and scene_props.mesh_export_gltf_type == "GLB":
                # Rough estimate: with compression, ~100 bytes per triangle
                estimated_mesh_size_mb = (mesh_size * 100) / (1024 * 1024)
                estimated_texture_size_mb = file_size_mb - estimated_mesh_size_mb
                if estimated_texture_size_mb > 0:
                    size_info += f" (est. mesh: {estimated_mesh_size_mb:.1f} MB, textures: {estimated_texture_size_mb:.1f} MB)"
            
            logger.info(
                f"Successfully exported {os.path.basename(export_filepath)} "
                f"({size_info})"
            )
            success = True
        except Exception as e:
            logger.error(
                f"Failed exporting {obj.name} as {fmt}: {e}", exc_info=True
            )
            success = False
        finally:
            # Restore original material references if we modified them
            if original_references:
                restore_material_references(original_references)
                logger.debug("Restored original material references")
    
    return success


def calculate_progressive_ratio(target_ratio, previous_ratio):
    """
    Calculate the decimation ratio needed to go from previous LOD to target LOD.
    
    Args:
        target_ratio (float): The target ratio from the original mesh (e.g., 0.5 for 50%)
        previous_ratio (float): The ratio of the previous LOD from original (e.g., 0.75 for 75%)
    
    Returns:
        float: The ratio to apply to get from previous LOD to target LOD
    """
    if previous_ratio <= 0:
        return target_ratio
    return target_ratio / previous_ratio


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
    
    # No texture restoration needed with the new simple system
    pass
    
    # Then remove the object
    try:
        mesh_data = obj.data # Store reference before removing object
        num_users = mesh_data.users
        poly_count = len(mesh_data.polygons) if mesh_data else 0
        was_large_mesh = poly_count > LARGE_MESH_THRESHOLD
        
        bpy.data.objects.remove(obj, do_unlink=True)
        logger.info(f"Cleaned up object: {log_name}")
        
        # If the mesh data had only this object as a user, remove it too
        if num_users == 1 and mesh_data:
             try:
                 # Clear geometry data for large meshes to free memory immediately
                 if was_large_mesh and hasattr(mesh_data, 'clear_geometry'):
                     mesh_data.clear_geometry()
                 bpy.data.meshes.remove(mesh_data)
                 logger.info(f"Cleaned up orphaned mesh data for: {log_name}")
             except (ReferenceError, Exception) as mesh_remove_e:
                 logger.warning(f"Issue removing mesh data for {log_name}: "
                                f"{mesh_remove_e}")
        
        # Force garbage collection for large meshes
        if was_large_mesh:
            import gc
            gc.collect()
            logger.info(f"Memory cleanup completed for large mesh: {log_name}")

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

                        # LOD Reuse Implementation
                        base_lod_obj = None
                        previous_ratio = 1.0
                        
                        for lod_level, target_ratio in enumerate(ratios):
                            lod_obj = None
                            lod_obj_name = None
                            try:
                                if lod_level == 0:
                                    # LOD0: Create base copy with modifiers applied
                                    logger.info(f"Creating base LOD0...")
                                    lod_obj = create_export_copy(
                                        original_obj, 
                                        context
                                    )
                                    (lod_obj_name, _) = setup_export_object(
                                        lod_obj, original_obj.name,
                                        scene_props, lod_level
                                    )
                                    apply_mesh_modifiers(lod_obj, scene_props.mesh_export_apply_modifiers)
                                    
                                    # LOD0 texture resizing is handled during export via save_external_textures
                                    # No need for special processing here
                                    
                                    # Keep reference for reuse
                                    base_lod_obj = lod_obj
                                else:
                                    # LOD1+: Reuse previous LOD with progressive decimation
                                    if base_lod_obj is None:
                                        raise RuntimeError("Base LOD object lost, cannot continue")
                                    
                                    logger.info(f"Building LOD{lod_level} from previous LOD...")
                                    
                                    # Calculate progressive ratio
                                    progressive_ratio = calculate_progressive_ratio(
                                        target_ratio, previous_ratio
                                    )
                                    logger.info(f"Progressive decimation ratio: {progressive_ratio:.3f} "
                                              f"(from {previous_ratio:.3f} to {target_ratio:.3f})")
                                    
                                    # Rename for current LOD
                                    (lod_obj_name, _) = setup_export_object(
                                        base_lod_obj, original_obj.name,
                                        scene_props, lod_level
                                    )
                                    
                                    # Apply progressive decimation
                                    apply_decimate_modifier(
                                        base_lod_obj, progressive_ratio,
                                        scene_props.mesh_export_lod_type,
                                        scene_props.mesh_export_lod_symmetry_axis,
                                        scene_props.mesh_export_lod_symmetry,
                                    )
                                    
                                    # Use the same object for export
                                    lod_obj = base_lod_obj
                                
                                # Triangulate if needed (applies to all LODs)
                                if scene_props.mesh_export_tri and lod_level == 0:
                                    # Only triangulate once on LOD0
                                    method = scene_props.mesh_export_tri_method
                                    k_nrms = scene_props.mesh_export_keep_normals
                                    triangulate_mesh(lod_obj, method, k_nrms)

                                # Export current LOD
                                lod_file_path = os.path.join(export_base_path,
                                                           lod_obj_name)
                                if export_object(lod_obj, lod_file_path,
                                               scene_props):
                                    successful_exports += 1
                                else:
                                    raise RuntimeError("Export func failed")
                                
                                # Update previous ratio for next iteration
                                previous_ratio = target_ratio

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
                                # Break the loop on error since subsequent LODs depend on previous
                                break
                            finally:
                                # Only cleanup at the very end
                                if lod_level == len(ratios) - 1 or not object_processed_successfully:
                                    cleanup_object(base_lod_obj, "base_lod_object")
                                    base_lod_obj = None
                                
                        # Memory cleanup between LOD levels for large meshes
                        if len(original_obj.data.polygons if original_obj.data else []) > LARGE_MESH_THRESHOLD:
                            import gc
                            gc.collect()
                            logger.debug("Memory cleanup after LOD level processing")
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
                            apply_mesh_modifiers(export_obj, scene_props.mesh_export_apply_modifiers)
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

    # Correct the property definition using annotation
    object_name: StringProperty()

    def execute(self, context):
        """Executes the selection using direct API."""
        # Access the property using self.object_name
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
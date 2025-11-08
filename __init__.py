# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2025 Bradley Walker

import bpy
import logging
from . import properties
from . import operators
from . import panels
from . import export_indicators # Still needed for timer and recent list

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


# Registration
classes = (
    *operators.classes,
    *panels.classes,
    # export_indicators registers its own classes/timer
)


def register():
    logger.info("Begin registration.")
    # 1. Properties FIRST
    properties.register_properties()
    logger.info("Properties registered.")

    # Debug code to verify registration
    test = hasattr(bpy.types.Scene, "mesh_exporter")
    logger.info(f"Verification - mesh_exporter exists: {test}")

    # 1.5 Initialise built-in presets
    operators.initialise_builtin_presets()
    logger.info("Built-in presets initialised.")

    # 2. Other Classes (Operators, Panels)
    for cls in classes:
        bpy.utils.register_class(cls)
    logger.info("Panel/Operator classes registered.")

    # 3. Indicators
    export_indicators.register()
    logger.info("Export indicators registered.")
    logger.info("Registration complete.")


def unregister():
    logger.info("Begin unregistration.")
    # Unregister in REVERSE order

    # 1. Indicators
    export_indicators.unregister()
    logger.info("Export indicators unregistered.")

    # 2. Other Classes
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError as e:
            logger.error(f"Couldn't unregister {cls}: {e}")
    logger.info("Panel/Operator classes unregistered.")

    # 3. Properties LAST
    properties.unregister_properties()
    logger.info("Properties unregistered.")
    logger.info("Unregistration complete.")


if __name__ == "__main__":
    register()
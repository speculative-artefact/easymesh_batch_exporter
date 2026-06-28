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
from . import properties
from . import operators
from . import panels
from . import export_indicators  # Still needed for timer and recent list


# Registration
classes = (
    *operators.classes,
    *panels.classes,
    # export_indicators registers its own classes/timer
)


def register():
    # 1. Properties FIRST
    properties.register_properties()

    # 1.5 Initialise built-in presets
    operators.initialise_builtin_presets()

    # 2. Other Classes (Operators, Panels)
    for cls in classes:
        bpy.utils.register_class(cls)

    # 3. Indicators
    export_indicators.register()


def unregister():
    # Unregister in REVERSE order

    # 1. Indicators
    export_indicators.unregister()

    # 2. Other Classes
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass

    # 3. Properties LAST
    properties.unregister_properties()


if __name__ == "__main__":
    register()

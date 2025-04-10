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
from . import export_indicators # Still needed for timer and recent list

# Registration
classes = (
    *operators.classes,
    *panels.classes,
    # export_indicators registers its own classes/timer
)

def register():
    # First register export indicators (including the timer)
    from . import export_indicators
    export_indicators.register()
    
    # Then register operators which may use the timer
    from . import operators
    operators.register()

def unregister():
    export_indicators.unregister() # Unregister timer first
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    properties.unregister_properties()

if __name__ == "__main__":
    register()
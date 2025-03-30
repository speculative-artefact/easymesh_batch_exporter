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

bl_info = {
    "name": "Custom Mesh Exporter",
    "author": "Bradley Walker",
    "version": (1, 0, 0),
    "blender": (3, 5, 0),
    "location": "View3D > Sidebar > Mesh Exporter",
    "description": "Export multiple selected objects with customisable settings",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

import bpy
# for development
bpy.utils.user_resource("EXTENSIONS", path="vscode_development")

# Import other modules
from . import properties
from . import operators
from . import panels

# Registration
def register():
    properties.register_properties()
    operators.register()
    panels.register()

def unregister():
    panels.unregister()
    operators.unregister()
    properties.unregister_properties()

if __name__ == "__main__":
    register()
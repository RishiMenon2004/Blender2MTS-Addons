# ##### BEGIN GPL LICENSE BLOCK #####
#   Copyright (C) 2021  Turbo Defender
#   
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#   
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#    
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, contact Turbo Defender at turbodefender82004@gmail.com
# ##### END GPL LICENSE BLOCK #####

#Addon properties
bl_info = {
    "name": "MTS/IV Collision Group Exporter",
    "author": "Turbo Defender | Gyro Hero | Laura Darkez",
    "version": (2, 5),
    "blender": (2, 90, 0),
    "location": "Object Properties —> MTS/IV Collision Properties",
    "description": "Exports Blender cubes as MTS/IV collision boxes",
    "category": "MTS"
}

#Import blender modules
import bpy
from bpy.types import (Panel, UIList)
from bpy_extras.io_utils import (ExportHelper, ImportHelper)
from bpy.props import (
    BoolProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
    EnumProperty,
    PointerProperty,
    CollectionProperty,
)

#Import python bundled modules
import math
import numpy as NP
import os
import subprocess
import sys
import importlib

from collections import namedtuple

Dependency = namedtuple("Dependency", ["module", "package", "name"])

dependencies = (Dependency(module="json5", package=None, name="json"),)

dependencies_installed = False

def import_module(module_name, global_name=None, reload=True):
    """
    Import a module.
    :param module_name: Module to import.
    :param global_name: (Optional) Name under which the module is imported. If None the module_name will be used.
       This allows to import under a different name with the same effect as e.g. "import numpy as np" where "np" is
       the global_name under which the module can be accessed.
    :raises: ImportError and ModuleNotFoundError
    """
    if global_name is None:
        global_name = module_name

    if global_name in globals():
        importlib.reload(globals()[global_name])
    else:
        # Attempt to import the module and assign it to globals dictionary. This allow to access the module under
        # the given name, just like the regular import would.
        globals()[global_name] = importlib.import_module(module_name)

def install_pip():
    """
    Installs pip if not already present. Please note that ensurepip.bootstrap() also calls pip, which adds the
    environment variable PIP_REQ_TRACKER. After ensurepip.bootstrap() finishes execution, the directory doesn't exist
    anymore. However, when subprocess is used to call pip, in order to install a package, the environment variables
    still contain PIP_REQ_TRACKER with the now nonexistent path. This is a problem since pip checks if PIP_REQ_TRACKER
    is set and if it is, attempts to use it as temp directory. This would result in an error because the
    directory can't be found. Therefore, PIP_REQ_TRACKER needs to be removed from environment variables.
    :return:
    """

    try:
        # Check if pip is already installed
        subprocess.run([sys.executable, "-m", "pip", "--version"], check=True)
    except subprocess.CalledProcessError:
        import ensurepip

        ensurepip.bootstrap()
        os.environ.pop("PIP_REQ_TRACKER", None)
        
def install_and_import_module(module_name, package_name=None, global_name=None):
    """
    Installs the package through pip and attempts to import the installed module.
    :param module_name: Module to import.
    :param package_name: (Optional) Name of the package that needs to be installed. If None it is assumed to be equal
       to the module_name.
    :param global_name: (Optional) Name under which the module is imported. If None the module_name will be used.
       This allows to import under a different name with the same effect as e.g. "import numpy as np" where "np" is
       the global_name under which the module can be accessed.
    :raises: subprocess.CalledProcessError and ImportError
    """
    if package_name is None:
        package_name = module_name

    if global_name is None:
        global_name = module_name

    # Blender disables the loading of user site-packages by default. However, pip will still check them to determine
    # if a dependency is already installed. This can cause problems if the packages is installed in the user
    # site-packages and pip deems the requirement satisfied, but Blender cannot import the package from the user
    # site-packages. Hence, the environment variable PYTHONNOUSERSITE is set to disallow pip from checking the user
    # site-packages. If the package is not already installed for Blender's Python interpreter, it will then try to.
    # The paths used by pip can be checked with `subprocess.run([bpy.app.binary_path_python, "-m", "site"], check=True)`

    # Create a copy of the environment variables and modify them for the subprocess call
    environ_copy = dict(os.environ)
    environ_copy["PYTHONNOUSERSITE"] = "1"

    subprocess.run([sys.executable, "-m", "pip", "install", package_name], check=True, env=environ_copy)

    # The installation succeeded, attempt to import the module again
    import_module(module_name, global_name)
        
#Operator: Importer
class MTS_OT_ImportCollisions(bpy.types.Operator, ImportHelper):
    #Class options
    bl_idname = "mts.import_collision_boxes"
    bl_label = "(MTS/IV) Import Collisions"
    bl_description = "Import collisionGroups from a JSON file"
    
    filename_ext = ".json"
    filter_glob: StringProperty(
        default = "*.json",
        options = {'HIDDEN'},
    )
    
    def execute(self, context):
        col_name = 'Collision Groups'
        if col_name not in bpy.data.collections:
            bpy.ops.collection.create(name=col_name)
            box_collection = bpy.data.collections[col_name]
            bpy.context.scene.collection.children.link(box_collection)
            
        box_collection = bpy.context.view_layer.layer_collection.children[col_name]
        bpy.context.view_layer.active_layer_collection = box_collection
        
        
        with open(self.filepath, 'r') as f:
            file = json.loads(f.read())
        
            if 'collisionGroups' in file:
                collisionGroups = file['collisionGroups']
                
                for collisionGroup in collisionGroups:
                    bpy.ops.mts.add_collision_group()
                    newCollisionGroup = context.scene.mts_collision_groups[-1]
                    newCollisionGroup.isInterior = collisionGroup['isInterior'] if 'isInterior' in collisionGroup else False
                    newCollisionGroup.isForBullet = collisionGroup['isForBullet'] if 'isForBullet' in collisionGroup else False
                    newCollisionGroup.health = collisionGroup['health'] if 'health' in collisionGroup else 0
                    newCollisionGroup.applyAfter = collisionGroup['applyAfter'] if 'applyAfter' in collisionGroup else ""
                    collisions = collisionGroup['collisions']
                
                    for collision in collisions:
                        width = collision['width']
                        height = collision['height']
                        pos = collision['pos']
                        
                        bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0], -1*pos[2], pos[1]), scale=(width, width, height))
                        obj = context.object
                        settings = obj.mts_collision_settings
                        
                        if 'variableType' in collision:
                            settings.variableName = collision['variableName']
                            settings.variableValue = collision['variableValue'] if 'variableValue' in collision else 0
                            settings.variableType = collision['variableType']
                        
                        if 'collidesWithLiquids' in collision:
                            settings.collidesWithLiquids = collision['collidesWithLiquids']
                        else:
                            settings.collidesWithLiquids = False
                            
                        if 'armorThickness' in collision:
                            settings.armorThickness = collision['armorThickness']
                        
                        context.scene.mts_collision_groups_index = len(context.scene.mts_collision_groups) - 1
                        bpy.ops.mts.assign_collision_to_group()
                    
            if 'collisionGroups' not in file:
                self.report({'ERROR_INVALID_INPUT'}, "NO COLLISION-GROUPS FOUND")
                return {'CANCELLED'}
        
        self.report({'OPERATOR'}, "Import Finished")
        return {'FINISHED'}

#Operator: Exporter      
class MTS_OT_ExportCollisions(bpy.types.Operator, ExportHelper):
    #Class options
    bl_idname = "mts.export_collision_boxes"
    bl_label = "(MTS/IV) Export Collisions"
    bl_description = "Export collisionGroups as a JSON file"
    
    filename_ext = ".json"

    def execute(self, context):
        self.report({'INFO'}, "Export Started")
        f = open(self.filepath, "w")
        firstEntry = True
        
        """
        {
            "collisionGroups": [
                //collision group name
                {
                    "isInterior": false,
                    "health": 100,
                    "collisions": [
                        {
                            "pos": [x, y, z],
                            "width": 1,
                            "height": 1,
                            "collidesWithLiquids": true,
                            "armorThickness": 0,
                            "variableName": "door_left",
                            "variableType": "toggle"|"set"|"increment"|"button",
                            "variableValue": 0,
                            "clampMin": 0,
                            "clampMax": 1
                        }
                    ],
                    "applyAfter": "door_left",
                    "animations": []
                }
            ]
        }
        
        """
        
        #Write Collisions
        f.write("{\n\t\"collisionGroups\": [\n")
        
        for collision_group in context.scene.mts_collision_groups:
            if firstEntry:
                f.write("\t\t//{name}\n".format(name=collision_group.name))
                firstEntry = False
            else:
                f.write(",\n\n\t\t//{name}\n".format(name=collision_group.name))
                
            f.write("\t\t{\n")
            
            if collision_group.isInterior:
                f.write("\t\t\t\"isInterior\": true,\n")
                
            if collision_group.isForBullets:
                f.write("\t\t\t\"isForBullets\": true,\n")
            
            f.write("\t\t\t\"health\": {health},\n".format(health=collision_group.health))
            
            f.write("\t\t\t\"collisions\": [")
            
            firstCollisionEntry = True
            
            for obj in collision_group.collisions:
                collision = obj.collision
                if firstCollisionEntry:
                    f.write("\n\t\t\t\t//{name}\n\t\t\t\t{bracket}\n".format(name=collision.name, bracket="{"))
                else:
                    f.write(",\n\t\t\t\t//{name}\n\t\t\t\t{bracket}\n".format(name=collision.name, bracket="{"))
                    
                if  (collision.mts_collision_settings.subdivideWidth > 0) or (collision.dimensions[0] != collision.dimensions[1]):
                    self.divide_collision_box(collision, f, context)
                else:
                    self.export_collision_box(collision.location, collision.dimensions, collision.mts_collision_settings, f, context)
            
                firstCollisionEntry = False
            
            f.write("\n\t\t\t]")
                
            if collision_group.applyAfter != "":
                f.write(",\n\t\t\t\"applyAfter\": \"{applyAfter}\"".format(applyAfter=str(collision_group.applyAfter)))
            
            f.write(",\n\t\t\t\"animations\": []")
            
            f.write("\n\t\t}")
                
        f.write("\n\t]\n}")

        return {'FINISHED'}
    
    def divide_collision_box(self, obj, f, context):
        # We need to break this box into smaller boxes
        if obj.mts_collision_settings.subdivideWidth > 0 or obj.mts_collision_settings.subdivideHeight:
            # Boxes are of a specified size
            boxSize = obj.mts_collision_settings.subdivideWidth if obj.mts_collision_settings.subdivideWidth > 0 else min(obj.dimensions[0], obj.dimensions[1])
            if boxSize > min(obj.dimensions[0], obj.dimensions[1]):
                boxSize = min(obj.dimensions[0], obj.dimensions[1])
            boxSizeZ = obj.mts_collision_settings.subdivideHeight if obj.mts_collision_settings.subdivideHeight > 0 else obj.dimensions[2]
            if boxSizeZ > obj.dimensions[2]:
                boxSizeZ = obj.dimensions[2]
            numX = math.ceil(obj.dimensions[0] / boxSize)
            numY = math.ceil(obj.dimensions[1] / boxSize)
            numZ = math.ceil(obj.dimensions[2] / boxSizeZ)
        else:
            # Length and width are unequal, so break it into multiple boxes in the long axis ONLY
            boxSize = min(obj.dimensions[0], obj.dimensions[1])
            if obj.dimensions[0] > obj.dimensions[1]:
                #X is the longer axis
                numX = math.ceil(obj.dimensions[0] / obj.dimensions[1])
                numY = 1
            else:
                #Y is the longer axis
                numX = 1
                numY = math.ceil(obj.dimensions[1] / obj.dimensions[0])
            numZ = 1
            boxSizeZ = obj.dimensions[2]

        # Determine how much total overlap there is, if any, in each axis
        overlapX = numX*boxSize - obj.dimensions[0]
        overlapY = numY*boxSize - obj.dimensions[1]
        overlapZ = numZ*boxSizeZ - obj.dimensions[2]
        # Divide by the number of overlaps, unless there are none
        overlapXper = overlapX / (numX-1) if numX>1 else 0
        overlapYper = overlapY / (numY-1) if numY>1 else 0
        overlapZper = overlapZ / (numZ-1) if numZ>1 else 0

        # List the coordinates for each dimension
        # Different calculations for even vs odd numbers of boxes
        origin = obj.location
        offset = 0 if numX % 2 == 1 else 0.5*(boxSize - overlapXper)
        xList = [origin[0]] if numX % 2 == 1 else [origin[0] - offset, origin[0] + offset]
        for n in range((numX-1) // 2): #Ignore the middle 1 or 2 boxes, those were added in the line above
            # Add the next furthest box on each side
            xList.insert(0, origin[0] - offset - (n+1)*(boxSize-overlapXper))
            xList.append(origin[0] + offset + (n+1)*(boxSize-overlapXper))

        offset = 0 if numY % 2 == 1 else 0.5*(boxSize - overlapYper)
        yList = [origin[1]] if numY % 2 == 1 else [origin[1] - offset, origin[1] + offset]
        for n in range((numY-1) // 2): #Ignore the middle 1 or 2 boxes, those were added in the line above
            # Add the next furthest box on each side
            listLen = len(yList)
            yList.insert(0, origin[1] - offset - (n+1)*(boxSize-overlapYper))
            yList.append(origin[1] + offset + (n+1)*(boxSize-overlapYper))

        offset = 0 if numZ % 2 == 1 else 0.5*(boxSizeZ - overlapZper)
        zList = [origin[2]] if numZ % 2 == 1 else [origin[2] - offset, origin[2] + offset]
        for n in range((numZ-1) // 2): #Ignore the middle 1 or 2 boxes, those were added in the line above
            # Add the next furthest box on each side
            listLen = len(zList)
            zList.insert(0, origin[2] - offset - (n+1)*(boxSizeZ-overlapZper))
            zList.append(origin[2] + offset + (n+1)*(boxSizeZ-overlapZper))

        # Make numX * numY * numZ boxes
        firstSubBox = True
        rot = [n for n in obj.rotation_euler]
        for x in xList:
            for y in yList:
                for z in zList:
                    if not firstSubBox:
                        f.write(",\n\t\t\t\t{\n")
                    else:
                        firstSubBox = False
                    # Check if we need to rotate the positions
                    pos = [x,y,z]
                    if rot.count(0) == 3: # No rotation
                        self.export_collision_box(pos, [boxSize,boxSize,boxSizeZ], obj.mts_collision_settings, f, context)
                    else:
                        newPos = rotate(pos, rot, origin)
                        self.export_collision_box(newPos, [boxSize,boxSize,boxSizeZ], obj.mts_collision_settings, f, context)
            
    def export_collision_box(self, location, dimensions, colset, f, context):
        
        f.write("\t\t\t\t\t\"pos\":[{x}, {y}, {z}],\n".format(x=round(location[0],5), y=round(location[2],5), z=-1*round(location[1],5)))
        
        f.write("\t\t\t\t\t\"width\": {}, \n".format(round(dimensions[0],5)))
        
        f.write("\t\t\t\t\t\"height\": {}".format(round(dimensions[2],5)))
        
        if colset.collidesWithLiquids:
            f.write(",\n\t\t\t\t\t\"collidesWithLiquids\": true")
        
        if colset.damageMultiplier != 1.0:
            f.write(",\n\t\t\t\t\t\"damageMultiplier\": {}".format(colset.damageMultiplier))
            
        if colset.armorThickness != 0:
            f.write(",\n\t\t\t\t\t\"armorThickness\": {}".format(colset.armorThickness))
        
        if colset.heatArmorThickness != 0:
            f.write(",\n\t\t\t\t\t\"heatArmorThickness\": {}".format(colset.heatArmorThickness))
            
        if colset.variableName != "" and colset.variableType != 0:
            f.write(",\n\t\t\t\t\t\"variableName\": \"{}\",".format(colset.variableName))
            f.write("\n\t\t\t\t\t\"variableValue\": {},".format(colset.variableValue))
            f.write("\n\t\t\t\t\t\"variableType\": \"{}\"".format(colset.variableType))
        
        f.write("\n\t\t\t\t}")

#LayoutOperator: Add New Collision Group
class MTS_OT_AddGroupToList(bpy.types.Operator):
    bl_idname = "mts.add_collision_group"
    bl_label = "(MTS/IV) Add Collision Group To Project"
    bl_description = "Add a new collision group to the project"
    
    def execute(self, context):
        context.scene.mts_collision_groups.add()
        context.scene.mts_collision_groups[-1].name = "Collision Group %s" % (len(context.scene.mts_collision_groups))
        
        return {'FINISHED'}

#LayoutOperator: Delete Active Collision Group
class MTS_OT_DeleteGroupFromList(bpy.types.Operator):
    bl_idname = "mts.remove_collision_group"
    bl_label = "(MTS/IV) Add Collision Group From Project"
    bl_description = "Delete the active collision group"
    
    @classmethod
    def poll(cls, context):
        return context.scene.mts_collision_groups
    
    def execute(self, context):
        collision_group_list = context.scene.mts_collision_groups
        index = context.scene.mts_collision_groups_index
        
        for collisionItem in collision_group_list[index].collisions:
            collisionItem.collision.mts_collision_settings.assignedCollisionGroupIndex = -1
            print("Removed collision" + collisionItem.collision.name + " from group")
        
        collision_group_list.remove(index)
        new_index = min(max(0, index - 1), len(collision_group_list) - 1)
        context.scene.mts_collision_groups_index = new_index if new_index >= 0 else 0
        
        return {'FINISHED'}

#Operator: Assign Selected Cube to Collision Group
class MTS_OT_AssignCollisionToGroup(bpy.types.Operator):
    bl_idname = "mts.assign_collision_to_group"
    bl_label = "(MTS/IV) Assign Collision Box to Selected Collision Group"
    bl_description = "Assign the selected collision box to the active collision group"
    
    @classmethod
    def poll(cls, context):
        return context.scene.mts_collision_groups
    
    def execute(self, context):
        cg_list = context.scene.mts_collision_groups
        active_cg_index = context.scene.mts_collision_groups_index
        obj_collision_props = context.active_object.mts_collision_settings
        
        print("Assigned: " + obj_collision_props.assignedCollisionGroupIndex.__str__() + " | Active: " + active_cg_index.__str__())
        
        if obj_collision_props.assignedCollisionGroupIndex != -1 and obj_collision_props.assignedCollisionGroupIndex == active_cg_index:
            if context.active_object == cg_list[active_cg_index].collisions[obj_collision_props.self_index].collision:
               
                print(context.active_object.name + " | " + cg_list[active_cg_index].collisions[obj_collision_props.self_index].collision.name)
               
                print(obj_collision_props.assignedCollisionGroupIndex.__str__() + " already exist at " + active_cg_index.__str__())
                
                self.report({'INFO'}, "Collision Box already assigned to this group")
                
                return {'CANCELLED'}
            
            else:
                
                self.report({'INFO'}, "Duplicate Index Found")
                obj_collision_props.assignedCollisionGroupIndex = -1
                self.report({'INFO'}, "Error Fixed. Please Assign To Group Again")
                
                return {'CANCELLED'}
        
        else:
            if obj_collision_props.assignedCollisionGroupIndex != -1 and obj_collision_props.assignedCollisionGroupIndex != active_cg_index and cg_list[active_cg_index]:
                print("removed from previous group: " + obj_collision_props.assignedCollisionGroupIndex.__str__())
                cg_list[obj_collision_props.assignedCollisionGroupIndex].collisions.remove(obj_collision_props.self_index)
                
            obj_collision_props.assignedCollisionGroupIndex = active_cg_index
            new_collision = cg_list[obj_collision_props.assignedCollisionGroupIndex].collisions.add()
            new_collision.collision = context.active_object
            obj_collision_props.self_index = len(cg_list[obj_collision_props.assignedCollisionGroupIndex].collisions) - 1
            
            print("new index: " + obj_collision_props.assignedCollisionGroupIndex.__str__())
            
            self.report({'INFO'}, "Assigned Collision Box to Collision Group: %s" % (cg_list[obj_collision_props.assignedCollisionGroupIndex].name))
            
            return {'FINISHED'}

#LayoutOperator: Delete Active Collision Group
class MTS_OT_DeleteCollisionFromGroup(bpy.types.Operator):
    bl_idname = "mts.remove_collision_from_group"
    bl_label = "(MTS/IV) Remove Collision From Collision Group"
    bl_description = "Remove the active collision from the active collision group"
    
    @classmethod
    def poll(cls, context):
        return context.scene.mts_collision_groups
    
    def execute(self, context):
        collision_group_list = context.scene.mts_collision_groups
        cg_index = context.scene.mts_collision_groups_index
        
        active_group = collision_group_list[cg_index]
        
        if len(active_group.collisions) > 0:
            active_collision = active_group.collisions[active_group.collision_index]
                    
            if active_collision.collision:
                print("Removed collision" + active_collision.collision.name + " from group " + active_group.name)
                active_collision.collision.mts_collision_settings.self_index = -1
                active_collision.collision.mts_collision_settings.assignedCollisionGroupIndex = -1
                
            active_group.collisions.remove(active_group.collision_index)
            new_index = min(max(0, active_group.collision_index - 1), len(active_group.collisions) - 1)
            active_group.collision_index = new_index if new_index >= 0 else 0
        
        return {'FINISHED'}

# #Operator: Mark selected objects as collisions/doors
# class MTS_OT_AssignAllToGroup(bpy.types.Operator):
#     #Class options
#     bl_idname = "mts.assign_all_to_group"
#     bl_label = "(MTS/IV) Assign All Selected Objects to the Active Collision Group"
#     bl_description = "A"
        
#     @classmethod
#     def poll(cls, context):
#         return len(context.selected_objects) > 0
    
#     def execute(self, context):
#         for obj in context.selected_objects:
#             bpy.context.view_layer.objects.active = obj
#             bpy.ops.mts.assign_collision_to_group()
#         return {'FINISHED'}

#PropertyGroup: Collision Box
class CollisionBoxItem(bpy.types.PropertyGroup):
    
    assignedCollisionGroupIndex: IntProperty(
        name = "Assigned Collision Group Index",
        default = -1
    )
    
    self_index: IntProperty(
        name = "Self Index",
        default = -1
    )
        
    collidesWithLiquids: BoolProperty(
        name = "Collides With Liquids",
        default = False
    )
    
    armorThickness: FloatProperty(
        name = "Armour Thickness",
        default = 0.0,
        min = 0,
        max = 1000
    )
    
    heatArmorThickness: FloatProperty(
        name = "Heat Armour Thickness",
        default = 0.0,
        min = 0,
        max = 1000
    )
    
    damageMultiplier: FloatProperty(
        name = "Damage Multiplier",
        default = 1.0,
        min = 0,
        max = 1000
    )
    
    variableName: StringProperty(
        name = "Variable Name",
        default = ""
    )
    
    variableValue: IntProperty(
        name = "Variable Value",
        default = 0
    )
    
    variableType: EnumProperty(
        name = "Variable Type",
        default = "toggle",
        items = [
            ("toggle",      "Toggle",       "Clicking this box will toggle the variable from 0 to 1, or 1 to 0 depending on current value"),
            ("set",         "Set",          "Clicking this box will set the variable to the defined value"),
            ("increment",   "Increment",    "Clicking this box will increment the variable by the defined value"),
            ("button",      "Button",       "Clicking this box will set the variable to the value. When the player lets go of the mouse button, it will be set back to 0")
        ]
    )
        
    subdivideWidth: FloatProperty(
        name = "Subdivision Width",
        default = 0.0,
        min = 0,
        max = 1000
    )
        
    subdivideHeight: FloatProperty(
        name = "Subdivision Height",
        default = 0.0,
        min = 0,
        max = 1000
    )

#PropertyGroup: Pointer Property of Type Collision Box 
class CollisionBoxPointer(bpy.types.PropertyGroup):
    
    collision: PointerProperty(
        type = bpy.types.Object
    )

#PropertyGroup: Collision Group
class CollisionGroupItem(bpy.types.PropertyGroup):
    
    name: StringProperty(
        name = "Name",
        default = "Collision Group"
    )
    
    isInterior: BoolProperty(
        name = "Is Interior",
        default = False
    )
    
    isForBullets : BoolProperty(
        name = "Is For Bullets",
        default = False
    )
    
    health: IntProperty(
        name = "Health",
        default = 0,
        min = 0,
        max = 9999,
        soft_max = 100
    )
    
    applyAfter: StringProperty(
        name = "Apply After",
        default = ""
    )
    
    collisions: CollectionProperty(
        type = CollisionBoxPointer
    )
    
    collision_index: IntProperty(
        name = "Collision Index",
        default = 0
    )

#UIList: Collision Groups
class MTS_UL_CollisionGroupsList(UIList):
    bl_idname = "MTS_UL_collisiongroupslist"
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        custom_icon = 'OUTLINER_COLLECTION'
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if index == context.scene.mts_collision_groups_index:
                layout.prop(item, "name", text="", emboss=False, icon=custom_icon)
            else:
                layout.label(text=item.name, icon=custom_icon)
            
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon=custom_icon)

#UIList: Collisions
class MTS_UL_CollisionsList(UIList):
    bl_idname = "MTS_UL_collisionslist"
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        custom_icon = 'MESH_CUBE'
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.collision.name, icon=custom_icon)
            
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon=custom_icon)

#Panel: Draw the collision groups panel
class MTS_PT_MTSCollisionGroupPanel(Panel):
    bl_idname = "MTS_PT_mtscollisiongroup"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_label = "MTS/IV Collision Groups"
    
    def draw(self, context):
        layout = self.layout
        
        row = layout.row(align=True)
        column = row.column(align=True)
        column.template_list("MTS_UL_collisiongroupslist", "MTS_Collision_Groups", context.scene, "mts_collision_groups", context.scene, "mts_collision_groups_index")
        if context.scene.mts_collision_groups and len(context.scene.mts_collision_groups) >= 0:
            activeItem = context.scene.mts_collision_groups[context.scene.mts_collision_groups_index]
            column.prop(activeItem, "name", icon="OUTLINER_COLLECTION", text="")
        
        column = row.column(align=True)
        column.operator("mts.add_collision_group", icon='ADD', text="")
        column.operator("mts.remove_collision_group", icon='REMOVE', text="")
        
        if context.scene.mts_collision_groups and len(context.scene.mts_collision_groups) >= 0:
            activeItem = context.scene.mts_collision_groups[context.scene.mts_collision_groups_index]

            layout.separator()
            
            row = layout.row()
            row.label(text="Collision Group properties:")
            
            box = layout.box()
            
            row = box.row()
            row.prop(activeItem, "isInterior", icon="MOD_WIREFRAME")
            row.prop(activeItem, "isForBullets", icon="STYLUS_PRESSURE")
            
            row = box.row()
            row.prop(activeItem, "health", slider=True, icon="ADD")
            
            row = box.row()
            row.prop(activeItem, "applyAfter", text="Apply After", icon="LIBRARY_DATA_INDIRECT")
            
            layout.separator()
            
            row = layout.row()
            row.label(text="Collisions:")
            
            row = layout.row()
            row.template_list("MTS_UL_collisionslist", "MTS_Collisions", activeItem, "collisions", activeItem, "collision_index")
            
            column = row.column(align=True)
            column.operator("mts.remove_collision_from_group", icon='REMOVE', text="")

#Panel: Draw the collision box panel
class MTS_PT_MTSCollisionPanel(Panel):
    bl_idname = "MTS_PT_mtscollision"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "MTS/IV Collision Properties"
    
    #Draw function
    def draw(self, context):
        obj = context.object
        collisionsettings = obj.mts_collision_settings
        
        layout = self.layout
        
        #import export operators
        row = layout.row()
        row.operator(icon='EXPORT', operator="mts.export_collision_boxes")
        row.operator(icon='IMPORT', operator="mts.import_collision_boxes")
        
        layout.separator()
        
        row = layout.row()
        row.label(text="Collision Groups in Project:")
        
        #UIList of collision groups in project
        row = layout.row(align=True)
        column = row.column(align=True)
        column.template_list("MTS_UL_collisiongroupslist", "MTS_Collision_Groups", context.scene, "mts_collision_groups", context.scene, "mts_collision_groups_index")
        if context.scene.mts_collision_groups and len(context.scene.mts_collision_groups) >= 0:
            activeItem = context.scene.mts_collision_groups[context.scene.mts_collision_groups_index]
            column.prop(activeItem, "name", icon="OUTLINER_COLLECTION", text="")
        
        #+/- collision group buttons
        column = row.column(align=True)
        column.operator("mts.add_collision_group", icon='ADD', text="")
        column.operator("mts.remove_collision_group", icon='REMOVE', text="")
        
        layout.separator()
        
        row = layout.row(align=True)
        column = row.column()
        if collisionsettings.assignedCollisionGroupIndex >= 0:
            column.prop(context.scene.mts_collision_groups[collisionsettings.assignedCollisionGroupIndex], "name", icon="OUTLINER_COLLECTION", text="Assigned To")
        else:
            column.label(text="Assigned To:")
        
        #assign/remove object from collision group
        row = layout.row(align=True)
        row.operator("mts.assign_collision_to_group", text="Assign")
        row.operator("mts.remove_collision_from_group", text="Remove")
        
        layout.separator()
        
        #collision properties
        row = layout.row()
        row.label(text="Collision Box Properties")
        
        box = layout.box()
        
        row = box.row()
        row.prop(collisionsettings, "collidesWithLiquids", icon="FORCE_FORCE")
        
        row = box.row()
        row.prop(collisionsettings, "armorThickness")
        row.prop(collisionsettings, "heatArmorThickness")
        
        layout.separator()
        
        layout.label(text="Variable Properties")
        box = layout.box()
        
        variableRow1 = box.row()
        
        column = variableRow1.column()
        column.label(text="Variable Name:")
        column.prop(collisionsettings, "variableName", text="", icon="DRIVER_TRANSFORM")
        
        column = variableRow1.column()
        column.label(text="Variable Type:")
        column.prop(collisionsettings, "variableType", text="")
        
        variableRow2 = box.row()
        variableRow2.prop(collisionsettings, "variableValue")
        
        layout.separator()
        
        layout.label(text="Subdivision Settings")
        box = layout.box()
        row = box.row()
        row.prop(collisionsettings, "subdivideWidth")
        row.prop(collisionsettings, "subdivideHeight")

#Panel: Parent for drawing the main MTS/IV tab in the numbers panel
class MTS_View3D_Parent:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MTS/IV"
    
#Panel: Draw the collision tools panel in the numbers panel
class MTS_V3D_CollisionPanel(MTS_View3D_Parent, Panel):
    bl_idname = "MTS_PT_V3D_collisionpanel"
    bl_label = "MTS/IV Collision Tools"

    #Draw function
    def draw(self, context):
        layout = self.layout
        
        # row = layout.row()
        # row.operator("mts.assign_all_to_group", text="Assign Selected")
        
        row = layout.row()
        row.operator(icon="EXPORT", operator="mts.export_collision_boxes", text="Export Collisions")
        
        row = layout.row()
        row.operator(icon="IMPORT", operator="mts.import_collision_boxes", text="Import Collisions")

#Create export button for export menu
def menu_func_export(self, context):
    self.layout.operator("mts.export_collision_boxes", text="MTS/IV Collision Boxes Array (.json)")

#Create import button for import menu
def menu_func_import(self, context):
    self.layout.operator("mts.import_collision_boxes", text="MTS/IV JSON(.json)")
    

def rotate(v, axis, center):
    # Takes a vector and a rotation axis, and returns the rotated vector
    relV = NP.subtract(v, center) # Make sure we rotate about the origin
    cosX = math.cos(axis[0])
    sinX = math.sin(axis[0])
    cosY = math.cos(axis[1])
    sinY = math.sin(axis[1])
    cosZ = math.cos(axis[2])
    sinZ = math.sin(axis[2])

    rotatedV = [relV[0]*(cosY*cosZ-sinX*-sinY*sinZ)    + relV[1]*(-sinX*-sinY*cosZ-cosY*sinZ)    + relV[2]*(-cosX*-sinY),
                relV[0]*(cosX*sinZ)                    + relV[1]*(cosX*cosZ)                     + relV[2]*(-sinX),
                relV[0]*(-sinY*cosZ+sinX*cosY*sinZ)    + relV[1]*(sinX*cosY*cosZ+sinY*sinZ)      + relV[2]*(cosX*cosY)]

    return NP.add(rotatedV, center) # Add the origin back in when we're done

class MTS_OT_install_dependencies(bpy.types.Operator):
    bl_idname = "mts.install_dependencies"
    bl_label = "Install dependencies"
    bl_description = ("Downloads and installs the required python packages for this add-on. "
                      "Internet connection is required. Blender may have to be started with "
                      "elevated permissions in order to install the package")
    bl_options = {"REGISTER", "INTERNAL"}

    @classmethod
    def poll(self, context):
        # Deactivate when dependencies have been installed
        return not dependencies_installed

    def execute(self, context):
        try:
            install_pip()
            for dependency in dependencies:
                install_and_import_module(module_name=dependency.module,
                                          package_name=dependency.package,
                                          global_name=dependency.name)
        except (subprocess.CalledProcessError, ImportError) as err:
            self.report({"ERROR"}, str(err))
            return {"CANCELLED"}

        global dependencies_installed
        dependencies_installed = True

        # Register the panels, operators, etc. since dependencies are installed
        for cls in classes:
            bpy.utils.register_class(cls)

        return {"FINISHED"}

class MTS_Preferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
        layout = self.layout
        layout.operator(MTS_OT_install_dependencies.bl_idname, icon="CONSOLE")

preference_classes = (
    MTS_OT_install_dependencies,
    MTS_Preferences,
)

classes = (
    MTS_OT_ImportCollisions,
    MTS_OT_ExportCollisions,
    MTS_OT_AddGroupToList,
    MTS_OT_DeleteGroupFromList,
    MTS_OT_AssignCollisionToGroup,
    MTS_OT_DeleteCollisionFromGroup,
    # MTS_OT_AssignAllToGroup,
    CollisionBoxItem,
    CollisionBoxPointer,
    CollisionGroupItem,
    MTS_UL_CollisionGroupsList,
    MTS_UL_CollisionsList,
    MTS_PT_MTSCollisionGroupPanel,
    MTS_PT_MTSCollisionPanel,
    MTS_V3D_CollisionPanel,
)
   
def register():
    from bpy.utils import register_class
    
    for cls in preference_classes:
        register_class(cls)
    
    global dependencies_installed
    dependencies_installed = False
        
    try:
        for dependency in dependencies:
            import_module(module_name=dependency.module, global_name=dependency.name)
        dependencies_installed = True
    except ModuleNotFoundError:
        # Don't register other panels, operators etc.
        return
    
    for cls in classes:
        register_class(cls)
        
    bpy.types.Scene.mts_collision_groups = CollectionProperty(type=CollisionGroupItem)
    bpy.types.Scene.mts_collision_groups_index = IntProperty(name="mts_collision_groups_index", default=0)
    bpy.types.Object.mts_collision_settings = PointerProperty(type=CollisionBoxItem)
    
    #Append the export operator to the export menu
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    #Append the import operator to the import menu
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
        
def unregister():
    
    #Remove the export operator from the export menu
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    #Remove the import operator from the import menu
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    
    from bpy.utils import unregister_class
    for cls in preference_classes:
        unregister_class(cls)
        
    if dependencies_installed:
        for cls in classes:
            bpy.utils.unregister_class(cls)
        
if __name__ == "__main__":
    register()
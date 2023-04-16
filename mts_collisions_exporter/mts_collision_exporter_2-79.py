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
    "name": "MTS/IV Collision Box Exporter",
    "author": "Turbo Defender | Gyro Hero | Laura Darkez",
    "version": (2, 1),
    "blender": (2, 79, 0),
    "location": "Object Properties —> MTS/IV Collision Properties",
    "description": "Exports Blender cubes as MTS/IV collision boxes",
    "category": "MTS"
}

#Import blender modules
import bpy
from bpy.types import Panel
from bpy_extras.io_utils import (ExportHelper, ImportHelper)
from bpy.props import (
        BoolProperty,
        BoolVectorProperty,
        EnumProperty,
        FloatProperty,
        IntProperty,
        PointerProperty,
        StringProperty,
        )

#Import python bundled modules
import math
import numpy as NP
import json

##Operator: Importer
class MTS_OT_ImportCollisions(bpy.types.Operator, ImportHelper):
    #Class options
    bl_idname = "mts.import_collision_boxes"
    bl_label = "Import Collisions"
    bl_description = "Import collision boxes from a JSON file"
    
    filename_ext = ".json"
    filter_glob= StringProperty(
            default="*.json",
            options={'HIDDEN'},
            )
    
    def execute(self, context):
        
        with open(self.filepath, 'r') as f:
            file = json.loads(f.read())
        
            if 'collision' in file and len(file['collision']) > 0:
                collisions = file['collision']
                
                for collision in collisions:
                    width = collision['width']
                    height = collision['height']
                    pos = collision['pos']
                    collidesWithLiquids = False
                    armorThickness = 0
                    heatArmorThickness = 0
                    damageMultiplier = 0
                    variableName = ""
                    variableValue = 0
                    variableType = "toggle"
                    
                    if 'collidesWithLiquids' in collision:
                        collidesWithLiquids = collision['collidesWithLiquids']
                        
                    if 'armorThickness' in collision:
                        armorThickness = collision['armorThickness']
                        
                    if 'heatArmorThickness' in collision:
                        heatArmorThickness = collision['heatArmorThickness']
                        
                    if 'damageMultiplier' in collision:
                        damageMultiplier = collision['damageMultiplier']
                        
                    if 'variableName' in collision:
                        variableName = collision['variableName']
                        
                    if 'variableValue' in collision:
                        variableValue = collision['variableValue']
                        
                    if 'variableType' in collision:
                        variableType = collision['variableType']
                        
                    bpy.ops.mesh.primitive_cube_add(radius=2, location=(pos[0], -1*pos[2], pos[1]))
                    obj = context.object                    
                    obj.dimensions = (width, width, height)
                    settings = obj.mts_collision_settings
                    settings.collisionType = (False, True, False)
                    settings.collidesWithLiquids = collidesWithLiquids
                    settings.armorThickness = armorThickness
                    settings.heatArmorThickness = heatArmorThickness
                    settings.damageMultiplier = damageMultiplier
                    settings.variableName = variableName
                    settings.variableValue = variableValue
                    settings.variableType = variableType
                    
            else:
                self.report({'ERROR_INVALID_INPUT'}, "NO COLLISIONS FOUND")
                return {'CANCELLED'}
        
        self.report({'OPERATOR'}, "Import Finished")
        bpy.ops.object.select_all(action='TOGGLE')
        bpy.ops.object.select_all(action='TOGGLE')
        return {'FINISHED'}

##Operator: Exporter      
class MTS_OT_ExportCollisions(bpy.types.Operator, ExportHelper):
    #Class options
    bl_idname = "mts.export_collision_boxes"
    bl_label = "Export Collisions"
    bl_description = "Export collision and door boxes as a JSON snippet"
    
    filename_ext = ".json"

    def execute(self, context):
        self.report({'INFO'}, "Export Started")
        f = open(self.filepath, "w")
        
        self.collision = []
        
        #Write Collisions
        for obj in context.scene.objects:
            if obj.mts_collision_settings.collisionType[1]:
                if (obj.mts_collision_settings.subdivideWidth > 0) or (obj.dimensions[0] != obj.dimensions[1]):
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
                    rot = [n for n in obj.rotation_euler]
                    for x in xList:
                        for y in yList:
                            for z in zList:
                                # Check if we need to rotate the positions
                                pos = [x,y,z]
                                if rot.count(0) == 3: # No rotation
                                    self.export_collision_box(pos, [boxSize,boxSize,boxSizeZ], obj.mts_collision_settings, f, context)
                                else:
                                    newPos = rotate(pos, rot, origin)
                                    self.export_collision_box(newPos, [boxSize,boxSize,boxSizeZ], obj.mts_collision_settings, f, context)

                else:
                    self.export_collision_box(obj.location, obj.dimensions, obj.mts_collision_settings, f, context)
        
        json.dump({ 'collision': self.collision }, f, indent=2)
        
        self.report({'INFO'}, "Export Complete")

        return {'FINISHED'}
            
    def export_collision_box(self, location, dimensions, colset, f, context):
        
        collision_box = {
            'pos': [
                round(location[0],5),
                round(location[2],5),
                -1*round(location[1],5)
            ],
            
            'width': round(dimensions[0],5),
            
            'height': round(dimensions[2],5)
        }
        
        if colset.collidesWithLiquids:
            collision_box['collidesWithLiquids'] = True
        
        if colset.armorThickness > 0:
            collision_box['armorThickness'] = colset.armorThickness
        
        if colset.heatArmorThickness > 0:
            collision_box['heatArmorThickness'] = colset.heatArmorThickness
        
        if colset.heatArmorThickness != 1.0:
            collision_box['heatArmorThickness'] = colset.heatArmorThickness
        
        if colset.variableName != "" and colset.variableValue != 0:
            collision_box['variableName'] = colset.variableName
            collision_box['variableValue'] = colset.variableValue
            collision_box['variableType'] = colset.variableType

        self.collision.append(collision_box)
            
#Operator: Mark selected objects as collisions/doors
class MTS_OT_MarkAsCollision(bpy.types.Operator):
    #Class options
    bl_idname = "mts.mark_as_collision"
    bl_label = "(MTS/IV) Mark all selected as collision"
    bl_description = "Mark selected objects as a collision box"
    
    @classmethod
    def poll(cls, context):
        return context.object is not None
    
    def execute(self, context):
        for obj in context.selected_objects:
                obj.mts_collision_settings['collisionType'] = (False, True)
                if ('defaultsSet' not in obj.mts_collision_settings):
                    obj.mts_collision_settings['defaultsSet'] = True
                    obj.mts_collision_settings['collidesWithLiquids'] = False
                    obj.mts_collision_settings['armorThickness'] = 0
                    obj.mts_collision_settings['heatArmorThickness'] = 0
                    obj.mts_collision_settings['damageMultiplier'] = 0
                    obj.mts_collision_settings['variableName'] = ""
                    obj.mts_collision_settings['variableValue'] = 0
                    obj.mts_collision_settings['variableType'] = "toggle"
                    obj.mts_collision_settings['manualSubdivision'] = False
                    obj.mts_collision_settings['subdivideWidth'] = 0
                    obj.mts_collision_settings['subdivideHeight'] = 0
        return {'FINISHED'}

def get_collision_type(self):
    if ('collisionType' in self):
        return self['collisionType']
    else:
        return (True, False) 

def set_collision_type(self, value):
    if ('collisionType' in self):
        prevValue = self['collisionType']
    else:
        prevValue = (True, False) 
    
    new_value = (False, False)
    
    if (prevValue[0] != value[0]):
        new_value = (True, False)
        
    elif (prevValue[1] != value[1]):
        if(value[1] == False):
            new_value = (True, False)
        else:
            new_value = (False, True)
        
    if ('defaultsSet' not in self):
        self['defaultsSet'] = True
        self['collidesWithLiquids'] = False
        self['armorThickness'] = 0
        self['heatArmorThickness'] = 0
        self['damageMultiplier'] = 0
        self['variableName'] = ""
        self['variableValue'] = 0
        self['variableType'] = "toggle"
        self['manualSubdivision'] = False
        self['subdivideWidth'] = 0
        self['subdivideHeight'] = 0
        
    self['collisionType'] = new_value

#Create the custom properties for collision and door boxes  
class CollisionSettings(bpy.types.PropertyGroup):
    
    collisionType= BoolVectorProperty(
        name = "Collision Type",
        default=(True, False),
        size=2,
        set=set_collision_type,
        get=get_collision_type
        )
    
    defaultsSet= BoolProperty(
        default=False
        )
        
    collidesWithLiquids= BoolProperty(
        name = "Collides With Liquids",
        default = False
        )
    
    armorThickness= FloatProperty(
        name = "Armour Thickness",
        default = 0.0,
        min = 0,
        max = 1000
        )
    
    heatArmorThickness= FloatProperty(
        name = "Heat Armour Thickness",
        default = 0.0,
        min = 0,
        max = 1000
        )
    
    damageMultiplier= FloatProperty(
        name = "Damage Multiplier",
        default = 1.0,
        min = 0,
        max = 1000
        )
    
    variableName= StringProperty(
        name = "Variable Name",
        default = ""
        )
    
    variableValue= IntProperty(
        name = "Variable Value",
        default = 0
        )
    
    variableType= EnumProperty(
        name = "Variable Type",
        default = "toggle",
        items = [
            ("toggle",      "Toggle",       "Clicking this box will toggle the variable from 0 to 1, or 1 to 0 depending on current value"),
            ("set",         "Set",          "Clicking this box will set the variable to the defined value"),
            ("increment",   "Increment",    "Clicking this box will increment the variable by the defined value"),
            ("button",      "Button",       "Clicking this box will set the variable to the value. When the player lets go of the mouse button, it will be set back to 0")
        ]
        )
    
    manualSubdivision= BoolProperty(
        name = "Manual Subdivision",
        default = False
        )
        
    subdivideWidth= FloatProperty(
        name = "Subdivision Width",
        default = 0.0,
        min = 0,
        max = 1000
        )
        
    subdivideHeight= FloatProperty(
        name = "Subdivision Height",
        default = 0.0,
        min = 0,
        max = 1000
        )

#Panel: Draw the collision and door box panel
class MTS_PT_MTSCollisionBasePanel(Panel):
    #Class options
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "MTS/IV Collision Properties"
    bl_idname = "OBJECT_PT_mtscollision"
    
    #Draw function
    def draw(self, context):
        #create a layout
        layout = self.layout
        #get the current active object
        obj = context.object
        #get it's custom properties
        collisionsettings = obj.mts_collision_settings
        
        row = layout.row(align=True)
        #import operator button
        row.operator(icon='IMPORT', operator="mts.import_collision_boxes")
        #export operator button
        row.operator(icon='EXPORT', operator="mts.export_collision_boxes")
        row = layout.row()

        row = layout.row()
        row.label(text="Collision Type:")
        row = layout.row(align=True)
        row.prop(collisionsettings, "collisionType", text = "None", index=0, icon='OBJECT_DATA')
        row.prop(collisionsettings, "collisionType", text = "Collision Box", index=1, icon='VIEW3D')
        
        layout.separator()
        
        #check if the collision property is enabled
        if collisionsettings['collisionType'][1] == True:
            row = layout.row()
            box = row.box()
            
            row = box.row()
            row.label(text="Collision Box:")
            
            row = box.row()
            row.prop(collisionsettings, "collidesWithLiquids", icon='MOD_WAVE')
            row.prop(collisionsettings, "damageMultiplier")
            
            row = box.row()
            row.prop(collisionsettings, "armorThickness")
            row.prop(collisionsettings, "heatArmorThickness")
            
            box.separator()
            
            row = box.row()
            row.label("Variable:")
            
            row = box.row()
            row.prop(collisionsettings, "variableName", text="Name")
            
            row = box.row()
            row.prop(collisionsettings, "variableValue")
            row.prop(collisionsettings, "variableType", text="")
            
            box.separator()
            
            row = box.row()
            row.label("Subdivision:")
            
            row = box.row()
            row.prop(collisionsettings, "manualSubdivision", icon='MODIFIER')
            
            if (collisionsettings['manualSubdivision']):
                row = box.row()
                #width of subdivision, to split a big box into multiple ones
                row.prop(collisionsettings, "subdivideWidth")
                #height of the subdivision, to split a big box into multiple ones
                row.prop(collisionsettings, "subdivideHeight")
            
#Panel: Parent for drawing the main MTS/IV tab in the numbers panel
class MTS_View3D_Parent:
    #Class options
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'

#Panel: Draw the collision tools panel in the numbers panel
class MTS_V3D_CollisionPanel(MTS_View3D_Parent, Panel):
    #Class options
    bl_category = "MTS/IV"
    bl_context = "objectmode"
    bl_label = "MTS/IV Collision Tools"
    bl_idname = "MTS_PT_V3D_collisionpanel"

    #Draw function
    def draw(self, context):
        #create a layout
        layout = self.layout
        row = layout.row()
        #mark as collision operator button
        row.operator("mts.mark_as_collision", text="Mark As Collision")
        row = layout.row()
        #import operator button
        row.operator(operator="mts.import_collision_boxes")
        row = layout.row()
        #export operator button
        row.operator(operator="mts.export_collision_boxes")

#Create export button for export menu
def menu_func_export(self, context):
    self.layout.operator("mts.export_collision_boxes", text="MTS/IV Collisions(.json)")

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

classes = (
    MTS_OT_ImportCollisions,
    MTS_OT_ExportCollisions,
    MTS_OT_MarkAsCollision,
    CollisionSettings,
    MTS_PT_MTSCollisionBasePanel,
    MTS_V3D_CollisionPanel,
)
        
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
        
    bpy.types.Object.mts_collision_settings = PointerProperty(type=CollisionSettings)
    
    #Append the export operator to the export menu
    bpy.types.INFO_MT_file_export.append(menu_func_export)
    #Append the import operator to the import menu
    bpy.types.INFO_MT_file_import.append(menu_func_import)
    
        
def unregister():
    
    #Remove the export operator from the export menu
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    #Remove the import operator from the import menu
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
        
if __name__ == "__main__":
    register()
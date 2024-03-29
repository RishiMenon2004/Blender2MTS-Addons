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
    "version": (1, 8),
    "blender": (2, 90, 0),
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
        FloatProperty,
        StringProperty,
        EnumProperty,
        PointerProperty,
        )

#Import python bundled modules
import math
import numpy as NP
import json
        
#Operator: Importer
class MTS_OT_ImportCollisions(bpy.types.Operator, ImportHelper):
    #Class options
    bl_idname = "mts.import_collision_boxes"
    bl_label = "Import Collisions"
    bl_description = "Import collision and door boxes from a JSON file"
    
    filename_ext = ".json"
    filter_glob: StringProperty(
            default="*.json",
            options={'HIDDEN'},
            )
    
    def execute(self, context):
        col_name = 'Collision and Doors'
        if 'Collision and Doors' not in bpy.data.collections:
            bpy.ops.collection.create(name=col_name)
            box_collection = bpy.data.collections[col_name]
            bpy.context.scene.collection.children.link(box_collection)
            
        box_collection = bpy.context.view_layer.layer_collection.children[col_name]
        bpy.context.view_layer.active_layer_collection = box_collection
        
        
        with open(self.filepath, 'r') as f:
            file = json.loads(f.read())
        
            if 'collision' in file:
                collisions = file['collision']
                
                for collision in collisions:
                    width = collision['width']
                    height = collision['height']
                    pos = collision['pos']
                    
                    if 'collidesWithLiquids' in collision:
                        floats = collision['collidesWithLiquids']
                    else:
                        floats = False
                        
                    if 'isInterior' in collision:
                        interior = collision['isInterior']
                    else:
                        interior = False
                        
                    if 'armorThickness' in collision:
                        armor = collision['armorThickness']
                    else:
                        armor = False
                        
                    bpy.ops.mesh.primitive_cube_add(size=1, location=(pos[0], -1*pos[2], pos[1]), scale=(width, width, height))
                    obj = context.object
                    settings = obj.mts_collision_settings
                    settings.isCollision = True
                    settings.collidesWithLiquids = floats
                    settings.isInterior = interior
                    settings.armorThickness = armor
                
            if 'doors' in file:
                doors = file['doors']
                
                for door in doors:
                    name = door['name']
                    width = door['width']
                    height = door['height']
                    closedPos = door['closedPos']
                    openPos = door['openPos']
                    
                    if 'closeOnMovement' in door:
                        movement = door['closeOnMovement']
                    else:
                        movement = False
                        
                    if 'closedByDefault' in door:
                        default = door['closedByDefault']
                    else:
                        default = False    
                        
                    if 'activateOnSeated' in door:
                        seated = door['activateOnSeated']
                    else:
                        seated = False    
                        
                    if 'ignoresClicks' in door:
                        clicks = door['ignoresClicks']
                    else:
                        clicks = False

                    if 'armorThickness' in door:
                        armor = door['armorThickness']
                    else:
                        armor = 0
                    
                    bpy.ops.mesh.primitive_cube_add(size=2, location=(closedPos[0], -1*closedPos[2], closedPos[1]), scale=(width, width, height))
                    closedobj = context.object
                    closedobj.name = name + "_closed"
                    
                    bpy.ops.mesh.primitive_cube_add(size=2, location=(openPos[0], -1*openPos[2], openPos[1]), scale=(width, width, height))
                    openobj = context.object
                    openobj.name = name + "_open"
                    openobj.display_type = "WIRE"
                    
                    settings = closedobj.mts_collision_settings
                    
                    settings.isDoor = True
                    settings.doorName = name
                    openobj.mts_collision_settings.doorName = name
                    settings.closeOnMovement = movement
                    settings.closedByDefault = default
                    settings.activateOnSeated = seated
                    settings.ignoresClicks = clicks
                    settings.doorArmorThickness = armor
                    settings.openPos = openobj
                    
            if 'collision' not in file or 'doors' not in file:
                self.report({'ERROR_INVALID_INPUT'}, "NO COLLISIONS FOUND")
                return {'CANCELLED'}
        
        self.report({'OPERATOR'}, "Import Finished")
        return {'FINISHED'}

#Operator: Exporter      
class MTS_OT_ExportCollisions(bpy.types.Operator, ExportHelper):
    #Class options
    bl_idname = "mts.export_collision_boxes"
    bl_label = "Export Collisions"
    bl_description = "Export collision and door boxes as a JSON snippet"
    
    filename_ext = ".json"

    def execute(self, context):
        firstEntry = True
        self.report({'INFO'}, "Export Started")
        f = open(self.filepath, "w")
        
        #Write Collisions
        f.write("{\n    \"collision\": [\n") 
        for obj in context.scene.objects:
            if obj.mts_collision_settings.isCollision and not obj.mts_collision_settings.isDoor:
                if firstEntry:
                    f.write("        {\n")
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
                                if not(firstEntry):
                                    f.write(",\n        {\n")
                                else:
                                    firstEntry = False
                                # Check if we need to rotate the positions
                                pos = [x,y,z]
                                if rot.count(0) == 3: # No rotation
                                    self.export_collision_box(obj.name, pos, [boxSize,boxSize,boxSizeZ], obj.mts_collision_settings, f, context)
                                else:
                                    newPos = rotate(pos, rot, origin)
                                    self.export_collision_box(obj.name, newPos, [boxSize,boxSize,boxSizeZ], obj.mts_collision_settings, f, context)


                else:
                    if not(firstEntry):
                        f.write(",\n        {\n")
                    self.export_collision_box(obj.name, obj.location, obj.dimensions, obj.mts_collision_settings, f, context)

                if firstEntry:
                    firstEntry = False
                
        f.write("\n    ],\n\n")
        
        #Write Doors
        f.write("    \"doors\": [\n")
        firstEntry = True
        for obj in context.scene.objects:
            if obj.mts_collision_settings.isDoor:
                if obj.mts_collision_settings['openPos'] == None:
                    self.report({'INFO'}, "openPos was not defined for %s" % (obj.name))
                if firstEntry:
                    firstEntry = False
                    f.write("        {\n")
                else:
                    f.write(",\n        {\n")
                self.export_doors(obj, obj.mts_collision_settings, f, context)
        f.write("\n    ],")
        f.write("\n}")
        
        self.report({'OPERATOR'}, "Export Complete")

        return {'FINISHED'}
            
    def export_collision_box(self, name, location, dimensions, colset, f, context):
        
        f.write("            \"name\": \"%s\",\n" % name)
        
        f.write("            \"pos\": [%s, %s, %s],\n" % (round(location[0],5), round(location[2],5), -1*round(location[1],5)))
        
        f.write("            \"width\": %s, \n" % (round(dimensions[0],5)))
        
        f.write("            \"height\": %s" % (round(dimensions[2],5)))
        
        if colset.isInterior:
            f.write(",\n            \"isInterior\": true")
        
        if colset.collidesWithLiquids:
            f.write(",\n            \"collidesWithLiquids\": true")
        
        if colset.armorThickness != 0:
            f.write(",\n            \"armorThickness\": %s" % (colset.armorThickness))
        
        f.write("\n        }")
        
    def export_doors(self, obj, colset, f, context):
        
        openPos = colset.openPos
        
        #write the entries for one collision
        f.write("            \"name\": \"%s\",\n" % (colset.doorName))
        
        f.write("            \"closedPos\":[%s, %s, %s],\n" % (round(obj.location[0],5), round(obj.location[2],5), -1*round(obj.location[1],5)))

        if openPos != None:
            f.write("            \"openPos\":[%s, %s, %s],\n" % (round(openPos.location[0],5), round(openPos.location[2],5), -1*round(openPos.location[1],5)))
        else:
            f.write("            \"openPos\": \"was not defined for %s\",\n" % (obj.name))
        
        f.write("            \"width\": %s, \n" % (round(obj.dimensions[0],5)))
        
        f.write("            \"height\": %s" % (round(obj.dimensions[2],5)))
        
        if colset.closedByDefault:
            f.write(",\n            \"closedByDefault\": true")
        
        if colset.closeOnMovement:
            f.write(",\n            \"closeOnMovement\": true")
            
        if colset.activateOnSeated:
            f.write(",\n            \"activateOnSeated\": true")
            
        if colset.ignoresClicks:
            f.write(",\n            \"ignoresClicks\": true")

        if colset.doorArmorThickness != 0:
            f.write(",\n            \"armorThickness\": %s" % (colset.doorArmorThickness))
            
        f.write("\n        }")

#Operator: Mark selelcted objects as collisions/doors
class MTS_OT_MarkAsCollision(bpy.types.Operator):
    #Class options
    bl_idname = "mts.mark_as_collision"
    bl_label = "(MTS/IV) Mark all selected as collison"
    bl_property = "type_search"
    bl_description = "Enable the collsion or door property for the selected objects"
        
    @classmethod
    def poll(cls, context):
        return context.object is not None
    
    type_search: EnumProperty(
    name="Collision Type Search",
    items=(
            ('COLLISION', "Collision", ""),
            ('DOOR', "Door", ""),
        ),
    )
    
    def execute(self, context):
        if self.type_search == 'COLLISION':
            for obj in context.selected_objects:
                    obj.mts_collision_settings['isCollision'] = True
        elif self.type_search == 'DOOR':
            for obj in context.selected_objects:
                    obj.mts_collision_settings['isDoor'] = True
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'RUNNING_MODAL'}

class MTS_OT_MarkAsInterior(bpy.types.Operator):
    bl_idname = "mts.mark_as_interior"
    bl_label = "(MTS/IV) Mark all selected as interior"
    bl_description = "Enable the interior property for the selected objects"
    
    @classmethod
    def poll(cls, context):
        return context.object is not None
    
    def execute(self, context):
        for obj in context.selected_objects:
            obj.mts_collision_settings['isInterior'] = True
        return {'FINISHED'}

#Create the custom properties for collision and door boxes
class CollisionSettings(bpy.types.PropertyGroup):

    def update_open_pos(self, context):
        obj = context.object
        colset = obj.mts_collision_settings
        target_obj = colset.openPos
        target_colset = target_obj.mts_collision_settings
    
        target_colset['isCollision'] = False
        target_colset['isDoor'] = False
        
        return None

    #collisions
    isCollision: BoolProperty(
        name = "Is Collision",
        default = False
        )
                
    isInterior: BoolProperty(
        name = "Interior Collision",
        default = False
        )
        
    collidesWithLiquids: BoolProperty(
        name = "Floats on Liquids",
        default = False
        )
        
    armorThickness: FloatProperty(
        name = "Armour Thickness",
        default = 0.0,
        min = 0,
        max = 1000
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
    
    #doors
    isDoor: BoolProperty(
        name = "Is Door",
        default = False
        )
    
    doorName: StringProperty(
        name = "Door Name",
        default = "unnamed_door"
        )
    
    closedByDefault: BoolProperty(
        name = "Closed by Default",
        default = False
        )
        
    closeOnMovement: BoolProperty(
        name = "Close on Movement",
        default = False
        )
        
    activateOnSeated: BoolProperty(
        name = "Activate When Seated",
        default = False
        )
        
    ignoresClicks: BoolProperty(
        name = "Ignores User Clicks",
        default = False
        )

    doorArmorThickness: FloatProperty(
        name = "Armour Thickness",
        default = 0.0,
        min = 0,
        max = 1000
        )
        
    openPos: PointerProperty(
        type = bpy.types.Object,
        name = "Open Position Box",
        update = update_open_pos
        )

#Panel: Draw the parent panel for the collision boxes and door hitboxes
class MTS_PT_MTSCollisionBasePanel(Panel):
    #Class options
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "MTS/IV Collision Properties"
    bl_idname = "MTS_PT_mtscollision"
    
    #Draw function
    def draw(self, context):
        #create a layout
        layout = self.layout
        row = layout.row()
        #export operator button
        row.operator(icon='EXPORT', operator="mts.export_collision_boxes")
        #import operator button
        row.operator(icon='IMPORT', operator="mts.import_collision_boxes")
        row = layout.row()
        #warning text
        row.label(icon='ERROR', text="Note: openPos boxes should not use the Collision or Door property else it'll mess you up")

#Panel: Draw the collision box panel
class MTS_PT_MTSCollisionPanel(Panel):
    #Class options
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_parent_id = "MTS_PT_mtscollision"
    bl_label = "Collision Box Properties"
    
    #Draw function
    def draw(self, context):
        #create a layout
        layout = self.layout
        #get the current active object
        obj = context.object
        #get it's custom properties
        collisionsettings = obj.mts_collision_settings
        
        #collsion property
        row = layout.row()
        row.prop(collisionsettings, "isCollision", text = "Collision")
        #check if the collision property is enabled
        if collisionsettings.isCollision == True:
            #interior collision
            row.prop(collisionsettings, "isInterior", text = "Interior Collision") 
            row = layout.row()
            #floating collision
            row.prop(collisionsettings, "collidesWithLiquids", text = "Floats on Liquids")
            #armour thickness
            row.prop(collisionsettings, "armorThickness", text = "Armor Thickness")
            row = layout.row()
            #width of subdivision, to split a big box into multiple ones
            row.prop(collisionsettings, "subdivideWidth", text = "Subdivision Width")
            #height of the subdivision, to split a big box into multiple ones
            row.prop(collisionsettings, "subdivideHeight", text = "Subdivision Height")

#Panel: Draw the door hitbox panel
class MTS_PT_MTSDoorsPanel(Panel):
    #Class options
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_parent_id = "MTS_PT_mtscollision"
    bl_label = "Door Collision Properties"
    
    #Draw function
    def draw(self, context):
        #create a layout
        layout = self.layout
        #get the current active object
        obj = context.object
        #get it's custom properties
        collisionsettings = obj.mts_collision_settings
        
        row = layout.row()
        #check if the door property is enabled if so show the name property
        if collisionsettings.isDoor == True:
            row.prop(collisionsettings, "doorName", text = "Door Name")
            row = layout.row()
        #door property
        row.prop(collisionsettings, "isDoor", text = "Door")
        #check if the door property is enabled
        if collisionsettings.isDoor == True:
            #add the rest of the properties 
            #closed by default
            row.prop(collisionsettings, "closedByDefault", text = "Closed by Default") 
            row = layout.row()
            #close on movement
            row.prop(collisionsettings, "closeOnMovement", text = "Close on Movement")
            #close/open when sitting/dismounting
            row.prop(collisionsettings, "activateOnSeated", text = "Activate When Seated")
            row = layout.row()
            #ignores clicks
            row.prop(collisionsettings, "ignoresClicks", text = "Ignores User Clicks")
            #armour thickness
            row.prop(collisionsettings, "doorArmorThickness", text = "Armor Thickness")
            row = layout.row()
            #pointer to the open pos object of the door
            row.prop(collisionsettings, "openPos", text = "Open Pos Box")

#Panel: Parent for drawing the main MTS/IV tab in the numbers panel
class MTS_View3D_Parent:
    #Class options
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MTS/IV"
    
#Panel: Draw the collision tools panel in the numbers panel
class MTS_V3D_CollisionPanel(MTS_View3D_Parent, Panel):
    #Class options
    bl_idname = "MTS_PT_V3D_collisionpanel"
    bl_label = "MTS/IV Collision Tools"

    #Draw function
    def draw(self, context):
        #create a layout
        layout = self.layout
        row = layout.row()
        #mark as collision operator button
        row.operator("mts.mark_as_collision")
        row = layout.row()
        #export operator button
        row.operator(icon="EXPORT", operator="mts.export_collision_boxes")
        row = layout.row()
        #import operator button
        row.operator(icon="IMPORT", operator="mts.import_collision_boxes")
        row = layout.row()
        #interior collision operator button
        row.operator(operator="mts.mark_as_interior")

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

classes = (
    MTS_OT_ImportCollisions,
    MTS_OT_ExportCollisions,
    MTS_OT_MarkAsCollision,
    MTS_OT_MarkAsInterior,
    CollisionSettings,
    MTS_PT_MTSCollisionBasePanel,
    MTS_PT_MTSCollisionPanel,
    MTS_PT_MTSDoorsPanel,
    MTS_V3D_CollisionPanel
)
        
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
        
    bpy.types.Object.mts_collision_settings = bpy.props.PointerProperty(type=CollisionSettings)
    
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
    for cls in classes:
        unregister_class(cls)
        
if __name__ == "__main__":
    register()
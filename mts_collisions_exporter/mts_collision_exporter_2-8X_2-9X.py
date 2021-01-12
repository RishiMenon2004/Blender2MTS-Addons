bl_info = {
    "name": "MTS/IV Collision Box Exporter",
    "author": "Turbo Defender | Gyro Hero | Laura Darkez",
    "version": (1, 7),
    "blender": (2, 90, 0),
    "location": "Object —> MTS/IV Collision Properties",
    "description": "Exports Blender cubes as MTS/IV collision boxes",
    "category": "Object"
}

import bpy
import math
import numpy as NP
from bpy_extras.io_utils import ExportHelper
from bpy.props import (
        BoolProperty,
        FloatProperty,
        StringProperty,
        EnumProperty,
        PointerProperty,
        )
#exporter      
class SCENE_OT_ExportCollisions(bpy.types.Operator, ExportHelper):
    bl_idname = "object.export_collision_boxes"
    bl_label = "Export Collisions"
    
    filename_ext = ".json"
    
    def __init__(self):
        pass

    def execute(self, context):
        firstEntry = True
        self.report({'INFO'}, "Export Started")
        f = open(self.filepath, "w")
        
        #Write Collisions
        f.write("\"collision\": [\n") 
        for obj in context.scene.objects:
            if obj.mts_collision_settings.isCollision and not obj.mts_collision_settings.isDoor:
                if firstEntry:
                    f.write("    {\n")
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
                                    f.write(",\n    {\n")
                                else:
                                    firstEntry = False
                                # Check if we need to rotate the positions
                                pos = [x,y,z]
                                if rot.count(0) == 3: # No rotation
                                    self.export_collision_box(pos, [boxSize,boxSize,boxSizeZ], obj.mts_collision_settings, f, context)
                                else:
                                    newPos = rotate(pos, rot, origin)
                                    self.export_collision_box(newPos, [boxSize,boxSize,boxSizeZ], obj.mts_collision_settings, f, context)


                else:
                    if not(firstEntry):
                        f.write(",\n    {\n")
                    self.export_collision_box(obj.location, obj.dimensions, obj.mts_collision_settings, f, context)

                if firstEntry:
                    firstEntry = False
                
        f.write("\n],\n\n")
        
        #Write Doors
        f.write("\"doors\": [\n")
        firstEntry = True
        for obj in context.scene.objects:
            if obj.mts_collision_settings.isDoor:
                if obj.mts_collision_settings['openPos'] == None:
                    self.report({'INFO'}, "openPos was not defined for %s" % (obj.name))
                if firstEntry:
                    firstEntry = False
                    f.write("    {\n")
                else:
                    f.write(",\n    {\n")
                self.export_doors(obj, obj.mts_collision_settings, f, context)
        f.write("\n],")
        
        self.report({'INFO'}, "Export Complete")

        return {'FINISHED'}
            
    def export_collision_box(self, location, dimensions, colset, f, context):
        
        f.write("        \"pos\":[%s, %s, %s],\n" % (round(location[0],5), round(location[2],5), -1*round(location[1],5)))
        
        f.write("        \"width\": %s, \n" % (round(dimensions[0],5)))
        
        f.write("        \"height\": %s" % (round(dimensions[2],5)))
        
        if colset.isInterior:
            f.write(",\n        \"isInterior\": true")
        
        if colset.collidesWithLiquids:
            f.write(",\n        \"collidesWithLiquids\": true")
        
        if colset.armorThickness != 0:
            f.write(",\n        \"armorThickness\": %s" % (colset.armorThickness))
        
        f.write("\n    }")
        
    def export_doors(self, obj, colset, f, context):
        
        openPos = colset.openPos
        
        #write the entries for one collision
        f.write("        \"name\": \"%s\",\n" % (colset.doorName))
        
        f.write("        \"closedPos\":[%s, %s, %s],\n" % (round(obj.location[0],5), round(obj.location[2],5), -1*round(obj.location[1],5)))

        if openPos != None:
            f.write("        \"openPos\":[%s, %s, %s],\n" % (round(openPos.location[0],5), round(openPos.location[2],5), -1*round(openPos.location[1],5)))
        else:
            f.write("        \"openPos\": \"was not defined for %s\",\n" % (obj.name))
        
        f.write("        \"width\": %s, \n" % (round(obj.dimensions[0],5)))
        
        f.write("        \"height\": %s" % (round(obj.dimensions[2],5)))
        
        if colset.closedByDefault:
            f.write(",\n        \"closedByDefault\": true")
        
        if colset.closeOnMovement:
            f.write(",\n        \"closeOnMovement\": true")
            
        if colset.activateOnSeated:
            f.write(",\n        \"activateOnSeated\": true")
            
        if colset.ignoresClicks:
            f.write(",\n        \"ignoresClicks\": true")
            
        f.write("\n    }")

class SCENE_OT_MarkAsCollision(bpy.types.Operator):
    bl_idname = "object.mark_as_collision"
    bl_label = "(MTS/IV) Mark all selected as collison"
    bl_property = "type_search"
        
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
    
def update_open_pos(self, context):
    obj = context.object
    colset = obj.mts_collision_settings
    target_obj = colset.openPos
    target_colset = target_obj.mts_collision_settings
    
    target_colset['isCollision'] = False
    target_colset['isDoor'] = False
        
    return
        
class CollisionSettings(bpy.types.PropertyGroup):
    
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
        
    openPos: PointerProperty(
        type = bpy.types.Object,
        name = "Open Position Box",
        update = update_open_pos
        )

#Draw the parent panel for the collision boxes and door hitboxes
class OBJECT_PT_MTSCollisionBasePanel(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "MTS/IV Collision Properties"
    bl_idname = "OBJECT_PT_mtscollision"
    
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.operator("object.export_collision_boxes")
        row = layout.row()
        row.label(icon='ERROR', text="Note: openPos boxes should not use the Collision or Door property else it'll mess you up")

#Draw the collision box panel
class OBJECT_PT_MTSCollisionPanel(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_parent_id = "OBJECT_PT_mtscollision"
    bl_label = "Collision Box Properties"
    
    def draw(self, context):
        layout = self.layout
        obj = context.object
        collisionsettings = obj.mts_collision_settings
        
        row = layout.row()
        row.prop(collisionsettings, "isCollision", text = "Collision")
        row.prop(collisionsettings, "isInterior", text = "Interior Collision") 
        row = layout.row()
        row.prop(collisionsettings, "collidesWithLiquids", text = "Floats on Liquids")
        row.prop(collisionsettings, "armorThickness", text = "Armor Thickness")
        row = layout.row()
        row.prop(collisionsettings, "subdivideWidth", text = "Subdivision Width")
        row.prop(collisionsettings, "subdivideHeight", text = "Subdivision Height")

#Draw the door hitbox panel
class OBJECT_PT_MTSDoorsPanel(bpy.types.Panel):
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_parent_id = "OBJECT_PT_mtscollision"
    bl_label = "Door Collision Properties"
    
    def draw(self, context):
        layout = self.layout
        obj = context.object
        collisionsettings = obj.mts_collision_settings
        
        row = layout.row()
        row.prop(collisionsettings, "doorName", text = "Door Name")
        row = layout.row()
        row.prop(collisionsettings, "isDoor", text = "Door")
        row.prop(collisionsettings, "closedByDefault", text = "Closed by Default") 
        row = layout.row()
        row.prop(collisionsettings, "closeOnMovement", text = "Close on Movement")
        row.prop(collisionsettings, "activateOnSeated", text = "Activate When Seated")
        row = layout.row()
        row.prop(collisionsettings, "ignoresClicks", text = "Ignores User Clicks")
        row.prop(collisionsettings, "openPos", text = "Open Pos Box")
    
def menu_func_export(self, context):
    self.layout.operator("object.export_collision_boxes", text="MTS/IV Collision Boxes Array (.json)")

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

#keymaps list
addon_keymaps = []

classes = (
    SCENE_OT_ExportCollisions,
    SCENE_OT_MarkAsCollision,
    CollisionSettings,
    OBJECT_PT_MTSCollisionBasePanel,
    OBJECT_PT_MTSCollisionPanel,
    OBJECT_PT_MTSDoorsPanel
)
        
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
        
    bpy.types.Object.mts_collision_settings = bpy.props.PointerProperty(type=CollisionSettings)
    
    #Append the export operator to the export menu
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc: 
        km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
        kmi = km.keymap_items.new("object.mark_as_collision", type='D', value='PRESS', ctrl=True, shift=True)
        addon_keymaps.append((km, kmi))
        
def unregister():
    for km,kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
        
if __name__ == "__main__":
    register()

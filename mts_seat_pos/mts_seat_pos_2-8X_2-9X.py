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
    "name": "MTS/IV Seat Tools",
    "author": "Turbo Defender",
    "version": (1, 0),
    "blender": (2, 90, 0),
    "location": "Object Properties –> MTS/IV Seat Properties",
    "description": "Exports Blender markers as MTS/IV part positions for seats",
    "category": "MTS"
}

import bpy
from bpy.types import Panel
from bpy_extras.io_utils import ExportHelper
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
)

#Operator: Exporter
class MTS_OT_ExportSeat(bpy.types.Operator, ExportHelper):
    #Class options
    bl_idname = "mts.export_seat_pos"
    bl_label = "Export Seat Positions"
    bl_description = "Export seat markers as a JSON snippet"
    
    filename_ext = ".json"

    def execute(self, context):
        firstEntry = True
        self.report({'INFO'}, "Export Started")
        f = open(self.filepath, "w")
        
        #Write parts section
        f.write("\"parts\": [\n")
        firstEntry = True
        for obj in context.scene.objects:
            if obj.mts_seat_settings.isSeat != False:
                if obj.mts_seat_settings.dismountPos == None:
                    self.report({'INFO'}, "dismountPos was not defined for %s" % (obj.name))
                if firstEntry:
                    firstEntry = False
                    f.write("    {\n")
                else:
                    f.write(",\n    {\n")
                self.export_seat(obj, obj.mts_seat_settings, f, context)
        f.write("\n],")
        
        self.report({'OPERATOR'}, "Export Complete")

        return {'FINISHED'}
        
    def export_seat(self, obj, colset, f, context):

        dismountPos = colset.dismountPos
        isController = colset.isController
        
        f.write("        \"pos\": [%s, %s, %s],\n" % (round(obj.location[0],5), round(obj.location[2],5), -1*round(obj.location[1],5)))

        f.write("        \"types\": [\"seat\"],\n")
        
        if dismountPos != [0.0, 0.0, 0.0]:
            f.write("        \"dismountPos\":[%s, %s, %s]" % (round(dismountPos[0]+obj.location[0],5), round(dismountPos[2+obj.location[2]],5), -1*round(dismountPos[1]+obj.location[0],5)))
        else:
            f.write("        \"dismountPos\": \"was not defined for %s\"" % (obj.name))
        
        if isController:
            f.write(",\n        \"isController\": true")
        
        f.write(",\n        \"linkedDoors\": []")
            
        f.write("\n    }")

#Operator: Create an one dimensional array of selected seat objects in the y axis
class MTS_OT_SeatArray(bpy.types.Operator):
    #Class options
    bl_idname = "mts.seat_array"
    bl_label = "(MTS/IV) Seat Marker Array"
    bl_description = "Make an array of MTS/IV seat markers"
    bl_options = {'REGISTER', 'UNDO'}
        
    spacing: FloatProperty(
        name= "Spacing",
        default= 0.25
        )
    
    count: IntProperty(
        name= "Count",
        default= 2,
        min = 1
        )
        
    @classmethod
    def poll(cls, context):
        return context.object is not None
    
    #Draw the custom layout for the operator properties panel
    def draw(self, context):
        #create a layout
        layout = self.layout
        row = layout.row()
        row.prop(self, "spacing")
        row.prop(self, "count")

    def execute(self, context):
        canDuplicate = True
        
        for obj in context.selected_objects:
            if obj.mts_seat_settings.isSeat is True and canDuplicate is not False:
                canDuplicate = True
            else:
                canDuplicate = False
                self.report({'ERROR'}, "Not all selected objects are seat markers!")
                return {'CANCELLED'}
            
        for i in range (0, self.count-1):
            bpy.ops.object.duplicate_move(TRANSFORM_OT_translate={"value":(0, self.spacing, 0)})
        
        return {'FINISHED'}

#Operator: Show a temporary preview of the dismount pos of the selected seat objects
class MTS_OT_DismountPreview(bpy.types.Operator):
    #Class options
    bl_idname = "mts.dismount_preview"
    bl_label = "(MTS/IV) Seat DismountPos Preview"
    bl_description = "Show a preview of the dismountPos of seat markers"
    
    #Create class variable for keeping track of the created preview objects
    previewObjs = []

    @classmethod
    def poll(cls, context):
        return context.object is not None
    
    def execute(self, context):
        self.previewObjs = []
        
        #create the preview objects
        for obj in context.selected_objects:
            if obj.mts_seat_settings.isSeat:
                dismountOffset = obj.mts_seat_settings.dismountOffset
                bpy.ops.object.empty_add(type='ARROWS', location= obj.location)
                context.object.name = "dismount preview"
                context.object.show_in_front = True
                bpy.ops.transform.translate(value=(dismountOffset[0], dismountOffset[1], dismountOffset[2]))
                bpy.ops.view3d.view_all()
                self.previewObjs.append(context.object)
    
    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        #Check if any of these keys are pressed and delete the preview objects
        if event.type in {'ESC', 'RIGHTMOUSE', 'LEFTMOUSE'}:
            for obj in self.previewObjs:
                bpy.data.objects.remove(object=obj, do_unlink=True)
            return {'FINISHED'}
        
        if event.type in {'MIDDLEMOUSE', 'TRACKPADPAN', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}
        
        return {'RUNNING_MODAL'}
    
    def invoke(self, context, event):
        if context.object is None:
            self.report({'ERROR'}, "Please select an active seat marker")
            return {'CANCELLED'}
        else:
            for obj in context.selected_objects:
                if not obj.mts_seat_settings.isSeat:
                    self.report({'ERROR'}, "Not all selected objects are seat markers!")
                    return {'CANCELLED'}
        
        if bpy.context.object.mode == 'EDIT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        self.execute(context)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

#Create the custom properties for seat markers
class SeatSettings(bpy.types.PropertyGroup):
    
    isSeat: BoolProperty(
        name = "Is Door",
        default = False
        )
    
    dismountOffset: FloatVectorProperty(
        name = "Dismount Pos",
        default = [0.0, 0.0, 0.0],
        precision = 5,
        step = 100,
        subtype = 'XYZ'
        )
        
    isController: BoolProperty(
        name = "Is Controller",
        default = False
        )

#Panel: Draw the parent panel for the collision boxes and door hitboxes
class MTS_PT_MTSSeatPanel(Panel):
    #Class options
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "MTS/IV Seat Properties"
    bl_idname = "MTS_PT_mtsseats"
    
    #Draw function
    def draw(self, context):
        #create a layout
        layout = self.layout
        #get the current active object
        obj = context.object
        #get it's custom properties
        seatsettings = obj.mts_seat_settings
        
        row = layout.row()
        #export operator button
        row.operator(icon='EXPORT', operator="mts.export_seat_pos")
        
        row = layout.row()
        #check if the seat property is enabled if so show the name property
        row.prop(seatsettings, "isSeat", text="Is Seat")
        if seatsettings.isSeat == True:
            #add the custom properties
            #controller seat
            row.prop(seatsettings, "isController", text="Is Controller")    
            row = layout.row()
            #dismount position
            row.prop(seatsettings, "dismountOffset", text="Dismount Offset")

#Panel: Parent for drawing the main MTS/IV tab in the numbers panel
class View3DPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MTS/IV"

#Panel: Draw the seat tools panel in the numbers panel
class MTS_V3D_SeatPanel(View3DPanel, Panel):
    #Class options
    bl_idname = "MTS_PT_V3D_seatpanel"
    bl_label = "MTS/IV Seat Tools"

    #Draw function
    def draw(self, context):
        #create a layout
        layout = self.layout
        row = layout.row()
        #seat array operator button
        row.operator("mts.seat_array")
        row = layout.row()
        #dismount preview operator button
        row.operator("mts.dismount_preview")
        row = layout.row()
        #export operator button
        row.operator(icon="EXPORT", operator="mts.export_seat_pos")

#Create export button for export menu
def menu_func_export(self, context):
    self.layout.operator("mts.export_seat_pos", text="MTS/IV Seat Array (.json)")

classes = (
    MTS_OT_ExportSeat,
    MTS_OT_SeatArray,
    MTS_OT_DismountPreview,
    SeatSettings,
    MTS_PT_MTSSeatPanel,
    MTS_V3D_SeatPanel,
)
        
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
        
    bpy.types.Object.mts_seat_settings = bpy.props.PointerProperty(type=SeatSettings)
    
    #Append the export operator to the export menu
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
        
def unregister():
    
    #Remove the export operator from the export menu
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
        
if __name__ == "__main__":
    register()
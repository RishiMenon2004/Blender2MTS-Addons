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
    "version": (2, 0),
    "blender": (2, 90, 0),
    "location": "Object Properties -> MTS/IV Seat Properties",
    "description": "Exports Blender markers as MTS/IV part positions for seats",
    "category": "MTS"
}

import bpy
from bpy.types import (Panel, UIList)
from bpy_extras.io_utils import ExportHelper
from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    EnumProperty,
    CollectionProperty,
)
import json

#Operator: Exporter
class MTS_OT_ExportSeat(bpy.types.Operator, ExportHelper):
    #Class options
    bl_idname = "mts.export_seat_pos"
    bl_label = "Export Seat Positions"
    bl_description = "Export seat markers as a JSON snippet"
    
    filename_ext = ".json"

    def execute(self, context):
        # firstEntry = True
        self.report({'INFO'}, "Export Started")
        f = open(self.filepath, "w")
        
        self.parts = []
        
        #Write parts section
        for obj in context.scene.objects:
            if obj.mts_seat_settings.isSeat != False:
                if obj.mts_seat_settings.dismountOffset == None:
                    self.report({'INFO'}, "dismountPos was not defined for %s" % (obj.name))

                self.export_seat(obj, obj.mts_seat_settings, f, context)
        
        json.dump({
            'parts': self.parts
        }, f, indent=2)
        
        f.close()
        
        self.report({'OPERATOR'}, "Export Complete")

        return {'FINISHED'}
        
    def export_seat(self, obj, colset, f, context):

        dismountOffset = colset.dismountOffset.copy()
        isWorldSpace = colset.isWorldSpace
        isController = colset.isController
        isPermanent = colset.isPermanent
        forceCameras = colset.forceCameras
        playerScale = colset.playerScale
        seatEffects = colset.seatEffects

        if(not isWorldSpace[0]):
            dismountOffset[0] += obj.location[0]
        if(not isWorldSpace[1]):
            dismountOffset[1] += obj.location[1]
        if(not isWorldSpace[2]):
            dismountOffset[2] += obj.location[2]
        
        seat = {
            'pos': [round(obj.location[0],5), round(obj.location[2],5), -1*round(obj.location[1],5)],
            'types': ["seat"],
            'dismountPos': [round(dismountOffset[0],5), round(dismountOffset[2],5), -1*round(dismountOffset[1],5)]
        }
        
        if isController:
            seat['isController'] = True
            
        if isPermanent:
            seat['isPermanent'] = True
            
        if forceCameras:
            seat['forceCameras'] = True
            
        if playerScale != 1:
            seat['playerScale'] = round(playerScale, 3)
            
        if len(seatEffects) > 0:
            effects = []
            for effect in seatEffects:
                print(effect.name)
                seatEffect = {
                    'name': effect.name,
                    'duration': effect.duration,
                    'amplifier': effect.amplifier
                }
                
                effects.append(seatEffect)
            
            seat['seatEffects'] = effects.copy()
        
        seat['linkedParts'] = []
        
        self.parts.append(seat)
#Operator: Add Seat Effect
class MTS_OT_AddSeatEffect(bpy.types.Operator):
    bl_idname = "mts.add_seat_effect"
    bl_label = "(MTS/IV) Add Seat Effect"
    bl_description = "Add a new potion effect to the selected seat object"
    
    def execute(self, context):
        obj = context.object
        if obj.mts_seat_settings.isSeat:
            obj.mts_seat_settings.seatEffects.add()
            obj.mts_seat_settings.seatEffects[-1].name = "speed"
            
        return {'FINISHED'}

class MTS_OT_DeleteSeatEffect(bpy.types.Operator):
    bl_idname = "mts.remove_seat_effect"
    bl_label = "(MTS/IV) Remove Seat Effect"
    bl_description = "Delete the active seat effect from the seat"
    
    @classmethod
    def poll(cls, context):
        return context.object.mts_seat_settings.seatEffects
    
    def execute(self, context):
        obj = context.object
        seat_effects = obj.mts_seat_settings.seatEffects
        index = obj.mts_seat_settings.seatEffectsIndex
        
        seat_effects.remove(index)
        new_index = min(max(0, index - 1), len(seat_effects) - 1)
        obj.mts_seat_settings.seatEffectsIndex = max(new_index, 0)
        
        return {'FINISHED'}

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
                dismountOffset = obj.mts_seat_settings.dismountOffset.copy()
                isWorldSpace = obj.mts_seat_settings.isWorldSpace
                bpy.ops.object.empty_add(type='ARROWS', location= obj.location)
                context.object.name = "dismount preview"
                context.object.show_in_front = True
                if(isWorldSpace[0]):
                    dismountOffset[0] -= obj.location[0]
                if(isWorldSpace[1]):
                    dismountOffset[1] -= obj.location[1]
                if(isWorldSpace[2]):
                    dismountOffset[2] -= obj.location[2]
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

class PotionEffects(bpy.types.PropertyGroup):
    name: EnumProperty (
        name = "Name",
        default = "speed",
        items = [
            (
                "speed", 
                "Speed",
                ""
            ),
            (
                "slowness", 
                "Slowness",
                ""
            ),
            (
                "haste", 
                "Haste",
                ""
            ),
            (
                "mining_fatigue", 
                "Mining Fatigue",
                ""
            ),
            (
                "strength", 
                "Strength",
                ""
            ),
            (
                "instant_health", 
                "Instant Health",
                ""
            ),
            (
                "instant_damage", 
                "Instant Damage",
                ""
            ),
            (
                "jump_boost", 
                "Jump Boost",
                ""
            ),
            (
                "nausea", 
                "Nausea",
                ""
            ),
            (
                "regeneration", 
                "Regeneration",
                ""
            ),
            (
                "resistance", 
                "Resistance",
                ""
            ),
            (
                "fire_resistance", 
                "Fireresistance",
                ""
            ),
            (
                "water_breathing", 
                "Water_Breathing",
                ""
            ),
            (
                "invisibility", 
                "Invisibility",
                ""
            ),
            (
                "blindness", 
                "Blindness",
                ""
            ),
            (
                "night_vision", 
                "Night Vision",
                ""
            ),
            (
                "hunger", 
                "Hunger",
                ""
            ),
            (
                "weakness", 
                "Weakness",
                ""
            ),
            (
                "poison", 
                "Poison",
                ""
            ),
            (
                "wither", 
                "Wither",
                ""
            ),
            (
                "health_boost", 
                "Health Boost",
                ""
            ),
            (
                "absorption", 
                "Absorption",
                ""
            ),
            (
                "saturation", 
                "Saturation",
                ""
            ),
            (
                "glowing", 
                "Glowing",
                ""
            ),
            (
                "levitation", 
                "Levitation",
                ""
            ),
            (
                "luck", 
                "Luck",
                ""
            ),
            (
                "unluck", 
                "Unluck",
                ""
            ),
        ]
    )
    
    duration: IntProperty(
        name = "Duration",
        default = 5,
        min = 1
    )
    
    amplifier: IntProperty(
        name = "Amplifier",
        default = 0,
        min = 0,
        max = 255
    )

#Create the custom properties for seat markers
class SeatSettings(bpy.types.PropertyGroup):
    
    isSeat: BoolProperty(
        name = "Is Seat",
        default = False
    )
    
    isController: BoolProperty(
        name = "Is Controller",
        default = False
    )
    
    isPermanent: BoolProperty(
        name = "Is Permanent",
        default = False
    )
    
    canDisableGun: BoolProperty(
        name = "Can Disable Gun",
        default = False
    )
    
    forceCameras: BoolProperty(
        name = "Force Cameras",
        default = False
    )
    
    playerScale: FloatProperty(
        name = "Player Scale",
        default = 1,
        min = 0.125,
        max = 999,
        soft_max = 100
    )
    
    seatEffects: CollectionProperty(
        name = "Seat Effects",
        type = PotionEffects
    )

    seatEffectsIndex: IntProperty(
        name = "Seat Effect Index",
        
    )

    dismountOffset: FloatVectorProperty(
        name = "Dismount Offset",
        default = [0.0, 0.0, 0.0],
        precision = 5,
        step = 100,
        subtype = 'XYZ'
    )
        
    isWorldSpace: BoolVectorProperty(
        name = "Is World Space",
        default = [False, False, False],
        subtype = 'XYZ'
    )

class MTS_UL_SeatEffectsList(UIList):
    bl_idname = "MTS_UL_seatEffectsList"
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        custom_icon = 'EXPERIMENTAL'
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if index == context.object.mts_seat_settings.seatEffectsIndex:
                layout.prop(item, "name", text="", emboss=False, icon=custom_icon)
            else:
                layout.label(text=item.name, icon=custom_icon)
            
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon=custom_icon)

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
        
        box = layout.row()
        #export operator button
        box.operator(icon='EXPORT', operator="mts.export_seat_pos")
        
        row = layout.row()
        row.label(text="Seat Properties")
        
        box = layout.box()
        
        row = box.row()
        row.prop(seatsettings, "isSeat", icon="MOD_SKIN")
        
        #check if the seat property is enabled if so show the name property
        if seatsettings.isSeat == True:
            #add the custom properties
            #controller seat
            row.prop(seatsettings, "isController", icon="MODIFIER")    
            
            row = box.row()
            row.prop(seatsettings, "isPermanent", icon="MODIFIER")    
            row.prop(seatsettings, "canDisableGun", icon="MODIFIER")    
            
            row = box.row()
            row.prop(seatsettings, "playerScale", icon="MODIFIER")    
            
            row = layout.row()
            row.label(text="Seat Effects")
            
            listRow = layout.row()
            
            column = listRow.column()
            
            box = column.box()
            
            box.template_list("MTS_UL_seatEffectsList", "Seat Potion Effects", seatsettings, "seatEffects", seatsettings, "seatEffectsIndex")
            if seatsettings.seatEffects and len(seatsettings.seatEffects) >= 0:
                activeItem = seatsettings.seatEffects[seatsettings.seatEffectsIndex]
                
                row = box.row()
                row.prop(activeItem, "name", text="Effect Name")
                
                row = box.row()
                row.prop(activeItem, "duration")
                row.prop(activeItem, "amplifier")
                
            column = listRow.column()
            column.operator("mts.add_seat_effect", icon='ADD', text="")
            column.operator("mts.remove_seat_effect", icon='REMOVE', text="")
            
            layout.separator()
            
            row = layout.row()
            row.label(text="Dismount Position")
            
            box = layout.box()
            row = box.row()
            row.column().prop(seatsettings, "dismountOffset", text="X {}".format("Pos" if seatsettings.isWorldSpace[0] else "Offset"), index=0)
            row.column().prop(seatsettings, "isWorldSpace", text="Use World Space", index=0, toggle=True, icon="ORIENTATION_GLOBAL")
            row = box.row()
            row.column().prop(seatsettings, "dismountOffset", text="Y {}".format("Pos" if seatsettings.isWorldSpace[1] else "Offset"), index=1)
            row.column().prop(seatsettings, "isWorldSpace", text="Use World Space", index=1, toggle=True, icon="ORIENTATION_GLOBAL")
            row = box.row()
            row.column().prop(seatsettings, "dismountOffset", text="Z {}".format("Pos" if seatsettings.isWorldSpace[2] else "Offset"), index=2)
            row.column().prop(seatsettings, "isWorldSpace", text="Use World Space", index=2, toggle=True, icon="ORIENTATION_GLOBAL")
            
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
    MTS_OT_AddSeatEffect,
    MTS_OT_DeleteSeatEffect,
    MTS_OT_SeatArray,
    MTS_OT_DismountPreview,
    PotionEffects,
    SeatSettings,
    MTS_UL_SeatEffectsList,
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
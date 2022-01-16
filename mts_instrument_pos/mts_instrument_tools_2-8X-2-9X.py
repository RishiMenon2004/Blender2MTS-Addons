# Addon properties
bl_info = {
    "name": "MTS/IV Instrument Tools",
    "author": "Turbo Defender",
    "version": (1, 0),
    "blender": (2, 90, 0),
    "location": "Object Properties –> MTS/IV Instrument Properties",
    "description": "Various tools for setting up instrumenst/gauges for mts",
    "category": "MTS"
}

import bpy
from bpy_extras.io_utils import (ExportHelper, ImportHelper)
from bpy.types import (
    Operator,
    Panel,
    Menu
)
from bpy.props import (
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    BoolProperty,
    StringProperty
)

import gpu_extras.presets as presets
import blf
import math
import json

import os

# Operator: Add instrument object
class MTS_OT_AddInstrument(Operator):
    bl_idname = "mts.add_instrument"
    bl_label = "(MTS/IV) Instrument"
    bl_description = "Add an instrument"

    pos: FloatVectorProperty(
        default = [0, 0, 0]
    )
    rot: FloatVectorProperty(
        default = [0, 0, 0]
    )

    scale: FloatProperty(
        default = 1
    )

    def execute(self, context):
        # round out scale to 4 decimals and create a new object that will act as the instrument
        self.scale = round(self.scale, 4)
        bpy.ops.mesh.primitive_plane_add(size=8, enter_editmode=False, align='WORLD', location=(self.pos[0], self.pos[2], self.pos[1]), scale=(self.scale, self.scale, self.scale), rotation=(math.radians(-90), 0, 0))
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        # manually apply certain properties
        obj = context.object
        obj.rotation_euler[0] = math.radians(self.rot[0])
        obj.rotation_euler[1] = math.radians(self.rot[1])
        obj.rotation_euler[2] = math.radians(self.rot[2])
        obj.scale[0] = self.scale
        obj.scale[1] = self.scale
        obj.scale[2] = self.scale
        obj.mts_instrument_settings.isInstrument = True
        return{'FINISHED'}

# Operator: Importer
class MTS_OT_ImportCollisions(bpy.types.Operator, ImportHelper):
    bl_idname = "mts.import_instruments"
    bl_label = "Import Instruments"
    bl_description = "Import instruments from a JSON file"
    
    filename_ext = ".json"
    filter_glob: StringProperty(
            default="*.json",
            options={'HIDDEN'},
            )
    
    def execute(self, context):
        # create a collection to put the imported instruments into
        col_name = 'Instruments'
        if 'Instruments' not in bpy.data.collections:
            bpy.ops.collection.create(name=col_name)
            inst_collection = bpy.data.collections[col_name]
            bpy.context.scene.collection.children.link(inst_collection)
            
        inst_collection = bpy.context.view_layer.layer_collection.children[col_name]
        bpy.context.view_layer.active_layer_collection = inst_collection
        
        # open the json file
        with open(self.filepath, 'r') as f:
            file = json.loads(f.read())
            
            # check if instruments list exist for json exported by this addon
            if 'instruments' in file:
                instruments = file['instruments']
                
                # loop through each instrument and save values to the vars 
                for instrument in instruments:
                    pos = instrument['pos']
                    rot = instrument['rot']
                    scale = instrument['scale']
                    hudX = instrument['hudX']
                    hudY = instrument['hudY']
                    hudScale = instrument['hudScale']
                    
                    # create instrument object using above vars
                    bpy.ops.mts.add_instrument(pos=pos, rot=rot, scale=scale)
                    obj = context.object
                    obj.name = "Instrument"
                    settings = obj.mts_instrument_settings
                    settings.hudX = hudX
                    settings.hudY = hudY
                    settings.scale = hudScale
                 
            # check if instruments list exist for vehicle json
            elif 'instruments' in file['motorized']:
                motorized = file['motorized']
                instruments = motorized['instruments']
                
                # loop through each instrument and save values to the vars 
                for instrument in instruments:
                    pos = instrument['pos']
                    rot = instrument['rot']
                    scale = instrument['scale']
                    hudX = instrument['hudX']
                    hudY = instrument['hudY']
                    hudScale = instrument['hudScale']
                    
                    # create instrument object using above vars
                    bpy.ops.mts.add_instrument(pos=pos, rot=rot, scale=scale)
                    obj = context.object
                    obj.name = "Instrument"
                    settings = obj.mts_instrument_settings
                    settings.hudX = hudX
                    settings.hudY = hudY
                    settings.scale = hudScale

            # throw an error if the json file is not formatted correctly
            else:
                self.report({'ERROR_INVALID_INPUT'}, "NO INSTRUMENTS FOUND")
                return {'CANCELLED'}
        
        self.report({'OPERATOR'}, "Import Finished")
        return {'FINISHED'}

# Operator: Exporter
class MTS_OT_ExportInstruments(Operator, ExportHelper):
    bl_idname = "mts.export_instruments"
    bl_label = "Export Instruments"
    
    filename_ext = ".json"

    def execute(self, context):
        self.report({'INFO'}, "Export Started")
        f = open(self.filepath, "w")
        
        # Write instruments list
        f.write("{\n")
        f.write("    \"instruments\": [\n")
        firstEntry = True
        for obj in context.scene.objects:
            if obj.mts_instrument_settings.isInstrument:
                # no comma for first entry, and set the var to false so it adds a comma for every entry after
                if firstEntry:
                    firstEntry = False
                    f.write("        {\n")
                else:
                    f.write(",\n        {\n")
                # call method to write the instrument to the json file
                self.export_instrument(obj, obj.mts_instrument_settings, f, context)
        f.write("\n    ]\n}")
        
        self.report({'OPERATOR'}, "Export Complete")
        return {'FINISHED'}
        
    def export_instrument(self, obj, instset, f, context):
        
        # get properties from the object and write to the json file

        f.write("            \"pos\": [%s, %s, %s],\n" % (round(obj.location[0],5), round(obj.location[2],5), -1*round(obj.location[1],5)))

        f.write("            \"rot\": [%s, %s, %s],\n" % (round(math.degrees(obj.rotation_euler[0]), 5), round(math.degrees(obj.rotation_euler[1]), 5), round(math.degrees(obj.rotation_euler[2]), 5)))
        
        f.write("            \"scale\": %s,\n" % (obj.scale[0]))

        f.write("            \"hudX\": %s,\n" % (instset.hudX))

        f.write("            \"hudY\": %s,\n" % (instset.hudY))

        f.write("            \"hudScale\": %s" % (instset.scale))
            
        f.write("\n        }")

# Operator: Set the hud properties of the instrument visually
class MTS_OT_InstrumentHUDPos(Operator):
    bl_idname = "mts.instrument_hudpos"
    bl_label = "(MTS/IV) Instrument HudPos"
    bl_description = "Adjust the HUDPos and scale of the selected instrument"
    
    # check if the context is an object 
    @classmethod
    def poll(cls, context):
        if context.object is not None and context.object.mts_instrument_settings.isInstrument:
            return True
    
    def modal(self, context, event):
        # redraw every call
        context.area.tag_redraw()
        
        # get object
        obj = context.object
        # get instrument settings
        instSet = obj.mts_instrument_settings
        
        #set the range where the mouse can interact with the instrument
        range_min = [(instSet.hudX - (64 * instSet.scale)) - 16 + self.panel_offset, (-instSet.hudY - (64 * instSet.scale)) - 16 + 140]
        range_max = [(instSet.hudX + (64 * instSet.scale)) + 16 + self.panel_offset, (-instSet.hudY + (64 * instSet.scale)) + 16 + 140]

        # if mouse moved
        if event.type == 'MOUSEMOVE' or event.type == 'INBETWEEN_MOUSEMOVE':
            # get the offset of the mouse from prev draw
            self.mouse_offset = [event.mouse_region_x - self.mouse_pos[0], event.mouse_region_y - self.mouse_pos[1]]
            # set mouse pos for current draw
            self.mouse_pos = [event.mouse_region_x, event.mouse_region_y]
            # if mouse down and in range then move the instrument by the mouse offset
            if event.value == 'PRESS':
                if range_min[0] < event.mouse_region_x < range_max[0] and range_min[1] < event.mouse_region_y < range_max[1]:
                    instSet.hudX += self.mouse_offset[0]
                    instSet.hudY -= self.mouse_offset[1]
        
            return {'RUNNING_MODAL'}

        # if right click and in range then open property editor
        elif event.type == 'RIGHTMOUSE':
            if range_min[0] < event.mouse_region_x < range_max[0] and range_min[1] < event.mouse_region_y < range_max[1]:
                bpy.ops.wm.call_menu(name=MTS_MT_HUDpropeditor.bl_idname)
            
            return {'RUNNING_MODAL'}
        
        # move instrument left
        elif event.type == 'LEFT_ARROW' and event.value == 'PRESS':
            if event.shift:
                instSet.hudX -= 1
            else:
                instSet.hudX -= 10
            
            return {'RUNNING_MODAL'}
        
        # move instrument right
        elif event.type == 'RIGHT_ARROW' and event.value == 'PRESS':
            if event.shift:
                instSet.hudX += 1
            else:
                instSet.hudX += 10
            
            return {'RUNNING_MODAL'}
            
        # move instrument up
        elif event.type == 'UP_ARROW' and event.value == 'PRESS':
            if event.shift:
                instSet.hudY -= 1
            else:
                instSet.hudY -= 10
            
            return {'RUNNING_MODAL'}
            
        # move instrument down
        elif event.type == 'DOWN_ARROW' and event.value == 'PRESS':
            if event.shift:
                instSet.hudY += 1
            else:
                instSet.hudY += 10

            return {'RUNNING_MODAL'}
        
        # confirm changes and close the operator
        elif event.type in {'SPACE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            
            return {'FINISHED'}
        
        return {'RUNNING_MODAL'}

    # when operator is invoked
    def invoke(self, context, event):
        # if in 3d view get the mouse pos and get the instrument settings
        if context.area.type == 'VIEW_3D':
            self.mouse_pos = [event.mouse_region_x, event.mouse_region_y]
            
            instSet = context.object.mts_instrument_settings
            
            self.mouse_offset = [0, 0]
            
            # get view width and set the panel offset
            area_width = context.area.width
            self.panel_offset = (area_width/2)-200
            
            def draw_callback_px(self, context):
                # import images
                dirname = os.path.dirname(os.path.abspath(__file__))
                gaugedir = os.path.join(dirname, "images/generic_gauge.png")
                huddir = os.path.join(dirname, "images/hud.png")
                previewdir = os.path.join(dirname, "images/gauge_preview.png")
                
                # dev paths
                # gaugedir = os.path.join("C:/Users/rishi/Documents/Rishi/GitHub/Blender2MTS-Addons/mts_instrument_pos/images/generic_gauge.png")
                # huddir = os.path.join("C:/Users/rishi/Documents/Rishi/GitHub/Blender2MTS-Addons/mts_instrument_pos/images/hud.png")
                # previewdir = os.path.join("C:/Users/rishi/Documents/Rishi/GitHub/Blender2MTS-Addons/mts_instrument_pos/images/gauge_preview.png")
                
                # load if they exist
                try:
                    gauge = bpy.data.images.load(gaugedir, check_existing=True)
                except:
                    self.report({'ERROR'}, "INSTRUMENT Image Not Found At: " + gaugedir)
                    
                try:
                    prev_gauge = bpy.data.images.load(previewdir, check_existing=True)
                except:
                    self.report({'ERROR'}, "PREVIEW Image Not Found At: " + previewdir)
                    
                try:
                    hud = bpy.data.images.load(huddir, check_existing=True)
                except:
                    self.report({'ERROR'}, "HUD Image Not Found At: " + huddir)
                
                gauge.gl_load()
                prev_gauge.gl_load()
                hud.gl_load()
                
                # draw the hud
                presets.draw_texture_2d(hud.bindcode, (self.panel_offset, 0), 400, 140)
                
                # set properties of the instrument
                self.gauge_dimensions = 128*instSet.scale
                self.gauge_pos = [(instSet.hudX - (self.gauge_dimensions/2))+self.panel_offset, (-instSet.hudY - (self.gauge_dimensions/2)) + 140]
                
                # for each unselected instrument draw the preview
                for obj in context.scene.objects:
                    if obj != context.object and obj.mts_instrument_settings.isInstrument:
                        inst_set = obj.mts_instrument_settings
                    
                        inst_dimension = 128*inst_set.scale
                        inst_pos = [(inst_set.hudX - (inst_dimension/2)) + self.panel_offset, (inst_set.hudY - (inst_dimension/2))]
                        presets.draw_texture_2d(prev_gauge.bindcode, (inst_pos[0], inst_pos[1]), inst_dimension, inst_dimension)
                
                # draw the instrument
                presets.draw_texture_2d(gauge.bindcode, (self.gauge_pos[0], self.gauge_pos[1]), self.gauge_dimensions, self.gauge_dimensions)
                
                # draw the pos text
                font_id = 0
                blf.enable(font_id, 4)
                blf.color(font_id, 1, 1, 1, 1)
                blf.shadow(font_id, 5, 0, 0, 0, 1)
                blf.shadow_offset(font_id, 1, -1)
                blf.position(font_id, 20, 40, 0)
                blf.size(font_id, 20, 72)
                blf.draw(font_id, "X: {}".format(instSet.hudX))
                blf.position(font_id, 20, 20, 0)
                blf.draw(font_id, "Y: {}".format(instSet.hudY))
            # the arguments we pass the the callback
            args = (self, context)
            
            # Add the region OpenGL drawing callback
            self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, args, 'WINDOW', 'POST_PIXEL')
            
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}

# custom properties for instruments
class InstrumentSettings(bpy.types.PropertyGroup):

    isInstrument: BoolProperty(
        name = "Instrument",
        default = False
    )

    hudX: IntProperty(
        name = "HUDPos X",
        default = 0
    )

    hudY: IntProperty(
        name = "HUDPos Y",
        default = 0
    )
    
    scale: FloatProperty(
        name = "Scale",
        default = 1,
        min = 0.125,
        soft_max = 10,
        step = 1,
        precision = 2,
        subtype = 'FACTOR'
    )

# Menu: Instrument hud properties
class MTS_MT_HUDpropeditor(Menu):
    bl_idname = "MTS_MT_HUDpropeditor"
    bl_label = "Instrument Properties"
    
    def draw(self, context):
        layout = self.layout
        # get instrument settings
        instsettings = context.object.mts_instrument_settings
        
        # instrument properties
        layout.prop(instsettings, "hudX", text="Hud Pos X")
        layout.prop(instsettings, "hudY", text="Hud Pos Y")
        layout.prop(instsettings, "scale", text="Hud Scale")

# Panel: Instrument properties panel
class MTS_PT_MTSInstrumentPanel(Panel):
    #Class options
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_label = "MTS/IV Instrument Properties"
    bl_idname = "MTS_PT_mtsinstruments"
    
    def draw(self, context):
        layout = self.layout
        # get the current active object
        obj = context.object
        # get it's instrument properties
        instrumentsettings = obj.mts_instrument_settings

        row = layout.row()
        row.operator(icon='EXPORT', operator="mts.export_instruments")
        row.operator(icon="IMPORT", operator="mts.import_instruments")

        # instrument properties
        row = layout.row()
        if instrumentsettings.isInstrument == True:
            row.prop(instrumentsettings, "hudX", text = "Hud Pos X") 
            row.prop(instrumentsettings, "hudY", text = "Hud Pos Y")
            
            row = layout.row()
            row.prop(instrumentsettings, "scale", text = "Hus Scale")

# Panel: Parent for drawing the main MTS/IV tab in the numbers panel
class MTS_View3D_Parent:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MTS/IV"

# Panel: Draw the instrument tools panel in the numbers panel
class MTS_V3D_InstrumentPanel(MTS_View3D_Parent, Panel):
    bl_idname = "MTS_PT_V3D_instrumentpanel"
    bl_label = "MTS/IV Instrument Tools"

    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        # mark as collision operator button
        row.operator("mts.instrument_hudpos")
        
        row = layout.row()
        # add instrument
        row.operator("mts.add_instrument", text="(MTS/IV) Add Instrument")
        
        row = layout.row()
        # export operator button
        row.operator(icon="EXPORT", operator="mts.export_instruments")
        # import operator button
        row.operator(icon="IMPORT", operator="mts.import_instruments")

# Create export button for export menu
def menu_func_export(self, context):
    self.layout.operator("mts.export_instruments", text="MTS/IV Instruments (.json)")

# Create import button for import menu
def menu_func_import(self, context):
    self.layout.operator("mts.import_instruments", text="MTS/IV Instruments (.json)")

classes = (
     MTS_OT_AddInstrument,
     MTS_OT_ImportCollisions,
     MTS_OT_ExportInstruments,
     MTS_OT_InstrumentHUDPos,
     InstrumentSettings,
     MTS_MT_HUDpropeditor,
     MTS_PT_MTSInstrumentPanel,
     MTS_V3D_InstrumentPanel
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Object.mts_instrument_settings = bpy.props.PointerProperty(type=InstrumentSettings)

    # Append the export operator to the export menu
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    
    # Append the import operator to the import menu
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():

    # Remove the export operator from the export menu
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    
    # Remove the import operator from the import menu
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)

if __name__ == "__main__":
    register()
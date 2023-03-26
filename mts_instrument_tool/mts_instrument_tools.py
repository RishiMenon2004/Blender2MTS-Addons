# Addon properties
import os
import json
import math
import blf
from gpu_extras.presets import draw_texture_2d
from bgl import *
from bpy.props import (
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    BoolProperty,
    StringProperty
)
from bpy.types import (
    Operator,
    Panel,
    Menu
)
from bpy_extras.io_utils import (ExportHelper, ImportHelper)
import bpy
bl_info = {
    "name": "MTS/IV Instrument Tools",
    "author": "Turbo Defender",
    "version": (1, 2),
    "blender": (2, 90, 0),
    "location": "Object Properties -> MTS/IV Instrument Properties",
    "description": "Various tools for setting up instruments/gauges for mts",
    "category": "MTS"
}


# Operator: Add instrument object

class MTS_OT_AddInstrument(Operator):
    bl_idname = "mts.add_instrument"
    bl_label = "(MTS/IV) Instrument"
    bl_description = "Add an instrument"

    pos: FloatVectorProperty(
        default=[0, 0, 0]
    )
    rot: FloatVectorProperty(
        default=[0, 0, 0]
    )

    scale: FloatProperty(
        default=1
    )

    def execute(self, context):
        # round out scale to 4 decimals and create a new object that will act as the instrument
        self.scale = round(self.scale, 4)
        bpy.ops.mesh.primitive_plane_add(size=8, enter_editmode=False, align='WORLD', location=(
            self.pos[0], self.pos[2], self.pos[1]), scale=(self.scale, self.scale, self.scale), rotation=(math.radians(-90), 0, 0))
        bpy.ops.object.transform_apply(
            location=False, rotation=True, scale=False)
        
        # manually apply certain properties
        obj = context.object
        
        obj.rotation_euler = [
            math.radians(self.rot[0]),
            math.radians(self.rot[1]),
            math.radians(self.rot[2])
        ]
        
        obj.scale[0] = obj.scale[1] = obj.scale[2] = self.scale
        
        obj.mts_instrument_settings.isInstrument = True
        return {'FINISHED'}

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
        collection_name = 'Instruments'
        if 'Instruments' not in bpy.data.collections:
            bpy.ops.collection.create(name=collection_name)
            inst_collection = bpy.data.collections[collection_name]
            bpy.context.scene.collection.children.link(inst_collection)

        inst_collection = bpy.context.view_layer.layer_collection.children[collection_name]
        bpy.context.view_layer.active_layer_collection = inst_collection

        # open the json file
        with open(self.filepath, 'r') as f:
            file = json.loads(f.read())
            instruments = file

            # check if instruments list exist for json exported by this addon
            if 'instruments' in file:
                instruments = file['instruments']

            # check if instruments list exist for vehicle json
            elif 'instruments' in file['motorized']:
                motorized = file['motorized']
                instruments = motorized['instruments']

            # throw an error if the json file is not formatted correctly
            else:
                self.report({'ERROR_INVALID_INPUT'}, "NO INSTRUMENTS FOUND")
                return {'CANCELLED'}

            # loop through each instrument and save values to the vars
            for instrument in instruments:
                pos = instrument['pos']
                rot = instrument['rot']
                scale = instrument['scale']

                bpy.ops.mts.add_instrument(pos=pos, rot=rot, scale=scale)

                obj = context.object
                obj.name = "Instrument"

                instSet = obj.mts_instrument_settings
                instSet.hudX = instrument['hudX']
                instSet.hudY = instrument['hudY']
                instSet.hudScale = instrument['hudScale']
                instSet.placeOnPanel = instrument['placeOnPanel'] if 'placeOnPanel' in instrument else False
                instSet.applyAfter = instrument['applyAfter'] if 'applyAfter' in instrument else ""

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
        self.instruments = []
        
        
        for obj in context.scene.objects:
            if obj.mts_instrument_settings.isInstrument:
        
                # call method to write the instrument to the json file
                self.export_instrument(obj, obj.mts_instrument_settings, f, context)
        
        json.dump({'instruments': self.instruments}, f, indent=2)

        self.report({'OPERATOR'}, "Export Complete")
        return {'FINISHED'}

    def export_instrument(self, obj, instSet, f, context):
        
        instrument = {
            'pos': [
                round(obj.location[0], 5),
                round(obj.location[2], 5),
                -1*round(obj.location[1], 5)
            ],
            'rot': [
                round(math.degrees(obj.rotation_euler[0]), 5),
                round(math.degrees(obj.rotation_euler[1]), 5),
                round(math.degrees(obj.rotation_euler[2]), 5)
            ],
            'scale': obj.scale[0],
            'hudX': instSet.hudX,
            'hudY': instSet.hudY,
            'hudScale': round(instSet.hudScale, 3),
        }

        if instSet.placeOnPanel:
            instrument['placeOnPanel'] = True

        if instSet.applyAfter != "":
            instrument['applyAfter'] = instSet.applyAfter

        self.instruments.append(instrument)

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

        # discard changes and close the operator
        def resetChanges():
            self.instSet.hudX = self.uHudX
            self.instSet.hudY = self.uHudY
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')

        def confirmChanges():
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')

        self.gauge_dimension = self.gauge_texture_size * self.instSet.hudScale

        self.gauge_pos = [
            self.instSet.hudX - (self.gauge_dimension/2) + self.panel_offset,
            -self.instSet.hudY - (self.gauge_dimension/2) + self.panel_dimensions[1]
        ]

        # set the range where the mouse can interact with the instrument
        range_min = [
            self.gauge_pos[0],
            self.gauge_pos[1]
        ]

        range_max = [
            self.instSet.hudX + (self.gauge_dimension/2) + self.panel_offset,
            -self.instSet.hudY + (self.gauge_dimension/2) + 140
        ]

        confirm_range_min = [
            self.gauge_pos[0] + self.gauge_dimension + 10,
            self.gauge_pos[1]
        ]
        confirm_range_max = [
            confirm_range_min[0] + 25,
            confirm_range_min[1] + 25
        ]
        cancel_range_min = [
            confirm_range_min[0],
            confirm_range_max[1] + 10
        ]
        cancel_range_max = [
            cancel_range_min[0] + 25,
            cancel_range_min[1] + 25
        ]

        if event.type == 'LEFTMOUSE':
            if range_min[0] < event.mouse_region_x < range_max[0] and range_min[1] < event.mouse_region_y < range_max[1]:
                self.is_dragging = event.value == 'PRESS'
                self.mouse_offset = [0, 0]
                self.mouse_pos = [event.mouse_region_x, event.mouse_region_y]
            elif confirm_range_min[0] < event.mouse_region_x < confirm_range_max[0] and confirm_range_min[1] < event.mouse_region_y < confirm_range_max[1]:
                if event.value == 'PRESS':
                    confirmChanges()
                    return {'FINISHED'}
            elif cancel_range_min[0] < event.mouse_region_x < cancel_range_max[0] and cancel_range_min[1] < event.mouse_region_y < cancel_range_max[1]:
                if event.value == 'PRESS':
                    resetChanges()
                    return {'CANCELLED'}
            else:
                self.is_dragging = event.value == False

            self.initialMoveHudX = self.instSet.hudX
            self.initialMoveHudY = self.instSet.hudY

        # if mouse moved
        if event.type == 'MOUSEMOVE':
            # if mouse pressed
            if self.is_dragging:
                # get the offset of the mouse from prev draw
                self.mouse_offset = [
                    event.mouse_region_x - self.mouse_pos[0], event.mouse_region_y - self.mouse_pos[1]]
                # move the instrument by the mouse offset
                self.instSet.hudX = self.initialMoveHudX + self.mouse_offset[0]
                self.instSet.hudY = self.initialMoveHudY - self.mouse_offset[1]

                return {'RUNNING_MODAL'}

        # if right click and in range then open property editor
        if event.type == 'RIGHTMOUSE':
            if range_min[0] < event.mouse_region_x < range_max[0] and range_min[1] < event.mouse_region_y < range_max[1]:
                bpy.ops.wm.call_menu(name=MTS_MT_HUDpropeditor.bl_idname)

            return {'RUNNING_MODAL'}

        if event.type == 'SPACE':
            resetChanges()
            return {'CANCELLED'}

        # move instrument left
        if event.type == 'LEFT_ARROW' and event.value == 'PRESS':
            if event.shift:
                self.instSet.hudX -= 1
            else:
                self.instSet.hudX -= 10

            return {'RUNNING_MODAL'}

        # move instrument right
        if event.type == 'RIGHT_ARROW' and event.value == 'PRESS':
            if event.shift:
                self.instSet.hudX += 1
            else:
                self.instSet.hudX += 10

            return {'RUNNING_MODAL'}

        # move instrument up
        if event.type == 'UP_ARROW' and event.value == 'PRESS':
            if event.shift:
                self.instSet.hudY -= 1
            else:
                self.instSet.hudY -= 10

            return {'RUNNING_MODAL'}

        # move instrument down
        if event.type == 'DOWN_ARROW' and event.value == 'PRESS':
            if event.shift:
                self.instSet.hudY += 1
            else:
                self.instSet.hudY += 10

            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}

    # when operator is invoked
    def invoke(self, context, event):
        # if in 3d view get the mouse pos and get the instrument settings
        if context.area.type == 'VIEW_3D':
            self.mouse_pos = [event.mouse_region_x, event.mouse_region_y]

            self.is_dragging = False
            self.right_press = False

            self.instSet = context.object.mts_instrument_settings

            # save initial values
            self.uHudX = self.instSet.hudX
            self.uHudY = self.instSet.hudY

            self.initialMoveHudX = self.instSet.hudX
            self.initialMoveHudY = self.instSet.hudY

            self.mouse_offset = [0, 0]

            # get view width and set the panel offset
            area_width = context.area.width
            
            self.panel_dimensions = [400, 140]
            self.panel_offset = (area_width - self.panel_dimensions[0])/2

            self.gauge_texture_size = 128
            self.gauge_dimension = self.gauge_texture_size * self.instSet.hudScale

            self.gauge_pos = [
                (self.instSet.hudX - (self.gauge_dimension/2)) + self.panel_offset,
                (-self.instSet.hudY - (self.gauge_dimension/2)) + self.panel_dimensions[1]
            ]

            def draw_callback_px(self, context):
                # import images
                dirname = os.path.dirname(os.path.abspath(__file__))
                gauge_dir = os.path.join(dirname, "mts_instrument_tools_images/generic_gauge.png")
                hud_dir = os.path.join(dirname, "mts_instrument_tools_images/hud.png")
                confirm_dir = os.path.join(dirname, "mts_instrument_tools_images/confirm_button.png")
                cancel_dir = os.path.join(dirname, "mts_instrument_tools_images/cancel_button.png")
                preview_dir = os.path.join(dirname, "mts_instrument_tools_images/gauge_preview.png")

                # load if they exist
                try:
                    gauge = bpy.data.images.load(gauge_dir, check_existing=True)
                    gauge.gl_load()
                except:
                    self.report({'ERROR'}, "INSTRUMENT Image Not Found At: " + gauge_dir)

                try:
                    prev_gauge = bpy.data.images.load(preview_dir, check_existing=True)
                    prev_gauge.gl_load()
                except:
                    self.report({'ERROR'}, "PREVIEW Image Not Found At: " + preview_dir)

                try:
                    hud = bpy.data.images.load(hud_dir, check_existing=True)
                    hud.gl_load()
                except:
                    self.report({'ERROR'}, "HUD Image Not Found At: " + hud_dir)

                try:
                    confirm_button = bpy.data.images.load(confirm_dir, check_existing=True)
                    confirm_button.gl_load()
                except:
                    self.report({'ERROR'}, "Button Image Not Found At: " + confirm_dir)

                try:
                    cancel_button = bpy.data.images.load(cancel_dir, check_existing=True)
                    cancel_button.gl_load()
                except:
                    self.report({'ERROR'}, "Button Image Not Found At: " + cancel_dir)

                glEnable(GL_BLEND)

                # draw the hud
                draw_texture_2d(
                    hud.bindcode, (
                        self.panel_offset,
                        0
                    ),
     				self.panel_dimensions[0],
         			self.panel_dimensions[1]
            	)

                self.gauge_dimensions = self.gauge_texture_size * self.instSet.hudScale

                # set properties of the instrument
                self.gauge_pos = [
                    (self.instSet.hudX - (self.gauge_dimensions/2)) + self.panel_offset,
                    (-self.instSet.hudY - (self.gauge_dimensions/2)) + self.panel_dimensions[1]
                ]

                # for each unselected instrument draw the preview
                for obj in context.scene.objects:
                    if obj != context.object and obj.mts_instrument_settings.isInstrument:
                        instSet = obj.mts_instrument_settings

                        inst_dimension = self.gauge_texture_size * instSet.hudScale
                        
                        inst_pos = [
                            (instSet.hudX - (inst_dimension/2)) +
                            self.panel_offset,
                            (-instSet.hudY - (inst_dimension/2)) +
                            self.panel_dimensions[1]
                        ]
                        
                        draw_texture_2d(
                            prev_gauge.bindcode, (
                                inst_pos[0],
                                inst_pos[1]
                            ),
                            inst_dimension,
                            inst_dimension
                        )

                # draw the instrument
                draw_texture_2d(
                    gauge.bindcode, (
						self.gauge_pos[0],
						self.gauge_pos[1]
                	),
                    self.gauge_dimensions,
                    self.gauge_dimensions
                )

                draw_texture_2d(
                    confirm_button.bindcode, (
                    	self.gauge_pos[0] + self.gauge_dimensions + 10,
                    	self.gauge_pos[1]
                	),
                    25, 25
                )

                draw_texture_2d(
                    cancel_button.bindcode, (
						self.gauge_pos[0] + self.gauge_dimensions + 10,
						self.gauge_pos[1] + 35
					),
                    25, 25
                )

                glDisable(GL_BLEND)

                # draw the pos text
                font_id = 0
                blf.enable(font_id, 4)
                blf.color(font_id, 1, 1, 1, 1)
                blf.shadow(font_id, 5, 0, 0, 0, 1)
                blf.shadow_offset(font_id, 1, -1)
                blf.size(font_id, 20, 72)
                blf.position(font_id, self.gauge_pos[0], self.gauge_pos[1] + self.gauge_dimensions + 40, 0)
                blf.draw(font_id, "X: {}".format(self.instSet.hudX))
                blf.position(font_id, self.gauge_pos[0], self.gauge_pos[1] + self.gauge_dimensions + 20, 0)
                blf.draw(font_id, "Y: {}".format(self.instSet.hudY))

            # the arguments we pass the the callback
            args = (self, context)

            # Add the region OpenGL drawing callback
            self._handle = bpy.types.SpaceView3D.draw_handler_add(
                draw_callback_px, args, 'WINDOW', 'POST_PIXEL')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}

# custom properties for instruments
class InstrumentSettings(bpy.types.PropertyGroup):

    isInstrument: BoolProperty(
        name="Instrument",
        default=False
    )

    hudX: IntProperty(
        name="HUDPos X",
        default=0
    )

    hudY: IntProperty(
        name="HUDPos Y",
        default=0
    )

    hudScale: FloatProperty(
        name="HUD Scale",
        default=1,
        min=0.125,
        soft_max=10,
        step=1,
        precision=2,
        subtype='FACTOR'
    )

    placeOnPanel: BoolProperty(
        name="Place on Panel",
        default=False
    )

    applyAfter: StringProperty(
        name="Apply After",
        default=""
    )

    optionalPartNumber: IntProperty(
        name="Optional Part Number",
        default=0,
        soft_max=100
    )

# Menu: Instrument hud properties
class MTS_MT_HUDpropeditor(Menu):
    bl_idname = "MTS_MT_HUDpropeditor"
    bl_label = "Instrument Properties"

    def draw(self, context):
        layout = self.layout
        
        # get instrument settings
        instSet = context.object.mts_instrument_settings

        # instrument properties
        layout.prop(instSet, "hudX", text="HUD Pos X")
        layout.prop(instSet, "hudY", text="HUD Pos Y")
        layout.prop(instSet, "hudScale", text="HUD Scale")

# Panel: Instrument properties panel
class MTS_PT_MTSInstrumentPanel(Panel):
    # Class options
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
        instSet = obj.mts_instrument_settings

        row = layout.row()
        row.operator(icon='EXPORT', operator="mts.export_instruments")
        row.operator(icon="IMPORT", operator="mts.import_instruments")

        # instrument properties
        if instSet.isInstrument == True:
            layout.separator()

            layout.label(text="Hud Properties")
            box = layout.box()
            row = box.row()
            row.prop(instSet, "hudX", text="HUD Pos X")
            row.prop(instSet, "hudY", text="HUD Pos Y")

            # hud scale
            row = box.row()
            row.prop(instSet, "hudScale", text="HUD Scale")
            row.prop(instSet, "placeOnPanel", icon="WINDOW")

            layout.separator()

            layout.label(text="Slot Properties")
            box = layout.box()
            row = box.row()
            row.prop(instSet, "optionalPartNumber")
            row.prop(instSet, "applyAfter", text="Apply After", icon="LIBRARY_DATA_INDIRECT")

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

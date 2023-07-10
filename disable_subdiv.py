import bpy

class Disable_Subdiv(bpy.types.Operator):
	"Disables subdivision for selected objects"
	bl_label = "Disable Subdivision"
	bl_idname = "nc.disable_subdiv"
	bl_options = {"REGISTER", "UNDO"}

	@classmethod
	def poll(cls, context):
		return context.active_object is not None

	def execute(self, context):
		for obj in context.selected_objects:
			for m in obj.modifiers:
				if m.type != "SUBSURF":
					continue
				m.show_render = False
				m.show_viewport = False
		return {"FINISHED"}

def menu_func(self, context):
	self.layout.operator(Disable_Subdiv.bl_idname)

def register():
	bpy.utils.register_class(Disable_Subdiv)
	bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
	bpy.utils.unregister_class(Disable_Subdiv)
	bpy.types.VIEW3D_MT_object.remove(menu_func)
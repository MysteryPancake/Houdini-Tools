import bpy

bl_info = {
	"name": "ALA British Weather",
	"description": "Quickly assign sequence caches to characters",
	"author": "MysteryPancake",
	"version": (1, 0),
	"blender": (3, 5, 0),
	"location": "View 3D > Tool Shelf > British Weather",
	"support": "COMMUNITY",
	"category": "Rigging",
}

supported_rigs = {
	"gary": {
		"tie": [
			("C:\\Users\\MysteryPancake\\Desktop\\CLOTHSHIT\\gary_ties_v1.abc", "Ties Act 1", ""),
		],
		#"shirt": [],
		#"pants": []
	},
	#"carol": {
		#"blouse": [],
		#"skirt": [],
		#"scarf_": [],
		#"scarf2_": [],
		#"hair_main": [],
		#"hair_front_right": [],
		#"hair_front_left": []
	#}
}

#lib_cache = {}

#def get_anim_libs(self, context):
	#return lib_cache

#def set_anim_lib(self, context):
	# TODO
	#print("TODO")

#class Properties(bpy.types.PropertyGroup):
	#anim_lib: bpy.props.EnumProperty(name="Animation Library", items=get_anim_libs, update=set_anim_lib, default=None, options={"ANIMATABLE"})

#class Load_Animation(bpy.types.Operator):
	#bl_label = "Apply"
	#bl_idname = "bw.load_animation"

	#def execute(self, context):
		#bpy.ops.cachefile.open(filepath="C:\\Users\\MysteryPancake\\Desktop\\CLOTHSHIT\\cloth_anims.abc")
		#file = bpy.data.cache_files[-1]
		#print(file.object_paths)

		#return {"FINISHED"}

class Add_Cache_Modifier(bpy.types.Operator):
	"""Adds an animated sequence cache to the selected object"""
	bl_label = "Add Animation Cache Modifier"
	bl_idname = "bw.add_cache"
	bl_options = {"REGISTER", "UNDO"}

	modifier_name = "BW_ANIM"
	rig_name: bpy.props.StringProperty()
	object_name: bpy.props.StringProperty()

	def execute(self, context):
		target = getattr(context, "bw_target", None)
		if not target or not self.rig_name or not self.object_name:
			return {"CANCELLED"}
		
		# Never add the same modifier twice
		modifier = None
		for m in target.modifiers:
			if m.name == self.modifier_name:
				modifier = m
		
		if not modifier:
			modifier = target.modifiers.new(name=self.modifier_name, type="MESH_SEQUENCE_CACHE")
			bpy.ops.object.modifier_move_to_index({"object": target}, modifier=self.modifier_name, index=0)
		
		# Get animation libraries for the chosen object
		libs = supported_rigs[self.rig_name][self.object_name]
		chosen_lib = libs[0]

		# Load animation as cache file
		bpy.ops.cachefile.open(filepath=chosen_lib[0])
		cache = bpy.data.cache_files[-1]
		
		# Loop animation using driver
		cache.override_frame = True
		driver = cache.driver_add("frame").driver
		start_frame = 0
		loop_frames = 30
		speed = 1
		offset = 0
		speed_str = "" if speed == 1 else " * speed"
		offset_str = "" if offset == 0 else " + offset"
		frame_str = f"frame{speed_str}{offset_str}"
		if start_frame == 0:
			# Simple looping animation
			driver.expression = f"({frame_str}) % {loop_frames}"
		else:
			# Impact animation, loop after a specific frame
			driver.expression = f"min({frame_str}, ({frame_str} - {start_frame}) % {loop_frames} + {start_frame})"

		# Assign cache to modifier
		modifier.cache_file = cache
		modifier.object_path = "/rest"

		bpy.context.view_layer.objects.active = target

		return {"FINISHED"}

#class Animation_List(bpy.types.UIList):
#	bl_idname = "ALA_UL_Animation_List"
	#def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
		# TODO
		#layout.label(text="HAHA")

class Attachment_Panel(bpy.types.Panel):
	bl_label = "British Weather"
	bl_idname = "ALA_PT_Attachment_Panel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "British Weather"

	def draw(self, context):
		#props = context.scene.bw_props
		layout = self.layout

		selected = context.active_object
		if not selected or selected.type != "ARMATURE":
			layout.label(text="Please select a rig!")
			return
		
		found_rig = None
		for rig in supported_rigs:
			if rig in selected.name.lower():
				found_rig = rig
				break
		
		if found_rig:
			# Selected rig label
			layout.label(text=f"Selected Rig: {found_rig.title()}")
			# Add modifier buttons
			objs = supported_rigs[found_rig]
			for obj_name in objs:
				for child in selected.children:
					if obj_name in child.name.lower():
						row = layout.row()
						# Pass data to operator using context pointers
						row.context_pointer_set(name="bw_target", data=child)
						# Can't pass objs[obj_name] so pass two strings instead
						params = row.operator(Add_Cache_Modifier.bl_idname, text=f"Animate {obj_name.title()}", icon="ADD")
						params.rig_name = found_rig
						params.object_name = obj_name
						break

			# Update dropdown content
			#global lib_cache
			#lib_cache = rig["libs"]

			# Library dropdown, hide label
			#layout.prop(props, "anim_lib", text="", icon="ASSET_MANAGER")

			# Animation list
			#layout.template_list(Animation_List.bl_idname, "", selected, "material_slots", selected, "active_material_index")
		else:
			layout.label(text=f"Unsupported Rig: {selected.name}")

# Dump all classes to register in here
classes = [Attachment_Panel, Add_Cache_Modifier]

def register() -> None:
	for cls in classes:
		bpy.utils.register_class(cls)
	#bpy.types.Scene.bw_props = bpy.props.PointerProperty(type=Properties)

def unregister() -> None:
	#del bpy.types.Scene.bw_props
	for cls in classes:
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()
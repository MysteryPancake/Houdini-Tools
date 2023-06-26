import bpy, functools
from uuid import uuid4

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
			("A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\cloth_library\\gary_ties_v1.abc", "Ties of the Office: Pack 1 of 3000", "", "ASSET_MANAGER", 0),
			("A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\cloth_library\\gary_ties_v2.abc", "The John Pork Signature Collection", "", "MONKEY", 1)
		],
		"shirt": [],
		"pants": []
	},
	"carol": {
		"blouse": [],
		"skirt": [],
		"scarf_": [],
		"scarf2_": [],
		"hair_main": [],
		"hair_front_right": [],
		"hair_front_left": []
	}
}

def load_cache(path: str) -> bpy.types.CacheFile:
	bpy.ops.cachefile.open(filepath=path)
	cache = bpy.data.cache_files[-1]
	# Randomize name to ensure it's always last
	cache.name = str(uuid4())
	return cache

def set_driver(cache: bpy.types.CacheFile, speed: float, offset: float, start_frame: int = 0, loop_frames: int = 30) -> None:
	# Never add the same driver twice
	driver = None
	anim_data = cache.animation_data
	if anim_data and anim_data.drivers:
		driver = anim_data.drivers[-1].driver
	else:
		driver = cache.driver_add("frame").driver

	# Loop animation using driver
	cache.override_frame = True
	speed_str = "" if speed == 1 else " * speed"
	offset_str = "" if offset == 0 else " + offset"
	frame_str = f"frame{speed_str}{offset_str}"
	if start_frame == 0:
		# Simple looping animation
		driver.expression = f"({frame_str}) % {loop_frames}"
	else:
		# Loop after a specific frame
		driver.expression = f"min({frame_str}, ({frame_str} - {start_frame}) % {loop_frames} + {start_frame})"

def update_anims(object: bpy.types.Object, cache: bpy.types.CacheFile) -> None:
	anim_data = object.bw_anim_data
	if not anim_data.caches:
		for path in cache.object_paths:
			item = anim_data.caches.add()
			item.name = path.path
	# Force UI update
	object.select_set(True)

def get_anim_libs(self, context):
	# TODO
	print("TODO")
	return supported_rigs["gary"]["tie"]

def set_anim_lib(self, context):
	target = getattr(context, "bw_target", None)
	modifier = getattr(context, "bw_modifier", None)
	if not target or not modifier:
		return
	
	# Load animation cache
	cache = load_cache(self.cache_lib)
	set_driver(cache, 1, 0, 0, 30)

	# Apply to modifier
	modifier.cache_file = cache
	modifier.object_path = "/rest"

	# Reset animation list
	self.caches.clear()

	# Update menu contents after brief delay
	bpy.app.timers.register(functools.partial(update_anims, target, cache), first_interval=0.01)

def set_anim(self, context):
	target = getattr(context, "bw_target", None)
	modifier = getattr(context, "bw_modifier", None)
	if not target or not modifier:
		return
	
	# Update animation cache
	selected_cache = self.caches[self.selected_index]
	modifier.object_path = selected_cache.name

	# Update driver settings
	set_driver(modifier.cache_file, selected_cache.speed, selected_cache.offset, 0, 30)

class Animation_Property(bpy.types.PropertyGroup):
	# Name is built into PropertyGroup
	speed: bpy.props.FloatProperty(name="Speed", default=1)
	offset: bpy.props.FloatProperty(name="Offset", default=0)

class Animation_List_Data(bpy.types.PropertyGroup):
	cache_lib: bpy.props.EnumProperty(name="Animation Library", items=get_anim_libs, update=set_anim_lib)
	caches: bpy.props.CollectionProperty(type=Animation_Property)
	selected_index: bpy.props.IntProperty(default=0, update=set_anim)

class Add_Cache_Modifier(bpy.types.Operator):
	"""Adds an animated sequence cache to the selected object"""
	bl_label = "Add Animation Cache Modifier"
	bl_idname = "bw.add_cache"
	bl_options = {"REGISTER", "UNDO"}

	cache_name = "BW_SEQUENCE_CACHE"
	weight_name = "BW_VERTEX_WEIGHT"

	rig_name: bpy.props.StringProperty(name="Rig Name")
	object_name: bpy.props.StringProperty(name="Object Name")

	def execute(self, context):
		target = getattr(context, "bw_target", None)
		if not target or not self.rig_name or not self.object_name:
			self.report({"ERROR_INVALID_INPUT"}, "Missing parameters!")
			return {"CANCELLED"}
		
		if self.rig_name not in supported_rigs:
			self.report({"ERROR_INVALID_INPUT"}, f"Unsupported rig {self.rig_name}!")
			return {"CANCELLED"}
		
		supported_objs = supported_rigs[self.rig_name]
		if self.object_name not in supported_objs:
			self.report({"ERROR_INVALID_INPUT"}, f"Unsupported object {self.object_name}!")
			return {"CANCELLED"}
		
		libs = supported_objs[self.object_name]
		if not libs:
			self.report({"ERROR_INVALID_INPUT"}, f"No animations for {self.object_name}!")
			return {"CANCELLED"}
		
		# Never add the same modifier twice
		cache_modifier = None
		weight_modifier = None

		for m in target.modifiers:
			match m.name:
				case self.cache_name:
					cache_modifier = m
				case self.weight_name:
					weight_modifier = m
		
		if not cache_modifier:
			cache_modifier = target.modifiers.new(name=self.cache_name, type="MESH_SEQUENCE_CACHE")
			bpy.ops.object.modifier_move_to_index({"object": target}, modifier=self.cache_name, index=0)
		
		if not weight_modifier:
			weight_modifier = target.modifiers.new(name=self.weight_name, type="VERTEX_WEIGHT_EDIT")
			bpy.ops.object.modifier_move_to_index({"object": target}, modifier=self.weight_name, index=1)
		
		# Load animation as cache file
		chosen_lib = libs[0]
		cache = load_cache(chosen_lib[0])
		set_driver(cache, 1, 0, 0, 30)

		# Assign cache to modifier
		cache_modifier.cache_file = cache
		cache_modifier.object_path = "/rest"

		# Add vertex weights for rigging, assume tie for now
		weight_modifier.vertex_group = "DEF-spine.003"
		weight_modifier.default_weight = 1
		weight_modifier.use_add = True
		weight_modifier.add_threshold = 0
		
		# Update menu contents after brief delay
		bpy.app.timers.register(functools.partial(update_anims, target, cache), first_interval=0.01)

		return {"FINISHED"}

class Animation_List(bpy.types.UIList):
	bl_idname = "ALA_UL_Animation_List"
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
		row = layout.row()
		row.label(text=item.name)

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
		
		if not found_rig:
			layout.label(text=f"Unsupported Rig: {selected.name}")
			return
		
		# Selected rig label
		layout.label(text=f"Selected Rig: {found_rig.title()}")
		# Add modifier buttons
		objs = supported_rigs[found_rig]
		for obj_name in objs:
			for child in selected.children:
				if obj_name not in child.name.lower():
					continue
				
				# Attempt to find cache modifier
				cache_modifier = None
				for m in child.modifiers:
					if m.name == Add_Cache_Modifier.cache_name:
						cache_modifier = m
						break
				
				col = layout.column()
				# Pass data around using context pointers
				col.context_pointer_set(name="bw_target", data=child)

				if cache_modifier:
					col.context_pointer_set(name="bw_modifier", data=cache_modifier)
					col.prop(child.bw_anim_data, "cache_lib", text="")
					col.template_list(Animation_List.bl_idname, "", child.bw_anim_data, "caches", child.bw_anim_data, "selected_index")
				else:
					# Can't pass objs[obj_name] so pass two strings instead
					params = col.operator(Add_Cache_Modifier.bl_idname, text=f"Animate {obj_name.title()}", icon="ADD")
					params.rig_name = found_rig
					params.object_name = obj_name
				break

# Dump all classes to register in here
classes = [Attachment_Panel, Add_Cache_Modifier, Animation_Property, Animation_List, Animation_List_Data]

def register() -> None:
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Object.bw_anim_data = bpy.props.PointerProperty(type=Animation_List_Data)

def unregister() -> None:
	del bpy.types.Object.bw_anim_data
	for cls in classes:
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()
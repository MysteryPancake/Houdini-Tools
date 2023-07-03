import bpy, functools
from uuid import uuid4

bl_info = {
	"name": "ALA No Cloth Sims",
	"description": "Avoid cloth sims for the small price of everything clipping",
	"author": "MysteryPancake",
	"version": (1, 0),
	"blender": (3, 5, 0),
	"location": "View 3D > Tool Shelf > No Cloth Sims",
	"support": "COMMUNITY",
	"category": "Rigging",
}

# ===========================================================================================================
# Welcome to your doom :)
# This addon makes it faster to add looping Sequence Caches to objects.

# Sequence Caches are animations stored in Alembic or USD files.
# To read them, Blender uses the "Mesh Sequence Cache" modifier to replace an object's vertices every frame.
# Only the vertices are replaced, so materials stay but UVs are replaced.

# Vertex groups are used to bind rigs to geometry in Blender.
# This fucks up since vertex groups can't be saved in Alembic or USD files, so Sequence Caches ruin the rig.
# TO fix this, you need to add the vertex groups again after the "Mesh Sequence Cache" modifier.
# This can be done with "Vertex Weight Edit", "Data Transfer" or Geometry Nodes.

# UPDATE: Vertex groups actually export to Alembic files now??? HOW???
# =============================================================================================================

supported = [
	{
		"mesh": "tie",
		"armature": "gary", # Optional, unused for now
		"libs": [
			("A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\cloth_library\\gary_test_cloth.abc", "Gary's Ties: Volume 1", "", "ASSET_MANAGER", 0)
		],
	}
]

def check_supported_fuzzy(name: str, key: str):
	for item in supported:
		if item.get(key, None) in name:
			return item

def check_supported_exact(name: str, key: str):
	for item in supported:
		if item.get(key, None) == name:
			return item

# Yucky code here, at least it works
def find_first_object(context: bpy.types.Context):
	for obj in context.selected_objects:
		if obj.type == "MESH":
			data = check_supported_fuzzy(obj.name, "mesh")
			if data:
				return (obj, data)
		for child in obj.children_recursive:
			if child.type != "MESH":
				continue
			data = check_supported_fuzzy(child.name, "mesh")
			if data:
				return (child, data)
	return (None, None)

def load_cache(path: str) -> bpy.types.CacheFile:
	bpy.ops.cachefile.open(filepath=path)
	cache = bpy.data.cache_files[-1]
	# Randomize the name so Blender doesn't reorder it
	cache.name = str(uuid4())
	return cache

def set_driver(cache: bpy.types.CacheFile, path: str, speed: float, offset: float) -> None:
	(name, loop_start, loop_end) = parse_path(path)
	loop_duration = loop_end - loop_start

	# Non-animated sequence, don't bother adding drivers
	if loop_duration == 0:
		return

	# Never add the same driver twice
	driver = None
	anim_data = cache.animation_data
	if anim_data and anim_data.drivers:
		driver = anim_data.drivers[-1].driver
	else:
		driver = cache.driver_add("frame").driver

	# Loop animation using frame driver
	cache.override_frame = True
	speed_str = "" if speed == 1 else f" * {speed}"
	offset_str = "" if offset == 0 else f" + {offset}"
	frame_str = f"frame{speed_str}{offset_str}"
	if loop_start == 0:
		# Simple looping animation
		driver.expression = f"({frame_str}) % {loop_duration + 1}"
	else:
		# Loop after a specific frame
		driver.expression = f"min({frame_str}, ({frame_str} - {loop_start}) % {loop_duration + 1} + {loop_start})"

def parse_path(path: str):
	"""Parses name and frame range data stored in an Alembic path"""
	# "/shirt/bruh/anim_lol_10_63" -> ("Anim Lol", 10, 63)
	# "/shirt/rest" -> ("Rest", 0, 0)
	# "/shirt/flap_12" -> ("Flap", 0, 12)
	# "/shirt/" -> ("", 0, 0)
	# "/shirt" -> ("Shirt", 0, 0)
	# "/" -> ("", 0, 0)
	# "" -> ("", 0, 0)

	# This shouldn't happen unless you screw up the export
	if not path:
		return ("", "", 0, 0)
	
	# Strip first slash, eg. "/flap_63" becomes "flap_63"
	if path[0] == "/":
		path = path[1:]
		
	parts = path.split("/")
	start_frame = 0
	end_frame = 0
	anim = parts[-1]
	
	# Find frame end, eg. tie_10_63 returns 63
	underscore = anim.rfind("_")
	if (underscore >= 0):
		try:
			end_frame = int(anim[underscore + 1:])
		except:
			pass
		anim = anim[:underscore]
		# Find frame start, eg. /flap_10_63 returns 10
		underscore = anim.rfind("_")
		if (underscore >= 0):
			try:
				start_frame = int(anim[underscore + 1:])
			except:
				pass
			anim = anim[:underscore]
	
	# User displayed name, eg. "/fast_flap_10_63" returns "Fast Flap"
	anim = anim.replace("_", " ").title()
	return (anim, start_frame, end_frame)

class Animation_List_Data(bpy.types.PropertyGroup):

	def get_anim_libs(self, context):
		(obj, data) = find_first_object(context)
		if data:
			return data["libs"]

	def set_anim_lib(self, context):
		target = getattr(context, "nc_target", None)
		modifier = getattr(context, "nc_modifier", None)
		if not target or not modifier:
			return
		
		cache = load_cache(self.cache_lib)
		modifier.cache_file = cache
	
	def set_anim(self, context):
		target = getattr(context, "nc_target", None)
		modifier = getattr(context, "nc_modifier", None)
		if not target or not modifier:
			return
		
		# Update animation cache
		selected_anim = modifier.cache_file.object_paths[self.selected_index]
		modifier.object_path = selected_anim.path

		# Update driver settings
		set_driver(modifier.cache_file, selected_anim.path, self.speed, self.offset)
	
	def update_driver(self, context):
		modifier = getattr(context, "nc_modifier", None)
		if not modifier:
			return
		set_driver(modifier.cache_file, modifier.object_path, self.speed, self.offset)

	cache_lib: bpy.props.EnumProperty(name="Animation Library", items=get_anim_libs, update=set_anim_lib)
	selected_index: bpy.props.IntProperty(default=0, update=set_anim)
	speed: bpy.props.FloatProperty(name="Speed", default=1, update=update_driver)
	offset: bpy.props.FloatProperty(name="Offset", default=0, update=update_driver)

class Animation_List(bpy.types.UIList):
	bl_idname = "ALA_UL_Animation_List"

	def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
		row = layout.row()
		name = parse_path(item.path)[0]
		row.label(text=name)

class Add_Cache_Modifier(bpy.types.Operator):
	"""Adds an animated sequence cache to the selected object"""
	bl_label = "Add Modifiers"
	bl_idname = "nc.add_cache"
	bl_options = {"REGISTER", "UNDO"}

	cache_name = "NC_SEQUENCE_CACHE"
	weight_name = "NC_VERTEX_WEIGHT"
	object_name: bpy.props.StringProperty(name="Object Name")

	def execute(self, context):
		target = getattr(context, "nc_target", None)
		if not target or not self.object_name:
			self.report({"ERROR_INVALID_INPUT"}, "Missing parameters!")
			return {"CANCELLED"}

		data = check_supported_exact(self.object_name, "mesh")
		if not data:
			self.report({"ERROR_INVALID_INPUT"}, f"Unsupported object {self.object_name}!")
			return {"CANCELLED"}
		
		libs = data["libs"]
		if not libs:
			self.report({"ERROR_INVALID_INPUT"}, f"No animations for {self.object_name}!")
			return {"CANCELLED"}
		
		# Ensure we don't add the same modifier twice
		cache_modifier: bpy.types.MeshSequenceCacheModifier = None
		weight_modifier: bpy.types.VertexWeightEditModifier = None

		for m in target.modifiers:
			match m.name:
				case self.cache_name:
					cache_modifier = m
				case self.weight_name:
					weight_modifier = m
		
		if not cache_modifier:
			cache_modifier = target.modifiers.new(name=self.cache_name, type="MESH_SEQUENCE_CACHE")
			bpy.ops.object.modifier_move_to_index({"object": target}, modifier=self.cache_name, index=0)
		
		# Hardcoded tie for now
		if self.object_name == "tie":
			if not weight_modifier:
				weight_modifier = target.modifiers.new(name=self.weight_name, type="VERTEX_WEIGHT_EDIT")
				bpy.ops.object.modifier_move_to_index({"object": target}, modifier=self.weight_name, index=1)

			# Add vertex weights for rigging, assume tie for now
			weight_modifier.vertex_group = "DEF-spine.003"
			weight_modifier.default_weight = 1
			weight_modifier.use_add = True
			weight_modifier.add_threshold = 0

		# Load the top library by default
		chosen_lib = libs[0]
		cache = load_cache(chosen_lib[0])

		# Assign cache to modifier
		cache_modifier.cache_file = cache

		return {"FINISHED"}

class Add_Overrides(bpy.types.Operator):
	"""Adds library overrides to the selected object"""
	bl_label = "Library Override Selected"
	bl_idname = "nc.add_overrides"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		bpy.ops.object.make_override_library()
		return {"FINISHED"}

class Reset_Position(bpy.types.Operator):
	"""Resets the position of the selected object"""
	bl_label = "Reset Position"
	bl_idname = "nc.reset_position"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		bpy.ops.object.location_clear()
		return {"FINISHED"}

class Reset_Rotation(bpy.types.Operator):
	"""Resets the rotation of the selected object"""
	bl_label = "Reset Rotation"
	bl_idname = "nc.reset_rotation"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		bpy.ops.object.rotation_clear()
		return {"FINISHED"}

class Brute_Force_Panel(bpy.types.Panel):
	bl_label = "Brute Force"
	bl_idname = "ALA_PT_Brute_Force_Panel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "No Cloth Sims"

	def draw(self, context):
		layout = self.layout
		layout.operator(Add_Overrides.bl_idname)
		layout.operator(Reset_Rotation.bl_idname)

class Animation_Panel(bpy.types.Panel):
	bl_label = "Animation"
	bl_idname = "ALA_PT_Animation_Panel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "No Cloth Sims"

	def draw(self, context):
		layout = self.layout
		props = context.scene.nc_props

		(obj, data) = find_first_object(context)
		if not data:
			layout.label(text="No supported object selected!")
			return
		
		mesh_name = data["mesh"]
		layout.label(text=f"Selected: {mesh_name}")

		# Pass stuff around with context pointers
		layout.context_pointer_set(name="nc_target", data=obj)

		# Check for cache modifier
		cache_modifier = None
		for m in obj.modifiers:
			if m.name == Add_Cache_Modifier.cache_name:
				cache_modifier = m
				break
		
		if cache_modifier:
			layout.context_pointer_set(name="nc_modifier", data=cache_modifier)
			layout.prop(props, "cache_lib", text="")
			layout.template_list(Animation_List.bl_idname, "", cache_modifier.cache_file, "object_paths", props, "selected_index")
			layout.prop(props, "speed")
			layout.prop(props, "offset")
		else:
			params = layout.operator(Add_Cache_Modifier.bl_idname, icon="ADD")
			params.object_name = data["mesh"]

# Dump all classes to register in here
classes = [Brute_Force_Panel, Animation_Panel, Add_Overrides, Reset_Position, Reset_Rotation, Add_Cache_Modifier, Animation_List, Animation_List_Data]

def register() -> None:
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Scene.nc_props = bpy.props.PointerProperty(type=Animation_List_Data)

def unregister() -> None:
	del bpy.types.Scene.nc_props
	for cls in classes:
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()
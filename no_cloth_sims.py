import bpy, os

bl_info = {
	"name": "No Cloth Sims",
	"description": "Avoid cloth sims for the small price of everything clipping",
	"author": "MysteryPancake",
	"version": (1, 0),
	"blender": (3, 5, 0),
	"location": "View 3D > Tool Shelf > COFFEE BREAK",
	"support": "COMMUNITY",
	"category": "ALA",
}

# ===========================================================================================================
# Welcome to your doom :)
# This addon makes it faster to add looping Sequence Caches to objects.

# Sequence Caches are animations stored in Alembic or USD files.
# To read them, Blender uses the "Mesh Sequence Cache" modifier to replace an object's vertices every frame.
# Only the vertices are replaced, so materials stay but UVs are replaced.

# Vertex groups are used to bind rigs to geometry in Blender.
# This screws up since vertex groups can't be saved in Alembic or USD files, so Sequence Caches ruin the rig.
# TO fix this, you need to add the vertex groups again after the "Mesh Sequence Cache" modifier.
# This can be done with "Vertex Weight Edit", "Data Transfer" or Geometry Nodes.

# UPDATE: Vertex groups actually export to Alembic files now!
# =============================================================================================================

supported = [
	{
		"mesh": "tie",
		"armature": "gary", # Optional, unused for now
		"libs": [
			("A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\cloth_library\\gary_test_ties_v2.abc", "Don't mess with the UVs v1", "", "ASSET_MANAGER", 0),
			("A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\cloth_library\\gary_dimension_ties.abc", "Dimension Ties", "", "MONKEY", 1),
			("A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\cloth_library\\gary_dimension_ties_v2.abc", "John Pork Signature Collection", "", "MONKEY", 2),
			("A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\cloth_library\\rest_tie.abc", "Rest Tie", "", "MONKEY", 3)
		],
	}
]

cache_modifier_name = "NC_SEQUENCE_CACHE"
weight_modifier_name = "NC_VERTEX_WEIGHT"

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
	# Cache order is random, so we need to find the match manually
	for cache in bpy.data.cache_files:
		if os.path.samefile(cache.filepath, path):
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

def get_shot_name() -> str:
	blend_file = bpy.path.basename(bpy.data.filepath)
	blend_name = os.path.splitext(blend_file)[0]
	last_dash = blend_name.rfind("_")
	return blend_name[:last_dash]

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
		return ("", 0, 0)
	
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
	anim = anim.replace("_", " ").strip().title()
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
	bake_name: bpy.props.StringProperty(name="Bake Name", default="tie")
	weight_name: bpy.props.StringProperty(name="Weight Name", default="DEF-spine.003")

class Animation_List(bpy.types.UIList):
	bl_idname = "ALA_UL_Animation_List"

	def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
		row = layout.row()
		name = parse_path(item.path)[0]
		row.label(text=name)

class Add_Modifiers(bpy.types.Operator):
	"""Adds an animated sequence cache to the selected object"""
	bl_label = "Add Modifiers"
	bl_idname = "nc.add_modifiers"
	bl_options = {"REGISTER", "UNDO"}

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
		cache_modifier: bpy.types.MeshSequenceCacheModifier = target.modifiers.get(cache_modifier_name)
		weight_modifier: bpy.types.VertexWeightEditModifier = target.modifiers.get(weight_modifier_name)

		if not cache_modifier:
			cache_modifier = target.modifiers.new(name=cache_modifier_name, type="MESH_SEQUENCE_CACHE")
			cache_modifier.use_vertex_interpolation = True
			cache_modifier.read_data = {"VERT", "UV"}
			bpy.ops.object.modifier_move_to_index({"object": target}, modifier=cache_modifier_name, index=0)
		
		# Hardcoded tie for now
		if self.object_name == "tie":
			if not weight_modifier:
				weight_modifier = target.modifiers.new(name=weight_modifier_name, type="VERTEX_WEIGHT_EDIT")
				bpy.ops.object.modifier_move_to_index({"object": target}, modifier=weight_modifier_name, index=1)

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

class Remove_Modifiers(bpy.types.Operator):
	"""Removes added animated sequence caches from the selected object"""
	bl_label = "Remove Modifiers"
	bl_idname = "nc.remove_modifiers"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		target = getattr(context, "nc_target", None)
		if not target:
			self.report({"ERROR_INVALID_INPUT"}, "Missing parameters!")
			return {"CANCELLED"}
		
		cache_modifier: bpy.types.MeshSequenceCacheModifier = target.modifiers.get(cache_modifier_name)
		if cache_modifier:
			target.modifiers.remove(cache_modifier)

		weight_modifier: bpy.types.VertexWeightEditModifier = target.modifiers.get(weight_modifier_name)
		if weight_modifier:
			target.modifiers.remove(weight_modifier)
		
		return {"FINISHED"}

class Bake_Animation(bpy.types.Operator):
	"""Bakes the animation to the FX folder in world space"""
	bl_label = "Bake in World Space"
	bl_idname = "nc.bake_animation"
	bl_options = {"REGISTER", "UNDO"}

	object_name: bpy.props.StringProperty(name="Object Name")

	def execute(self, context):
		target = getattr(context, "nc_target", None)
		if not target or not self.object_name:
			self.report({"ERROR_INVALID_INPUT"}, "Missing object name!")
			return {"CANCELLED"}
		
		shot = get_shot_name()
		if not shot:
			self.report({"ERROR_INVALID_INPUT"}, "Missing shot name!")
			return {"CANCELLED"}

		cache_folder = f"A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\Production\\{shot}\\caches\\abc"
		cache_file = f"{shot}_{self.object_name}.abc"

		# Ensure folders exist
		if not os.path.exists(cache_folder):
			os.umask(0)
			os.makedirs(cache_folder)

			# Add bonus folders too, why not
			os.makedirs( f"A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\Production\\{shot}\\blender")
			os.makedirs( f"A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\Production\\{shot}\\houdini")
			os.makedirs( f"A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\Production\\{shot}\\movies")

		# Make sure only the target is selected for export
		bpy.ops.object.select_all(action="DESELECT")
		target.select_set(True)
		bpy.ops.wm.alembic_export(filepath=os.path.join(cache_folder, cache_file), selected=True)

		return {"FINISHED"}

class Load_Bake(bpy.types.Operator):
	"""Loads a baked animation from the FX folder"""
	bl_label = "Load Baked Animation"
	bl_idname = "nc.load_bake"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		bake_name = context.scene.nc_props.bake_name
		if not bake_name:
			self.report({"ERROR_INVALID_INPUT"}, "Please type in a bake name!")
			return {"CANCELLED"}

		shot = get_shot_name()
		cache_folder = f"A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\Production\\{shot}\\caches\\abc"
		cache_file = f"{shot}_{bake_name}.abc"

		file_path = os.path.join(cache_folder, cache_file)
		if not os.path.exists(file_path):
			self.report({"ERROR_INVALID_INPUT"}, f"No sim named {cache_file} found!")
			return {"CANCELLED"}
		
		# Check for Shino required collection
		shino_col = context.scene.collection.children.get(f"{shot}_fx")
		if not shino_col:
			shino_col = bpy.data.collections.new(name=f"{shot}_fx")
			context.scene.collection.children.link(shino_col)

			# Add FX collection for Shino publish
			tie_col = bpy.data.collections.new(name=f"--> {shot}_{bake_name}_fx")
			shino_col.children.link(tie_col)

		# Import file
		bpy.ops.wm.alembic_import(filepath=file_path, always_add_cache_reader=True, set_frame_range=False)

		# Force the tie to work
		if bake_name == "tie":
			# Link material
			with bpy.data.libraries.load("A:\\mav\\2023\\sandbox\\studio2\\s223\\blender\\s223\\assets\\character\\chargary01.blend", link=True) as (data_from, data_to):
				data_to.materials = ["gary_tie"]
			# Assign material
			for obj in context.selected_objects:
				if obj.type == "MESH":
					obj.data.materials.append(data_to.materials[0])
					# Add missing subsurface modifier
					obj.modifiers.new(name="NC_SUBSURFACE", type="SUBSURF")

		return {"FINISHED"}

class Add_Overrides(bpy.types.Operator):
	"""Adds library overrides to the selected object"""
	bl_label = "Library Override Selected"
	bl_idname = "nc.add_overrides"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		bpy.ops.object.make_override_library()
		return {"FINISHED"}

class Toggle_Vertex_Weights(bpy.types.Operator):
	"""Toggle between vertex weights and bone envelopes"""
	bl_label = "Toggle Vertex Weights"
	bl_idname = "nc.toggle_weights"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		target = getattr(context, "nc_target", None)
		if not target:
			self.report({"ERROR_INVALID_INPUT"}, "Missing target!")
			return {"CANCELLED"}
			
		for m in target.modifiers:
			if m.type != "ARMATURE":
				continue
			m.use_bone_envelopes = m.use_vertex_groups
			m.use_vertex_groups = not m.use_vertex_groups

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

class Override_Weights(bpy.types.Operator):
	"""Replaces the vertex weights of the selected object"""
	bl_label = "Replace Vertex Weights"
	bl_idname = "nc.override_weights"
	bl_options = {"REGISTER", "UNDO"}

	def execute(self, context):
		props = context.scene.nc_props
		target = getattr(context, "nc_target", None)

		if not target:
			self.report({"ERROR_INVALID_INPUT"}, "Missing target!")
			return {"CANCELLED"}

		target.vertex_groups.clear()
		spine_group = target.vertex_groups.new(name=props.weight_name)
		spine_group.add([v.index for v in target.data.vertices], 1, "REPLACE")

		return {"FINISHED"}

class Assembly_Panel(bpy.types.Panel):
	bl_label = "Assembly"
	bl_idname = "ALA_PT_Assembly_Panel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "COFFEE BREAK"

	def draw(self, context):
		layout = self.layout
		props = context.scene.nc_props
		layout.prop(props, "bake_name")
		layout.operator(Load_Bake.bl_idname, icon="IMPORT")

class Brute_Force_Panel(bpy.types.Panel):
	bl_label = "Brute Force"
	bl_idname = "ALA_PT_Brute_Force_Panel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "COFFEE BREAK"

	def draw(self, context):
		layout = self.layout
		layout.operator(Add_Overrides.bl_idname, icon="UNLINKED")
		layout.operator(Reset_Position.bl_idname, icon="OBJECT_ORIGIN")
		layout.operator(Reset_Rotation.bl_idname, icon="DRIVER_ROTATIONAL_DIFFERENCE")

class Animation_Panel(bpy.types.Panel):
	bl_label = "Animation"
	bl_idname = "ALA_PT_Animation_Panel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "COFFEE BREAK"

	def draw(self, context):
		layout = self.layout
		props = context.scene.nc_props

		(obj, data) = find_first_object(context)
		if not obj:
			layout.label(text="No supported object selected!")
			return
		
		mesh_name = data["mesh"]
		layout.label(text=f"Selected: {mesh_name}")

		# Pass stuff around with context pointers
		layout.context_pointer_set(name="nc_target", data=obj)

		# Check for cache modifier
		cache_modifier = obj.modifiers.get(cache_modifier_name)
		if cache_modifier:
			layout.context_pointer_set(name="nc_modifier", data=cache_modifier)
			
			row = layout.row()
			split = row.split(factor=0.9, align=True)
			split.prop(props, "cache_lib", text="")
			split.operator(Remove_Modifiers.bl_idname, text="", icon="X")

			layout.template_list(Animation_List.bl_idname, "", cache_modifier.cache_file, "object_paths", props, "selected_index")
			layout.prop(props, "speed")
			layout.prop(props, "offset")
		
			layout.operator(Toggle_Vertex_Weights.bl_idname, text="Swap Parenting Mode", icon="MOD_SIMPLEDEFORM")
			layout.operator(Override_Weights.bl_idname, icon="MESH_DATA")
			layout.prop(props, "weight_name")

			layout.operator(Bake_Animation.bl_idname, icon="FILE_TICK").object_name = mesh_name
		else:
			layout.operator(Add_Modifiers.bl_idname, text=f"Animate {mesh_name.title()}", icon="ADD").object_name = mesh_name

# Dump all classes to register in here
classes = [
	Brute_Force_Panel, Animation_Panel, Assembly_Panel,
	Add_Overrides, Reset_Position, Reset_Rotation, Add_Modifiers, Remove_Modifiers, Load_Bake, Bake_Animation, Toggle_Vertex_Weights, Override_Weights,
	Animation_List, Animation_List_Data
]

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

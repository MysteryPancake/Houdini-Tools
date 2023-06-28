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

# The array below contains all supported armatures and objects.

# For armatures, it works like this:
# 1. Search for a rig containing "gary", for example "gary_001"
# 2. Search the rig's children for matching objects, for example "tie_final"
# 3. Add a button to animate each child object
# 4. Profit

# Part names must exactly match the exported Alembic path names
# For example "tie" matches animations under "/tie/*"

supported = [
	{
		"armature": "gary",
		"libs": [
			("A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\cloth_library\\gary_test_cloth.abc", "Gary's Drip: Volume 1", "", "ASSET_MANAGER", 0)
		],
		"parts": ["tie", "shirt", "pants"]
	},
	{
		"armature": "carol",
		"libs": [],
		"parts": ["blouse", "skirt", "scarf_", "scarf2_", "hair_main", "hair_front_right", "hair_front_left"]
	}
]

class Animation_Property(bpy.types.PropertyGroup):
	"""Animation properties for each Mesh Sequence Cache"""

	def update_driver(self, context):
		item = getattr(context, "nc_item", None)
		modifier = getattr(context, "nc_modifier", None)
		if not item or not modifier:
			return
		set_driver(modifier.cache_file, item)

	# Name is built into PropertyGroup
	path: bpy.props.StringProperty(name="Path")
	speed: bpy.props.FloatProperty(name="Speed", default=1, update=update_driver)
	offset: bpy.props.FloatProperty(name="Offset", default=0, update=update_driver)
	loop_start: bpy.props.IntProperty(name="Loop Start Frame", default=0)
	loop_duration: bpy.props.IntProperty(name="Loop Duration", default=0)

# This will get used for objects later
def find_rig_data(name: str, category: str):
	for item in supported:
		if item.get(category, None) in name:
			return item

def load_cache(path: str) -> bpy.types.CacheFile:
	# Load the cache again, never use multiusers
	# In Blender, each cache directly stores the timing properties
	# Animation timing must be independent per object, so we need independent caches
	bpy.ops.cachefile.open(filepath=path)
	cache = bpy.data.cache_files[-1]
	# Randomize the name so Blender doesn't reorder it
	cache.name = str(uuid4())
	return cache

def set_driver(cache: bpy.types.CacheFile, prop: Animation_Property) -> None:
	# Non-animated sequence, don't bother adding drivers
	if prop.loop_duration == 0:
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
	speed_str = "" if prop.speed == 1 else f" * {prop.speed}"
	offset_str = "" if prop.offset == 0 else f" + {prop.offset}"
	frame_str = f"frame{speed_str}{offset_str}"
	if prop.loop_start == 0:
		# Simple looping animation
		driver.expression = f"({frame_str}) % {prop.loop_duration + 1}"
	else:
		# Loop after a specific frame
		driver.expression = f"min({frame_str}, ({frame_str} - {prop.loop_start}) % {prop.loop_duration + 1} + {prop.loop_start})"

def extract_path_data(path: str):
	"""Extract category, name and frame range data stored in an Alembic path"""
	# Examples:
	# "/shirt/bruh/anim_lol_10_63" -> ("shirt", "Anim Lol", 10, 63)
	# "/shirt/rest" -> ("shirt", "Rest", 0, 0)
	# "/shirt/flap_12" -> ("shirt", "Flap", 0, 12)
	# "/shirt/" -> ("shirt", "", 0, 0)
	# "/shirt" -> ("", "Shirt", 0, 0)
	# "/" -> ("", "", 0, 0)
	# "" -> ("", "", 0, 0)

	# This shouldn't happen unless you screw up the export
	if not path:
		return ("", "", 0, 0)
	
	# Strip first slash, eg. "/tie/flap_63" becomes "tie/flap_63"
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
		# Find frame start, eg. /tie/flap_10_63 returns 10
		underscore = anim.rfind("_")
		if (underscore >= 0):
			try:
				start_frame = int(anim[underscore + 1:])
			except:
				pass
			anim = anim[:underscore]
	
	# Find category, eg. "/tie/flap_63" returns "tie", but "/tie" returns ""
	category = "" if len(parts) <= 1 else parts[0]
	
	# User displayed name, eg. "/tie/fast_flap_10_63" returns "Fast Flap"
	anim = anim.replace("_", " ").title()
	return (category, anim, start_frame, end_frame)

def update_anims(obj: bpy.types.Object, cache: bpy.types.CacheFile, modifier: bpy.types.MeshSequenceCacheModifier) -> None:
	props = obj.nc_props
	if props.caches:
		return
	
	# Populate list and default to rest animation
	for path in cache.object_paths:
		data = extract_path_data(path.path)
		
		# Only list items within the current category
		if props.object_name != data[0]:
			continue

		item = props.caches.add()
		item.path = path.path
		item.name = data[1]
		item.loop_start = data[2]
		item.loop_duration = data[3] - data[2]

		# Default to rest animation
		if data[1] == "Rest":
			props.selected_index = len(props.caches) - 1
			modifier.object_path = path.path

class Animation_List_Data(bpy.types.PropertyGroup):

	def get_anim_libs(self, context):
		selected = context.active_object
		if not selected or selected.type != "ARMATURE":
			return
		found_rig = find_rig_data(selected.name.lower(), "armature")
		if found_rig:
			return found_rig["libs"]

	def set_anim_lib(self, context):
		target = getattr(context, "nc_target", None)
		modifier = getattr(context, "nc_modifier", None)
		if not target or not modifier:
			return
		
		# See load_cache for why I'm not using multiusers for this
		cache = load_cache(self.cache_lib)
		modifier.cache_file = cache

		# Reset animation list
		self.caches.clear()

		# Update menu contents, Blender takes a bit to load the file
		bpy.app.timers.register(functools.partial(update_anims, target, cache, modifier), first_interval=0.01)
	
	def set_anim(self, context):
		target = getattr(context, "nc_target", None)
		modifier = getattr(context, "nc_modifier", None)
		if not target or not modifier:
			return
		
		# Update animation cache
		selected_cache = self.caches[self.selected_index]
		modifier.object_path = selected_cache.path

		# Update driver settings
		set_driver(modifier.cache_file, selected_cache)

	object_name: bpy.props.StringProperty(name="Object Name")
	cache_lib: bpy.props.EnumProperty(name="Animation Library", items=get_anim_libs, update=set_anim_lib)
	caches: bpy.props.CollectionProperty(type=Animation_Property)
	selected_index: bpy.props.IntProperty(default=0, update=set_anim)

class Add_Cache_Modifier(bpy.types.Operator):
	"""Adds an animated sequence cache to the selected object"""
	
	bl_label = "Add Animation Cache Modifier"
	bl_idname = "nc.add_cache"
	bl_options = {"REGISTER", "UNDO"}

	cache_name = "NC_SEQUENCE_CACHE"
	weight_name = "NC_VERTEX_WEIGHT"

	rig_name: bpy.props.StringProperty(name="Rig Name")
	object_name: bpy.props.StringProperty(name="Object Name")

	def execute(self, context):
		target = getattr(context, "nc_target", None)
		if not target or not self.rig_name or not self.object_name:
			self.report({"ERROR_INVALID_INPUT"}, "Missing parameters!")
			return {"CANCELLED"}
		
		# Store object name on target for later
		target.nc_props.object_name = self.object_name
		
		rig_match = None
		for item in supported:
			if item.get("armature", None) == self.rig_name:
				rig_match = item
				break
		
		if not rig_match:
			self.report({"ERROR_INVALID_INPUT"}, f"Unsupported rig {self.rig_name}!")
			return {"CANCELLED"}
		
		libs = rig_match["libs"]
		if not libs:
			self.report({"ERROR_INVALID_INPUT"}, f"No animations for {self.object_name}!")
			return {"CANCELLED"}
		
		# Reset object rotation
		target.rotation_euler = (0, 0, 0)

		# Never add the same modifier twice
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
		
		# See load_cache for why I'm not using multiusers for this
		chosen_lib = libs[0]
		cache = load_cache(chosen_lib[0])

		# Assign cache to modifier
		cache_modifier.cache_file = cache
		
		# TEMPORARY HACK HERE
		if self.object_name == "tie":
			if not weight_modifier:
				weight_modifier = target.modifiers.new(name=self.weight_name, type="VERTEX_WEIGHT_EDIT")
				bpy.ops.object.modifier_move_to_index({"object": target}, modifier=self.weight_name, index=1)

			# Add vertex weights for rigging, assume tie for now
			weight_modifier.vertex_group = "DEF-spine.003"
			weight_modifier.default_weight = 1
			weight_modifier.use_add = True
			weight_modifier.add_threshold = 0
		
		# Update menu contents, Blender takes a bit to load the file
		bpy.app.timers.register(functools.partial(update_anims, target, cache, cache_modifier), first_interval=0.01)

		return {"FINISHED"}

class Animation_List(bpy.types.UIList):
	bl_idname = "ALA_UL_Animation_List"
	
	def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
		row = layout.row()
		row.context_pointer_set(name="nc_item", data=item)
		row.label(text=item.name)
		# Only draw speed and offset for animated items
		if item.loop_duration > 0:
			row.prop(item, "speed")
			row.prop(item, "offset")

class Attachment_Panel(bpy.types.Panel):
	bl_label = "No Cloth Sims"
	bl_idname = "ALA_PT_Attachment_Panel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "No Cloth Sims"

	def draw(self, context):
		layout = self.layout
		selected = context.active_object

		if not selected or selected.type != "ARMATURE":
			layout.label(text="Please select a rig!")
			return
		
		rig_data = find_rig_data(selected.name.lower(), "armature")
		if not rig_data:
			layout.label(text=f"Unsupported Rig: {selected.name}")
			return
		
		# Selected rig label
		rig_name = rig_data["armature"]
		layout.label(text=f"Selected Rig: {rig_name.title()}")

		# Add modifier buttons
		for obj_name in rig_data["parts"]:
			for child in selected.children:
				# Ignore non-matching children
				if obj_name not in child.name.lower():
					continue
				
				# Check for cache modifier
				cache_modifier = None
				for m in child.modifiers:
					if m.name == Add_Cache_Modifier.cache_name:
						cache_modifier = m
						break
				
				# Pass stuff around with context pointers
				col = layout.column()
				col.context_pointer_set(name="nc_target", data=child)

				if cache_modifier:
					col.context_pointer_set(name="nc_modifier", data=cache_modifier)
					col.prop(child.nc_props, "cache_lib", text="")
					col.template_list(Animation_List.bl_idname, "", child.nc_props, "caches", child.nc_props, "selected_index")
				else:
					# Can't pass Python lists, so pass two strings instead
					params = col.operator(Add_Cache_Modifier.bl_idname, text=f"Animate {obj_name.title()}", icon="ADD")
					params.rig_name = rig_name
					params.object_name = obj_name
				break

# Dump all classes to register in here
classes = [Attachment_Panel, Add_Cache_Modifier, Animation_Property, Animation_List, Animation_List_Data]

def register() -> None:
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Object.nc_props = bpy.props.PointerProperty(type=Animation_List_Data)

def unregister() -> None:
	del bpy.types.Object.nc_props
	for cls in classes:
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()
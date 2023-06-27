import bpy, functools
from uuid import uuid4

bl_info = {
	"name": "No Cloth Sims",
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
# This can be done with "Vertex Weight Edit", "Vertex Weight Proximity", "Data Transfer" or Geometry Nodes.
# =============================================================================================================

# The array below contains all supported armatures and objects.

# For armatures, it works like this:
# 1. Search for a rig containing "gary", for example "gary_001"
# 2. Search the rig's children for matching objects, for example "tie_final"
# 3. Add a button to animate each child object
# 4. Profit

# Part names must match the exported Alembic path names
# For example, "tie" matches animations under "/tie/*"

supported = [
	{
		"armature": "gary",
		"libs": [
			("A:\\mav\\2023\\sandbox\\studio2\\s223\\departments\\fx\\cloth_library\\gary_test_ties.abc", "Gary's Drip: Volume 1", "", "ASSET_MANAGER", 0)
		],
		"parts": ["tie", "shirt", "pants"]
	},
	{
		"armature": "carol",
		"libs": [],
		"parts": ["blouse", "skirt", "scarf_", "scarf2_", "hair_main", "hair_front_right", "hair_front_left"]
	}
]

# Can't use a dict, later plans
def get_supported_data(name: str, category: str):
	for item in supported:
		if item.get(category, None) in name:
			return item

def load_cache(path: str) -> bpy.types.CacheFile:
	bpy.ops.cachefile.open(filepath=path)
	cache = bpy.data.cache_files[-1]
	# Randomize name to ensure it's always last
	cache.name = str(uuid4())
	return cache

def set_driver(cache: bpy.types.CacheFile, speed: float, offset: float, start_frame: int = 0, loop_frames: int = 64) -> None:
	# Never add the same driver twice
	driver = None
	anim_data = cache.animation_data
	if anim_data and anim_data.drivers:
		driver = anim_data.drivers[-1].driver
	else:
		driver = cache.driver_add("frame").driver

	# Loop animation using driver
	cache.override_frame = True
	speed_str = "" if speed == 1 else f" * {speed}"
	offset_str = "" if offset == 0 else f" + {offset}"
	frame_str = f"frame{speed_str}{offset_str}"
	if start_frame == 0:
		# Simple looping animation
		driver.expression = f"({frame_str}) % {loop_frames}"
	else:
		# Loop after a specific frame
		driver.expression = f"min({frame_str}, ({frame_str} - {start_frame}) % {loop_frames} + {start_frame})"

def update_anims(object: bpy.types.Object, cache: bpy.types.CacheFile) -> None:
	props = object.nc_props
	if not props.caches:
		selected = 0
		for path in cache.object_paths:
			item = props.caches.add()
			item.name = path.path.replace("_", " ").title()
			item.path = path.path
			if path.path == "/rest":
				selected = len(props.caches) - 1
		# Ensure rest animation is selected by default
		props.selected_index = selected

	# Force UI update
	object.select_set(True)

class Animation_Property(bpy.types.PropertyGroup):

	def update_driver(self, context):
		item = getattr(context, "nc_item", None)
		modifier = getattr(context, "nc_modifier", None)
		if not item or not modifier:
			return
		set_driver(modifier.cache_file, item.speed, item.offset, 0, 64)

	# Name is built into PropertyGroup
	path: bpy.props.StringProperty(name="Path")
	speed: bpy.props.FloatProperty(name="Speed", default=1, update=update_driver)
	offset: bpy.props.FloatProperty(name="Offset", default=0, update=update_driver)

class Animation_List_Data(bpy.types.PropertyGroup):

	def get_anim_libs(self, context):
		selected = context.active_object
		if not selected or selected.type != "ARMATURE":
			return
		found_rig = get_supported_data(selected.name.lower(), "armature")
		if found_rig:
			return found_rig["libs"]

	def set_anim_lib(self, context):
		target = getattr(context, "nc_target", None)
		modifier = getattr(context, "nc_modifier", None)
		if not target or not modifier:
			return
		
		# Load animation cache
		cache = load_cache(self.cache_lib)
		set_driver(cache, 1, 0, 0, 64)

		# Apply to modifier
		modifier.cache_file = cache
		modifier.object_path = "/rest"

		# Reset animation list
		self.caches.clear()

		# Update menu contents after brief delay
		bpy.app.timers.register(functools.partial(update_anims, target, cache), first_interval=0.01)
	
	def set_anim(self, context):
		target = getattr(context, "nc_target", None)
		modifier = getattr(context, "nc_modifier", None)
		if not target or not modifier:
			return
		
		# Update animation cache
		selected_cache = self.caches[self.selected_index]
		modifier.object_path = selected_cache.name

		# Update driver settings
		set_driver(modifier.cache_file, selected_cache.speed, selected_cache.offset, 0, 64)

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

	def execute(self, context):
		target = getattr(context, "nc_target", None)
		if not target or not self.rig_name:
			self.report({"ERROR_INVALID_INPUT"}, "Missing parameters!")
			return {"CANCELLED"}
		
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
		
		if not weight_modifier:
			weight_modifier = target.modifiers.new(name=self.weight_name, type="VERTEX_WEIGHT_EDIT")
			bpy.ops.object.modifier_move_to_index({"object": target}, modifier=self.weight_name, index=1)
		
		# Load animation as cache file
		# TODO: FIX THIS
		# chosen_lib = libs[0]
		# cache = load_cache(chosen_lib[0])
		# set_driver(cache, 1, 0, 0, 64)

		# Assign cache to modifier
		# cache_modifier.cache_file = cache
		# cache_modifier.object_path = "/rest"

		# Add vertex weights for rigging, assume tie for now
		weight_modifier.vertex_group = "DEF-spine.003"
		weight_modifier.default_weight = 1
		weight_modifier.use_add = True
		weight_modifier.add_threshold = 0
		
		# Update menu contents after brief delay
		# bpy.app.timers.register(functools.partial(update_anims, target, cache), first_interval=0.01)

		return {"FINISHED"}

class Animation_List(bpy.types.UIList):
	bl_idname = "ALA_UL_Animation_List"

	def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
		row = layout.row()
		row.context_pointer_set(name="nc_item", data=item)
		row.label(text=item.name)
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
		
		found_rig = get_supported_data(selected.name.lower(), "armature")
		if not found_rig:
			layout.label(text=f"Unsupported Rig: {selected.name}")
			return
		
		# Selected rig label
		rig_name = found_rig["armature"]
		layout.label(text=f"Selected Rig: {rig_name.title()}")

		# Add modifier buttons
		for obj_name in found_rig["parts"]:
			for child in selected.children:
				# Ignore non-matching children
				if obj_name not in child.name.lower():
					continue
				
				# Attempt to find cache modifier
				cache_modifier = None
				for m in child.modifiers:
					if m.name == Add_Cache_Modifier.cache_name:
						cache_modifier = m
						break
				
				# Pass data around using context pointers
				col = layout.column()
				col.context_pointer_set(name="nc_target", data=child)

				if cache_modifier:
					col.context_pointer_set(name="nc_modifier", data=cache_modifier)
					col.prop(child.nc_props, "cache_lib", text="")
					col.template_list(Animation_List.bl_idname, "", child.nc_props, "caches", child.nc_props, "selected_index")
				else:
					# Can't pass objs[obj_name] so pass two strings instead
					params = col.operator(Add_Cache_Modifier.bl_idname, text=f"Animate {obj_name.title()}", icon="ADD")
					params.rig_name = rig_name
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
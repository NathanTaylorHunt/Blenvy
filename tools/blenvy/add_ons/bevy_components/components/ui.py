import json
import bpy

from ..utils import get_selection_type
from .metadata import do_item_custom_properties_have_missing_metadata, get_bevy_components


def draw_propertyGroup( propertyGroup, layout, nesting =[], rootName=None):
    is_enum = getattr(propertyGroup, "with_enum")
    is_list = getattr(propertyGroup, "with_list") 
    is_map = getattr(propertyGroup, "with_map")
    # item in our components hierarchy can get the correct propertyGroup by STRINGS because of course, we cannot pass objects to operators...sigh

    # if it is an enum, the first field name is always the list of enum variants, the others are the variants
    field_names = propertyGroup.field_names
    #print("")
    #print("drawing", propertyGroup, nesting, "component_name", rootName)
    if is_enum:
        subrow = layout.row()
        display_name = field_names[0] if propertyGroup.tupple_or_struct == "struct" else ""
        subrow.prop(propertyGroup, field_names[0], text=display_name)
        subrow.separator()
        selection = getattr(propertyGroup, "selection")

        for fname in field_names[1:]:
            if fname == "variant_" + selection:
                subrow = layout.row()
                display_name = fname if propertyGroup.tupple_or_struct == "struct" else ""

                nestedPropertyGroup = getattr(propertyGroup, fname)
                nested = getattr(nestedPropertyGroup, "nested", False)
                #print("nestedPropertyGroup", nestedPropertyGroup, fname, nested)
                if nested:
                    draw_propertyGroup(nestedPropertyGroup, subrow.column(), nesting + [fname], rootName )
                # if an enum variant is not a propertyGroup
                break
    elif is_list:
        item_list = getattr(propertyGroup, "list")
        list_index = getattr(propertyGroup, "list_index")
        box = layout.box()
        split = box.split(factor=0.9)
        list_column, buttons_column = (split.column(),split.column())

        list_column = list_column.box()
        for index, item  in enumerate(item_list):
            row = list_column.row()
            draw_propertyGroup(item, row, nesting, rootName)
            icon = 'CHECKBOX_HLT' if list_index == index else 'CHECKBOX_DEHLT'
            op = row.operator('blenvy.component_list_select_item', icon=icon, text="")
            op.component_name = rootName
            op.property_group_path = json.dumps(nesting)
            op.selection_index = index

        #various control buttons
        buttons_column.separator()
        row = buttons_column.row()
        op = row.operator('blenvy.component_list_actions', icon='ADD', text="")
        op.action = 'ADD'
        op.component_name = rootName
        op.property_group_path = json.dumps(nesting)

        row = buttons_column.row()
        op = row.operator('blenvy.component_list_actions', icon='REMOVE', text="")
        op.action = 'REMOVE'
        op.component_name = rootName
        op.property_group_path = json.dumps(nesting)

        buttons_column.separator()
        row = buttons_column.row()
        op = row.operator('blenvy.component_list_actions', icon='TRIA_UP', text="")
        op.action = 'UP'
        op.component_name = rootName
        op.property_group_path = json.dumps(nesting)

        row = buttons_column.row()
        op = row.operator('blenvy.component_list_actions', icon='TRIA_DOWN', text="")
        op.action = 'DOWN'
        op.component_name = rootName
        op.property_group_path = json.dumps(nesting)

    elif is_map:
        root = layout.row().column()
        if hasattr(propertyGroup, "list"): # TODO: improve handling of non drawable UI
            keys_list = getattr(propertyGroup, "list")
            values_list = getattr(propertyGroup, "values_list")
            box = root.box()
            row = box.row()
            row.label(text="Add entry:")
            keys_setter = getattr(propertyGroup, "keys_setter")
            draw_propertyGroup(keys_setter, row, nesting, rootName)

            values_setter = getattr(propertyGroup, "values_setter")
            draw_propertyGroup(values_setter, row, nesting, rootName)

            op = row.operator('blenvy.component_map_actions', icon='ADD', text="")
            op.action = 'ADD'
            op.component_name = rootName
            op.property_group_path = json.dumps(nesting)

            box = root.box()
            split = box.split(factor=0.9)
            list_column, buttons_column = (split.column(),split.column())
            list_column = list_column.box()

            for index, item  in enumerate(keys_list):
                row = list_column.row()
                draw_propertyGroup(item, row, nesting, rootName)

                value = values_list[index]
                draw_propertyGroup(value, row, nesting, rootName)

                op = row.operator('blenvy.component_map_actions', icon='REMOVE', text="")
                op.action = 'REMOVE'
                op.component_name = rootName
                op.property_group_path = json.dumps(nesting)
                op.target_index = index


            #various control buttons
            buttons_column.separator()
            row = buttons_column.row()
        

    else: 
        for fname in field_names:
            #subrow = layout.row()
            nestedPropertyGroup = getattr(propertyGroup, fname)
            nested = getattr(nestedPropertyGroup, "nested", False)
            display_name = fname if propertyGroup.tupple_or_struct == "struct" else ""

            if nested:
                layout.separator()
                layout.separator()

                layout.label(text=display_name) #  this is the name of the field/sub field
                layout.separator()
                subrow = layout.row()
                draw_propertyGroup(nestedPropertyGroup, subrow, nesting + [fname], rootName )
            else:
                subrow = layout.row()
                subrow.prop(propertyGroup, fname, text=display_name)
                subrow.separator()


class BLENVY_PT_components_panel(bpy.types.Panel):
    bl_idname = "BLENVY_PT_components_panel"
    bl_label = ""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bevy Components"
    bl_context = "objectmode"
    bl_parent_id = "BLENVY_PT_SidePanel"

    @classmethod
    def poll(cls, context):
        return context.window_manager.blenvy.mode == 'COMPONENTS'
        return context.object is not None 

    def draw_header(self, context):
        layout = self.layout
        name = ""
        target_type = ""
        object = next(iter(context.selected_objects), None)
        collection = context.collection
        if object is not None:
            name = object.name
            target_type = "Object"
        elif collection is not None:
            name = collection.name
            target_type = "Collection"
        # name = context.object.name if context.object != None else ''
        layout.label(text=f"Components for {name} ({target_type})")

        #print("object", context.object, "active", context.active_object, "objects", context.selected_objects)

    def draw(self, context):
        object = next(iter(context.selected_objects), None)
        collection = context.collection
        layout = self.layout

        # we get & load our component registry
        registry = bpy.context.window_manager.components_registry 
        selected_component = bpy.context.window_manager.blenvy.components.component_selector
        registry_has_type_infos = registry.has_type_infos()

        if object is not None:
            draw_component_ui(layout, object, registry, selected_component, registry_has_type_infos, context)
        elif collection is not None:
            draw_component_ui(layout, collection, registry, selected_component, registry_has_type_infos, context)
        else: 
            layout.label(text ="Select an object to edit its components")      



def draw_component_ui(layout, object_or_collection, registry, selected_component, registry_has_type_infos, context):
    row = layout.row(align=True)
    row.prop(context.window_manager.blenvy.components, "component_selector", text="Component: ")

    # add components
    row = layout.row(align=True)
    op = row.operator("blenvy.component_add", text="Add", icon="ADD")
    op.component_type = selected_component
    row.enabled = selected_component != ''

    layout.separator()

    # paste components
    row = layout.row(align=True)
    row.operator("blenvy.component_paste", text="Paste component ("+bpy.context.window_manager.copied_source_component_name+")", icon="PASTEDOWN")
    row.enabled = registry_has_type_infos and context.window_manager.copied_source_item_name != ''

    layout.separator()

    # upgrate custom props to components
    upgradeable_customProperties = registry.has_type_infos() and do_item_custom_properties_have_missing_metadata(object_or_collection)
    if upgradeable_customProperties:
        row = layout.row(align=True)
        op = row.operator("blenvy.component_from_custom_property", text="generate components from custom properties" , icon="LOOP_FORWARDS") 
        layout.separator()


    components_in_object = object_or_collection.components_meta.components
    #print("components_names", dict(components_bla).keys())

    for component_name in sorted(get_bevy_components(object_or_collection)) : # sorted by component name, practical
        if component_name == "components_meta": 
            continue
        # anything withouth metadata gets skipped, we only want to see real components, not all custom props
        component_meta =  next(filter(lambda component: component["long_name"] == component_name, components_in_object), None)
        if component_meta == None: 
            continue
        
        component_invalid = getattr(component_meta, "invalid")
        invalid_details = getattr(component_meta, "invalid_details")
        component_visible = getattr(component_meta, "visible")
        single_field = False

        # our whole row 
        box = layout.box() 
        row = box.row(align=True)
        # "header"
        row.alert = component_invalid
        row.prop(component_meta, "enabled", text="")
        row.label(text=component_name)

        # we fetch the matching ui property group
        root_propertyGroup_name =  registry.get_propertyGroupName_from_longName(component_name)
        """print("root_propertyGroup_name", root_propertyGroup_name)"""

        if root_propertyGroup_name:
            propertyGroup = getattr(component_meta, root_propertyGroup_name, None)
            """print("propertyGroup", propertyGroup)"""
            if propertyGroup:
                # if the component has only 0 or 1 field names, display inline, otherwise change layout
                single_field = len(propertyGroup.field_names) < 2
                prop_group_location = box.row(align=True).column()
                """if single_field:
                    prop_group_location = row.column(align=True)#.split(factor=0.9)#layout.row(align=False)"""
                
                if component_visible:
                    if component_invalid:
                        error_message = invalid_details if component_invalid else "Missing component UI data, please reload registry !"
                        prop_group_location.label(text=error_message)
                    draw_propertyGroup(propertyGroup, prop_group_location, [root_propertyGroup_name], component_name)
                else :
                    row.label(text="details hidden, click on toggle to display")
            else:
                error_message = invalid_details if component_invalid else "Missing component UI data, please reload registry !"
                row.label(text=error_message)

        # "footer" with additional controls
        if component_invalid:
            if root_propertyGroup_name:
                propertyGroup = getattr(component_meta, root_propertyGroup_name, None)
                if propertyGroup:
                    unit_struct = len(propertyGroup.field_names) == 0
                    if unit_struct: 
                        op = row.operator("blenvy.component_fix", text="", icon="SHADERFX")
                        op.component_name = component_name
                        row.separator()

        op = row.operator("blenvy.component_remove", text="", icon="X")
        op.component_name = component_name
        op.item_name = object_or_collection.name
        op.item_type = get_selection_type(object_or_collection)
        row.separator()
        
        op = row.operator("blenvy.component_copy", text="", icon="COPYDOWN")
        op.source_component_name = component_name
        op.source_item_name = object_or_collection.name
        op.source_item_type = get_selection_type(object_or_collection)
        row.separator()
        
        #if not single_field:
        toggle_icon = "TRIA_DOWN" if component_visible else "TRIA_RIGHT"
        op = row.operator("blenvy.component_toggle_visibility", text="", icon=toggle_icon)
        op.component_name = component_name
        #row.separator()



class BLENVY_PT_component_tools_panel(bpy.types.Panel):
    """panel listing all the missing bevy types in the schema"""
    bl_idname = "BLENVY_PT_component_tools_panel"
    bl_label = "Rename / Fix/ Update Components"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bevy Components"
    bl_context = "objectmode"
    bl_parent_id = "BLENVY_PT_SidePanel"
    bl_options = {'DEFAULT_CLOSED'}
    bl_description = "advanced tooling"

    @classmethod
    def poll(cls, context):
        return context.window_manager.blenvy.mode == 'COMPONENTS'

    def draw_invalid_or_unregistered_header(self, layout, items):
        row = layout.row()

        for item in items:
            col = row.column()
            col.label(text=item)

    def draw_invalid_or_unregistered(self, layout, status, component_name, target, item_type):
        item_type_short = item_type.lower()
        registry = bpy.context.window_manager.components_registry 
        registry_has_type_infos = registry.has_type_infos()
        selected_component = target.components_meta.component_selector

        row = layout.row()

        col = row.column()
        operator = col.operator("blenvy.select_item", text=f"{target.name}({item_type_short})")
        operator.target_name = target.name
        operator.item_type = item_type

        col = row.column()
        col.label(text=status)

        col = row.column()
        col.label(text=component_name)

        col = row.column()
        # each components_meta has a component selector to pick components from
        components_meta = target.components_meta
        col.prop(components_meta, "component_selector", text="")


        col = row.column()
        operator = col.operator("blenvy.component_rename", text="", icon="SHADERFX") #rename
        target_component_name = registry.type_infos[selected_component]['long_name'] if selected_component in registry.type_infos else ""
        operator.original_name = component_name
        operator.target_items = json.dumps([(target.name, item_type)]) # tupple
        operator.target_name = target_component_name
        col.enabled = registry_has_type_infos and component_name != "" and target_component_name != ""  and component_name != target_component_name


        col = row.column()
        operator = col.operator("blenvy.component_remove", text="", icon="X")
        operator.item_name = target.name
        operator.component_name = component_name
        operator.item_type = get_selection_type(target)

    def draw_invalid_item_entry(self, layout, item, invalid_component_names, items_with_invalid_components, item_type):
        blenvy_custom_properties = ['components_meta', 'bevy_components', 'user_assets', 'generated_assets' ] # some of our own hard coded custom properties that should be ignored
        if "components_meta" in item:
            components_metadata = item.components_meta.components
            object_component_names = []
            for index, component_meta in enumerate(components_metadata):
                long_name = component_meta.long_name
                if component_meta.invalid:
                    self.draw_invalid_or_unregistered(layout, "Invalid", long_name, item, item_type)
                
                    if not item.name in items_with_invalid_components:
                        items_with_invalid_components.append((item.name, item_type))
                    
                    if not long_name in invalid_component_names:
                        invalid_component_names.append(long_name)


                object_component_names.append(long_name) 

            for custom_property in item.keys():
                # Invalid (something is wrong)
                # Unregistered (not in registry) 
                # Upgrade Needed (Old-style component)

                status = None
                if custom_property not in blenvy_custom_properties and custom_property not in object_component_names:
                    status = "Upgrade Needed"

                if status is not None:
                    self.draw_invalid_or_unregistered(layout, status, custom_property, item, item_type)

                    if not item.name in items_with_invalid_components:
                        items_with_invalid_components.append((item.name, item_type))
                    """if not long_name in invalid_component_names:
                        invalid_component_names.append(custom_property)""" # FIXME

    def draw(self, context):
        layout = self.layout
        registry = bpy.context.window_manager.components_registry 
        registry_has_type_infos = registry.has_type_infos()
        selected_object = context.selected_objects[0] if len(context.selected_objects) > 0 else None
        selected_component = bpy.context.window_manager.blenvy.components.component_selector

        row = layout.row()
        row.label(text= "------------------ Single item actions: Rename / Fix / Upgrade -------------------")#"Invalid/ unregistered components")

        items_with_invalid_components = []
        invalid_component_names = []
        items_with_original_components = []


        self.draw_invalid_or_unregistered_header(layout, ["Item","Status", "Component", "Target"])

        # for possible bulk actions
        original_name = bpy.context.window_manager.blenvy.components.source_component_selector
        target_component_name = bpy.context.window_manager.blenvy.components.target_component_selector

        for object in bpy.data.objects: # TODO: very inneficent
            if len(object.keys()) > 0:
                self.draw_invalid_item_entry(layout, object, invalid_component_names, items_with_invalid_components, "OBJECT")

                if original_name != "" and "components_meta" in object:
                    components_metadata = object.components_meta.components
                    for index, component_meta in enumerate(components_metadata):
                        long_name = component_meta.long_name
                        if long_name == original_name:
                            items_with_original_components.append((object.name, "OBJECT"))

        for collection in bpy.data.collections:
            if len(collection.keys()) > 0:
                self.draw_invalid_item_entry(layout, collection, invalid_component_names, items_with_invalid_components, "COLLECTION")

                if original_name != "" and "components_meta" in collection:
                    components_metadata = collection.components_meta.components
                    for index, component_meta in enumerate(components_metadata):
                        long_name = component_meta.long_name
                        if long_name == original_name:
                            items_with_original_components.append((collection.name, "COLLECTION"))

        if len(items_with_invalid_components) == 0:
            layout.label(text="Nothing to see here , all good !")

        #print("items_with_original_components", items_with_original_components)
        layout.separator()
        layout.separator()
        row = layout.row()
        row.label(text="------------------Bulk actions: Rename / Fix / Upgrade -------------------")
  
        row = layout.row()
        col = row.column()
        col.label(text="Component")
        col = row.column()
        col.label(text="Target")
        col = row.column()
        col.label(text="------")

        row = layout.row()
        col = row.column()
        col.prop(bpy.context.window_manager.blenvy.components, "source_component_selector", text="")

        col = row.column()
        col.prop(bpy.context.window_manager.blenvy.components, "target_component_selector", text="")
    
        col = row.column()
        components_rename_progress = context.window_manager.components_rename_progress
        if components_rename_progress == -1.0:
            operator = col.operator("blenvy.component_rename", text="apply", icon="SHADERFX")
            operator.original_name = original_name
            operator.target_name = target_component_name
            operator.target_items = json.dumps(items_with_original_components)
            col.enabled = registry_has_type_infos and original_name != "" and original_name != target_component_name
        else:
            if hasattr(layout,"progress") : # only for Blender > 4.0
                col.progress(factor = components_rename_progress, text=f"updating {components_rename_progress * 100.0:.2f}%")

        col = row.column()
        remove_components_progress = context.window_manager.components_remove_progress
        if remove_components_progress == -1.0:
            operator = row.operator("blenvy.component_remove_from_all_items", text="", icon="X")
            operator.component_name = context.window_manager.bevy_component_rename_helper.original_name
            col.enabled = registry_has_type_infos and original_name != ""
        else:
            if hasattr(layout,"progress") : # only for Blender > 4.0
                col.progress(factor = remove_components_progress, text=f"updating {remove_components_progress * 100.0:.2f}%")

        layout.separator()
        """layout.separator()
        row = layout.row()
        box= row.box()
        box.label(text="Conversions between custom properties and components & vice-versa")

        row = layout.row()
        row.label(text="WARNING ! The following operations will overwrite your existing custom properties if they have matching types on the bevy side !")
        row.alert = True

        ##
        row = layout.row()
        custom_properties_from_components_progress_current = context.window_manager.custom_properties_from_components_progress

        if custom_properties_from_components_progress_current == -1.0:
            row.operator(BLENVY_OT_components_refresh_custom_properties_current.bl_idname, text="update custom properties of current object" , icon="LOOP_FORWARDS")
            row.enabled = registry_has_type_infos and selected_object is not None
        else:
            if hasattr(layout,"progress") : # only for Blender > 4.0
                layout.progress(factor = custom_properties_from_components_progress_current, text=f"updating {custom_properties_from_components_progress_current * 100.0:.2f}%")

        layout.separator()
        row = layout.row()
        custom_properties_from_components_progress_all = context.window_manager.custom_properties_from_components_progress_all

        if custom_properties_from_components_progress_all == -1.0:
            row.operator(BLENVY_OT_components_refresh_custom_properties_all.bl_idname, text="update custom properties of ALL objects" , icon="LOOP_FORWARDS")
            row.enabled = registry_has_type_infos
        else:
            if hasattr(layout,"progress") : # only for Blender > 4.0
                layout.progress(factor = custom_properties_from_components_progress_all, text=f"updating {custom_properties_from_components_progress_all * 100.0:.2f}%")

        ########################

        row = layout.row()
        row.label(text="WARNING ! The following operations will try to overwrite your existing ui values if they have matching types on the bevy side !")
        row.alert = True

        components_from_custom_properties_progress_current = context.window_manager.components_from_custom_properties_progress

        row = layout.row()
        if components_from_custom_properties_progress_current == -1.0:
            row.operator(BLENVY_OT_components_refresh_propgroups_current.bl_idname, text="update UI FROM custom properties of current object" , icon="LOOP_BACK")
            row.enabled = registry_has_type_infos and selected_object is not None
        else:
            if hasattr(layout,"progress") : # only for Blender > 4.0
                layout.progress(factor = components_from_custom_properties_progress_current, text=f"updating {components_from_custom_properties_progress_current * 100.0:.2f}%")

        layout.separator()
        row = layout.row()
        components_from_custom_properties_progress_all = context.window_manager.components_from_custom_properties_progress_all

        if components_from_custom_properties_progress_all == -1.0:
            row.operator(BLENVY_OT_components_refresh_propgroups_all.bl_idname, text="update UI FROM custom properties of ALL objects" , icon="LOOP_BACK")
            row.enabled = registry_has_type_infos
        else:
            if hasattr(layout,"progress") : # only for Blender > 4.0
                layout.progress(factor = components_from_custom_properties_progress_all, text=f"updating {components_from_custom_properties_progress_all * 100.0:.2f}%")

"""
"""These python functions are accessed by the create_otl.py program
so we can import and link them to our Houdini OTL."""

import hou
import re


class ValidationError(Exception):
    pass


def render_on_farm(karma_node: hou.Node) -> None:
    """This functions runs the farm render function from our ShotGrid app.py"""
    import sgtk

    eng = sgtk.platform.current_engine()
    app = eng.apps["tk-houdini-karma"]

    app.submit_to_farm(karma_node)


def render_locally(karma_node: hou.Node) -> None:
    """This functions runs the local render function from our ShotGrid app.py"""
    import sgtk

    eng = sgtk.platform.current_engine()
    app = eng.apps["tk-houdini-karma"]

    app.render_locally(karma_node)


def open_folder(karma_node: hou.Node) -> None:
    """This function runs the open folder function from our ShotGrid app.py"""
    import sgtk

    eng = sgtk.platform.current_engine()
    app = eng.apps["tk-houdini-karma"]

    app.open_folder(karma_node)


def update_resolution(karma_node: hou.Node) -> None:
    """This function updates the resolution on the karmarendersettings node inside
    the subnet. I could not get this to work with simple referencing expressions."""
    karma_render_settings = karma_node.node("karmarendersettings")
    karma_render_settings.parm("res_mode").set("Manual")
    karma_render_settings.parm("res_mode").pressButton()
    karma_render_settings.parm("resolutionx").set(karma_node.parm("resolutionx").eval())
    karma_render_settings.parm("resolutiony").set(karma_node.parm("resolutiony").eval())


def clear_all_automated_lightgroup_lpe_tags(all_nodes: list[hou.Node]) -> None:
    """Deletes all LPE tags that starts with LG_ from all lights in scene.

    Args:
        all_nodes: List of all the nodes in the scene.
    """
    for node in all_nodes:
        if node.type().name().startswith("light"):
            lpe_param = node.parm("xn__inputskarmalightlpetag_wcbff")
            if lpe_param:
                for expression in lpe_param.eval().split():
                    if expression.startswith("LG_"):
                        lpe_param.set("")


def get_lightgroup_user_settings(karma_node: hou.Node) -> dict:
    """Retrieves the lightgroups information that the user has set
    on the SGTK Karma node.

    Args:
        karma_node: SGTK Karma node

    Returns:
        light_groups_info: Dict with info about all our custom light groups
    """
    light_group_multiparm_count = karma_node.parm("light_groups_select").eval()
    light_groups_info = {}

    for light_group_index in range(1, light_group_multiparm_count + 1):
        light_group_name_parm = f"light_group_name_{light_group_index}"
        selected_light_lops_parm = f"select_light_lops_{light_group_index}"

        light_group_name = karma_node.parm(light_group_name_parm).eval()
        selected_light_lops = karma_node.parm(selected_light_lops_parm).eval()

        light_groups_info[light_group_name] = selected_light_lops.split()

    return light_groups_info


def set_lightgroups_lpe_tags(light_groups_info: dict) -> None:
    """Validates the light groups, then goes over all lights in
    the dict and adds the correct LPE tags.

    Args:
        light_groups_info: Dict with all light groups

    Raises:
        ValidationError: Error when validation fails
    """
    lights_list = []
    for light_group in light_groups_info:
        if not re.match(r"^[A-Za-z0-9_]+$", light_group):
            error_message = f"Error: Invalid light group name: '{light_group}'. You can only use letters, numbers and underscores."
            raise ValidationError(error_message)

        for light in light_groups_info[light_group]:
            try:
                if light not in lights_list:
                    lights_list.append(light)
                    light_node = hou.node(light)

                    lpe_control_parm = light_node.parm(
                        "xn__inputskarmalightlpetag_control_xpbff"
                    )
                    lpe_control_parm.set("set")
                    lpe_control_parm.pressButton()

                    lpe_param = light_node.parm("xn__inputskarmalightlpetag_wcbff")
                    lpe_param.set(f"LG_{light_group}")
                    lpe_param.pressButton()

                else:
                    error_message = f"Error: Node {light} is in several light groups. A light can only be in one group."
                    raise ValidationError(error_message)

            except AttributeError:
                error_message = f"Error: Can't set LPE tags for node {light} in light group list {light_group}."
                raise ValidationError(error_message)


def remove_all_automated_render_vars(karma_node: hou.Node, prefix: str) -> None:
    """Removes all lightgroups from our render vars that start with the given prefix.
    It starts removing in reversed order so we keep the correct indexes.

    Args:
        karma_node: SGTK Karma node
        prefix: Renders vars with this prefix will be removed
    """
    karma_render_settings = karma_node.node("karmarendersettings")
    extra_render_variables = karma_render_settings.parm("extrarendervars")

    lightgroups_to_remove = []
    for i in range(1, extra_render_variables.eval() + 1):
        if karma_render_settings.parm(f"name{i}") and karma_render_settings.parm(
            f"name{i}"
        ).eval().startswith(prefix):
            lightgroups_to_remove.append(i)

    for i in reversed(lightgroups_to_remove):
        # Instance indices are 1-based, but removal is 0-based
        karma_render_settings.parm("extrarendervars").removeMultiParmInstance(i - 1)


def add_all_automated_lightgroups_to_render_vars(
    light_groups_info: dict, karma_node: hou.Node
) -> None:
    """Adds all our lightgroups to the karma render settings additional
    render variables.

    Args:
        light_groups_info: Dict of lightgroups and their information
        karma_node: SGTK Karma render node
    """
    karma_render_settings = karma_node.node("karmarendersettings")
    extra_render_variables = karma_render_settings.parm("extrarendervars")

    for light_group in light_groups_info:
        render_variable_index = extra_render_variables.eval() + 1
        extra_render_variables.set(render_variable_index)
        karma_render_settings.parm(f"name{render_variable_index}").set(
            f"LG_{light_group}"
        )
        karma_render_settings.parm(f"format{render_variable_index}").set("color3f")
        karma_render_settings.parm(f"sourceName{render_variable_index}").set(
            f"C.*<L.'LG_{light_group}'>"
        )
        karma_render_settings.parm(f"sourceType{render_variable_index}").set("lpe")


def setup_light_groups(karma_node: hou.Node) -> None:
    """Updates the light groups according to user settings.

    Args:
        karma_node : SGTK Karma render node
    """

    stage = hou.node("/stage")

    clear_all_automated_lightgroup_lpe_tags(stage.allSubChildren())

    light_groups_info = get_lightgroup_user_settings(karma_node)

    try:
        set_lightgroups_lpe_tags(light_groups_info)

    except ValidationError as error_message:
        hou.ui.displayMessage(
            str(error_message),
            severity=hou.severityType.Error,
        )
        return

    remove_all_automated_render_vars(karma_node, "LG_")

    add_all_automated_lightgroups_to_render_vars(light_groups_info, karma_node)


def add_all_lights_to_lightgroups(karma_node: hou.Node) -> None:
    """adds all the lights that are found in stage.
    
    Args:
        karma_node: SGTK Karma node
    """
    stage = hou.node("/stage")
    stage_nodes = stage.children()
    light_types = [
        "<hou.OpNodeType for Lop light::2.0>",
        "<hou.OpNodeType for Lop domelight::3.0>",
        "<hou.OpNodeType for Lop distantlight::2.0>",
        "<hou.OpNodeType for Lop karmaphysicalsky>",
        "<hou.OpNodeType for Lop karmaskydomelight>"
    ]

    lightgroup_names = []
    lightgroup_paths = []

    for node in stage_nodes:
        if str(node.type()) in light_types:
            relative_path = node.path().replace("/stage/", "../")
            lightgroup_paths.append(relative_path)
            lightgroup_names.append(node.name())

    karma_node.parm("light_groups_select").set(str(len(lightgroup_names)))

    light_group_multiparm_count = karma_node.parm("light_groups_select").eval()

    for light_group_index in range(1, light_group_multiparm_count + 1):
        light_group_name_parm = f"light_group_name_{light_group_index}"
        selected_light_lops_parm = f"select_light_lops_{light_group_index}"

        karma_node.parm(light_group_name_parm).set(lightgroup_names[light_group_index - 1])
        karma_node.parm(selected_light_lops_parm).set(lightgroup_paths[light_group_index - 1])

def add_all_automated_prefs_to_render_vars(karma_node: hou.Node) -> None:
    """Adds all our prefs to the karma render settings additional
    render variables.

    Args:
        karma_node: SGTK Karma node
    """
    karma_render_settings = karma_node.node("karmarendersettings")
    extra_render_variables = karma_render_settings.parm("extrarendervars")

    pref_count = karma_node.parm("pref_select").eval()
    for pref_index in range(1, pref_count + 1):
        pref_name_parm = f"pref_name_{pref_index}"
        pref_name = f"pRef_{karma_node.parm(pref_name_parm).eval()}"

        render_variable_index = extra_render_variables.eval() + 1
        extra_render_variables.set(render_variable_index)
        karma_render_settings.parm(f"name{render_variable_index}").set(pref_name)
        karma_render_settings.parm(f"format{render_variable_index}").set("color3f")
        karma_render_settings.parm(f"sourceName{render_variable_index}").set(pref_name)
        karma_render_settings.parm(f"sourceType{render_variable_index}").set("primvar")


def validate_prefs(karma_node: hou.Node) -> None:
    """Goes over our prefs and checks for issues.

    Args:
        karma_node: SGTK Karma node

    Raises:
        ValidationError: Error when validation fails
    """
    pref_count = karma_node.parm("pref_select").eval()

    for pref_index in range(1, pref_count + 1):
        pref_name_parm = f"pref_name_{pref_index}"
        pref_name = f"{karma_node.parm(pref_name_parm).eval()}"

        if pref_name == "":
            error_message = f"Error: Invalid pref name: '{pref_name}'. You can only use letters, numbers and underscores."
            raise ValidationError(error_message)

        if not re.match(r"^[A-Za-z0-9_]+$", pref_name):
            error_message = f"Error: Invalid pref name: '{pref_name}'. You can only use letters, numbers and underscores."
            raise ValidationError(error_message)

        pref_path_parm = f"select_pref_{pref_index}"
        pref_path = karma_node.parm(pref_path_parm).eval()

        if pref_path == "":
            error_message = f"Error: Invalid pref path for pref {pref_name}: '{pref_path}'. You can only use letters, numbers and underscores."
            raise ValidationError(error_message)

        if pref_path.startswith("/stage"):
            karma_node.parm(pref_path_parm).set(pref_path.replace("/stage", ""))


def setup_prefs(karma_node: hou.Node) -> None:
    """Sets up the pref render variables.

    Args:
        karma_node: SGTK Karma node
    """
    try:
        validate_prefs(karma_node)
    except ValidationError as error_message:
        hou.ui.displayMessage(
            str(error_message),
            severity=hou.severityType.Error,
        )
        return

    remove_all_automated_render_vars(karma_node, "pRef_")
    add_all_automated_prefs_to_render_vars(karma_node)


def setup_deep_settings(karma_node: hou.Node) -> None:
    """This function sets our deep setting based on simpler options
    that are presented in the node interface.

    Args:
        karma_node : SGTK Karma render node
    """
    karma_render_settings = karma_node.node("karmarendersettings")

    # Hard surface
    if karma_node.parm("deep_target").eval() == 0:
        karma_render_settings.parm("dcmvars").set("")
        karma_render_settings.parm("dcmofsize").set(1)

    # Volumes
    if karma_node.parm("deep_target").eval() == 1:
        karma_render_settings.parm("dcmvars").set("/Render/Products/Vars/Beauty")
        karma_render_settings.parm("dcmofsize").set(3)

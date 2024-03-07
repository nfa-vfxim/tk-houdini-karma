"""These python functions are accessed by the create_otl.py program
so we can import and link them to our Houdini OTL."""

import hou
import re


def render_on_farm(node: hou.Node) -> None:
    """This functions runs the farm render function from our ShotGrid app.py"""
    import sgtk

    eng = sgtk.platform.current_engine()
    app = eng.apps["tk-houdini-karma"]

    app.submit_to_farm(node)


def render_locally(node: hou.Node) -> None:
    """This functions runs the local render function from our ShotGrid app.py"""
    import sgtk

    eng = sgtk.platform.current_engine()
    app = eng.apps["tk-houdini-karma"]

    app.render_locally(node)


def update_resolution(node: hou.Node) -> None:
    """This function updates the resolution on the karmarendersettings node inside
    the subnet. I could not get this to work with simple referencing expressions."""
    karma_render_settings = node.node("karmarendersettings")
    karma_render_settings.parm("res_mode").set("Manual")
    karma_render_settings.parm("res_mode").pressButton()
    karma_render_settings.parm("resolutionx").set(node.parm("resolutionx").eval())
    karma_render_settings.parm("resolutiony").set(node.parm("resolutiony").eval())


def setup_light_groups(karma_node: hou.Node) -> None:
    """This function clears all automated LPE tags from lights,
    then it sets their tags according to user input,
    after which it will set the proper render variables."""

    # First we clear all our LPE tags so we can add them again later
    stage = hou.node("/stage")

    all_nodes = stage.allSubChildren()

    for node in all_nodes:
        if node.type().name().startswith("light"):
            lpe_param = node.parm("xn__karmalightlpetag_31af")
            if lpe_param:
                expressions_to_keep = ""
                for expression in lpe_param.eval().split():
                    # We only remove our own LPE tags so the custom ones remain.
                    if not expression.startswith("LG_"):
                        expressions_to_keep += expression

                lpe_param.set(expressions_to_keep)

    # Now we add our LPE tags to the lights
    light_group_multiparm_count = karma_node.parm("light_groups_select").eval()
    light_groups_info = {}

    for light_group_index in range(1, light_group_multiparm_count + 1):
        # Collecting light group information from Karma node
        light_group_name_parm = f"light_group_name_{light_group_index}"
        selected_light_lops_parm = f"select_light_lops_{light_group_index}"

        light_group_name = karma_node.parm(light_group_name_parm).eval()
        selected_light_lops = karma_node.parm(selected_light_lops_parm).eval()

        light_groups_info[light_group_name] = selected_light_lops.split()

    lights_list = []
    for light_group in light_groups_info:
        if not re.match(r"^[A-Za-z0-9_]+$", light_group):
            hou.ui.displayMessage(
                f"Error: Invalid light group name: '{light_group}'. You can only use letters, numbers and underscores.",
                severity=hou.severityType.Error,
            )
            return

        # Using the collected information to set LPE tags
        for light in light_groups_info[light_group]:
            try:
                if light not in lights_list:
                    lights_list.append(light)
                    light_node = hou.node(light)

                    lpe_control_parm = light_node.parm(
                        "xn__karmalightlpetag_control_4fbf"
                    )
                    lpe_control_parm.set("set")
                    lpe_control_parm.pressButton()

                    lpe_param = light_node.parm("xn__karmalightlpetag_31af")
                    lpe_param.set(f"LG_{light_group}")
                    lpe_param.pressButton()

                else:
                    hou.ui.displayMessage(
                        f"Error: Node {light} is in several light groups. A light can only be in one group.",
                        severity=hou.severityType.Error,
                    )
                    return
            except AttributeError:
                hou.ui.displayMessage(
                    f"Error: Can't set LPE tags for node {light} in light group list {light_group}.",
                    severity=hou.severityType.Error,
                )
                return

    # Now we add the render vars to the Karma render settings node
    karma_render_settings = karma_node.node("karmarendersettings")
    extra_render_variables = karma_render_settings.parm("extrarendervars")

    indices_to_remove = []
    # Collect our automated render variables so we can remove only those
    for i in range(1, extra_render_variables.eval() + 1):
        if karma_render_settings.parm(f"name{i}") and karma_render_settings.parm(
            f"name{i}"
        ).eval().startswith("LG_"):
            indices_to_remove.append(i)

    # Remove instances from the last to the first to avoid re-indexing issues
    for i in reversed(indices_to_remove):
        # Instance indices are 1-based, but removal is 0-based
        karma_render_settings.parm("extrarendervars").removeMultiParmInstance(i - 1)

    # Add our automated light groups back in
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

def setup_prefs(karma_node: hou.Node) -> None:
    pass

def setup_deep_settings(node: hou.Node) -> None:
    karma_render_settings = node.node("karmarendersettings")

    # Hard surface
    if node.parm("deep_target").eval() == 0:
        karma_render_settings.parm("dcmvars").set("")
        karma_render_settings.parm("dcmofsize").set(1)

    # Volumes
    if node.parm("deep_target").eval() == 1:
        karma_render_settings.parm("dcmvars").set("/Render/Products/Vars/Beauty")
        karma_render_settings.parm("dcmofsize").set(3)

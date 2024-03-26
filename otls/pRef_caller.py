"""This python file gets inserted into the pRef_caller node in the OTL."""

import hou

from pxr import Sdf, UsdGeom


def get_prefs_list(karma_node: hou.node) -> list[dict]:
    """Creates a list of prefs that we have to process.

    Args:
        karma_node: SGTK Karma node

    Returns:
        prefs_list: List of prefs information
    """
    pref_count = karma_node.parm("pref_select").eval()

    prefs_list = []
    for pref_index in range(1, pref_count + 1):
        pref_info = {}
        pref_name_parm = f"pref_name_{pref_index}"
        pref_path_parm = f"select_pref_{pref_index}"
        pref_source_frame_parm = f"pref_source_frame_{pref_index}"

        pref_info["pref_name"] = f"pRef_{karma_node.parm(pref_name_parm).eval()}"
        pref_info["pref_path"] = f"{karma_node.parm(pref_path_parm).eval()}/**"
        pref_info["pref_source_frame"] = karma_node.parm(pref_source_frame_parm).eval()

        prefs_list.append(pref_info)

    return prefs_list


def compute_pref_point_references(karma_node: hou.Node, stage) -> None:
    """Computes pref point references and adds them as primvars to our stage.
    Based on this blog post by Andreas Kjær-Jensen: https://www.andreaskj.com/live-pref-in-solaris/

    Args:
        karma_node: SGTK Karma node
        stage: Stage we're working in
    """
    prefs_list = get_prefs_list(karma_node)

    for pref_data in prefs_list:
        ls = hou.LopSelectionRule()
        ls.setPathPattern(pref_data["pref_path"] + " & %type:Mesh")
        paths = ls.expandedPaths(stage=stage)

        for prim in paths:
            prim = stage.GetPrimAtPath(prim)
            primvarsapi = UsdGeom.PrimvarsAPI(prim)
            points = prim.GetAttribute("points")
            points_values = points.Get(pref_data["pref_source_frame"])
            primvar = primvarsapi.CreatePrimvar(
                pref_data["pref_name"],
                Sdf.ValueTypeNames.Color3fArray,
                UsdGeom.Tokens.vertex,
            )
            primvar.Set(points_values)


compute_pref_point_references(hou.pwd().parent(), hou.pwd().editableStage())

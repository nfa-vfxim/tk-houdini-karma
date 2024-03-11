"""This slightly messy and large file is used to create the SGTK Karma OTL.
We build the OTL using this file so we can easily change things and rebuild the OTL
without going into Houdini and clicking a bunch of messy buttons. This file is 
long and a bit unorganized, however this is still better than the alternative.

To build the OTL you must run this from a Houdini python shell:

exec(open(r"path-to-app\tk-houdini-karma\otls\create_otl.py").read())

exec(open(r"C:/Users/Mervin.vanBrakel/Documents/ShotGrid/DevApps/tk-houdini-karma/otls/create_otl_19.5.py").read())
"""

import os
import re

import hou

# Set the path to the OTL folder here. We can't use something like os.path.realpath because
# we're running this from within an interactive shell.
OTL_FOLDER = (
    "C:/Users/Mervin.vanBrakel/Documents/ShotGrid/DevApps/tk-houdini-karma/otls/"
)


# The following functions help us with building the OTL.
def convert_naming_scheme(naming_scheme) -> tuple:
    """This function converts a Houdini naming scheme to a tuple
    that we can actually work with."""
    if naming_scheme == hou.parmNamingScheme.Base1:
        return "1", "2", "3", "4"
    elif naming_scheme == hou.parmNamingScheme.XYZW:
        return "x", "y", "z", "w"
    elif naming_scheme == hou.parmNamingScheme.XYWH:
        return "x", "y", "w", "h"
    elif naming_scheme == hou.parmNamingScheme.UVW:
        return "u", "v", "w"
    elif naming_scheme == hou.parmNamingScheme.RGBA:
        return "r", "g", "b", "a"
    elif naming_scheme == hou.parmNamingScheme.MinMax:
        return "min", "max"
    elif naming_scheme == hou.parmNamingScheme.MaxMin:
        return "max", "min"
    elif naming_scheme == hou.parmNamingScheme.StartEnd:
        return "start", "end"
    elif naming_scheme == hou.parmNamingScheme.BeginEnd:
        return "begin", "end"


def link_parameter(
    origin: hou.node, parameter_name: str, level=1, prepend="", append=""
) -> None:
    """This function links a parameter on a Houdini node
    to an expression, allowing for dynamic updates."""
    org_parameter = origin.parmTemplateGroup().find(parameter_name)

    if not org_parameter:
        print("Parameter not found: ", parameter_name)
        return

    # Determine the expression prefix based on the parameter's data type
    parameter_type = "ch"
    if org_parameter.dataType() == hou.parmData.String:
        parameter_type = "chsop"

    # If the parameter is single-component, directly set its expression
    if org_parameter.numComponents() == 1:
        origin.parm(parameter_name).setExpression(
            '{}("{}{}")'.format(
                parameter_type, "../" * level, prepend + parameter_name + append
            )
        )

    # If the parameter has multiple components, set an expression for each component
    else:
        scheme = convert_naming_scheme(org_parameter.namingScheme())
        for i in range(org_parameter.numComponents()):
            origin.parm(parameter_name + scheme[i]).setExpression(
                '{}("{}{}")'.format(
                    parameter_type,
                    "../" * level,
                    prepend + parameter_name + append + scheme[i],
                )
            )


def link_deep_parameters(
    origin: hou.Node, parameters: list, prepend: str = "", append: str = ""
) -> None:
    """This function recursively links parameters from a list to the origin node
    with optional prepending and appending strings."""
    for parameter in parameters:
        # If the parameter is a folder, recurse into it
        if parameter.type() == hou.parameterTemplateType.Folder:
            link_deep_parameters(origin, parameter.parmTemplates(), prepend, append)
        else:
            # Otherwise, link the individual parameter
            link_parameter(
                origin, parameter.name(), level=2, prepend=prepend, append=append
            )


def reference_parameter(
    origin: hou.Node,
    dist: list,
    parameter: str,
    conditional: tuple = None,
    join_to_next=False,
) -> None:
    """This function references a parameter on a node,
    potentially with a condition, and appends it to a template group."""
    org_parameters = origin.parmTemplateGroup()
    org_parameter = org_parameters.find(parameter)

    if not org_parameter:
        print("Parameter not found:", parameter)
        return

    if conditional:
        org_parameter.setConditional(conditional[0], conditional[1])

    if join_to_next:
        org_parameter.setJoinWithNext(True)
    else:
        org_parameter.setJoinWithNext(False)

    # Depending on the 'dist' object's type, append or add the parameter template
    if hasattr(dist, "append"):
        if org_parameter.name() == "engine":
            org_parameter.setItemGeneratorScript(
                "opmenu -l -a karmarendersettings engine"
            )
        if org_parameter.name() == "camera":
            org_parameter.setItemGeneratorScript(
                "kwargs['node'].node('karmarendersettings').hm().getCameras(kwargs)"
            )

        dist.append(org_parameter)
    elif hasattr(dist, "addParmTemplate"):
        # I couldn't find another place to add generator scripts so this mess will have to do
        if org_parameter.name() == "dcm":
            org_parameter.setLabel("Deep camera map")
        if org_parameter.name() == "light_sampling_mode":
            org_parameter.setItemGeneratorScript(
                "opmenu -l -a karmarendersettings light_sampling_mode"
            )
        if org_parameter.name() == "vblur":
            org_parameter.setItemGeneratorScript(
                "opmenu -l -a karmarendersettings vblur"
            )
        if org_parameter.name() == "instance_vblur":
            org_parameter.setItemGeneratorScript(
                "opmenu -l -a karmarendersettings instance_vblur"
            )
        if org_parameter.name() == "aspectRatioConformPolicy":
            org_parameter.setItemGeneratorScript(
                "opmenu -l -a karmarendersettings aspectRatioConformPolicy"
            )

        dist.addParmTemplate(org_parameter)
    else:
        print("Undefined method for distributing parameter templates.")
        return

    # Link the original parameter to the distribution
    link_parameter(origin, parameter)


def rename_deep_parameters(
    parameters: list, prepend: str = "", append: str = ""
) -> list:
    """This function renames deep parameters recursively,
    with optional prepending and appending strings."""
    for parameter in parameters:
        # Rename the parameter by adding prepend and append strings
        parameter.setName(f"{prepend}{parameter.name()}{append}")

        # If the parameter is a folder, recurse into it to rename its children
        if parameter.type() == hou.parameterTemplateType.Folder:
            renamed = rename_deep_parameters(parameter.parmTemplates(), prepend, append)
            parameter.setParmTemplates(renamed)

    return parameters


def space_camel_case(text: str) -> str:
    """This function inserts a space before each capital letter in a
    camelCase or PascalCase string, effectively converting it
    from camelCase/PascalCase to a space-separated string."""
    return re.sub(r"((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))", r" \1", text)


def _get_metadata_block():
    """
    Get a MultiparmBlock to set up metadata with

    Returns:
        hou.FolderParmTemplate: MultiparmBlock with metadata entries
    """
    metadata_entries = hou.FolderParmTemplate(
        "metadata_entries", "Entries", folder_type=hou.folderType.MultiparmBlock
    )
    metadata_entries.addParmTemplate(
        hou.StringParmTemplate("metadata_#_key", "Key", 1, join_with_next=True)
    )

    metadata_types = [
        {"key": "float", "name": "Float", "type": "float", "components": 1},
        {"key": "int", "name": "Integer", "type": "int", "components": 1},
        {"key": "string", "name": "String", "type": "string", "components": 1},
        {"key": "v2f", "name": "Vector 2 Float", "type": "float", "components": 2},
        {"key": "v2i", "name": "Vector 2 Int", "type": "int", "components": 2},
        {"key": "v3f", "name": "Vector 3 Float", "type": "float", "components": 3},
        {"key": "v3i", "name": "Vector 3 Int", "type": "int", "components": 3},
        {"key": "box2f", "name": "Box 2 Float", "type": "float", "components": 4},
        {"key": "box2i", "name": "Box 2 Int", "type": "int", "components": 4},
        {"key": "m33f", "name": "Matrix 3x3", "type": "float", "components": 9},
        {"key": "m44f", "name": "Matrix 4x4", "type": "float", "components": 16},
    ]
    metadata_names = [md_type["key"] for md_type in metadata_types]
    metadata_labels = [md_type["name"] for md_type in metadata_types]

    metadata_entries.addParmTemplate(
        hou.MenuParmTemplate(
            "metadata_#_type", "   Type", metadata_names, metadata_labels
        )
    )

    for md_type in metadata_types:
        if md_type["type"] == "float":
            parm = hou.FloatParmTemplate(
                f"metadata_#_{md_type['key']}", "Value", md_type["components"]
            )
        elif md_type["type"] == "int":
            parm = hou.IntParmTemplate(
                f"metadata_#_{md_type['key']}", "Value", md_type["components"]
            )
        elif md_type["type"] == "string":
            parm = hou.StringParmTemplate(
                f"metadata_#_{md_type['key']}", "Value", md_type["components"]
            )
        parm.setConditional(
            hou.parmCondType.HideWhen, f"{{ metadata_#_type != {md_type['key']} }}"
        )
        metadata_entries.addParmTemplate(parm)

    return metadata_entries


# Here we start actually building the OTL/HDA.

# Delete node if it's there already so we can make a fresh new one.
hda = hou.node("/stage/SGTK_Karma_Render")
if hda:
    hda.destroy()

hda = hou.node("/stage/").createNode("subnet", "SGTK_Karma_Render")

# Create standard nodes which we will link to later
# Input null needed by loputils to fetch camera list for some reason
null_node = hda.createNode("null", "input")
karma_render_settings = hda.createNode("karmarenderproperties", "karmarendersettings")
karma_cryptomatte = hda.createNode("karmacryptomatte", "karmacryptomatte")
crypto_switch = hda.createNode("switch", "crypto_switch")
motionblur = hda.createNode("motionblur", "motionblur")
motionblur_switch = hda.createNode("switch", "motionblur_switch")
render_product_edit = hda.createNode("renderproduct", "renderproduct_edit")
node_user_metadata = hda.createNode("attribwrangle", "user_metadata")
node_sg_metadata = hda.createNode("attribwrangle", "sg_metadata")
python_node = hda.createNode("pythonscript", "pRef_caller")
usdrender_rop = hda.createNode("usdrender_rop", "usdrender_rop")
output_node = hda.createNode("output", "output0")

# Link nodes
karma_render_settings.setInput(0, null_node)
karma_cryptomatte.setInput(0, karma_render_settings)
crypto_switch.setInput(0, karma_render_settings)
crypto_switch.setInput(1, karma_cryptomatte)
motionblur.setInput(0, crypto_switch)
motionblur_switch.setInput(0, crypto_switch)
motionblur_switch.setInput(1, motionblur)
render_product_edit.setInput(0, motionblur_switch)
node_user_metadata.setInput(0, render_product_edit)
node_sg_metadata.setInput(0, node_user_metadata)
python_node.setInput(0, node_sg_metadata)
usdrender_rop.setInput(0, python_node)
output_node.setInput(0, python_node)
output_node.setDisplayFlag(True)

hda.layoutChildren(
    (
        null_node,
        karma_cryptomatte,
        karma_render_settings,
        crypto_switch,
        motionblur,
        motionblur_switch,
        render_product_edit,
        node_user_metadata,
        node_sg_metadata,
        python_node,
        usdrender_rop,
        output_node,
    )
)
hda.setSelected(True)

# Setting standard karma settings
karma_render_settings.parm("dcmvars").set("")
karma_render_settings.parm("dcmcompression").set(1)

# Setting standard cryptomatte settings
karma_cryptomatte.parm("renderproductmode").set(1)

# Setting standard crypto_switch settings
crypto_switch.parm("input").setExpression(
    '1 if hou.pwd().inputs()[1].evalParm("doprimcrypto") or hou.pwd().inputs()[1].evalParm("domtlcrypto") else 0',
    language=hou.exprLanguage.Python,
)

# Setting standard motionblur_switch settings
motionblur_switch.parm("input").setExpression(
    '1 if hou.pwd().parent().evalParm("enablemblur") else 0',
    language=hou.exprLanguage.Python,
)

# Setting the render product settings
render_product_edit.parm("createprims").set("off")
render_product_edit.parm("primpattern").set("/Render/Products/dcm")
render_product_edit.parm("orderedVars_control").set("none")
render_product_edit.parm("productName_control").set("none")
render_product_edit.parm("productType_control").set("none")
render_product_edit.parm("xn__karmaproductdcmzbias_control_nmbh").set("set")

# Setting the metadata wrangle settings
for i, node in enumerate([node_user_metadata, node_sg_metadata]):
    node.parm("primpattern").set("/Render/** & %type:RenderProduct")

    if i == 0:
        level = "../"
    else:
        level = ""
        metadata_params = node_sg_metadata.parmTemplateGroup()
        metadata_params.addParmTemplate(_get_metadata_block())
        metadata_params.addParmTemplate(hou.StringParmTemplate("artist", "Artist", 1))
        node_sg_metadata.setParmTemplateGroup(metadata_params)

    node.parm("snippet").set(
        f'for (int i = 1; i <= chi("{level}metadata_entries"); i++) {{ \n\
    string type = chs(sprintf("{level}metadata_%g_type", i)); \n\
    string name = "driver:parameters:OpenEXR:" + chs(sprintf("{level}metadata_%g_key", i)); \n\
    string value_name = sprintf("{level}metadata_%g_%s", i, type); \n\
            \n\
    if (type == "float") \n\
        usd_setattrib(0, @primpath, name, chf(value_name)); \n\
    else if (type == "int") \n\
        usd_setattrib(0, @primpath, name, chi(value_name)); \n\
    else if (type == "string") \n\
        usd_setattrib(0, @primpath, name, chs(value_name)); \n\
    else if (startswith(type, "v")) \n\
        usd_setattrib(0, @primpath, name, chv(value_name)); \n\
    else if (startswith(type, "bix")) \n\
        usd_setattrib(0, @primpath, name, chp(value_name)); \n\
    else if (type == "m33f") \n\
        usd_setattrib(0, @primpath, name, ch3(value_name)); \n\
    else if (type == "m44f") \n\
        usd_setattrib(0, @primpath, name, ch4(value_name)); \n\
}} \n\n\
usd_setattrib(0, @primpath, "driver:parameters:artist", chs("artist"));'
    )

# Setting the python pRef system setting
python_node.parm("python").set(
    "hou.pwd().parent().hdaModule().compute_pref_point_references(hou.pwd().parent(), hou.pwd().editableStage())"
)

# Creating the HDA
hda = hou.Node.createDigitalAsset(
    hda,
    "sgtk_karma",
    os.path.join(OTL_FOLDER, "sgtk_karma.otl"),
    min_num_inputs=2,
    version="1.0.3",
    ignore_external_references=True,
)
hda.type().setDefaultColor(hou.Color(0.9, 0.5, 0.2))

hda_def = hda.type().definition()
hda_options = hda_def.options()

python_module = open(os.path.join(OTL_FOLDER, "python_functions.py"), "r")

hda_def.addSection("PythonModule", python_module.read())
hda_def.setExtraFileOption("python_functions/IsPython", True)
hda_def.addSection("OnCreated", 'kwargs["node"].setColor(hou.Color(0.9, 0.5, 0.2))')
hda_def.setExtraFileOption("OnCreated/IsPython", True)
hda_def.addSection("EditableNodes", "karmarendersettings usdrender_rop")


# HDA Icon
image_file = os.path.join(OTL_FOLDER, "karma.svg")
icon_section_name = "IconSVG"

with open(image_file, "rb") as image:
    icon_data = image.read()

hda_def.addSection(icon_section_name, icon_data)
hda_def.setIcon("opdef:{}?{}".format(hda.type().nameWithCategory(), icon_section_name))
hda_def.setMaxNumOutputs(0)


# Starting here we add the actual buttons and stuff
hda_parameters = hda_def.parmTemplateGroup()
karma_render_settings_parameters = karma_render_settings.parmTemplateGroup()

# Top buttons
hda_parameters.append(
    hou.ButtonParmTemplate(
        "executeFarm",
        "Render on farm",
        join_with_next=True,
        script_callback="hou.phm().render_on_farm(kwargs['node'])",
        script_callback_language=hou.scriptLanguage.Python,
    )
)
hda_parameters.append(
    hou.ButtonParmTemplate(
        "executeLocal",
        "Render locally",
        join_with_next=True,
        script_callback="hou.phm().render_locally(kwargs['node'])",
        script_callback_language=hou.scriptLanguage.Python,
    )
)
hda_parameters.append(
    hou.ButtonParmTemplate(
        "openFolder",
        "Open folder",
        join_with_next=True,
        script_callback="hou.phm().open_folder(kwargs['node'])",
        script_callback_language=hou.scriptLanguage.Python,
    )
)


hda_parameters.append(hou.SeparatorParmTemplate("sep_1"))

# Comma after "main" because default_value takes the first item in a list.
# A string is a list of letters, so otherwise it would just be "m"
hda_parameters.append(
    hou.StringParmTemplate("name", "Name", 1, default_value=("main",))
)

hda_parameters.append(hou.SeparatorParmTemplate("sep_2"))

# Basic render settings
reference_parameter(usdrender_rop, hda_parameters, "trange")
reference_parameter(
    usdrender_rop,
    hda_parameters,
    "f",
    (hou.parmCondType.DisableWhen, '{ trange == "off" }'),
)
reference_parameter(karma_render_settings, hda_parameters, "camera")


resolution_parm_template = hou.IntParmTemplate(
    "resolution",
    "Resolution",
    2,
    default_value=(1920, 1080),
    script_callback="hou.phm().update_resolution(kwargs['node'])",
    script_callback_language=hou.scriptLanguage.Python,
)
hda_parameters.append(resolution_parm_template)

hda_parameters.append(hou.SeparatorParmTemplate("sep_3"))

reference_parameter(karma_render_settings, hda_parameters, "engine")

reference_parameter(
    karma_render_settings,
    hda_parameters,
    "samplesperpixel",
    (hou.parmCondType.HideWhen, '{ engine != "cpu" }'),
)

reference_parameter(
    karma_render_settings,
    hda_parameters,
    "pathtracedsamples",
)

reference_parameter(
    karma_render_settings,
    hda_parameters,
    "importsecondaryinputvars",
)


# Rendering
rendering = hou.FolderParmTemplate("rendering", "Rendering")


# Rendering -> Samples
secondary_samples = hou.FolderParmTemplate("secondary_sampling", "Secondary")
reference_parameter(karma_render_settings, secondary_samples, "varianceaa_minsamples")
reference_parameter(karma_render_settings, secondary_samples, "varianceaa_maxsamples")

reference_parameter(karma_render_settings, secondary_samples, "diffusequality")
reference_parameter(karma_render_settings, secondary_samples, "reflectquality")
reference_parameter(karma_render_settings, secondary_samples, "refractquality")
reference_parameter(karma_render_settings, secondary_samples, "volumequality")
reference_parameter(karma_render_settings, secondary_samples, "sssquality")

reference_parameter(karma_render_settings, secondary_samples, "light_sampling_mode")
reference_parameter(karma_render_settings, secondary_samples, "light_sampling_quality")

reference_parameter(karma_render_settings, secondary_samples, "screendoorlimit")
reference_parameter(karma_render_settings, secondary_samples, "volumesteprate")


rendering.addParmTemplate(secondary_samples)

# Rendering -> Limits
for folder in karma_render_settings_parameters.findFolder("Rendering").parmTemplates():
    if folder.label() == "Limits":
        rendering.addParmTemplate(folder)

        for parameter in folder.parmTemplates():
            link_parameter(karma_render_settings, parameter.name())

# Rendering -> Camera Effects
rendering_camera_effects = hou.FolderParmTemplate("camera_effects", "Camera Effects")
reference_parameter(karma_render_settings, rendering_camera_effects, "enabledof")
reference_parameter(karma_render_settings, rendering_camera_effects, "enablemblur")

motion_blur_settings = hou.FolderParmTemplate(
    "motion_blur_settings",
    "Motion Blur",
    folder_type=hou.folderType.Simple,
    conditionals={hou.parmCondType.DisableWhen: "{ enablemblur != 1 }"},
)
reference_parameter(karma_render_settings, motion_blur_settings, "mblur")
reference_parameter(
    karma_render_settings,
    motion_blur_settings,
    "xformsamples",
    (hou.parmCondType.DisableWhen, "{ mblur != 1 }"),
)
reference_parameter(
    karma_render_settings,
    motion_blur_settings,
    "geosamples",
    (hou.parmCondType.DisableWhen, "{ mblur != 1 }"),
)
reference_parameter(
    karma_render_settings,
    motion_blur_settings,
    "vblur",
    (hou.parmCondType.DisableWhen, "{ mblur != 1 }"),
)
reference_parameter(
    karma_render_settings,
    motion_blur_settings,
    "instance_vblur",
    (hou.parmCondType.DisableWhen, "{ mblur != 1 }"),
)
reference_parameter(
    karma_render_settings,
    motion_blur_settings,
    "instance_samples",
    (hou.parmCondType.DisableWhen, "{ mblur != 1 }"),
)
reference_parameter(
    karma_render_settings,
    motion_blur_settings,
    "volumevblurscale",
    (hou.parmCondType.DisableWhen, "{ mblur != 1 }"),
)
reference_parameter(
    karma_render_settings,
    motion_blur_settings,
    "disableimageblur",
    (hou.parmCondType.DisableWhen, "{ velocity == 0 motionvectors == 0 }"),
)

rendering_camera_effects.addParmTemplate(motion_blur_settings)

rendering.addParmTemplate(rendering_camera_effects)

# Rendering -> Aspect Ratio
rendering_aspect_ratio = hou.FolderParmTemplate("aspect_ratio", "Aspect Ratio")
reference_parameter(
    karma_render_settings, rendering_aspect_ratio, "aspectRatioConformPolicy"
)
reference_parameter(karma_render_settings, rendering_aspect_ratio, "dataWindowNDC")
reference_parameter(karma_render_settings, rendering_aspect_ratio, "pixelAspectRatio")

rendering.addParmTemplate(rendering_aspect_ratio)

hda_parameters.append(rendering)


# AOVs
aovs = hou.FolderParmTemplate("aovs", "AOVs")

denoise_checkbox = hou.ToggleParmTemplate("denoise", "Denoise AOVs")
aovs.addParmTemplate(denoise_checkbox)


# AOVs -> Component level output
component_level_output = hou.FolderParmTemplate(
    "component_level_output",
    "Component Level Output",
    folder_type=hou.folderType.Collapsible,
)

# AOVs -> Component level output -> Beauty
beauty_aovs = hou.FolderParmTemplate(
    "beauty_aovs",
    "Beauty",
    folder_type=hou.folderType.Collapsible,
)
reference_parameter(karma_render_settings, beauty_aovs, "beauty")
reference_parameter(karma_render_settings, beauty_aovs, "beautyunshadowed")
component_level_output.addParmTemplate(beauty_aovs)

# AOVs -> Component level output -> Diffuse
diffuse_aovs = hou.FolderParmTemplate(
    "diffuse_aovs",
    "Diffuse",
    folder_type=hou.folderType.Collapsible,
)

reference_parameter(karma_render_settings, diffuse_aovs, "combineddiffuse")
reference_parameter(karma_render_settings, diffuse_aovs, "directdiffuse")
reference_parameter(karma_render_settings, diffuse_aovs, "indirectdiffuse")
reference_parameter(karma_render_settings, diffuse_aovs, "combineddiffuseunshadowed")
reference_parameter(karma_render_settings, diffuse_aovs, "directdiffuseunshadowed")
reference_parameter(karma_render_settings, diffuse_aovs, "indirectdiffuseunshadowed")
component_level_output.addParmTemplate(diffuse_aovs)

# AOVs -> Component level output -> Reflections and refractions
reflection_refraction_aovs = hou.FolderParmTemplate(
    "reflections_refractions",
    "Reflections and Refractions",
    folder_type=hou.folderType.Collapsible,
)

reference_parameter(
    karma_render_settings, reflection_refraction_aovs, "combinedglossyreflection"
)
reference_parameter(
    karma_render_settings, reflection_refraction_aovs, "directglossyreflection"
)
reference_parameter(
    karma_render_settings, reflection_refraction_aovs, "indirectglossyreflection"
)
reference_parameter(
    karma_render_settings, reflection_refraction_aovs, "glossytransmission"
)
reference_parameter(karma_render_settings, reflection_refraction_aovs, "coat")
component_level_output.addParmTemplate(reflection_refraction_aovs)

# AOVs -> Component level output -> Lights and Emission
lights_emission_aovs = hou.FolderParmTemplate(
    "lights_emission",
    "Lights and Emission",
    folder_type=hou.folderType.Collapsible,
)

reference_parameter(karma_render_settings, lights_emission_aovs, "combinedemission")
reference_parameter(karma_render_settings, lights_emission_aovs, "directemission")
reference_parameter(karma_render_settings, lights_emission_aovs, "indirectemission")
reference_parameter(karma_render_settings, lights_emission_aovs, "visiblelights")
component_level_output.addParmTemplate(lights_emission_aovs)


# AOVs -> Component level output -> Volume
volume_aovs = hou.FolderParmTemplate(
    "volume",
    "Volume",
    folder_type=hou.folderType.Collapsible,
)

reference_parameter(karma_render_settings, volume_aovs, "combinedvolume")
reference_parameter(karma_render_settings, volume_aovs, "directvolume")
reference_parameter(karma_render_settings, volume_aovs, "indirectvolume")
component_level_output.addParmTemplate(volume_aovs)


# AOVs -> Component level output -> SSS
sss_aov = hou.FolderParmTemplate(
    "sss_folder",
    "SSS",
    folder_type=hou.folderType.Collapsible,
)

reference_parameter(karma_render_settings, sss_aov, "sss")
component_level_output.addParmTemplate(sss_aov)

# AOVs -> Component level output -> Albedo
albedo_aov = hou.FolderParmTemplate(
    "albedo_folder",
    "Albedo",
    folder_type=hou.folderType.Collapsible,
)

reference_parameter(karma_render_settings, albedo_aov, "albedo")
component_level_output.addParmTemplate(albedo_aov)


aovs.addParmTemplate(component_level_output)


# AOVs -> Component level output
ray_level_output = hou.FolderParmTemplate(
    "ray_level_output",
    "Ray Level Output",
    folder_type=hou.folderType.Collapsible,
)

reference_parameter(karma_render_settings, ray_level_output, "P")
reference_parameter(karma_render_settings, ray_level_output, "D")
reference_parameter(karma_render_settings, ray_level_output, "time")
reference_parameter(karma_render_settings, ray_level_output, "near")
reference_parameter(karma_render_settings, ray_level_output, "far")
reference_parameter(karma_render_settings, ray_level_output, "mask")
reference_parameter(karma_render_settings, ray_level_output, "contrib")
reference_parameter(karma_render_settings, ray_level_output, "hitP")
reference_parameter(karma_render_settings, ray_level_output, "hitPz")
reference_parameter(karma_render_settings, ray_level_output, "hitstack")
reference_parameter(karma_render_settings, ray_level_output, "element")
reference_parameter(karma_render_settings, ray_level_output, "primid")
reference_parameter(karma_render_settings, ray_level_output, "hituv")
reference_parameter(karma_render_settings, ray_level_output, "hitdist")
reference_parameter(karma_render_settings, ray_level_output, "dPdz")
reference_parameter(karma_render_settings, ray_level_output, "hitN")
reference_parameter(karma_render_settings, ray_level_output, "hitNg")
reference_parameter(karma_render_settings, ray_level_output, "flags")
reference_parameter(karma_render_settings, ray_level_output, "motionvectors")
reference_parameter(karma_render_settings, ray_level_output, "velocity")

aovs.addParmTemplate(ray_level_output)


# AOVs -> Cryptomatte
cryptomatte = hou.FolderParmTemplate(
    "cryptomatte",
    "Cryptomatte",
    folder_type=hou.folderType.Collapsible,
)

cryptomatte.addParmTemplate(hou.LabelParmTemplate("primitives", "Primitives"))
reference_parameter(karma_cryptomatte, cryptomatte, "doprimcrypto")
cryptomatte.addParmTemplate(hou.LabelParmTemplate("materials", "Materials"))
reference_parameter(karma_cryptomatte, cryptomatte, "domtlcrypto")

aovs.addParmTemplate(cryptomatte)

# AOVs -> Deep
deep_settings = hou.FolderParmTemplate(
    "deep_settings",
    "Deep camera map",
    folder_type=hou.folderType.Simple,
)

reference_parameter(karma_render_settings, deep_settings, "dcm")
deep_settings.addParmTemplate(
    hou.MenuParmTemplate(
        "deep_target",
        "Deep target",
        ("hard_surface", "volumes"),
        ("Hard surface", "Volumes"),
        script_callback="hou.phm().setup_deep_settings(kwargs['node'])",
        script_callback_language=hou.scriptLanguage.Python,
        disable_when="{ dcm == 0 }",
    )
)

reference_parameter(
    render_product_edit,
    deep_settings,
    "xn__karmaproductdcmzbias_m8ah",
    (hou.parmCondType.DisableWhen, "{ dcm == 0 }"),
)


aovs.addParmTemplate(deep_settings)


# AOVs -> Light groups
light_groups = hou.FolderParmTemplate(
    "light_groups",
    "Light Groups",
    folder_type=hou.folderType.Simple,
)

light_groups.addParmTemplate(
    hou.ButtonParmTemplate(
        "setup_light_groups",
        "Update light groups",
        script_callback="hou.phm().setup_light_groups(kwargs['node'])",
        script_callback_language=hou.scriptLanguage.Python,
    )
)

light_group_item = hou.FolderParmTemplate(
    "light_groups_select",
    "Light Groups",
    folder_type=hou.folderType.MultiparmBlock,
)
light_group_name = hou.StringParmTemplate(
    "light_group_name_#",
    "Name",
    1,
    string_type=hou.stringParmType.Regular,
    naming_scheme=hou.parmNamingScheme.Base1,
)

light_operator_list = hou.StringParmTemplate(
    "select_light_lops_#",
    "Select Light LOPs",
    1,
    string_type=hou.stringParmType.NodeReferenceList,
    naming_scheme=hou.parmNamingScheme.Base1,
    tags={
        "opfilter": "!!LOP!!",
        "oprelative": ".",
    },
)

light_group_item.addParmTemplate(light_group_name)
light_group_item.addParmTemplate(light_operator_list)
light_group_item.addParmTemplate(hou.SeparatorParmTemplate("lgSep#"))

light_groups.addParmTemplate(light_group_item)


aovs.addParmTemplate(light_groups)


# AOVs -> pRefs
# Still working on this, will be functional in the next update :)
prefs = hou.FolderParmTemplate(
    "prefs",
    "pRefs",
    folder_type=hou.folderType.Simple,
)

prefs.addParmTemplate(
    hou.ButtonParmTemplate(
        "setup_prefs",
        "Update pRefs",
        script_callback="hou.phm().setup_prefs(kwargs['node'])",
        script_callback_language=hou.scriptLanguage.Python,
    )
)

pref_item = hou.FolderParmTemplate(
    "pref_select",
    "pRefs",
    folder_type=hou.folderType.MultiparmBlock,
)

pref_name = hou.StringParmTemplate(
    "pref_name_#",
    "Name",
    1,
    string_type=hou.stringParmType.Regular,
    naming_scheme=hou.parmNamingScheme.Base1,
)

pref_primpattern_list = hou.StringParmTemplate(
    "select_pref_#",
    "Select object",
    1,
    string_type=hou.stringParmType.NodeReference,
    naming_scheme=hou.parmNamingScheme.Base1,
    tags={
        "opfilter": "!!LOP!!",
        "oprelative": ".",
    },
)

pref_source_frame = hou.IntParmTemplate(
    "pref_source_frame_#", "Source frame", 1, min=0, max=3000
)

pref_item.addParmTemplate(pref_name)
pref_item.addParmTemplate(pref_primpattern_list)
pref_item.addParmTemplate(pref_source_frame)
pref_item.addParmTemplate(hou.SeparatorParmTemplate("prefSep#"))

prefs.addParmTemplate(pref_item)
aovs.addParmTemplate(prefs)


hda_parameters.append(aovs)

# Metadata
metadata_folder = hou.FolderParmTemplate("metadata_folder", "Metadata")
metadata_parmblock = _get_metadata_block()
metadata_folder.addParmTemplate(metadata_parmblock)
hda_parameters.append(metadata_folder)

hda_def.setParmTemplateGroup(hda_parameters)


hda.indirectInputs()[0].outputs()[0].destroy()

hda.node("input").setInput(0, hda.indirectInputs()[0])
hda.node("karmarendersettings").setInput(1, hda.indirectInputs()[1])
hda.parm("xn__karmaproductdcmzbias_m8ah").set(0.01)

hda_def.save(hda_def.libraryFilePath(), hda, hda_options)

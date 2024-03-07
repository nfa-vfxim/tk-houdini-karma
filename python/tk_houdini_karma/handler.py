"""This file contains all functions that we need for our SGTK Karma App to work.
We access these functions through app.py, which is a bit cleaner to access."""

import json
import os
import re

import hou
import sgtk

from .farm_dialog import farm_submission_window
from ..datamodel.metadata import MetaData


class karma_node_handler(object):
    def __init__(self, app) -> None:
        self.app = app
        self.sg = self.app.shotgun

    def submit_to_farm(self, node: hou.Node) -> None:
        """This function opens the dialogue box for submitting
        our Karma job to to the Deadline render farm.

        Args:
            node (hou.Node): USD Render ROP node
        """
        node.allowEditingOfContents()

        if not self.setup_output_paths(node):
            return

        if not self.setup_metadata(node):
            return

        render_name = node.parm("name").eval()

        # Create directories
        render_paths = self.get_output_paths(node)
        for path in render_paths:
            self.__create_directory(path)

        # Determine basic variables for submission
        file_name = hou.hipFile.name()
        file_name = os.path.basename(file_name).split(".")[0] + " (%s)" % render_name

        # Determine framerange
        framerange = self.get_output_range(node)
        framerange = f"{framerange[0]}-{framerange[1]}"

        # Start submission panel
        render_aovs = self.get_render_aovs(node)

        global farm_submission
        farm_submission = farm_submission_window(
            self.app, node, file_name, 50, framerange, render_paths, render_aovs
        )
        farm_submission.show()

    def render_locally(self, node: hou.Node) -> None:
        """Start local render

        Args:
            node (hou.Node): RenderMan node
            network (str): Network type
        """
        node.allowEditingOfContents()

        if not self.setup_output_paths(node):
            return

        if not self.setup_metadata(node):
            return

        render_paths = self.get_output_paths(node)

        for path in render_paths:
            self.__create_directory(path)

        node.node("usdrender_rop").parm("execute").pressButton()

        hou.ui.displayMessage(
            "Local render started! Check your Render -> Scheduler to see the progress.",
            severity=hou.severityType.Message,
        )

    @staticmethod
    def validate_node(node: hou.Node) -> bool:
        """This function will make sure all the parameters
        are filled in and setup correctly.

        Args:
            node (hou.Node): SGTK Karma node
        """
        # First we'll check if there is a name
        render_name = node.parm("name").eval()
        if render_name == "":
            hou.ui.displayMessage(
                "Name is not defined, please set the name parameter before submitting.",
                severity=hou.severityType.Error,
            )
            return False

        if not render_name.isalnum():
            hou.ui.displayMessage(
                "Name is not alphanumeric, please only use alphabet letters (a-z) and numbers (0-9).",
                severity=hou.severityType.Error,
            )
            return False

        # Make sure the node has an input to render
        inputs = node.inputs()
        if len(inputs) <= 0:
            hou.ui.displayMessage(
                "Node doesn't have input, please connect this "
                "ShotGrid Kamera Render node to "
                "the stage to render.",
                severity=hou.severityType.Error,
            )
            return False

        return True

    def setup_metadata(self, node: hou.Node) -> None:
        """Sets ShotGrid metadata and validates user-set metadata. 'Borrowed' from tk-houdini-renderman."""
        md_config = self.app.get_setting("render_metadata")

        md_items = [
            MetaData("colorspace", "string", "ACES - ACEScg"),
        ]
        md_config_groups = {}

        for md in md_config:
            key = f'rmd_{md.get("key")}'
            md_items.append(
                MetaData(
                    key,
                    md.get("type"),
                    f'`{md.get("expression")}`'
                    if md.get("expression")
                    else md.get("value"),
                )
            )
            group = md.get("group")
            # TODO should use prefixed version in group mapping?
            if md_config_groups.get(group):
                md_config_groups.get(group).append(key)
            else:
                md_config_groups[group] = [key]
        md_items.append(
            MetaData("rmd_PostRenderGroups", "string", json.dumps(md_config_groups))
        )

        md_artist = str(self.app.context.user["id"])

        # Check if custom metadata has valid keys
        for j in range(1, node.evalParm("metadata_entries") + 1):
            md_key = node.parm(f"metadata_{j}_key").eval()
            if not re.match(r"^[A-Za-z0-9_]+$", md_key):
                hou.ui.displayMessage(
                    f'The metadata key "{md_key}" is invalid. You can only use letters, numbers, and '
                    f"underscores.",
                    severity=hou.severityType.Error,
                )
                return False

        node_md = node.node("sg_metadata")

        node_md.parm("artist").set(md_artist)

        node_md.parm("metadata_entries").set(0)
        node_md.parm("metadata_entries").set(len(md_items))

        for i, item in enumerate(md_items):
            item: MetaData

            node_md.parm(f"metadata_{i + 1}_key").set(item.key)
            node_md.parm(f"metadata_{i + 1}_type").set(item.type)
            if "`" in item.value:
                expression = item.value[1:-1]
                expression = re.sub(r"(ch[a-z]*)(\()([\"'])", r"\1(\3../", expression)

                node_md.parm(f"metadata_{i + 1}_{item.type}").setExpression(expression)
            else:
                node_md.parm(f"metadata_{i + 1}_{item.type}").set(item.value)

        return True

    def setup_output_paths(self, node: hou.Node) -> bool:
        """This function sets the proper ShotGrid output paths for our node."""

        karma_renderingsettings_node = node.node("karmarendersettings")
        karma_crypto_node = node.node("karmacryptomatte")

        if not self.validate_node(node):
            return False

        karma_renderingsettings_node.parm("picture").set(
            self.get_output_path(node, "main")
        )

        karma_renderingsettings_node.parm("dcmfilename").set(
            self.get_output_path(node, "deep")
        )

        karma_crypto_node.parm("cryptopicture").set(
            self.get_output_path(node, "crypto")
        )

        return True

    def get_output_path(self, node: hou.Node, aov_name: str) -> str:
        """Calculate render path for an aov

        Args:
            node (hou.Node): Karma node
            aov_name (str): AOV name
        """
        aov_name = aov_name[0].lower() + aov_name[1:]

        current_filepath = hou.hipFile.path()

        work_template = self.app.get_template("work_file_template")
        render_template = self.app.get_template("output_render_template")

        # Set fields
        fields = work_template.get_fields(current_filepath)
        fields["SEQ"] = "FORMAT: $F"
        fields["output"] = node.parm("name").eval()
        fields["aov_name"] = aov_name
        fields["width"] = node.parm("resolutionx").eval()
        fields["height"] = node.parm("resolutiony").eval()

        return render_template.apply_fields(fields).replace(os.sep, "/")

    def get_output_paths(self, node: hou.Node) -> list[str]:
        """This function returns all output paths for the Deadline job."""
        paths = []

        paths.append(self.get_output_path(node, "main"))

        # Crypto needs seperate file because of a Nuke bug
        if node.evalParm("doprimcrypto") or node.evalParm("domtlcrypto"):
            paths.append(self.get_output_path(node, "crypto"))

        if node.evalParm("denoise"):
            paths.append(self.get_output_path(node, "denoise"))

        if node.evalParm("dcm"):
            paths.append(self.get_output_path(node, "deep"))

        return paths

    def get_output_range(self, node: hou.Node) -> list[int]:
        """This function returns our frame range or a single frame."""
        framerange_type = node.parm("trange").eval()

        if framerange_type > 0:
            start_frame = int(node.parm("f1").eval())
            end_frame = int(node.parm("f2").eval())
            framerange = [start_frame, end_frame]
        else:
            current_frame = int(hou.frame())
            framerange = [current_frame, current_frame]

        return framerange

    def __create_directory(self, render_path: str):
        """This function creates the directory to render to.

        Args:
            render_path (str): Render path to create directory for
        """
        directory = os.path.dirname(render_path)

        # If directory doesn't exist, create it
        if not os.path.isdir(directory):
            os.makedirs(directory)
            self.app.logger.debug("Created directory %s." % directory)

    def get_published_status(self, node: hou.Node) -> bool:
        """This function will check on ShotGrid if there is a publish
        with exactly the same name on the project. If
        there is a publish existing it will return a "True" value,
        otherwise a "False" value

        Args:
            node (hou.Node): Karma node
        """
        sg = self.sg

        # Define the regex to detect the Houdini "$F4" expressions
        # (or other numbers to define the padding)
        regex = r"[$][fF]\d"

        # Get the raw string from the picture parameter
        file_path = node.node("karmarendersettings").parm("picture").rawValue()

        # Detect "$F4" in the file path, and return it
        frame_match = re.search(regex, file_path)
        frame_match = frame_match.group(0)

        # Detect the padding number specified
        padding_length = re.search("[0-9]", frame_match)
        padding_length = padding_length.group(0)

        # Replace $F4 with %04d format
        file_name = file_path.replace(frame_match, "%0" + str(padding_length) + "d")
        file_name = os.path.basename(file_name)

        # Get current project ID
        current_engine = sgtk.platform.current_engine()
        current_context = current_engine.context
        project_id = current_context.project["id"]

        # Create the filter to search on ShotGrid for publishes with the same file name
        filters = [
            ["project", "is", {"type": "Project", "id": project_id}],
            ["code", "is", file_name],
        ]

        # Search on ShotGrid
        published_file = sg.find_one("PublishedFile", filters)

        # If there is no publish, it will return a None value.
        # So set the variable is_published to "False"
        if published_file is None:
            is_published = False
        # If the value is not None, there is a publish with the
        # same name. So set the variable is_published to "True
        else:
            is_published = True

        return is_published

    def get_render_aovs(self, node: hou.Node) -> list:
        """This functions gets our AOV list which we can later use for denoising."""
        render_aovs = self.get_toggle_key_value_list_inside_subfolder(
            node, "component_level_output"
        )
        render_aovs += self.get_toggle_key_value_list_inside_subfolder(
            node, "ray_level_output"
        )
        render_aovs += self.get_lightgroup_aovs(node)

        print(render_aovs)
        return render_aovs

    @staticmethod
    def get_toggle_key_value_list_inside_subfolder(
        node: hou.Node, folder_name: str
    ) -> list:
        """This function returns toggles inside several folders which are within a folder."""
        parm_template_group = node.parmTemplateGroup()
        base_folder = parm_template_group.find(folder_name)

        toggle_key_value_list = []
        for parameter_template in base_folder.parmTemplates():
            if parameter_template.type() != hou.parmTemplateType.Folder:
                parm = node.parm(parameter_template.name())
                if parm.eval():
                    toggle_key_value_list.append(parm.name())

                continue

            for toggle_parm_template in parameter_template.parmTemplates():
                parm = node.parm(toggle_parm_template.name())
                if parm.eval():
                    toggle_key_value_list.append(parm.name())

        return toggle_key_value_list

    @staticmethod
    def get_lightgroup_aovs(node: hou.Node) -> list:
        """This function returns a list of our user created light groups."""
        light_groups_select = node.parm("light_groups_select")

        light_groups_list = []
        for i in range(1, light_groups_select.eval() + 1):
            light_groups_list.append(f'LG_{node.parm(f"light_group_name_{i}").eval()}')

        return light_groups_list

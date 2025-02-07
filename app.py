"""This is the file that tk-houdini imports. We access all our functions in other code through this file. 

Example:
eng = sgtk.platform.current_engine()
app = eng.apps["tk-houdini-karma"]

app.submit_to_farm(node)"""

import hou
import sgtk


class tk_houdini_karma(sgtk.platform.Application):
    def init_app(self) -> None:
        """This functions initializes this app by importing all the code
        that is in this app's Python folder."""
        tk_houdini_karma_lop = self.import_module("tk_houdini_karma")
        self.handler = tk_houdini_karma_lop.karma_node_handler(self)

    def render_locally(self, node: hou.Node) -> None:
        """Starts a local render.

        Args:
            node (hou.Node): SGTK Karma Render node
        """
        self.handler.render_locally(node)

    def submit_to_farm(self, node: hou.Node) -> None:
        """This function opens the dialogue box for submitting
        our Karma job to to the Deadline render farm.

        Args:
            node (hou.Node):  SGTK Karma Render node
        """
        self.handler.submit_to_farm(node)

    def open_folder(self, node: hou.Node) -> None:
        """Opens the render folder in the OS appropriate file program.

        Args:
            node (hou.Node):  SGTK Karma Render node
        """
        self.handler.open_folder(node)

    def get_output_path(self, node: hou.Node, aov_name: str) -> str:
        """Calculate render path for an aov

        Args:
            node (hou.Node): SGTK Karma Render node
            aov_name (str): AOV name
        """
        return self.handler.get_output_path(node, aov_name)

    def get_output_range(self, node: hou.Node) -> list[int]:
        """Get output frame range for the Karma node

        Args:
            node (hou.Node): SGTK Karma Render node
        """
        return self.handler.get_output_range(node)

    def validate_node(self, node: hou.Node) -> str:
        """This function will make sure all the parameters
        are filled in and setup correctly.

        Args:
            node (hou.Node): SGTK Karma Render node
        """
        return self.handler.validate_node(node)

    def setup_metadata(self, node: hou.Node) -> None:
        """Sets ShotGrid metadata on node and validates user-set metadata.

        Args:
            node (hou.Node): SGTK Karma Render node
        """
        return self.handler.setup_metadata(node)

    def setup_output_paths(self, node: hou.Node) -> bool:
        """Sets the correct outputs on the SGTK Karma Render node

        Args:
            node (hou.Node): SGTK Karma Render node
        """
        return self.handler.setup_output_paths(node)

    def get_output_paths(self, node: hou.Node) -> list[str]:
        """Get output paths for the SGTK Karma Render node

        Args:
            node (hou.Node): SGTK Karma Render node
        """
        return self.handler.get_output_paths(node)

    def get_work_template(self) -> str:
        """Get work file template from ShotGrid, also used by the multi-publish collector."""
        return self.get_template("work_file_template")

    def get_render_template(self) -> str:
        """Get render file template from ShotGrid, also used by the multi-publish collector."""
        return self.get_template("output_render_template")

    def get_published_status(self, node: hou.Node) -> bool:
        """This function will check on ShotGrid if there is a publish
        with exactly the same name on the project, used by the multi-publish collector.

        Args:
            node (hou.Node): SGTK Karma Render node
        """
        return self.handler.get_published_status(node)

    def get_all_karma_nodes(self) -> tuple[hou.Node]:
        """Returns all nodes SGTK Karma nodes in our scene, used by the multi-publish collector."""
        self.log_debug("Retrieving sgtk_karma nodes...")
        nodes = hou.lopNodeTypeCategory().nodeType("sgtk_karma").instances()
        self.log_debug(f"Found {len(nodes)} sgtk_karma nodes.")
        return nodes

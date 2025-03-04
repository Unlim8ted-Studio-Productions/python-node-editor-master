from PySide6 import QtWidgets

from node_editor.node import Node
from nodes.common_widgets import TextLineEdit


class end_branch_Node(Node):
    def __init__(self):
        super().__init__()

        self.title_text = "End of Choice Node Branch"
        self.type_text = "REQUIRED"
        self.set_color(title_color=(255, 165, 0))

        self.add_pin(name="input", is_output=False, execution=True)
        self.add_pin(name="output in case of end of event", is_output=True, execution=True)


        self.build()

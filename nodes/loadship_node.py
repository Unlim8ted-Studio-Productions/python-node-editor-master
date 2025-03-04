from node_editor.node import Node
from PySide6 import QtWidgets

from node_editor.node import Node
from nodes.common_widgets import TextLineEdit, checkbox


class loadship_Node(Node):
    def __init__(self):
        super().__init__()

        self.title_text = "Load Ship"
        self.type_text = "ship"
        self.set_color(title_color=(255, 165, 0))
        self.add_pin(name="Ex In", is_output=False, execution=True)
        self.add_pin(name="Ex Out", is_output=True, execution=True)

        self.build()

    def init_widget(self):
        self.widget = QtWidgets.QWidget()
        self.widget.setFixedWidth(100)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.scaler_line = TextLineEdit()
        self.a = TextLineEdit()
        self.namelabel = QtWidgets.QLabel("ship name (for predifined ship, if you use this you must have a SEPERATE load ship node with auto bluprint field filled out):")
        layout.addWidget(self.namelabel)
        layout.addWidget(self.scaler_line)
        self.namelabell = QtWidgets.QLabel("ship name to load from auto bluprint:")
        layout.addWidget(self.namelabell)
        layout.addWidget(self.a)
        self.label = QtWidgets.QLabel("is hostile:")
        layout.addWidget(self.label)
        self.isunique = checkbox()
        layout.addWidget(self.isunique)
        self.widget.setLayout(layout)

        proxy = QtWidgets.QGraphicsProxyWidget()
        proxy.setWidget(self.widget)
        proxy.setParentItem(self)

        super().init_widget()
        
    def setinternaldata(self):
        self.scaler_line.setText(self.internaldata["text"])
        self.isunique.setChecked(self.internaldata["ishostile"])
        self.a.setText(self.internaldata["autoblueprint"])
        
    def setdata(self):
        self.internaldata["text"] = self.scaler_line.text()
        self.internaldata["autoblueprint"] = self.a.text()
        self.internaldata["ishostile"] = self.isunique.isChecked()
         
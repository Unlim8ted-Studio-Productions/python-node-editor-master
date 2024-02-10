import subprocess
import sys
import json
import tempfile
from PySide6 import QtWidgets, QtGui, QtCore
from node_editor.connection import Connection
from node_editor.gui.node_list import NodeList
from node_editor.gui.node_widget import NodeWidget
import logging
import os
from pathlib import Path
import importlib
import inspect
from xml.etree.ElementTree import Element, SubElement, tostring
import win32gui
import win32process

logging.basicConfig(level=logging.DEBUG)


class NodeEditorTab(QtWidgets.QMainWindow):
    OnProjectPathUpdate = QtCore.Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = None
        self.project_path = None
        self.imports = None  # we will store the project import node types here for now.

        icon = QtGui.QIcon("resources\\app.ico")
        self.setWindowIcon(icon)

        self.setWindowTitle("FTL Node Based Modding")
        settings = QtCore.QSettings("node-editor", "NodeEditor")

        # create a "File" menu and add an "Export CSV" action to it
        file_menu = QtWidgets.QMenu("File", self)
        self.menuBar().addMenu(file_menu)

        load_action = QtGui.QAction("Load Project", self)
        load_action.triggered.connect(self.loadproject)
        file_menu.addAction(load_action)

        save_action = QtGui.QAction("Save Project", self)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        create_ship_action = QtGui.QAction("Create New Ship", self)
        create_ship_action.triggered.connect(self.opensuperluminal2)
        file_menu.addAction(create_ship_action)

        create_node_action = QtGui.QAction("Create Node", self)
        create_node_action.triggered.connect(self.create_node)
        file_menu.addAction(create_node_action)

        # Layouts
        main_widget = QtWidgets.QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QtWidgets.QHBoxLayout()
        main_widget.setLayout(main_layout)
        left_layout = QtWidgets.QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Widgets
        self.node_list = NodeList(self)
        left_widget = QtWidgets.QWidget()
        self.splitter = QtWidgets.QSplitter()
        self.node_widget = NodeWidget(self)
        self.inspector_panel = NodeInspector()

        # Add Widgets to layouts
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(self.node_widget)
        self.splitter.addWidget(self.inspector_panel)
        left_widget.setLayout(left_layout)
        left_layout.addWidget(self.node_list)
        main_layout.addWidget(self.splitter)

        compilea = QtGui.QAction("Compile to xml format", self)
        compilea.triggered.connect(self.compile_to_ftl)
        file_menu.addAction(compilea)

        # Load the example project
        self.project_path = Path(__file__).parent.resolve() / "nodes"
        
        self.load_project(self.project_path, loadscene=False)

        # Restore GUI from last state
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))

            s = settings.value("splitterSize")
            self.splitter.restoreState(s)

    
    def convert_json_to_xml(self, json_data):
        event = Element('event', {'name': json_data['connections'][0]['start_id'], 'unique': 'true'})
        
        for node in json_data['nodes']:
            if node['type'] == 'event_Node':
                event_text = node['internal-data']['text']
                text_element = SubElement(event, 'text')
                text_element.text = event_text
            
            elif node['type'] == 'choice_Node':
                choice_element = SubElement(event, 'choice')
                choice_text = None
                
                for connection in json_data['connections']:
                    if connection['start_id'] == node['uuid']:
                        for node in json_data['nodes']:
                            if node['uuid'] == connection['end_id']:
                                choice_text = node['internal-data']['text']
                                text_element = SubElement(choice_element, 'text')
                                text_element.text = choice_text
                                break
                            
                if choice_text:
                    event_element = SubElement(choice_element, 'event')
                    # find the connected nodes for this choice
                    for connection in json_data['connections']:
                        if connection['start_id'] == node['uuid']:
                            for node in json_data['nodes']:
                                if node['uuid'] == connection['end_id']:
                                    self.convert_node_to_xml(node, event_element, json_data)
                                    break
                            break
                        
        return tostring(event, encoding='unicode')
    
    def convert_node_to_xml(self, node, parent_element, json_data):
        if node['type'] == 'text_Node':
            text_element = SubElement(parent_element, 'text')
            text_element.text = node['internal-data']['text']
        
        elif node['type'] == 'playsound_Node':
            playsound_element = SubElement(parent_element, 'playsound_Node')
        
        elif node['type'] == 'loadship_Node':
            ship_element = SubElement(parent_element, 'ship', {'name': node['internal-data']['text'], 'auto_blueprint': node['internal-data']['text']})
            SubElement(parent_element, 'ship', {'load': node['internal-data']['text'], 'hostile': str(node['internal-data']['ishostile'])})
        
        elif node['type'] == 'Reward_Node':
            reward_element = SubElement(parent_element, 'Reward_Node', {'amount': str(node['internal-data']['amount']), 'index': str(node['internal-data']['index'])})



    def compile_to_ftl(self):
        scene = self.node_widget.save_project()
        #path = tempfile.mktemp()
        #jsonv = []
        #with open(path, "w+") as f:
        #    json.dump(scene, f, indent=4)
        #    jsonv = f.readlines()
        #os.remove(path)
       # print(scene)
       
        print(self.convert_json_to_xml(scene))
        # TODO: somehow convert {'nodes': [{'type': 'choice_Node', 'x': 5155, 'y': 4866, 'uuid': '2228cbfa-8029-478c-9d62-dc4685a866ae', 'internal-data': {}}, {'type': 'event_Node', 'x': 4817, 'y': 4913, 'uuid': '23e4b45c-461f-4a65-a112-5af01b77df81', 'internal-data': {'text': 'example', 'isunique': True}}, {'type': 'text_Node', 'x': 4973, 'y': 4869, 'uuid': 'a0e8222a-ff19-498f-8c29-93e2f4257e2b', 'internal-data': {'text': 'A zoltan ship hails you'}}, {'type': 'text_Node', 'x': 5380, 'y': 4778, 'uuid': '70ca10c1-dbe8-4673-9e5c-3dce08666aa6', 'internal-data': {'text': 'Tell them about your mission and ask for supplies'}}, {'type': 'text_Node', 'x': 5353, 'y': 4952, 'uuid': '11e6b28e-0473-487f-8480-0069fd412c47', 'internal-data': {'text': 'attack!'}}, {'type': 'playsound_Node', 'x': 5514, 'y': 4927, 'uuid': 'a3e094c7-a188-443e-8a72-b4dd6199f1eb', 'internal-data': {}}, {'type': 'loadsound_Node', 'x': 5348, 'y': 5098, 'uuid': 'bf6b87c6-1d23-4a20-b5a8-34ccd36ffdf1', 'internal-data': {'filepath': ''}}, {'type': 'loadship_Node', 'x': 5699, 'y': 4947, 'uuid': 'b73ad069-3b0f-49ee-aca9-9af33beee56c', 'internal-data': {'text': 'enemy-zoltan', 'ishostile': True}}, {'type': 'text_Node', 'x': 5551, 'y': 4751, 'uuid': '4142a167-4f62-469a-967a-6814ca3c4fc3', 'internal-data': {'text': 'They give you some supplies to help you on your quest'}}, {'type': 'Reward_Node', 'x': 5734, 'y': 4725, 'uuid': '468cf1dc-4d15-46a9-958f-1b27b7353820', 'internal-data': {'amount': 20, 'index': 0}}], 'connections': [{'start_id': '4142a167-4f62-469a-967a-6814ca3c4fc3', 'end_id': '468cf1dc-4d15-46a9-958f-1b27b7353820', 'start_pin': 'Ex Out', 'end_pin': 'Input'}, {'start_id': 'a3e094c7-a188-443e-8a72-b4dd6199f1eb', 'end_id': 'b73ad069-3b0f-49ee-aca9-9af33beee56c', 'start_pin': 'Ex Out', 'end_pin': 'Ex In'}, {'start_id': 'bf6b87c6-1d23-4a20-b5a8-34ccd36ffdf1', 'end_id': 'a3e094c7-a188-443e-8a72-b4dd6199f1eb', 'start_pin': 'Audio', 'end_pin': 'AudioFile'}, {'start_id': '11e6b28e-0473-487f-8480-0069fd412c47', 'end_id': 'a3e094c7-a188-443e-8a72-b4dd6199f1eb', 'start_pin': 'Ex Out', 'end_pin': 'Ex In'}, {'start_id': '70ca10c1-dbe8-4673-9e5c-3dce08666aa6', 'end_id': '4142a167-4f62-469a-967a-6814ca3c4fc3', 'start_pin': 'Ex Out', 'end_pin': 'Ex In'}, {'start_id': '23e4b45c-461f-4a65-a112-5af01b77df81', 'end_id': 'a0e8222a-ff19-498f-8c29-93e2f4257e2b', 'start_pin': 'event_contain', 'end_pin': 'Ex In'}, {'start_id': 'a0e8222a-ff19-498f-8c29-93e2f4257e2b', 'end_id': '2228cbfa-8029-478c-9d62-dc4685a866ae', 'start_pin': 'Ex Out', 'end_pin': 'Ex In'}, {'start_id': '2228cbfa-8029-478c-9d62-dc4685a866ae', 'end_id': '70ca10c1-dbe8-4673-9e5c-3dce08666aa6', 'start_pin': 'Choice Output0', 'end_pin': 'Ex In'}, {'start_id': '2228cbfa-8029-478c-9d62-dc4685a866ae', 'end_id': '11e6b28e-0473-487f-8480-0069fd412c47', 'start_pin': 'Choice Output1', 'end_pin': 'Ex In'}]} to ftl xml format

    def save_project(self):
        print(self.node_widget.scene.items())
        file_dialog = QtWidgets.QFileDialog()
        file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        file_dialog.setDefaultSuffix("FTL-NODE-SCRIPT")
        file_dialog.setNameFilter("FTL-NODES-SCRIPT files (*.FTL-NODES-SCRIPT)")
        file_path, _ = file_dialog.getSaveFileName(caption="Save project", dir=str(self.project_path.absolute()), filter="FTL-NODES-SCRIPT files (*.FTL-NODES-SCRIPT)")
        self.node_widget.save_project(file_path)

    def load_project(self, project_path=None, loadscene=True, loadfile=None):
        if not project_path:
            return

        project_path = Path(project_path)
        if project_path.exists() and project_path.is_dir():
            self.project_path = project_path

            self.imports = {}

            for file in project_path.glob("*.py"):
                if not file.stem.endswith("_node"):
                    print("file:", file.stem)
                    continue
                spec = importlib.util.spec_from_file_location(file.stem, file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for name, obj in inspect.getmembers(module):
                    if not name.endswith("_Node"):
                        continue
                    if inspect.isclass(obj):
                        self.imports[obj.__name__] = {"class": obj, "module": module}
            if not loadfile:
                self.node_list.update_project(self.imports)

            # work on just the first json file. add the ability to work on multiple json files later
            if loadscene:
                for json_path in project_path.glob("*.json"):
                    self.node_widget.load_scene(json_path, self.imports)
                    break
            elif loadfile:
                self.node_widget.load_scene(loadfile, self.imports)

    def get_project_path(self):
        project_path = QtWidgets.QFileDialog.getExistingDirectory(
            None, "Select Project Folder", ""
        )
        if not project_path:
            return

        #self.load_project(project_path)
        
    def loadproject(self, returnname = False):
        file_dialog = QtWidgets.QFileDialog()
        #file_dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        #file_dialog.setDirectory()
        file_dialog.setDefaultSuffix("FTL-NODE-SCRIPT")
        #file_dialog.setNameFilter()
        file_path, _ = file_dialog.getOpenFileName(caption="Select project to load or click cancel", dir=str(self.project_path.absolute()), filter="FTL-NODES-SCRIPT files (*.FTL-NODES-SCRIPT)")
        
        self.load_project(self.project_path, loadscene=False, loadfile = file_path)
        
        if returnname:
            return Path(file_path).name

    def closeEvent(self, event):
        """
        Handles the close event by saving the GUI state and closing the application.

        Args:
            event: Close event.

        Returns:
            None.
        """

        # debugging lets save the scene:
        # self.node_widget.save_project("C:/Users/Howard/simple-node-editor/Example_Project/test.json")

        self.settings = QtCore.QSettings("node-editor", "NodeEditor")
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("splitterSize", self.splitter.saveState())
        QtWidgets.QWidget.closeEvent(self, event)

    def create_node(self):
        dialog = NodeCreationDialog(self)
        if dialog.exec_():
            node, filepath = dialog.create_node()
            if node:
                self.load_project(self.project_path, False)

    def opensuperluminal2(self):
        """ "This function opens the Superluminal 2 software and returns a message indicating whether the software was successfully opened or not.
        Parameters:
            - self (object): The object instance of the Superluminal 2 software.
        Returns:
            - str: A message indicating whether the software was successfully opened or not.
        Processing Logic:
            - Checks if the Superluminal 2 software is installed.
            - If installed, opens the software.
            - If not installed, returns an error message.
            - If successfully opened, returns a success message."""
        pass  # wont work for some reason


class NodeCreationDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Create New Node")
        layout = QtWidgets.QVBoxLayout()

        self.name_label = QtWidgets.QLabel("Node Name:")
        self.name_edit = QtWidgets.QLineEdit()
        self.type_label = QtWidgets.QLabel("Node Type:")
        self.type_edit = QtWidgets.QLineEdit()

        self.create_button = QtWidgets.QPushButton("Create")
        self.create_button.clicked.connect(self.accept)

        layout.addWidget(self.name_label)
        layout.addWidget(self.name_edit)
        layout.addWidget(self.type_label)
        layout.addWidget(self.type_edit)
        layout.addWidget(self.create_button)

        self.setLayout(layout)

    def create_node(self):
        # node_type = self.type_combo.currentText()
        node_name = self.name_edit.text()
        node_type = self.type_edit.text()

        node = base_node(node_name, node_type)  # , filename=node_name+r"_node.py")

        return node, r"/node" + node_name + r"_node.py"


class NodeInspector(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Node Inspector")
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        self.node = None

    def inspect_node(self, node):
        self.clear_inspector()
        self.node = node
        # Add inspector widgets based on the type of node

    def clear_inspector(self):
        self.node = None
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()


from node_editor.node import Node


class base_node(Node):
    def __init__(self, title, type):
        super().__init__()

        self.title_text = title
        self.type_text = type
        self.set_color(title_color=(0, 128, 0))

        self.add_pin(name="Ex In", is_output=False, execution=True)
        self.add_pin(name="Ex Out", is_output=True, execution=True)

        self.build()


class NodeTabWidget(QtWidgets.QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)

        self.plus_button = QtWidgets.QPushButton("+")
        self.plus_button.clicked.connect(self.add_new_tab)
        self.setCornerWidget(self.plus_button, QtCore.Qt.TopLeftCorner)

    def close_tab(self, index):
        widget = self.widget(index)
        if widget:
            widget.deleteLater()
            self.removeTab(index)

    def add_new_tab(self):
        dialog = NewTabDialog(self)
        result = dialog.exec_()
        if result == QtWidgets.QDialog.Accepted:
            tab_type = dialog.get_tab_type()
            if tab_type == "Existing Scene":
                file_dialog = QtWidgets.QFileDialog()
                #file_path, _ = file_dialog.getOpenFileName(caption="Select project to load or click cancel", filter="FTL-NODES-SCRIPT files (*.FTL-NODES-SCRIPT)", dir=str(launcher1.project_path.absolute()))
                new_tab = NodeEditorTab()
                name = new_tab.loadproject(True)
                self.addTab(new_tab, name)
                self.setCurrentIndex(self.indexOf(new_tab))
            elif tab_type == "New Scene":
                new_tab = NodeEditorTab()
                self.addTab(new_tab, "New Project")
                self.setCurrentIndex(self.indexOf(new_tab))
            elif tab_type == "Ship Creator":
                new_tab = ShipBuilderWindow()
                self.addTab(new_tab, "Ship Creator")
                self.setCurrentIndex(self.indexOf(new_tab))


class NewTabDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Tab Options")
        layout = QtWidgets.QVBoxLayout()

        self.radio_existing = QtWidgets.QRadioButton("Load Existing Scene")
        self.radio_new = QtWidgets.QRadioButton("Create New Scene")
        self.radio_ship_builder = QtWidgets.QRadioButton("Ship Creator")
        self.radio_existing.setChecked(True)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(self.radio_existing)
        layout.addWidget(self.radio_new)
        layout.addWidget(self.radio_ship_builder)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def get_tab_type(self):
        if self.radio_existing.isChecked():
            return "Existing Scene"
        elif self.radio_new.isChecked():
            return "New Scene"
        if self.radio_ship_builder.isChecked():
            return "Ship Creator"

class ShipBuilderWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ship Builder")
        self.layout = QtWidgets.QVBoxLayout()

        self.embedded_window = EmbeddedWindow()
        self.layout.addWidget(self.embedded_window)

        self.setLayout(self.layout)


class EmbeddedWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.process = None
        self.embed_process()

    def embed_process(self):
        exe_path = 'shipbuilder\Superluminal Win-32 v2.2.1\superluminal2.exe'
        self.process = subprocess.Popen(exe_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        # Wait for the process to start and get its window handle
        #self.process.wait(3)  # Adjust the timeout as needed
        hwnd = self.find_hwnd(self.process.pid)
        if hwnd:
            self.embed_window(hwnd)
        else:
            print("Failed to get window handle")

    def embed_window(self, hwnd):
        native_window = QtGui.QWindow.fromWinId(int(hwnd))
        if native_window:
            widget_container = QtWidgets.QWidget.createWindowContainer(native_window)
            self.layout.addWidget(widget_container)
            
    def find_hwnd(self, process_id):
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == process_id:
                    hwnds.append(hwnd)
            return True

        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        return hwnds[0] if hwnds else None


if __name__ == "__main__":
    import qdarktheme

    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon("resources\\app.ico"))
    qdarktheme.setup_theme()

    tab_widget = NodeTabWidget()

    launcher1 = NodeEditorTab()
    tab_widget.addTab(launcher1, "Project 1")

    tab_widget.show()
    sys.exit(app.exec())

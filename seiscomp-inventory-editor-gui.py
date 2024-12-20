#!/usr/bin/env python3

import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel, 
                           QPushButton, QFileDialog, QMessageBox, QLineEdit,
                           QFormLayout, QGroupBox, QTabWidget, QStyle, 
                           QStatusBar, QFrame, QSplitter, QMenu, QAction)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIcon, QPalette, QColor
from xml.etree import ElementTree as ET
from pathlib import Path
import copy
import re

class ValidationLineEdit(QLineEdit):
    def __init__(self, validator=None, required=False, parent=None):
        super().__init__(parent)
        self.validator = validator
        self.required = required
        self.textChanged.connect(self.validate)
        self.setStyleSheet("""
            QLineEdit { padding: 5px; border: 1px solid #ccc; border-radius: 3px; }
            QLineEdit:focus { border-color: #66afe9; }
        """)
        
    def validate(self):
        if not self.text() and self.required:
            self.setStyleSheet("QLineEdit { background-color: #ffe6e6; }")
            return False
        if self.validator and self.text():
            if not self.validator(self.text()):
                self.setStyleSheet("QLineEdit { background-color: #ffe6e6; }")
                return False
        self.setStyleSheet("""
            QLineEdit { background-color: white; padding: 5px; border: 1px solid #ccc; border-radius: 3px; }
            QLineEdit:focus { border-color: #66afe9; }
        """)
        return True

class SeisCompInventoryEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ns = {'sc3': 'http://geofon.gfz-potsdam.de/ns/seiscomp3-schema/0.12'}
        self.current_file = None
        self.tree = None
        self.root = None
        self.settings = QSettings('SeisCompEditor', 'InventoryEditor')
        self.unsaved_changes = False
        self.initUI()
        self.loadSettings()

    def initUI(self):
        # Set window properties
        self.setWindowTitle('SeisComP Inventory Editor')
        self.setMinimumSize(800, 600)

        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Create left panel for tree view
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add file controls with icons
        file_controls = QWidget()
        file_layout = QHBoxLayout(file_controls)
        self.load_button = QPushButton('Load XML')
        self.load_button.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.save_button = QPushButton('Save XML')
        self.save_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_button.setEnabled(False)
        file_layout.addWidget(self.load_button)
        file_layout.addWidget(self.save_button)
        left_layout.addWidget(file_controls)

        # Add tree widget with styling
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel('Inventory Structure')
        self.tree_widget.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
            QTreeWidget::item:selected {
                background-color: #e6f3ff;
                color: black;
            }
        """)
        left_layout.addWidget(self.tree_widget)
        
        # Create right panel for editing
        right_panel = QWidget()
        self.right_layout = QVBoxLayout(right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add tabs with styling
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin: 2px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QTabBar::tab:selected {
                background-color: #e6f3ff;
            }
        """)
        
        # Create tabs
        self.station_tab = QWidget()
        self.sensor_tab = QWidget()
        self.datalogger_tab = QWidget()
        self.stream_tab = QWidget()
        
        # Setup tabs
        self.setup_station_tab()
        self.setup_sensor_tab()
        self.setup_datalogger_tab()
        self.setup_stream_tab()
        
        # Add tabs to widget
        self.tab_widget.addTab(self.station_tab, "Station")
        self.tab_widget.addTab(self.sensor_tab, "Sensor")
        self.tab_widget.addTab(self.datalogger_tab, "Datalogger")
        self.tab_widget.addTab(self.stream_tab, "Stream")
        
        self.right_layout.addWidget(self.tab_widget)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        # Add splitter to layout
        layout.addWidget(splitter)

        # Connect signals
        self.load_button.clicked.connect(self.load_xml)
        self.save_button.clicked.connect(self.save_xml)
        self.tree_widget.itemClicked.connect(self.item_selected)
        
        # Create menu bar
        self.createMenuBar()

    def setup_station_tab(self):
        layout = QFormLayout(self.station_tab)
        
        station_group = QGroupBox("Station Information")
        station_layout = QFormLayout()
        
        # Create validated input fields
        self.station_code = ValidationLineEdit(required=True)
        self.station_name = ValidationLineEdit()
        self.station_description = ValidationLineEdit()
        self.station_lat = ValidationLineEdit(
            validator=lambda x: re.match(r'^-?\d*\.?\d*$', x) and -90 <= float(x) <= 90 if x else True
        )
        self.station_lon = ValidationLineEdit(
            validator=lambda x: re.match(r'^-?\d*\.?\d*$', x) and -180 <= float(x) <= 180 if x else True
        )
        self.station_elevation = ValidationLineEdit(
            validator=lambda x: re.match(r'^-?\d*\.?\d*$', x) if x else True
        )
        
        station_layout.addRow("Code:", self.station_code)
        station_layout.addRow("Name:", self.station_name)
        station_layout.addRow("Description:", self.station_description)
        station_layout.addRow("Latitude:", self.station_lat)
        station_layout.addRow("Longitude:", self.station_lon)
        station_layout.addRow("Elevation:", self.station_elevation)
        
        station_group.setLayout(station_layout)
        layout.addWidget(station_group)
        
        # Add update button with styling
        self.update_station_button = QPushButton("Update Station")
        self.update_station_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.update_station_button.clicked.connect(self.update_station)
        layout.addWidget(self.update_station_button)

    def setup_sensor_tab(self):
        layout = QFormLayout(self.sensor_tab)
        
        sensor_group = QGroupBox("Sensor Information")
        sensor_layout = QFormLayout()
        
        self.sensor_name = ValidationLineEdit()
        self.sensor_type = ValidationLineEdit()
        self.sensor_model = ValidationLineEdit()
        self.sensor_manufacturer = ValidationLineEdit()
        self.sensor_serial = ValidationLineEdit()
        
        sensor_layout.addRow("Name:", self.sensor_name)
        sensor_layout.addRow("Type:", self.sensor_type)
        sensor_layout.addRow("Model:", self.sensor_model)
        sensor_layout.addRow("Manufacturer:", self.sensor_manufacturer)
        sensor_layout.addRow("Serial Number:", self.sensor_serial)
        
        sensor_group.setLayout(sensor_layout)
        layout.addWidget(sensor_group)
        
        # Add update button
        self.update_sensor_button = QPushButton("Update Sensor")
        self.update_sensor_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.update_sensor_button.clicked.connect(self.update_sensor)
        layout.addWidget(self.update_sensor_button)

    def setup_datalogger_tab(self):
        layout = QFormLayout(self.datalogger_tab)
        
        datalogger_group = QGroupBox("Datalogger Information")
        datalogger_layout = QFormLayout()
        
        self.datalogger_name = ValidationLineEdit()
        self.datalogger_type = ValidationLineEdit()
        self.datalogger_model = ValidationLineEdit()
        self.datalogger_manufacturer = ValidationLineEdit()
        self.datalogger_serial = ValidationLineEdit()
        
        datalogger_layout.addRow("Name:", self.datalogger_name)
        datalogger_layout.addRow("Type:", self.datalogger_type)
        datalogger_layout.addRow("Model:", self.datalogger_model)
        datalogger_layout.addRow("Manufacturer:", self.datalogger_manufacturer)
        datalogger_layout.addRow("Serial Number:", self.datalogger_serial)
        
        datalogger_group.setLayout(datalogger_layout)
        layout.addWidget(datalogger_group)
        
        # Add update button
        self.update_datalogger_button = QPushButton("Update Datalogger")
        self.update_datalogger_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.update_datalogger_button.clicked.connect(self.update_datalogger)
        layout.addWidget(self.update_datalogger_button)

    def setup_stream_tab(self):
        layout = QFormLayout(self.stream_tab)
        
        stream_group = QGroupBox("Stream/Channel Information")
        stream_layout = QFormLayout()
        
        # Create validated input fields
        self.stream_code = ValidationLineEdit(required=True)
        
        # Time fields
        self.stream_start = ValidationLineEdit()
        self.stream_end = ValidationLineEdit()
        
        # Position fields
        self.stream_depth = ValidationLineEdit(
            validator=lambda x: re.match(r'^-?\d*\.?\d*$', x) if x else True
        )
        self.stream_azimuth = ValidationLineEdit(
            validator=lambda x: re.match(r'^-?\d*\.?\d*$', x) and 0 <= float(x) <= 360 if x else True
        )
        self.stream_dip = ValidationLineEdit(
            validator=lambda x: re.match(r'^-?\d*\.?\d*$', x) and -90 <= float(x) <= 90 if x else True
        )
        
        # Gain and sampling fields
        self.stream_gain = ValidationLineEdit(
            validator=lambda x: re.match(r'^-?\d*\.?\d*$', x) if x else True
        )
        self.stream_sampleRate = ValidationLineEdit(
            validator=lambda x: re.match(r'^\d*\.?\d*$', x) if x else True
        )
        self.stream_gainFrequency = ValidationLineEdit(
            validator=lambda x: re.match(r'^\d*\.?\d*$', x) if x else True
        )
        self.stream_gainUnit = ValidationLineEdit()
        
        # Additional fields
        self.stream_datalogger_serialnumber = ValidationLineEdit()
        self.stream_sensor_serialnumber = ValidationLineEdit()
        self.stream_flags = ValidationLineEdit()
        
        # Add fields to layout
        stream_layout.addRow("Code:", self.stream_code)
        stream_layout.addRow("Start Time:", self.stream_start)
        stream_layout.addRow("End Time:", self.stream_end)
        stream_layout.addRow("Depth (m):", self.stream_depth)
        stream_layout.addRow("Azimuth (°):", self.stream_azimuth)
        stream_layout.addRow("Dip (°):", self.stream_dip)
        stream_layout.addRow("Gain:", self.stream_gain)
        stream_layout.addRow("Sample Rate (Hz):", self.stream_sampleRate)
        stream_layout.addRow("Gain Frequency (Hz):", self.stream_gainFrequency)
        stream_layout.addRow("Gain Unit:", self.stream_gainUnit)
        stream_layout.addRow("Datalogger S/N:", self.stream_datalogger_serialnumber)
        stream_layout.addRow("Sensor S/N:", self.stream_sensor_serialnumber)
        stream_layout.addRow("Flags:", self.stream_flags)
        
        stream_group.setLayout(stream_layout)
        layout.addWidget(stream_group)
        
        # Add update button
        self.update_stream_button = QPushButton("Update Stream")
        self.update_stream_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.update_stream_button.clicked.connect(self.update_stream)
        layout.addWidget(self.update_stream_button)

    def createMenuBar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        open_action = QAction('Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.load_xml)
        file_menu.addAction(open_action)
        
        save_action = QAction('Save', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_xml)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu('Edit')
        
        expand_all_action = QAction('Expand All', self)
        expand_all_action.triggered.connect(self.tree_widget.expandAll)
        edit_menu.addAction(expand_all_action)
        
        collapse_all_action = QAction('Collapse All', self)
        collapse_all_action.triggered.connect(self.tree_widget.collapseAll)
        edit_menu.addAction(collapse_all_action)

    def loadSettings(self):
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)
        windowState = self.settings.value('windowState')
        if windowState:
            self.restoreState(windowState)
        lastDir = self.settings.value('lastDirectory')
        if lastDir:
            self.last_directory = lastDir

    def closeEvent(self, event):
        """Handle application close event"""
        if self.unsaved_changes:
            reply = QMessageBox.question(
                self, 'Save Changes?',
                'There are unsaved changes. Do you want to save before closing?',
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                self.save_xml()
            elif reply == QMessageBox.Cancel:
                event.ignore()
                return
                
        # Save application settings
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowState', self.saveState())
        if hasattr(self, 'last_directory'):
            self.settings.setValue('lastDirectory', self.last_directory)
        
        event.accept()

    def load_xml(self):
        """Load XML file with error handling and validation"""
        try:
            start_dir = getattr(self, 'last_directory', '')
            filename, _ = QFileDialog.getOpenFileName(
                self, "Load SeisComP Inventory",
                start_dir, "XML files (*.xml)"
            )
            
            if filename:
                self.last_directory = str(Path(filename).parent)
                tree = ET.parse(filename)
                root = tree.getroot()
                
                # Validate XML structure
                if not self._validate_xml_structure(root):
                    QMessageBox.warning(
                        self, "Invalid File",
                        "The selected file does not appear to be a valid SeisComP inventory file."
                    )
                    return
                
                self.current_file = filename
                self.tree = tree
                self.root = root
                self.populate_tree()
                self.save_button.setEnabled(True)
                self.statusBar.showMessage(f"Loaded: {filename}", 5000)
                
        except ET.ParseError as e:
            QMessageBox.critical(
                self, "XML Parse Error",
                f"Failed to parse XML file:\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"An unexpected error occurred:\n{str(e)}"
            )

    def _validate_xml_structure(self, root):
        """Validate basic SeisComP XML structure"""
        if root.tag != f'{{{self.ns["sc3"]}}}seiscomp':
            return False
        inventory = root.find('sc3:Inventory', self.ns)
        return inventory is not None

    def save_xml(self):
        if self.current_file and self.tree:
            try:
                # Create backup
                backup_path = Path(self.current_file).with_suffix('.xml.bak')
                Path(self.current_file).rename(backup_path)
                
                # Save new file
                self.tree.write(self.current_file, encoding='utf-8', xml_declaration=True)
                self.unsaved_changes = False
                self.statusBar.showMessage("File saved successfully", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save XML: {str(e)}")
                # Restore backup if exists
                if backup_path.exists():
                    backup_path.rename(self.current_file)

    def populate_tree(self):
        self.tree_widget.clear()
        inventory = self.root.find('sc3:Inventory', self.ns)
        if inventory is None:
            return

        # Add networks
        for network in inventory.findall('.//sc3:network', self.ns):
            network_item = QTreeWidgetItem(self.tree_widget)
            network_item.setText(0, f"Network: {network.get('code', '')}")
            network_item.setData(0, Qt.UserRole, ('network', network))
            
            # Add stations
            for station in network.findall('.//sc3:station', self.ns):
                station_item = QTreeWidgetItem(network_item)
                station_item.setText(0, f"Station: {station.get('code', '')}")
                station_item.setData(0, Qt.UserRole, ('station', station))
                
                # Add sensor locations
                for location in station.findall('.//sc3:sensorLocation', self.ns):
                    location_item = QTreeWidgetItem(station_item)
                    location_item.setText(0, f"Location: {location.get('code', '')}")
                    location_item.setData(0, Qt.UserRole, ('location', location))

                    # Add streams under location
                    for stream in location.findall('sc3:stream', self.ns):
                        stream_item = QTreeWidgetItem(location_item)
                        stream_item.setText(0, f"Stream: {stream.get('code', '')}")
                        stream_item.setData(0, Qt.UserRole, ('stream', stream))

        # Add sensors and dataloggers sections
        sensors = inventory.findall('.//sc3:sensor', self.ns)
        if sensors:
            sensors_item = QTreeWidgetItem(self.tree_widget)
            sensors_item.setText(0, "Sensors")
            for sensor in sensors:
                sensor_item = QTreeWidgetItem(sensors_item)
                sensor_item.setText(0, f"Sensor: {sensor.get('name', '')}")
                sensor_item.setData(0, Qt.UserRole, ('sensor', sensor))

        dataloggers = inventory.findall('.//sc3:datalogger', self.ns)
        if dataloggers:
            dataloggers_item = QTreeWidgetItem(self.tree_widget)
            dataloggers_item.setText(0, "Dataloggers")
            for datalogger in dataloggers:
                datalogger_item = QTreeWidgetItem(dataloggers_item)
                datalogger_item.setText(0, f"Datalogger: {datalogger.get('name', '')}")
                datalogger_item.setData(0, Qt.UserRole, ('datalogger', datalogger))

    def _get_element_text(self, element, tag, default=''):
        """Helper method to get element text with namespace and default value"""
        elem = element.find(f'sc3:{tag}', self.ns)
        return elem.text if elem is not None else default

    def _update_element_text(self, element, tag, value):
        """Helper method to update element text with namespace"""
        elem = element.find(f'sc3:{tag}', self.ns)
        if elem is None:
            if value:  # Only create new elements for non-empty values
                elem = ET.SubElement(element, f'{{{self.ns["sc3"]}}}{tag}')
        if value:
            elem.text = value
        elif elem is not None:
            element.remove(elem)  # Remove element if value is empty

    def update_station(self):
        if hasattr(self, 'current_element'):
            try:
                # Only set attributes if they have non-empty values
                if self.station_code.text():
                    self.current_element.set('code', self.station_code.text())
                if self.station_name.text():
                    self.current_element.set('name', self.station_name.text())
                elif 'name' in self.current_element.attrib:
                    del self.current_element.attrib['name']  # Remove empty name attribute
                    
                # Update element texts
                self._update_element_text(self.current_element, 'description', self.station_description.text())
                self._update_element_text(self.current_element, 'latitude', self.station_lat.text())
                self._update_element_text(self.current_element, 'longitude', self.station_lon.text())
                self._update_element_text(self.current_element, 'elevation', self.station_elevation.text())
                
                self.populate_tree()
                self.unsaved_changes = True
                self.statusBar.showMessage("Station updated successfully", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update station: {str(e)}")


    def update_sensor(self):
        if hasattr(self, 'current_element'):
            try:
                self.current_element.set('name', self.sensor_name.text())
                self._update_element_text(self.current_element, 'type', self.sensor_type.text())
                self._update_element_text(self.current_element, 'model', self.sensor_model.text())
                self._update_element_text(self.current_element, 'manufacturer', self.sensor_manufacturer.text())
                self._update_element_text(self.current_element, 'serialNumber', self.sensor_serial.text())
                self.populate_tree()
                self.unsaved_changes = True
                self.statusBar.showMessage("Sensor updated successfully", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update sensor: {str(e)}")

    def update_datalogger(self):
        if hasattr(self, 'current_element'):
            try:
                self.current_element.set('name', self.datalogger_name.text())
                self._update_element_text(self.current_element, 'type', self.datalogger_type.text())
                self._update_element_text(self.current_element, 'model', self.datalogger_model.text())
                self._update_element_text(self.current_element, 'manufacturer', self.datalogger_manufacturer.text())
                self._update_element_text(self.current_element, 'serialNumber', self.datalogger_serial.text())
                self.populate_tree()
                self.unsaved_changes = True
                self.statusBar.showMessage("Datalogger updated successfully", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update datalogger: {str(e)}")

    def update_stream(self):
        if hasattr(self, 'current_element'):
            try:
                # Update basic attributes
                self.current_element.set('code', self.stream_code.text())
                
                # Update time fields
                self._update_element_text(self.current_element, 'start', self.stream_start.text())
                self._update_element_text(self.current_element, 'end', self.stream_end.text())
                
                # Update position fields
                self._update_element_text(self.current_element, 'depth', self.stream_depth.text())
                self._update_element_text(self.current_element, 'azimuth', self.stream_azimuth.text())
                self._update_element_text(self.current_element, 'dip', self.stream_dip.text())
                
                # Update gain and sampling fields
                self._update_element_text(self.current_element, 'gain', self.stream_gain.text())
                
                # Handle sample rate conversion
                try:
                    sample_rate = float(self.stream_sampleRate.text())
                    self._update_element_text(self.current_element, 'sampleRateNumerator', str(int(sample_rate)))
                    self._update_element_text(self.current_element, 'sampleRateDenominator', '1')
                except (ValueError, TypeError):
                    pass
                
                self._update_element_text(self.current_element, 'gainFrequency', self.stream_gainFrequency.text())
                self._update_element_text(self.current_element, 'gainUnit', self.stream_gainUnit.text())
                
                # Update additional fields
                self._update_element_text(self.current_element, 'dataloggerSerialNumber', self.stream_datalogger_serialnumber.text())
                self._update_element_text(self.current_element, 'sensorSerialNumber', self.stream_sensor_serialnumber.text())
                self._update_element_text(self.current_element, 'flags', self.stream_flags.text())
                
                self.populate_tree()
                self.unsaved_changes = True
                self.statusBar.showMessage("Stream updated successfully", 5000)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update stream: {str(e)}")

    def item_selected(self, item):
        if not item:
            return
            
        item_type, element = item.data(0, Qt.UserRole)
        self.current_element = element
        
        if item_type == 'station':
            self.tab_widget.setCurrentWidget(self.station_tab)
            self.populate_station_fields(element)
        elif item_type == 'sensor':
            self.tab_widget.setCurrentWidget(self.sensor_tab)
            self.populate_sensor_fields(element)
        elif item_type == 'datalogger':
            self.tab_widget.setCurrentWidget(self.datalogger_tab)
            self.populate_datalogger_fields(element)
        elif item_type == 'stream':
            self.tab_widget.setCurrentWidget(self.stream_tab)
            self.populate_stream_fields(element)

    def populate_station_fields(self, station):
        self.station_code.setText(station.get('code', ''))
        self.station_name.setText(station.get('name', ''))
        self.station_description.setText(self._get_element_text(station, 'description'))
        self.station_lat.setText(self._get_element_text(station, 'latitude'))
        self.station_lon.setText(self._get_element_text(station, 'longitude'))
        self.station_elevation.setText(self._get_element_text(station, 'elevation'))

    def populate_sensor_fields(self, sensor):
        self.sensor_name.setText(sensor.get('name', ''))
        self.sensor_type.setText(self._get_element_text(sensor, 'type'))
        self.sensor_model.setText(self._get_element_text(sensor, 'model'))
        self.sensor_manufacturer.setText(self._get_element_text(sensor, 'manufacturer'))
        self.sensor_serial.setText(self._get_element_text(sensor, 'serialNumber'))

    def populate_datalogger_fields(self, datalogger):
        self.datalogger_name.setText(datalogger.get('name', ''))
        self.datalogger_type.setText(self._get_element_text(datalogger, 'type'))
        self.datalogger_model.setText(self._get_element_text(datalogger, 'model'))
        self.datalogger_manufacturer.setText(self._get_element_text(datalogger, 'manufacturer'))
        self.datalogger_serial.setText(self._get_element_text(datalogger, 'serialNumber'))

    def populate_stream_fields(self, stream):
        # Basic attributes
        self.stream_code.setText(stream.get('code', ''))
        
        # Time fields
        self.stream_start.setText(self._get_element_text(stream, 'start'))
        self.stream_end.setText(self._get_element_text(stream, 'end'))
        
        # Position fields
        self.stream_depth.setText(self._get_element_text(stream, 'depth'))
        self.stream_azimuth.setText(self._get_element_text(stream, 'azimuth'))
        self.stream_dip.setText(self._get_element_text(stream, 'dip'))
        
        # Gain and sampling fields
        self.stream_gain.setText(self._get_element_text(stream, 'gain'))
        
        # Calculate sample rate from numerator/denominator
        numerator = self._get_element_text(stream, 'sampleRateNumerator', '0')
        denominator = self._get_element_text(stream, 'sampleRateDenominator', '1')
        try:
            sample_rate = float(numerator) / float(denominator)
            self.stream_sampleRate.setText(str(sample_rate))
        except (ValueError, ZeroDivisionError):
            self.stream_sampleRate.setText('')
        
        self.stream_gainFrequency.setText(self._get_element_text(stream, 'gainFrequency'))
        self.stream_gainUnit.setText(self._get_element_text(stream, 'gainUnit'))
        
        # Additional fields
        self.stream_datalogger_serialnumber.setText(self._get_element_text(stream, 'dataloggerSerialNumber'))
        self.stream_sensor_serialnumber.setText(self._get_element_text(stream, 'sensorSerialNumber'))
        self.stream_flags.setText(self._get_element_text(stream, 'flags'))

def main():
    app = QApplication(sys.argv)
    
    # Set application-wide style
    app.setStyle('Fusion')
    
    # Set color palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    app.setPalette(palette)
    
    editor = SeisCompInventoryEditor()
    editor.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
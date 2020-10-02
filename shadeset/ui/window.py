# -*- coding: utf-8 -*-

# Local imports
from . import res
from .widgets import (
    ConfigForm,
    ExportForm,
    ImportForm,
    WindowHeader,
)

# Third party imports
from .Qt import QtWidgets
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
from maya import OpenMayaUI

# Compatability
try:
    long
except NameError:
    long = int


class ShadesetUI(MayaQWidgetDockableMixin, QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super(ShadesetUI, self).__init__(*args, **kwargs)

        self.header = WindowHeader(img=res.get_path('shadesets.png'))
        self.tabs = QtWidgets.QTabWidget(self)
        self.tabs.setDocumentMode(True)
        tabs_bar = self.tabs.tabBar()
        tabs_bar.setDrawBase(False)
        tabs_bar.setExpanding(True)
        self.import_tab = ImportForm(self.tabs)
        self.export_tab = ExportForm(self.tabs)
        self.config_tab = ConfigForm(self.tabs)
        self.config_tab.config_changed.connect(self.on_config_changed)
        self.tabs.addTab(self.import_tab, 'Import')
        self.tabs.addTab(self.export_tab, 'Export')
        self.tabs.addTab(self.config_tab, 'Config')
        self.tabs.currentChanged.connect(self.on_tab_changed)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.header)
        layout.addWidget(self.tabs)

        self.setLayout(layout)
        self.setWindowTitle('Shadesets')
        self.setStyleSheet(open(res.get_path('style.css')).read())

    def on_tab_changed(self, index):
        if index == 0:
            self.import_tab.update_form()
        elif index == 1:
            self.export_tab.update_form()
        else:
            self.config_tab.update_form()

    def on_config_changed(self):
        pass


def show(cache={}, restore=False):
    if 'window' not in cache:
        cache['window'] = ShadesetUI()
        workspace_control = OpenMayaUI.MQtUtil.getCurrentParent()
        pointer = OpenMayaUI.MQtUtil.findControl(cache['window'].objectName())
        OpenMayaUI.MQtUtil.addWidgetToMayaLayout(
            long(pointer),
            long(workspace_control),
        )

    if not restore:
        cache['window'].show(
            dockable=True,
            uiScript='import shadeset.ui;shadeset.ui.show(restore=True)'
        )

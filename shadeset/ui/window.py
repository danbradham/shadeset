# -*- coding: utf-8 -*-

# Local imports
from .. import lib
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

    _instance = None

    def __init__(self, *args, **kwargs):
        super(ShadesetUI, self).__init__(*args, **kwargs)

        self.header = WindowHeader(img=res.get_path('shadesets.png'))
        self.tabs = QtWidgets.QTabWidget(self)
        self.tabs.setDocumentMode(True)
        tabs_bar = self.tabs.tabBar()
        tabs_bar.setDrawBase(False)
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


def restore():
    '''Called when Maya opens to restore the Shadeset UI.'''

    # Set initial state
    if not lib.session['project']:
        lib.session['project'] = lib.guess_project()

    workspace_control = OpenMayaUI.MQtUtil.getCurrentParent()
    ShadesetUI._instance = ShadesetUI()
    pointer = OpenMayaUI.MQtUtil.findControl(ShadesetUI._instance.objectName())
    OpenMayaUI.MQtUtil.addWidgetToMayaLayout(
        long(pointer),
        long(workspace_control),
    )


def show(**kwargs):
    '''Show the Shadeset UI.'''

    if ShadesetUI._instance is None:

        # Set initial state
        if not lib.session['project']:
            lib.session['project'] = lib.guess_project()

        ShadesetUI._instance = ShadesetUI()

    ShadesetUI._instance.show(
        dockable=True,
        uiScript='import shadeset.ui.window; shadeset.ui.window.restore()'
    )

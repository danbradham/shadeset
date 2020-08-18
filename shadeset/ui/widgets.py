# -*- coding: utf-8 -*-
from __future__ import print_function

# Standard library imports
import os
from fnmatch import fnmatch

# Local imports
from . import res
from .. import api, lib, utils

# Third party imports
from Qt import QtCore, QtGui, QtWidgets


class WindowHeader(QtWidgets.QLabel):

    def __init__(self, img, parent=None):
        super(WindowHeader, self).__init__(parent)
        self.setObjectName("WindowHeader")
        self.setPixmap(QtGui.QPixmap(QtGui.QImage(img)))


class ExportForm(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(ExportForm, self).__init__(parent=parent)

        self.asset = QtWidgets.QListWidget()
        self.asset.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding
        )
        self.suffix = QtWidgets.QLineEdit()
        self.preview = QtWidgets.QLabel()
        self.selection = QtWidgets.QCheckBox('Selected &Hierarchies')
        self.selection.setChecked(True)
        self.render_layers = QtWidgets.QCheckBox('&Render Layers')
        self.export_button = QtWidgets.QPushButton('&Export Shadeset')
        self.attr_prefixes_label = QtWidgets.QLabel('Attribute Prefixes')
        self.attr_prefixes_label.setToolTip(
            'Space separated list of attribute prefixes to include in export.'
        )
        self.attr_prefixes = QtWidgets.QLineEdit()
        self.attr_prefixes.setText(' '.join(lib.get_export_attr_prefixes()))
        self.attrs_label = QtWidgets.QLabel('Attributes')
        self.attrs_label.setToolTip(
            'Space separated list of attributes to include in export.'
        )
        self.attrs = QtWidgets.QLineEdit()
        self.attrs.setText(' '.join(lib.get_export_attrs()))

        options = QtWidgets.QGroupBox()
        options_layout = QtWidgets.QVBoxLayout()
        options_layout.addWidget(self.selection)
        options_layout.addWidget(self.render_layers)
        options_layout.addWidget(self.attr_prefixes_label)
        options_layout.addWidget(self.attr_prefixes)
        options_layout.addWidget(self.attrs_label)
        options_layout.addWidget(self.attrs)
        options.setLayout(options_layout)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.addWidget(QtWidgets.QLabel('Asset'))
        self.layout.addWidget(self.asset)
        self.layout.addWidget(QtWidgets.QLabel('Suffix'))
        self.layout.addWidget(self.suffix)
        self.layout.addWidget(self.preview)
        self.layout.addWidget(options)
        self.layout.addWidget(self.export_button)
        self.setLayout(self.layout)

        self.export_button.clicked.connect(self.export)
        self.asset.currentItemChanged.connect(self.update_preview)
        self.suffix.textChanged.connect(self.update_preview)

        self.update_form()
        self.update_preview()

    def state(self):
        asset_item = self.asset.currentItem()
        asset = None
        if asset_item:
            asset = asset_item.asset

        return dict(
            asset=asset,
            suffix=self.suffix.text(),
            selection=self.selection.isChecked(),
            render_layers=self.render_layers.isChecked(),
            attr_prefixes=self.attr_prefixes.text().split(),
            attrs=self.attrs.text().split()
        )

    def add_asset(self, asset):
        item = QtWidgets.QListWidgetItem()
        item.setText(asset['asset'])
        item.asset = asset
        self.asset.addItem(item)

    def update_form(self):
        self.asset.clear()
        assets = lib.get_assets(lib.session['project'])
        for _, asset in sorted(assets.items()):
            self.add_asset(asset)

    def update_preview(self):
        state = self.state()
        if not state['asset']:
            self.preview.setText('Select an asset...')
            return

        name = state['asset']['asset']
        if state['suffix']:
            name += '_' + state['suffix']

        next_publish = lib.get_next_publish(state['asset'], name)
        self.preview.setText(next_publish['basename'])

    def export(self):
        # TODO: move to controller

        state = self.state()

        # Update export attribute settings
        # These are used by CustomAttributesSet
        lib.set_export_attrs(state['attrs'])
        lib.set_export_attr_prefixes(state['attr_prefixes'])

        if not state['asset']:
            self.preview.setText('Select an asset...')
            return

        if state['selection']:
            ss = api.gather_hierarchy(render_layers=state['render_layers'])
        else:
            ss = api.gather(
                selection=state['selection'],
                render_layers=state['render_layers'],
            )

        name = state['asset']['asset']
        if state['suffix']:
            name += '_' + state['suffix']

        next_publish = lib.get_next_publish(state['asset'], name)
        ss.export(
            outdir=next_publish['dirname'],
            name=next_publish['basename'].rsplit('.', 1)[0],
        )


class ImportForm(QtWidgets.QWidget):

    def __init__(self, parent=None):

        super(ImportForm, self).__init__(parent=parent)

        self.project = QtWidgets.QComboBox()
        self.project.setSizeAdjustPolicy(
            self.project.AdjustToMinimumContentsLengthWithIcon
        )
        self.asset = QtWidgets.QListWidget()
        self.shadeset = QtWidgets.QListWidget()
        self.selection = QtWidgets.QCheckBox('Selected &Hierarchies')
        self.selection.setChecked(True)
        self.render_layers = QtWidgets.QCheckBox('&Render Layers')
        self.apply_button = QtWidgets.QPushButton('&Apply Shadeset')

        options = QtWidgets.QGroupBox()
        options_layout = QtWidgets.QVBoxLayout()
        options_layout.addWidget(self.selection)
        options_layout.addWidget(self.render_layers)
        options.setLayout(options_layout)

        self.layout = QtWidgets.QGridLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setHorizontalSpacing(20)
        self.layout.setRowStretch(3, 1)
        self.layout.addWidget(QtWidgets.QLabel('Project'), 0, 0)
        self.layout.addWidget(self.project, 1, 0)
        self.layout.addWidget(QtWidgets.QLabel('Asset'), 2, 0)
        self.layout.addWidget(self.asset, 3, 0)
        self.layout.addWidget(QtWidgets.QLabel('ShadeSet'), 2, 1)
        self.layout.addWidget(self.shadeset, 3, 1)
        self.layout.addWidget(options, 4, 1)
        self.layout.addWidget(self.apply_button, 5, 1)
        self.setLayout(self.layout)

        self.apply_button.clicked.connect(self.apply)
        self.project.activated.connect(self.on_project_changed)
        self.asset.currentItemChanged.connect(self.on_asset_changed)

        self._projects = None
        self.update_form()

    def state(self):
        # Get selected project
        project = self.project.currentText()

        # Get selected asset
        asset_item = self.asset.currentItem()
        asset = None
        if asset_item:
            asset = asset_item.asset

        # Get selected shadeset
        shadeset_item = self.shadeset.currentItem()
        shadeset = None
        if shadeset_item:
            shadeset = shadeset_item.publish

        return dict(
            project=project,
            asset=asset,
            shadeset=shadeset,
            selection=self.selection.isChecked(),
            render_layers=self.render_layers.isChecked(),
        )

    def update_form(self):
        self.project.blockSignals(True)
        self.project.clear()
        for project in sorted(lib.get_projects()):
            self.project.addItem(project)
        self.project.blockSignals(False)

        if lib.session['project']:
            index = self.project.findText(lib.session['project'])
            if index:
                self.project.setCurrentIndex(index)

        self.update_asset_widget()

    def add_asset(self, asset):
        item = QtWidgets.QListWidgetItem()
        item.setText(asset['asset'])
        item.asset = asset
        self.asset.addItem(item)

    def on_project_changed(self):
        project = self.project.currentText()
        lib.set_project(project)
        self.update_asset_widget()

    def update_asset_widget(self):
        self.asset.clear()
        assets = lib.get_assets(lib.session['project'])
        for _, asset in sorted(assets.items()):
            self.add_asset(asset)

    def on_asset_changed(self):
        self.update_shadeset_widget()

    def add_shadeset(self, publish):
        item = QtWidgets.QListWidgetItem()
        item.setText(publish['basename'].rsplit('.', 1)[0])
        item.publish = publish
        self.shadeset.addItem(item)

    def update_shadeset_widget(self):
        self.shadeset.clear()

        state = self.state()
        if state['asset']:
            publishes = lib.get_publishes(state['asset'])
            for name, versions in sorted(publishes.items()):
                for version, publish in sorted(versions.items()):
                    self.add_shadeset(publish)

    def apply(self):
        # TODO: Move to controller

        from maya import cmds
        state = self.state()
        publish = state['shadeset']

        layer = cmds.editRenderLayerGlobals(q=True, crl=True)
        if not layer == 'defaultRenderLayer':
            # TODO log an error and return instead
            raise Exception('You must be in the masterLayer to apply '
                            'a shadeset.')

        reference_shadeset = True
        pattern = publish['path'].split('.')[0] + '*_shadingGroups.mb'
        shaders_path = publish['path'].replace('.yml', '_shadingGroups.mb')
        norm_path = os.path.normpath(shaders_path)
        file_name = os.path.basename(norm_path)

        for ref in cmds.ls(references=True):
            # Ignore loose reference nodes
            try:
                ref_path = cmds.referenceQuery(ref, filename=True)
                ref_path = ref_path.split('{')[0]
            except RuntimeError as e:
                if "not associated with a reference file" in str(e):
                    continue
                raise

            ref_name = os.path.basename(ref_path)
            if norm_path == os.path.normpath(ref_path):
                response = QtWidgets.QMessageBox.question(
                    self,
                    'Reapply shadeset...',
                    'Reapply {} ?'.format(file_name),
                    QtWidgets.QMessageBox.Yes,
                    QtWidgets.QMessageBox.No,
                )
                if response == QtWidgets.QMessageBox.No:
                    return

                sel = cmds.ls(sl=True, long=True)
                cmds.file(ref_path, loadReference=ref)
                cmds.select(sel, replace=True)
                reference_shadeset = False

            elif fnmatch(ref_path, pattern):

                response = QtWidgets.QMessageBox.question(
                    self,
                    'Replace shadeset...',
                    'Replace {} with {}?'.format(ref_name, file_name),
                    QtWidgets.QMessageBox.Yes,
                    QtWidgets.QMessageBox.No,
                )
                if response == QtWidgets.QMessageBox.No:
                    return

                sel = cmds.ls(sl=True, long=True)
                utils.update_reference(
                    ref_node=ref,
                    in_file=shaders_path,
                    namespace='sg'
                )
                cmds.select(sel, replace=True)
                reference_shadeset = False

        ss = api.load(publish['path'])
        if reference_shadeset:
            ss.reference()

        ss.apply(
            selection=state['selection'],
            render_layers=state['render_layers'],
        )


class ConfigForm(QtWidgets.QWidget):

    config_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super(ConfigForm, self).__init__(parent=parent)

        self.projects_root = QtWidgets.QLineEdit()
        self.projects_root.editingFinished.connect(
            self.on_projects_root_changed
        )
        self.projects_root_button = QtWidgets.QToolButton(self)
        self.projects_root_button.setIcon(
            QtGui.QIcon(res.get_path('folder.png'))
        )
        self.projects_root_button.clicked.connect(
            self.on_projects_root_button_clicked
        )
        projects_root_layout = QtWidgets.QHBoxLayout()
        projects_root_layout.addWidget(self.projects_root)
        projects_root_layout.addWidget(self.projects_root_button)
        projects_root_layout.setStretch(0, 1)

        self.asset_template = QtWidgets.QLineEdit()
        self.asset_template.editingFinished.connect(
            self.on_asset_template_changed
        )
        self.publish_template = QtWidgets.QLineEdit()
        self.publish_template.editingFinished.connect(
            self.on_publish_template_changed
        )

        self.file_template = QtWidgets.QLineEdit()
        self.file_template.editingFinished.connect(
            self.on_file_template_changed
        )

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.addWidget(QtWidgets.QLabel('Projects Root'))
        self.layout.addLayout(projects_root_layout)
        self.layout.addWidget(QtWidgets.QLabel('Assets Template'))
        self.layout.addWidget(self.asset_template)
        self.layout.addWidget(QtWidgets.QLabel('Publish Template'))
        self.layout.addWidget(self.publish_template)
        self.layout.addWidget(QtWidgets.QLabel('File Template'))
        self.layout.addWidget(self.file_template)
        self.layout.addStretch()
        self.setLayout(self.layout)

        self.update_form()

    def update_form(self):
        self.projects_root.setText(lib.get_projects_root())
        self.asset_template.setText(lib.get_asset_template())
        self.publish_template.setText(lib.get_publish_template())
        self.file_template.setText(lib.get_file_template())

    def on_projects_root_changed(self):
        lib.set_projects_root(self.projects_root.text())
        self.config_changed.emit()

    def on_projects_root_button_clicked(self):
        browse = QtWidgets.QFileDialog()
        browse.setFileMode(browse.Directory)
        browse.setOption(browse.ShowDirsOnly)
        folder = browse.getExistingDirectory(
            self,
            'Choose Projects Root',
            lib.get_projects_root(),
        )
        if not folder:
            return

        lib.set_projects_root(folder)
        self.projects_root.setText(folder)
        self.config_changed.emit()

    def on_asset_template_changed(self):
        lib.set_asset_template(self.asset_template.text())
        self.config_changed.emit()

    def on_publish_template_changed(self):
        lib.set_publish_template(self.publish_template.text())
        self.config_changed.emit()

    def on_file_template_changed(self):
        lib.set_file_template(self.file_template.text())
        self.config_changed.emit()

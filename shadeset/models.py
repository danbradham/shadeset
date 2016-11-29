# -*- coding: utf-8 -*-

from collections import defaultdict
from copy import deepcopy
from contextlib import contextmanager
from .packages import yaml
from . import utils
import maya.cmds as cmds
import shutil
import os


class ShadeSet(dict):
    '''A dictionary subclass used to gather and export scene shading data

    :param path: Path to loaded shadeset.yml file
    '''

    registry = set()

    def __init__(self, path=None, *args, **kwargs):
        self.path = path
        self.root = None
        self.name = None
        if self.path:
            self.root = os.path.dirname(self.path)
            self.name = os.path.splitext(os.path.basename(self.path))[0]
        super(ShadeSet, self).__init__(*args, **kwargs)

    def relative(self, path):
        return os.path.join(self.root, path)

    @classmethod
    def load(cls, shade_path):
        '''Load scene shading data from an exported shadeset'''

        with open(shade_path, 'r') as f:
            shade_data = yaml.load(f.read())

        return cls(shade_path, shade_data)

    @classmethod
    def gather(cls, selection=True, render_layers=False):
        '''Gather shading data from a scene using the registered
        :class:`Subset` s. Returns a new :class:`ShadeSet` object containing
        the gathered data.

        :param selection: if True gather shading data for the selected
            transforms
        :param render_layers: if True shading data for all render layers
        '''

        shade_set = cls()

        if render_layers:
            layers_data = defaultdict(dict)

            with RenderLayers(RenderLayer.names()) as layers:

                for layer in layers:
                    layer.activate()

                    for subset in cls.registry:
                        data = subset.gather(selection=selection)
                        layers_data[layer.name].update(data)

            if layers_data:
                shade_set['render_layers'] = dict(layers_data)

        for subset in cls.registry:
            data = subset.gather(selection=selection)
            shade_set.update(data)

        return shade_set

    @utils.maintains_selection
    def reference(self):
        '''Reference subset dependencies'''
        for subset in self.registry:
            subset.reference(self)

    @utils.maintains_selection
    def import_(self):
        '''Import subset dependencies'''
        for subset in self.registry:
            subset.import_(self)

    @utils.maintains_selection
    def apply(self, selection=False, render_layers=False):
        '''Apply this :class:`ShadeSet` to the currently opened scene'''

        for subset in self.registry:
            subset.apply(self, selection=selection)

        if not render_layers:
            return

        render_layers = self.get('render_layers', None)
        if render_layers:
            with RenderLayers(render_layers.keys()) as layers:
                for layer in layers:

                    if not layer.exists:
                        layer.create()
                    layer.activate()

                    for subset in self.registry:
                        subset.apply(
                            render_layers[layer.name],
                            selection=selection
                        )

    @utils.maintains_selection
    def export(self, outdir, name):
        '''Export this :class:`ShadeSet` to a directory

        :param outdir: Output directory
        '''

        made_dir = False
        if not os.path.exists(outdir):
            os.makedirs(outdir)
            made_dir = True

        try:
            self._export(outdir, name)
        except:
            if made_dir:
                shutil.rmtree(outdir)
            raise

    def _export(self, outdir, name):

        for subset in self.registry:
            subset.export(self, outdir, name)

        shade_path = os.path.join(outdir, name + '.yml')
        encoded = yaml.safe_dump(dict(self), default_flow_style=False)

        with open(shade_path, 'w') as f:
            f.write(encoded)


class SubSet(object):

    def gather(self, selection):
        raise NotImplementedError()

    def import_(self, shade_set):
        pass

    def reference(self, shade_set):
        pass

    def export(self, shade_set, outdir, name):
        pass

    def apply(self, shade_set, selection=False):
        raise NotImplementedError()


class ShadingGroupsSet(SubSet):

    def path(self, shade_set):
        return os.path.join(
            shade_set.root,
            shade_set.name + '_shadingGroups.mb'
        )

    def gather(self, selection):

        data = {}

        if selection:
            transforms = cmds.ls(sl=True, long=True)
        else:
            transforms = cmds.ls(long=True, transforms=True)

        shading_groups = []
        for t in transforms:
            sgs = utils.get_shading_groups(t)
            if sgs:
                shading_groups.extend(sgs)

        shading_groups = set(shading_groups)

        for sg in shading_groups:
            members = cmds.sets(sg, query=True)
            if not members:
                continue

            _id = utils.add_id(sg)
            members = utils.short_names(members)
            data[str(sg)] = {
                'meta_id': _id,
                'members': members,
            }

        return {'shadingGroups': data}

    def import_(self, shade_set):
        path = self.path(shade_set)
        utils.import_shader(path)

    def reference(self, shade_set):
        path = self.path(shade_set)
        utils.reference_shader(path, namespace='BaseShadeSet')

    def export(self, shade_set, outdir, name):
        shading_groups = shade_set['shadingGroups'].keys()
        if 'render_layers' in shade_set:
            for render_layer, data in shade_set['render_layers'].items():
                shading_groups.extend(data['shadingGroups'].keys())
        shading_groups = list(set(shading_groups))

        path = os.path.join(outdir, name + '_shadingGroups.mb')
        utils.export_shader(shading_groups, path)

    def apply(self, shade_set, selection=False):

        for sg, sg_data in shade_set['shadingGroups'].items():
            if sg == 'initialShadingGroup':
                shading_group = 'initialShadingGroup'
            else:
                shading_group = utils.node_from_id(sg_data['meta_id'])

            members = utils.find_members(sg_data['members'])

            if selection:
                nodes = cmds.ls(sl=True, long=True)
                members = [m for m in members
                           if utils.member_in_hierarchy(m, *nodes)]

            utils.assign_shading_group(shading_group, members)


class LayerMembershipSet(SubSet):

    def gather(self, selection):

        layer = RenderLayer.active()
        if layer.name == 'defaultRenderLayer':
            return {}

        return {'layer_membership': utils.short_names(layer.members)}

    def apply(self, shade_set, selection=False):
        if not 'layer_membership' in shade_set:
            return

        layer = RenderLayer.active()

        members = utils.find_members(shade_set['layer_membership'])

        if selection:
            nodes = cmds.ls(sl=True, long=True)
            members = [m for m in members
                       if utils.member_in_hierarchy(m, *nodes)]

        layer.add_members(members)


ShadeSet.registry.add(ShadingGroupsSet())
ShadeSet.registry.add(LayerMembershipSet())


class RenderLayer(object):

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self):
        return str(self) == str(other)

    @property
    def exists(self):
        return self.name in self.names()

    def create(self):
        if self.exists:
            raise Exception('This layer already exists...')

        cmds.createRenderLayer(name=self.name, empty=True)

    def activate(self):
        cmds.editRenderLayerGlobals(currentRenderLayer=self.name)

    @property
    def members(self):
        return cmds.editRenderLayerMembers(self.name, q=True, fullNames=True)

    def remove_members(self, *members):
        args = [self.name] + list(members)
        cmds.editRenderLayerMembers(*args, remove=True)

    def add_members(self, *members):
        args = [self.name] + list(members)
        cmds.editRenderLayerMembers(*args, noRecurse=True)

    @classmethod
    def names(cls):
        return cmds.ls(type='renderLayer')

    @classmethod
    def all(cls):
        for layer in cls.names():
            return cls(layer)

    @classmethod
    def active(cls):
        return cls(cmds.editRenderLayerGlobals(crl=True, q=True))


@contextmanager
def RenderLayers(layers):
    '''Context manager that yields a RenderLayer generator. Restores the
    previously active render layer afterwards.'''

    old_layer = RenderLayer.active()

    try:
        yield (RenderLayer(layer) for layer in layers)
    except:
        raise
    finally:
        old_layer.activate()

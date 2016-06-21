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
                        layers_data[layer.name].update(
                            subset.gather(selection=selection)
                        )

            if layers_data:
                shade_set['render_layers'] = layers_data

        for subset in cls.registry:
            data = subset.gather(selection=selection)
            print data
            shade_set.update(data)

        return shade_set

    def reference(self):
        '''Reference this ShadeSets dependencies'''
        for subset in self.registry:
            subset.reference(self)

    def import_(self):
        '''Import this ShadeSets dependencies'''
        for subset in self.registry:
            subset.import_(self)

    def apply(self):
        '''Apply this :class:`ShadeSet` to the currently opened scene'''

        shade_set = deepcopy(self)
        render_layers = shade_set.pop('render_layers', None)

        for subset in self.registry:
            subset.apply(shade_set)

        if render_layers:
            with RenderLayers(render_layers.keys()) as layers:
                for layer in layers:
                    if not layer.exists:
                        continue
                    for subset in self.registry:
                        subset.apply(render_layers[layer])

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

        out_shade_set = deepcopy(self)
        render_layers = out_shade_set.pop('render_layers', None)

        for subset in self.registry:
            subset.export(out_shade_set, outdir, name)

        if render_layers:
            with RenderLayers(render_layers.keys()) as layers:
                for layer in layers:
                    for subset in self.registry:
                        subset.export(render_layers[layer], outdir, name)
                out_shade_set['render_layers'] = render_layers

        shade_path = os.path.join(outdir, name + '.yml')
        encoded = yaml.safe_dump(dict(self), default_flow_style=False)

        with open(shade_path, 'w') as f:
            f.write(encoded)


class SubSet(object):

    def gather(self, selection):
        raise NotImplementedError()

    def import_(self, shade_set):
        raise NotImplementedError()

    def export(self, shade_set, outdir, name):
        raise NotImplementedError()

    def apply(self, shade_set):
        raise NotImplementedError()


class BaseSet(SubSet):

    def gather(self, selection):

        data = defaultdict(dict)

        if selection:
            transforms = cmds.ls(sl=True, long=True, transforms=True)
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
            data['shadingGroups'][str(sg)] = {
                'meta_id': _id,
                'members': members,
            }

        return data

    def import_(self, shade_set):
        shaders_path = os.path.join(shade_set.root, shade_set.name + '.mb')
        utils.import_shader(shaders_path)

    def reference(self, shade_set):
        shaders_path = os.path.join(shade_set.root, shade_set.name + '.mb')
        utils.reference_shader(shaders_path, namespace='BaseShadeSet')

    def export(self, shade_set, outdir, name):
        shading_groups = shade_set['shadingGroups'].keys()
        utils.export_shader(shading_groups, os.path.join(outdir, name + '.mb'))

    def apply(self, shade_set):

        for sg, sg_data in shade_set['shadingGroups'].items():
            if sg == 'initialShadingGroup':
                shading_group = 'initialShadingGroup'
            else:
                shading_group = utils.node_from_id(sg_data['meta_id'])
            members = utils.find_members(sg_data['members'])
            utils.assign_shading_group(shading_group, members)


ShadeSet.registry.add(BaseSet())


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
        return self.name in get_render_layers()

    def create(self):
        if self.exists:
            raise Exception('This layer already exists...')

        cmds.createRenderLayer(name=self.name, empty=True)

    def activate(self):
        cmds.editRenderLayerGlobals(currentRenderLayer=self.name)

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

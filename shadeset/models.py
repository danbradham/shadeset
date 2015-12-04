from collections import defaultdict
from copy import deepcopy
from contextlib import contextmanager
from .packages import yaml
from . import utils
import maya.cmds as cmds
import shutil
import os


class ShadeSet(dict):
    '''An object containing scene shading information.'''

    _subsets = set()

    @classmethod
    def register(cls, subset):
        cls._subsets.add(subset)

    @classmethod
    def unregister(cls, subset):
        cls._subsets.discard(subset)

    @classmethod
    def gather(cls, selection=True, render_layers=False):
        shade_set = cls()

        if render_layers:
            layers_data = defaultdict(dict)

            with RenderLayers(RenderLayer.names()) as layers:
                for layer in layers:
                    layer.activate()

                    for subset in cls._subsets:
                        layers_data[layer.name].update(
                            subset.gather(selection=selection)
                        )

            if layers_data:
                shade_set['render_layers'] = layers_data

        for subset in cls._subsets:
            shade_set.update(subset.gather(selection=selection))

        return shade_set

    def apply(self):

        shade_set = deepcopy(self)
        render_layers = shade_set.pop('render_layers', None)

        for subset in self._subsets:
            subset.apply(shade_set)

        if render_layers:
            with RenderLayers(render_layers.keys()) as layers:
                for layer in layers:
                    if not layer.exists:
                        continue
                    for subset in self._subsets:
                        subset.apply(render_layers[layer])

    def export(self, outdir):

        made_dir = False
        if not os.path.exists(outdir):
            os.makedirs(outdir)
            made_dir = True

        try:
            self._export(outdir)
        except:
            if made_dir:
                shutil.rmtree(outdir)
            raise

    def _export(self, outdir):

        out_shade_set = deepcopy(self)
        render_layers = out_shade_set.pop('render_layers', None)

        for subset in self._subsets:
            subset.export(out_shade_set, outdir)

        if render_layers:
            with RenderLayers(render_layers.keys()) as layers:
                for layer in layers:
                    for subset in self._subsets:
                        subset.export(render_layers[layer], outdir)
                out_shade_set['render_layers'] = render_layers

        shade_path = os.path.join(outdir, 'shadeset.yml')
        encoded = yaml.safe_dump(self, default_flow_style=False)

        with open(shade_path, 'w') as f:
            f.write(encoded)


class BaseSet(object):

    @staticmethod
    def gather(selection):

        data = defaultdict(dict)

        if selection:
            transforms = cmds.ls(sl=True, long=True, transforms=True)
        else:
            transforms = cmds.ls(long=True, transforms=True)

        for t in transforms:
            shader = utils.get_shader(t)
            if shader:
                data['geometry'][t] = shader
                data['materials'].setdefault(shader, '')

        return data

    @staticmethod
    def export(shade_set, outdir):

        materials = shade_set.get('materials', None)
        if not materials:
            return

        for material in materials.keys():
            rel_path = 'materials/{}.mb'.format(material)
            out_file = os.path.join(outdir, rel_path)
            shade_set['materials'][material] = rel_path

            utils.export_material(material, out_file)


ShadeSet.register(BaseSet)


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

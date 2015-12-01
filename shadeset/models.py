from .utils import *
from collections import defaultdict
from copy import deepcopy


class ShadeSet(dict):
    '''An object containing scene shading information.'''

    _subsets = set()

    @classmethod
    def gather(cls, render_layers=True):
        shade_set = cls()

        if render_layers:
            layers_data = defaultdict(dict)

            for layer in render_layer_iterator(get_scene_render_layers()):
                for subset in self.subsets:
                    layers_data[layer].update(subset.gather())

            if layers_data:
                shade_set['RenderLayers'] = layers_data

        for subset in self.subsets:
            shade_set.update(subset.gather())


    def apply(self):

        shade_set = deepcopy(self)
        render_layers = shade_set.pop('RenderLayers', None)

        for subset in self.subsets:
            subset.apply(shade_set)

        for layer in render_layer_iterator(render_layers.keys()):
            for subset in self.subsets:
                subset.apply(render_layers[layer])

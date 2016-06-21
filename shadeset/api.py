from .models import ShadeSet

__all__ = ['gather', 'load', 'register_subset', 'unregister_subset']


def gather(**kwargs):
    '''Gather shading data from a scene using the registered
    :class:`Subset` s. Returns a new :class:`ShadeSet` object containing
    the gathered data.

    :param selection: if True gather shading data for the selected transforms
    :param render_layers: if True shading data for all render layers
    '''

    return ShadeSet.gather(**kwargs)


def load(shade_path):
    '''Load a :class:`ShadeSet` from disk.

    :param shade_path: Path to shadeset.yml file
    '''

    return ShadeSet.load(shade_path)


def register_subset(subset):
    '''Register a subset derived from :class:`SubSet`'''

    ShadeSet.registry.add(subset)


def unregister_subset(subset):
    '''Unregister a subset derived from :class:`SubSet`'''

    ShadeSet.registry.discard(subset)


def clear_registry():
    '''Unregister all :class:`SubSet`s'''

    ShadeSet.registry.clear()

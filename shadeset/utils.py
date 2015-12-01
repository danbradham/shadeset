from contextlib import contextmanager


def get_scene_render_layers():
    return []


def render_layer_iterator(layers):

    old_layer = ''

    for layer in layers:
        try:
            # activate render layer
            yield layer
        except:
            continue
        yield

    # reactivate old_layer

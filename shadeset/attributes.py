# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

# Third party imports
from maya import cmds


def get_attr(path, attr):
    '''Get an attribute's value.'''

    attr_path = path + '.' + attr
    if not cmds.attributeQuery(attr, node=path, exists=True):
        return

    value = cmds.getAttr(attr_path)
    if isinstance(value, list) and isinstance(value[0], tuple):
        value = value[0]

    return value


def get_type_kwarg_from_value(value):
    '''Returns a type keyword argument to be used with cmds.addAttr for a
    python type. Returns None when an attribute type can not be determined.

    This method only supports a limited number of simple python types.
        str, float, float2, float3, int, int2, int3, bool

    Examples::

        assert get_type_kwarg_from_value('Hello') == {'dataType': 'string'}
        assert get_type_kwarg_from_Value(100) == {'attributeType': 'long'}
        assert get_type_kwarg_from_Value(1.0) == {'attributeType': 'double'}
        assert get_type_kwarg_from_Value(True) == {'attributeType': 'bool'}
    '''
    if not isinstance(value, (list, tuple)):
        value = [value]
    type_key = tuple([type(v) for v in value])
    return {
        (str,): {'dataType': 'string'},
        (float,): {'attributeType': 'double'},
        (float,float): {'attributeType': 'double2'},
        (float,float,float): {'attributeType': 'double3'},
        (int,): {'attributeType': 'long'},
        (int,int): {'attributeType': 'long2'},
        (int,int,int): {'attributeType': 'long3'},
        (bool,): {'attributeType': 'bool'},
    }.get(type_key)


def get_type_flag(type, compound=False):
    '''Returns the type flag (attributeType or dataType) for an attribute type
    that is required when adding an attribute.

    Example::

        path = 'some_node'
        add_attr_kwargs = {
            'longName': 'custom_attr',
            get_type_flag('string'): 'string',
        }
        cmds.addAttr(path, **add_attr_kwargs)
    '''
    if compound:
        return 'attributeType'
    return ('attributeType', 'dataType')[type in {
        'matrix', 'string', 'stringArray', 'doubleArray', 'Int32Array',
        'reflectance', 'spectrum', 'float2', 'float3', 'double2',
        'double3', 'long2', 'long3', 'short2', 'short3', 'vectorArray',
        'nurbsCurve', 'nurbsSurface', 'mesh', 'lattice', 'pointArray'
    }]


def is_unpackable(type):
    '''Returns True for attribute types whose values should be unpacked
    when setting the attribute.

    Example::

        path = 'some.attr'
        value = [0, 10, 0]
        type_ = 'float3'
        if is_unpackable(type_):
            cmds.setAttr(path, *value, type=type_)
        else:
            cmds.setAttr(path, value)
    '''
    return type in {
        'float2', 'float3', 'double2', 'double3', 'long2', 'long3',
        'compound', 'spectrum', 'reflectance', 'matrix', 'fltMatrix',
        'reflectanceRBG', 'spectrumRGB', 'short2', 'short3', 'doubleArray',
        'Int32Array', 'vectorArray'
    }


def is_typeable(type):
    '''Returns True for attribute types where the type flag is required to
    set the attribute. For example the type flag must be provided to set
    "string" attributes.

    Example::

        path = 'some.attr'
        value = 'Hello World'
        type_ = 'string'
        if is_typeable(type_):
            cmds.setAttr(path, value, type=type_)
        else:
            cmds.setAttr(path, value)
    '''
    return type in {
        'float2', 'float3', 'double2', 'double3', 'long2', 'long3',
        'compound', 'spectrum', 'reflectance', 'matrix', 'fltMatrix',
        'reflectanceRBG', 'spectrumRGB', 'short2', 'short3', 'doubleArray',
        'Int32Array', 'vectorArray', 'string', 'byte'
    }


def get_attr_schema(path, attr):
    '''Returns a schema describing an attribute.

    Schemas can be used to add attributes to nodes using the add_attr method.
    They can also be used with set_attr to provide more robust way of setting
    attributes.
    '''

    if not cmds.attributeQuery(attr, node=path, exists=True):
        return

    children = []
    child_attrs = cmds.attributeQuery(attr, node=path, listChildren=True) or []
    for child_attr in child_attrs:
        children.append(
            {
                'type': cmds.getAttr(path + '.' + child_attr, type=True),
                'longName': child_attr,
                'keyable': cmds.attributeQuery(child_attr, node=path, k=True),
                'parent': attr,
            }
        )

    enumName = cmds.attributeQuery(attr, node=path, listEnum=True)
    if enumName:
        enumName = enumName[0]

    attr_path = path + '.' + attr
    return {
        'type': cmds.getAttr(attr_path, type=True),
        'longName': attr,
        'shortName': cmds.attributeName(attr_path, short=True),
        'niceName': cmds.attributeName(attr_path, nice=True),
        'children': children,
        'enumName': enumName,
        'keyable': (
            cmds.getAttr(attr_path, keyable=True) or
            cmds.getAttr(attr_path, channelBox=True)
        ),
        'usedAsColor': cmds.attributeQuery(attr, node=path, usedAsColor=True),
    }


def get_attrs_with_prefix(path, prefix):
    '''Get all attributes with the specified prefix'''

    return [attr for attr in cmds.listAttr(path) if attr.startswith(prefix)]


def collect_attributes(root, attributes, attribute_prefixes=None):
    '''Collect attributes from a hierarchy.

    Arguments:
        root (str): Root dag path.
        attributes (list): List of attributes to collect.
        attribute_prefixes (list): List of attribute_prefixes to collect.

    Returns:
        dict containing attribute schemas and attribute values by dag path.

    Example Return Value::

        {
            'schemas': {
                'visibility': {
                    'type': 'bool',
                    'type_option': 'attributeType',
                    'keyable': True,
                }
            },
            'values': {
                '|geo|aShape1': {
                    'visibility': True,
                }
            },
        }
    '''

    results = {'schemas': defaultdict(dict), 'values': defaultdict(dict)}

    attribute_prefixes = attribute_prefixes or []
    hierarchy = get_hierarchy(root)

    for path in hierarchy:
        clean_path = get_relative_paths([path], root)[0]
        clean_path = remove_namespaces([clean_path])[0]
        for attr in attributes:

            if attr not in results['schemas']:
                schema = get_attr_schema(path, attr)
                if schema:
                    results['schemas'][attr] = schema

            value = get_attr(path, attr)
            if value is not None:
                results['values'][clean_path][attr] = value

        for attr_prefix in attribute_prefixes:
            for attr in get_attrs_with_prefix(path, attr_prefix):

                if cmds.attributeQuery(attr, node=path, listParent=True):
                    # Skip child attributes assuming that the attributes
                    # parent will already be collected.
                    continue

                if attr not in results['schemas']:
                    schema = get_attr_schema(path, attr)
                    if schema:
                        results['schemas'][attr] = schema

                value = get_attr(path, attr)
                if value is not None:
                    results['values'][clean_path][attr] = value

    return results


def add_attr_from_schema(path, schema=None):
    '''Add an attribute using a schema returned by get_attr_schema.'''

    # Setup schema for addAttr
    schema = dict(schema)
    children = schema.pop('children', [])
    attr_type = schema.pop('type')
    schema[get_type_flag(attr_type, compound=bool(children))] = attr_type
    if schema['enumName'] is None:
        schema.pop('enumName')

    # Add attribute
    cmds.addAttr(path, **schema)

    # Add child attributes
    for child in children:
        child_schema = dict(child)
        child_type = child_schema.pop('type')
        child_schema[get_type_flag(child_type)] = child_type
        cmds.addAttr(path, **child_schema)


def set_attr(path, attr, value, schema=None):
    '''Set an attributes value.'''

    args = [path + '.' + attr]
    kwargs = {}

    if schema:
        attr_type = schema['type']
        if is_unpackable(attr_type):
            args.extend(value)
        else:
            args.append(value)

        if is_typeable(attr_type):
            kwargs['type'] = schema['type']
    else:
        if isinstance(type, (list, tuple)):
            args.extend(value)
        else:
            args.append(value)
        if isinstance(type, basestring):
            kwargs['type'] = 'string'

    try:
        cmds.setAttr(*args, **kwargs)
    except RuntimeError as e:
        if 'locked or connected' in str(e):
            cmds.warning(str(e).split(':', 1)[-1].rstrip())


def apply_attributes(
    attributes,
    root='|',
    namespace=None,
    strict=False,
):
    '''Set attributes on dag paths listed in an attributes dict.

    Arguments:
        attributes (dict): Like the results of collect_attributes
        root (str): Apply shadingEngines only to members found under this
            dag path. Defaults to '|' matching any node in the scene.
        namespace (str): Namespace containing dag paths to set attrs on.
        strict (bool): When strict is False, the first element of a path is
            removed, allowing members in hierarchies that match but may be
            under a different root node. Defaults to False.
    '''

    for path, attrs in attributes['values'].items():

        matching_paths = find_matching_paths(path, root, namespace, strict)

        for attr, value in attrs.items():

            schema = attributes['schemas'].get(attr)

            for path in matching_paths:

                if not cmds.attributeQuery(attr, node=path, exists=True):
                    if schema:
                        add_attr_from_schema(path, schema)
                    else:
                        kwargs = {'ln': attr, 'k': True}
                        kwargs.update(get_type_kwarg_from_value(value))
                        cmds.addAttr(path, **kwargs)

                set_attr(path, attr, value, schema)

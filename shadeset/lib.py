# -*- coding: utf-8 -*-
'''
Simple pipeline api used to find projects, assets and published shadesets.
'''

# Standard library imports
import os
from glob import glob

# Local imports
from . import config
from . import pat


session = {
    'project': None,
    'asset': None,
}


def normalize(*parts):
    return os.path.normpath(os.path.join(*parts)).replace('\\', '/')


def get_projects_root():
    '''Get the directory containing your projects.

    This is the {root} field in templates.
    '''
    return config.projects_root


def set_projects_root(path):
    '''Set the directory containing your projects.

    This is the {root} field in templates.
    '''
    config.projects_root = path


def get_projects():
    '''Get a list of projects'''

    projects_root = get_projects_root()
    projects = []
    for item in os.listdir(get_projects_root()):

        path = normalize(projects_root, item)
        if os.path.isfile(path):
            continue

        if item.startswith('.'):
            continue

        projects.append(item)

    return projects


def set_project(project):
    '''Set the active project.'''

    session['project'] = project


def get_asset_template():
    '''Get the asset template.'''

    return config.asset_template


def set_asset_template(template):
    '''Set the template used to lookup assets.

    Let's look at some examples of assets and templates you could use.

    Examples:
        Assets:   C:/projects/my_project/assets/asset_a
                  C:/projects/my_project/shots/shot_010
        Template: {root}/{project}/{folder}/{asset}

        Assets:   C:/projects/my_project/3d/assets/prop/table
                  C:/projects/my_project/3d/shots/seq_010/seq_010_010
        Template: {root}/{project}/3d/{folder}/{collection}/{asset}
    '''
    config.asset_template = template


def get_assets(project, **query):
    '''Get a dict of assets in a project.

    Pass query fields to narrow the results. These can be any fields you use
    in your ASSETS_TEMPLATE. {root}, {project} and {asset} are the only
    essential fields you must use in your templates.

    Arguments:
        project (str): Name of project to get assets from
        **query: Fields used to narrow results

    Returns:
        dict: Keys are asset names and values are asset dicts.
    '''

    tmpl = pat.compile(get_asset_template())
    fields = {field: '*' for field in tmpl.fields}
    fields.update(
        root=get_projects_root(),
        project=project,
        **query
    )
    lookup_pattern = tmpl.format(**fields)

    assets = {}
    for path in sorted(glob(lookup_pattern)):

        # Skip loose files
        if os.path.isfile(path):
            continue

        # Skip folders beginning with .
        if os.path.basename(path).startswith('.'):
            continue

        path = normalize(path)
        fields = tmpl.parse(path)
        if fields is None:
            print('shadeset| Failed to parse: ' + path)
            continue

        asset = dict(
            path=path,
            **fields
        )
        assets[fields['asset']] = asset

    return assets


def set_asset(asset):
    '''Set the active asset.'''

    session['asset'] = asset


def get_asset(project, asset, **query):
    '''Get a dict of fields for an asset.'''

    query[asset] = asset
    assets = get_assets(project, **query)
    return assets[asset]


def get_publish_template():
    '''Get the publish template.'''

    return config.publish_template


def set_publish_template(template):
    '''Set the template used to determine where to publish shadesets for a
    given asset. The first part of this template should match your asset
    template.

    Let's look at some examples of publish folders and templates you could use.

    Examples:
        Publish:   C:/projects/my_project/assets/asset_a/publish/shadesets
                   C:/projects/my_project/shots/shot_010/publish/shadesets
        Template:  {root}/{project}/{folder}/{asset}/publish/ssets
    '''
    config.publish_template = template


def get_publish_folder(asset):
    '''Get the folder shadesets are publish to for a specific asset.'''

    tmpl = pat.compile(get_publish_template())
    return tmpl.format(**asset)


def set_file_template(template):
    config.file_template = template


def get_file_template():
    return config.file_template


def get_publish_file_template():
    return normalize(get_publish_template(), get_file_template())


def get_publishes(asset, name=None):
    '''Get the published shadesets for a specific asset.

    Arguments:
        asset (dict): Asset data as returned by get_assets and get_asset
        name (str): Name used to lookup shadesets.

    Returns:
        dict: Dictionary containing publishes grouped by name and version.
    '''

    if name:
        tmpl = pat.compile(normalize(get_publish_template(), name + '_v*.yml'))
    else:
        tmpl = pat.compile(normalize(get_publish_template(), '*.yml'))

    publish_lookup = tmpl.format(**asset)
    publish_tmpl = pat.compile(get_publish_file_template())

    publishes = {}
    for path in sorted(glob(publish_lookup)):

        # Skip private files
        if os.path.basename(path).startswith('.'):
            continue

        path = normalize(path)
        fields = publish_tmpl.parse(path)
        if fields is None:
            print('shadeset| Failed to parse: ' + path)
            continue

        publish = dict(
            path=path,
            basename=os.path.basename(path),
            dirname=os.path.dirname(path),
            image=path.replace('.yml', '.png'),
            shaders=path.replace('.yml', '.ma'),
            **fields
        )
        versions = publishes.setdefault(publish['name'], {})
        versions[publish['version']] = publish

    return publishes


def get_latest_publish(asset, name):
    '''Get the latest publish for a specific shadeset.'''

    publishes = get_publishes(asset, name)
    if publishes:
        return sorted(publishes[name].items())[-1][1]


def get_next_publish(asset, name):
    '''Get the next available version for publishing.'''

    publish_folder = get_publish_folder(asset)
    publish_file_tmpl = get_file_template()
    publish_tmpl = pat.compile(get_publish_file_template())

    for i in range(999):
        potential_file = publish_file_tmpl.format(
            name=name,
            version=i + 1,
            ext='yml',
        )
        potential_path = normalize(publish_folder, potential_file)
        if os.path.isfile(potential_path):
            continue

        fields = publish_tmpl.parse(potential_path)
        publish = dict(
            path=potential_path,
            basename=os.path.basename(potential_path),
            dirname=os.path.dirname(potential_path),
            **fields
        )
        return publish


def get_export_attr_prefixes():
    '''Get the list of attribute prefixes to include in publishes'''

    return config.prefixes


def set_export_attr_prefixes(prefixes):
    '''Set the list of attribute prefixes to include in publishes'''

    config.prefixes = prefixes


def get_export_attrs():
    '''Get the list of attributes to include in publishes'''

    return config.attributes


def set_export_attrs(attrs):
    '''Set the list of attributes to include in publishes'''

    config.attributes = attrs

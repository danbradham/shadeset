# -*- cofing: utf-8 -*-
import os


if 'USERPROFILE' in os.environ:
    default_projects_root = os.path.expandvars('$USERPROFILE/projects')
else:
    default_projects_root = os.path.expanduser('~/projects')

projects_root = os.getenv(
    'SHADESET_PROJECTS',
    default_projects_root.replace('\\', '/')
)

asset_template = os.getenv(
    'SHADESET_ASSETS',
    '{root}/{project}/{asset_type}/{asset}'
)

publish_template = os.getenv(
    'SHADESET_PUBLISH',
    '{root}/{project}/{asset_type}/{asset}/publish/shadesets'
)

file_template = os.getenv(
    'SHADESET_FILE',
    '{name}_v{version:>03d}.{ext}'
)

prefixes = os.getenv(
    'SHADESET_ATTRPREFIXES',
    'mtoa_constant meta_'
).split()

attributes = os.getenv(
    'SHADESET_ATTRIBUTES',
    'aiOpaque'
).split()

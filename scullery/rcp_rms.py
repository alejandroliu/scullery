#
# RMS recipes
#
'''
## Resource management recipes

This recipe is used to list resources

```bash
scullery rms [projectname]
```

If no `projectname` is specified it should list all resources.  If
`projectname` is specified it will list all resources related
to the given project.

Output format can be controlled with ``-f`` / ``--format``:

| Format       | Description                         |
|--------------|-------------------------------------|
| ``terminal`` | Aligned columns for your terminal   |
| ``json``     | JSON array of resources             |
| ``csv``      | Comma-separated values              |
| ``tsv``      | Tab-separated values                |
| ``markdown`` | Markdown / pipe table               |

***
'''

import argparse

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from scullery import cloud
from scullery import formatters
from scullery import parsers


# Ordered list of (dict_key, column_label) pairs shown in the output.
COLUMNS: formatters.Columns = [
  ('project_name', 'Project'),
  ('provider',     'Provider'),
  ('type',         'Type'),
  ('name',         'Name'),
  ('region_id',    'Region'),
]


def run(args: argparse.Namespace) -> None:
  '''Resource management (specify a project to limit list)'''
  cc = cloud()
  resources = cc.rms.resources(args.project, args.type)
  rows = formatters.extract_rows(resources, COLUMNS)
  formatters.write_output(rows, COLUMNS, args.format)


def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the ``resources`` sub-parser'''
  pr = subp.add_parser('resources',
                       help='Resource management',
                       aliases=['rms', 'rsc'])
  pr.add_argument('-m', '--project',
                  help='Match project',
                  default=None)
  pr.add_argument('-t', '--type',
                  help='Resource type',
                  default=None)
  formatters.add_format_arg(pr)
  pr.set_defaults(recipe_cb=run)


parsers.register_parser('resources', parser)




#
# DeH recipes
#
'''
## Dedicated Host recipes

List available dedicated host types.

```bash
scullery deh AZ
```

The ``AZ`` can be a numeric index (``2``) or a full AZ name
(``eu-de-02``).  If omitted it defaults to the first available
availability zone.

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


# Columns for the list (default table) view.
COLUMNS: formatters.Columns = [
  ('host_type',      'Host Type'),
  ('host_type_name', 'Name'),
]


def run(args: argparse.Namespace) -> None:
  '''List available dedicated host types'''
  cc = cloud(scoped = True)
  if isinstance(args.az,str):
    if args.az.isdigit():
      args.az = int(args.az)
  ic(args)
  data = cc.deh.deh_types(args.az)
  rows = formatters.extract_rows(data, COLUMNS)
  formatters.write_output(rows, COLUMNS, args.format)


def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the ``deh`` sub-parser'''
  pr = subp.add_parser('deh',
                       help='Dedicated Host types',
                       aliases=['dedicated-host'])
  pr.add_argument('az',
                  nargs='?',
                  default=1,
                  help='Availability zone (number or name, default: %(default)s)')
  formatters.add_format_arg(pr)
  pr.set_defaults(recipe_cb=run)


parsers.register_parser('deh', parser)

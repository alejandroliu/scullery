#
# Roles recipe
#
'''
## Role recipes

Implements role recipes.

## list roles

List custom roles

```bash
scullery role
```
## list SYSTEM roles

List system roles.  These roles are built-in into the cloud infrastructure.

```bash
scullery role system
```

## get role details

Get the role details.

```bash
scullery role get role_name
```
## add custom role

Create a new custom role

```bash
scullery role add role_name [yaml_file]
```
Create a role using a `yaml_file`.  If no `yaml_file` is specified
it will read definition from `stdin`.

Example YAML:

```yaml
- Action:
  - 'ecs:*:get*'
  - 'ecs:*:list*'
  - 'ecs:*:stop*'
  - 'ecs:*:start*'
  - 'ecs:*:reboot*'
  Effect: Allow
```

See {py:obj}`scullery.iam.Iam.new_role` for more details.

## delete custom role

Delete a custom role

```bash
scullery role del role_name
```
***
'''

import argparse
import json
import os
import sys
import yaml

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from scullery import cloud
from scullery import formatters
from scullery import parsers
from scullery import usergroup


# Columns for the list (default table) view.
# Machine-readable formats (json/yaml/csv/tsv) include id;
# terminal/markdown omit it.
COLUMNS: formatters.Columns = [
  ('id',           'ID'),
  ('name',         'Name'),
  ('type',         'Type'),
  ('display_name', 'Display Name'),
  ('description',  'Description'),
]

# Columns for human-readable output (no raw id, no name).
COLUMNS_HUMAN: formatters.Columns = [
  ('type',         'Type'),
  ('display_name', 'Display Name'),
  ('description',  'Description'),
]

# Human-readable columns when --show-id is given.
COLUMNS_HUMAN_FULL: formatters.Columns = [
  ('id',           'ID'),
  ('name',         'Name'),
  ('type',         'Type'),
  ('display_name', 'Display Name'),
  ('description',  'Description'),
]

# Map short role-type codes to human-readable descriptions.
TYPE_MAP = {
  'AX': 'Account',
  'XA': 'Project',
  'AA': 'Both',
  'XX': 'None',
}

def dump_roles(roles:list) -> None:
  '''INTERNAL: print role details

  :param roles: List of roles to primt
  '''
  for role in roles:
    values = {
      'description': '',
      'display_name': '',
    }
    values.update(role)
    print('{name:16} {type} {display_name:24} {description}'.format(**values))

def list_cc_roles(args: argparse.Namespace) -> None:
  '''List custom roles'''
  cc = cloud()
  data = cc.iam.custom_roles()
  for r in data:
    r.setdefault('description', '')
    r.setdefault('display_name', '')
    if args.format in ('terminal', 'markdown'):
      typ = r.get('type', '')
      r['type'] = TYPE_MAP.get(typ, typ)
  if args.format in ('terminal', 'markdown'):
    cols = COLUMNS_HUMAN_FULL if getattr(args, 'long', False) else COLUMNS_HUMAN
  else:
    cols = COLUMNS
  rows = formatters.extract_rows(data, cols)
  formatters.write_output(rows, cols, args.format)

def del_role(args: argparse.Namespace) -> None:
  '''Delete one or more custom roles'''
  cc = cloud()
  for r in args.name:
    try:
      role = cc.iam.get_role(r)
      sys.stderr.write(f'{role}\n')
      cc.iam.del_role(role['id'])
    except KeyError:
      sys.stderr.write(f'{g}: Role not found\n')

def add_role(args: argparse.Namespace) -> None:
  '''Create a new custom role from a policy file'''
  cc = cloud()
  policies = yaml.safe_load(args.policy)

  new_role = usergroup.add_role(cc, args.name, policy = policies,
                                project = args.project,
                                description = args.description)

  print(json.dumps(new_role, indent=2))

def list_sys_roles(args: argparse.Namespace) -> None:
  '''List system (built-in) roles'''
  cc = cloud()
  data = cc.iam.system_roles()
  for r in data:
    r.setdefault('description', '')
    r.setdefault('display_name', '')
    if args.format in ('terminal', 'markdown'):
      typ = r.get('type', '')
      r['type'] = TYPE_MAP.get(typ, typ)
  if args.format in ('terminal', 'markdown'):
    cols = COLUMNS_HUMAN_FULL if getattr(args, 'long', False) else COLUMNS_HUMAN
  else:
    cols = COLUMNS
  rows = formatters.extract_rows(data, cols)
  formatters.write_output(rows, cols, args.format)


def get_role(args: argparse.Namespace) -> None:
  '''Show detailed info for one or more roles'''
  cc = cloud()
  for role_name in args.role:
    role = cc.iam.get_role(role_name)
    formatters.write_single_output(role, args.format)

def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the ``roles`` sub-parser'''
  pr = subp.add_parser('roles',
                        help = 'Role recipes',
                        aliases = ['role'])
  pr.set_defaults(recipe_cb = list_cc_roles)
  formatters.add_format_arg(pr)
  pr.add_argument('--long', '-l',
                  action='store_true', default=False,
                  help='Show Name and ID columns in human-readable output')

  rsp = pr.add_subparsers(title='op',
                          description='Operation.  If not spcified, list custom roles.',
                          required = False,
                          help = 'Operation')
  pp = rsp.add_parser('system',
                  help = 'List system roles',
                  aliases = ['sys', 's'])
  pp.set_defaults(recipe_cb = list_sys_roles)

  pp = rsp.add_parser('custom',
                  help = 'List custom roles',
                  aliases = ['cus'])
  pp.set_defaults(recipe_cb = list_cc_roles)

  pp = rsp.add_parser('get',
                  help = 'Get details for role',
                  aliases = ['g'])
  pp.add_argument('role',
                  help='Role to look-up',
                  nargs='+')
  pp.set_defaults(recipe_cb = get_role)
  formatters.add_single_format_arg(pp)

  pp = rsp.add_parser('add',
                  help = 'Add role',
                  aliases = ['new','create','a','n','c'])
  pp.add_argument('-d','--description','--desc', dest = 'description',
                  help = 'Description for this role')
  pp.add_argument('-p','--project','--proj', dest = 'project',
                  help = 'Include project name in description')
  pp.add_argument('name',
                  help = 'Role name to create')
  pp.add_argument('policy',
                  nargs = '?',
                  default = sys.stdin,
                  type = argparse.FileType('r'),
                  help = 'Policy file (if not specified will read from stdin)')
  pp.set_defaults(recipe_cb = add_role)

  pp = rsp.add_parser('del',
                  help = 'Delete role',
                  aliases = ['rm', 'd','rr'])
  pp.add_argument('name',
                  nargs='+',
                  help='Role name to delete')
  pp.set_defaults(recipe_cb = del_role)

parsers.register_parser('roles',parser)


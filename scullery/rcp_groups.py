#
# Group recipe
#
'''
## Group recipes

Group recipe implementations

## list groups

List groups

```bash
scullery grp
```

## get group details

Get details related to a group.  This will show group definitions,
assigned domain roles and member users.

```bash
scullery grp get groupname
```

## add group

Create a new group

```bash
scullery grp add groupname [description]
```

## del group

Delete a group

```bash
scullery grp del groupname
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
COLUMNS: formatters.Columns = [
  ('name',        'Name'),
  ('description', 'Description'),
]

def add_group(args: argparse.Namespace) -> None:
  '''Create a new group'''
  cc = cloud()
  newid = usergroup.add_group(cc, args.name,
            description = args.description,
            project = args.project)
  print('grp id', newid)

def del_group(args: argparse.Namespace) -> None:
  '''Delete one or more groups'''
  cc = cloud()
  for g in args.name:
    try:
      grps = cc.iam.groups(g)
      if len(grps) != 1: raise KeyError(g)
      cc.iam.del_group(grps[0]['id'])
      sys.stderr.write(f'Removed group: {g} ({grps[0]["id"]})\n')
    except KeyError:
      sys.stderr.write(f'{g}: Group not found\n')

def get_group(args: argparse.Namespace) -> None:
  '''Show detailed info for one or more groups'''
  cc = cloud()
  for group_name in args.group:
    group = cc.iam.groups(group_name)
    if len(group) != 1:
      sys.stderr.write(f'{group_name} not matched\n')
      continue
    group = group[0]

    if args.format == 'terminal':
      print('id:    {id}\n name: {name}\n desc: {description}'.format(**group))
      perms = cc.iam.get_domain_group_perms(group['domain_id'], group['id'])
      if len(perms) > 0:
        print(' Domain roles:')
        for r in perms:
          print('  - {display_name}: {description}'.format(**r))
      users = cc.iam.group_users(group['id'])
      if len(users) > 0:
        print(' users;')
        for u in users:
          print('   {name}: {description}'.format(**u))
    else:
      out = dict(group)
      out['domain_roles'] = cc.iam.get_domain_group_perms(group['domain_id'], group['id'])
      out['users'] = cc.iam.group_users(group['id'])
      formatters.write_single_output(out, args.format)

def list_groups(args: argparse.Namespace) -> None:
  '''List all groups'''
  cc = cloud()
  rows = formatters.extract_rows(cc.iam.groups(), COLUMNS)
  formatters.write_output(rows, COLUMNS, args.format)

def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the ``groups`` sub-parser'''
  pr = subp.add_parser('groups',
                        help = 'Group recipes',
                        aliases = ['group','grp','g'])
  gsp = pr.add_subparsers(title='op',
                          description='Operation.  If not spcified, list groups.',
                          required = False,
                          help = 'Operation')
  pp = gsp.add_parser('get',
                  help = 'Get details for group',
                  aliases = ['g'])
  pp.add_argument('group',
                  help='Group to look-up',
                  nargs='+')
  pp.set_defaults(recipe_cb = get_group)
  formatters.add_single_format_arg(pp)

  pp = gsp.add_parser('add',
                  help = 'Add group',
                  aliases = ['create', 'new','a'])
  pp.add_argument('-d','--description', '--desc', dest='description',
                    help = 'Optional description')
  pp.add_argument('-p','--project','--proj', dest = 'project',
                  help = 'Include project name in description')
  pp.add_argument('name',
                  help='Group name')
  pp.set_defaults(recipe_cb = add_group)

  pp = gsp.add_parser('del',
                  help = 'Delete group',
                  aliases = ['rm', 'd','rr'])
  pp.add_argument('name',
                  nargs='+',
                  help='Group name to delete')
  pp.set_defaults(recipe_cb = del_group)


  pr.set_defaults(recipe_cb = list_groups)
  formatters.add_format_arg(pr)


parsers.register_parser('groups',parser)


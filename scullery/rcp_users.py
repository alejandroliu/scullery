'''
## User recipes

This module implements user related recipes.  The following
verbs are recognized.

## list users

This will list cloud users.

```bash
scullery usr
```

## get

Get user details for a given user:

```bash
scullery usr get username
```

## add

Create user

```bash
scullery usr add [options]
```

Options:

- `--name=username` : User's name, if not specified a random user name
  will be generated.
- `--password=text` : User's password.  If not specified a random
  password will be generated.
- `--email=address` : Default e-mail address for this user
- `--desc=description` : Description for user
- `--group=groupname` : Make the new user member of `groupname`.  This
  option can be used multiple times.

## del

Delete user

```bash
scullery usr del username
```

## group

Use this verb to modify the groups this user belongs to.

### group add

Make this user a member of a group

```bash
scullery usr groupname add username
```

This will make `username` a member of `groupname`.

### group del

Remove this user from a group

```bash
scullery usr groupname del username
```

This will remove `username` from `groupname`.

***
'''
#
# Users recipe
#
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
  ('email',       'Email'),
]

def mod_group(args: argparse.Namespace) -> None:
  '''Add or remove a user from a group'''
  cc = cloud()
  q = cc.iam.groups(args.group)
  if len(q) != 1:
    sys.stderr.write(f'Unmatched group {args.group}\n')
    exit(4)
  group = q[0]
  q = cc.iam.users(args.user)
  if len(q) != 1:
    sys.stderr.write(f'Unmatched user {args.user}\n')
    exit(4)
  user = q[0]
  if args.op == 'add':
    cc.iam.add_group_user(group['id'],user['id'])
  elif args.op == 'del':
    cc.iam.del_group_user(group['id'],user['id'])
  else:
    raise KeyError(args.op)

def list_users(args: argparse.Namespace) -> None:
  '''List all users'''
  cc = cloud()
  data = cc.iam.users()
  # Ensure description key exists for every user (current code did this)
  for u in data:
    u.setdefault('description', '')
  rows = formatters.extract_rows(data, COLUMNS)
  formatters.write_output(rows, COLUMNS, args.format)

def get_user(args: argparse.Namespace) -> None:
  '''Show detailed info for one or more users'''
  cc = cloud()
  for user_name in args.user:
    users = cc.iam.users(user_name)
    if len(users) != 1:
      print(f'{user_name} not matched')
      continue
    u = users[0]

    if args.format == 'terminal':
      print(json.dumps(u, indent=2))
      q = cc.iam.user_groups(u['id'])
      if len(q) > 0:
        print('groups:')
        for g in q:
          print('  {name} {description}'.format(**g))
    else:
      out = dict(u)
      out['groups'] = cc.iam.user_groups(u['id'])
      formatters.write_single_output(out, args.format)

def add_user(args: argparse.Namespace) -> None:
  '''Create a new user'''
  cc = cloud()

  res = usergroup.add_user(cc,
              name = args.name,
              passwd = args.passwd,
              description = args.description,
              email = args.email,
              project = args.project,
              groups = args.group)
  print(yaml.dump(res))

def del_user(args: argparse.Namespace) -> None:
  '''Delete one or more users'''
  cc = cloud()
  for u in args.name:
    try:
      user = cc.iam.users(u)
      if len(user) != 1: raise KeyError(u)
      cc.iam.del_user(user[0]['id'])
      sys.stderr.write(f'Removed user: {u} ({user[0]["id"]})\n')
    except KeyError:
      sys.stderr.write(f'{u}: User not found\n')

def set_passwd(args: argparse.Namespace) -> None:
  '''Set or reset a user password'''
  cc = cloud()

  q = cc.iam.users(args.user)
  if len(q) != 1: raise KeyError(args.user)
  user_id = q[0]['id']
  if args.password is None:
    args.password = cc.iam.gen_user_password()
    print('password', args.password)
  cc.iam.reset_passwd( user_id, args.password, args.set_pwd)

def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the ``users`` sub-parser'''
  pr = subp.add_parser('users',
                        help = 'User recipes',
                        aliases = ['user','usr','u'])
  pr.set_defaults(recipe_cb = list_users)
  formatters.add_format_arg(pr)
  usp = pr.add_subparsers(title='op',
                          description='Operation.  If not spcified, list users.',
                          required = False,
                          help = 'Operation')
  pp = usp.add_parser('get',
                  help = 'Get details for user',
                  aliases = ['g'])
  pp.add_argument('user',
                  help='User to look-up',
                  nargs='+')
  pp.set_defaults(recipe_cb = get_user)
  formatters.add_single_format_arg(pp)

  pp = usp.add_parser('add',
                  help = 'Add user',
                  aliases = ['new','create','a','n','c'])

  pp.add_argument('-P','--password','--passwd', dest = 'passwd',
                  help = 'Password to use (if not specified a random password is used)')
  pp.add_argument('-n','--name', '--user', dest = 'name',
                  help = 'User name to create (it not specified a random name is used)')
  pp.add_argument('-m','-e','--email','--mail', dest = 'email',
                  help = 'Assign e-mail address')
  pp.add_argument('-d','--description','--desc', dest = 'description',
                  help = 'Description for this user')
  pp.add_argument('-p','--project','--proj', dest = 'project',
                  help = 'Include project name in description')
  pp.add_argument('-g','--group','--grp', dest = 'group',
                  action = 'append', default = [],
                  help = 'Assign group (can be specified multiple times)')

  pp.set_defaults(recipe_cb = add_user)

  pp = usp.add_parser('del',
                  help = 'Delete user',
                  aliases = ['rm', 'd','rr'])
  pp.add_argument('name',
                  nargs='+',
                  help='User name to delete')
  pp.set_defaults(recipe_cb = del_user)

  pp = usp.add_parser('group',
                  help = 'Modify user group membership',
                  aliases = ['grp', 'gr'])
  pp.add_argument('group',
                  help='Group to modify')
  pp.add_argument('op',
                  choices=['add','del'],
                  help='Add or Delete operation')
  pp.add_argument('user',
                  help='User to add/del from group')
  pp.set_defaults(recipe_cb = mod_group)

  pp = usp.add_parser('passwd',
                      help = 'set/reset user password',
                      aliases = [ 'reset-passwd', 'password', 'set-passwd', 'pass' ])
  pp.add_argument('-S', '--chg-pwd', dest = 'set_pwd',
                      help = 'Ask password to be changed on first login',
                      action = 'store_true', default = False)
  pp.add_argument('user',
                  help = 'User to modify')
  pp.add_argument('password',
                  nargs='?',
                  help='Password to set (if not specify will use a random string)')
  pp.set_defaults(recipe_cb = set_passwd)





parsers.register_parser('users',parser)

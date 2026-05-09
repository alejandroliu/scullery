#
# ECS recipes
#
'''
## Elastic Cloud Server recipes

List, inspect and control ECS servers, and query available flavors.

```bash
scullery ecs                   # list servers in current project
scullery ecs get <server>      # server details
scullery ecs flavors           # list available flavors
scullery ecs start <server>    # start a server
scullery ecs stop   <server>   # stop (soft) a server
scullery ecs reboot <server>   # reboot (soft) a server
```

Use ``-f`` / ``--force`` with ``stop`` and ``reboot`` for a hard
shutdown / hard reboot.

The ``flavors`` command accepts ``--ram`` (minimum GB, converted to MB
for the API) and ``--disk`` (minimum GB).

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
from scullery.api import ApiSession


# ── Column definitions ─────────────────────────────────────────────

COLUMNS_SERVERS_TTY: formatters.Columns = [
  ('name',   'Name'),
  ('status', 'Status'),
  ('image',  'Image'),
]

COLUMNS_SERVERS_FULL: formatters.Columns = [
  ('name',   'Name'),
  ('id',     'ID'),
  ('status', 'Status'),
  ('image',  'Image'),
]

COLUMNS_FLAVORS_TTY: formatters.Columns = [
  ('name',        'Name'),
  ('description', 'Description'),
  ('vcpus',       'vCPUs'),
  ('ram',         'RAM (GB)'),
]

COLUMNS_FLAVORS_FULL: formatters.Columns = [
  ('id',          'ID'),
  ('name',        'Name'),
  ('description', 'Description'),
  ('vcpus',       'vCPUs'),
  ('ram',         'RAM (GB)'),
]


# ── Helpers ────────────────────────────────────────────────────────

def _find_server(cc: ApiSession, name: str) -> str | None:
  '''Look up a server by name, return its ID (or *None*).'''
  for s in cc.ecs.servers():
    if s.get('name') == name:
      return s['id']
  return None


def _action(cc: ApiSession, server_id: str, action: dict) -> None:
  '''Send a server action (start/stop/reboot) via the ECS API.'''
  project_id = cc.project_id()
  url = f'v2.1/{project_id}/servers/{server_id}/action'
  resp = cc.post(cc.ecs.api_path(url), json=action)
  resp.raise_for_status()


# ── Commands ───────────────────────────────────────────────────────

def list_ecs(args: argparse.Namespace) -> None:
  '''List ECS servers in the current project scope'''
  cc = cloud(scoped=args.project or True)
  data = cc.ecs.servers(detail=True)

  # Resolve image IDs to human-readable names via IMS, with caching
  img_cache: dict[str, str] = {}
  for s in data:
    img = s.get('image')
    if isinstance(img, dict) and 'id' in img:
      img_id = img['id']
      if img_id not in img_cache:
        try:
          matches = list(cc.ims.images(id=img_id))
          img_cache[img_id] = matches[0].get('name', img_id) if matches else img_id
        except Exception:
          img_cache[img_id] = img_id
      s['image'] = img_cache[img_id]
    else:
      s['image'] = ''

  cols = COLUMNS_SERVERS_TTY if args.format in ('terminal', 'markdown') else COLUMNS_SERVERS_FULL
  rows = formatters.extract_rows(data, cols)
  formatters.write_output(rows, cols, args.format)


def list_flavors(args: argparse.Namespace) -> None:
  '''List available ECS flavors'''
  cc = cloud(scoped=args.project or True)
  params = {}
  if args.ram is not None:
    params['minRam'] = args.ram * 1024  # user says GB, API wants MB
  if args.disk is not None:
    params['minDisk'] = args.disk       # API already expects GB
  data = cc.ecs.flavors(**params)

  if args.format in ('terminal', 'markdown'):
    data = list(data)  # don't mutate the original
    for f in data:
      try:
        f['ram'] = int(int(f['ram']) / 1024)
      except (ValueError, TypeError):
        pass
  cols = COLUMNS_FLAVORS_FULL if args.format in ('json', 'yaml') else COLUMNS_FLAVORS_TTY
  rows = formatters.extract_rows(data, cols)
  formatters.write_output(rows, cols, args.format)


def get_ecs(args: argparse.Namespace) -> None:
  '''Show detailed info for one or more ECS servers'''
  cc = cloud(scoped=args.project or True)
  all_servers = cc.ecs.servers(detail=True)
  for name in args.server:
    found = [s for s in all_servers if s.get('name') == name]
    if not found:
      print(f'{name}: server not found')
      continue
    for s in found:
      formatters.write_single_output(s, args.format)


def start_ecs(args: argparse.Namespace) -> None:
  '''Start one or more ECS servers'''
  cc = cloud(scoped=args.project or True)
  for name in args.server:
    sid = _find_server(cc, name)
    if sid is None:
      print(f'{name}: server not found')
      continue
    _action(cc, sid, {'os-start': {}})
    print(f'{name}: started')


def stop_ecs(args: argparse.Namespace) -> None:
  '''Stop one or more ECS servers'''
  cc = cloud(scoped=args.project or True)
  action_type = 'HARD' if args.force else 'SOFT'
  for name in args.server:
    sid = _find_server(cc, name)
    if sid is None:
      print(f'{name}: server not found')
      continue
    _action(cc, sid, {'os-stop': {'type': action_type}})
    print(f'{name}: stopped')


def reboot_ecs(args: argparse.Namespace) -> None:
  '''Reboot one or more ECS servers'''
  cc = cloud(scoped=args.project or True)
  action_type = 'HARD' if args.force else 'SOFT'
  for name in args.server:
    sid = _find_server(cc, name)
    if sid is None:
      print(f'{name}: server not found')
      continue
    _action(cc, sid, {'reboot': {'type': action_type}})
    print(f'{name}: rebooted')


# ── Parser ─────────────────────────────────────────────────────────

def parser(subp: argparse.ArgumentParser) -> None:
  '''Register the ``ecs`` sub-parser'''
  pr = subp.add_parser('ecs',
                       help='Elastic Cloud Server management',
                       aliases=['elastic-cloud-server'])
  pr.add_argument('--project',
                  help='Project name to scope credentials')
  pr.set_defaults(recipe_cb=list_ecs)
  formatters.add_format_arg(pr)

  sp = pr.add_subparsers(title='op',
                         description='Operation.  If not specified, list servers.',
                         required=False,
                         help='Operation')

  # -- flavors ----------------------------------------------------------
  pp = sp.add_parser('flavors',
                     help='List available flavors',
                     aliases=['fl'])
  pp.add_argument('--ram', type=int, default=None,
                  help='Minimum memory in GB')
  pp.add_argument('--disk', type=int, default=None,
                  help='Minimum disk size in GB')
  formatters.add_format_arg(pp)
  pp.set_defaults(recipe_cb=list_flavors)

  # -- get --------------------------------------------------------------
  pp = sp.add_parser('get',
                     help='Get details for a server',
                     aliases=['g'])
  pp.add_argument('server', nargs='+', help='Server name(s)')
  formatters.add_single_format_arg(pp)
  pp.set_defaults(recipe_cb=get_ecs)

  # -- start ------------------------------------------------------------
  pp = sp.add_parser('start',
                     help='Start a server',
                     aliases=['on'])
  pp.add_argument('server', nargs='+', help='Server name(s)')
  pp.set_defaults(recipe_cb=start_ecs)

  # -- stop -------------------------------------------------------------
  pp = sp.add_parser('stop',
                     help='Stop a server',
                     aliases=['off'])
  pp.add_argument('--force', '-f', action='store_true', default=False,
                  help='Force hard shutdown')
  pp.add_argument('server', nargs='+', help='Server name(s)')
  pp.set_defaults(recipe_cb=stop_ecs)

  # -- reboot -----------------------------------------------------------
  pp = sp.add_parser('reboot',
                     help='Reboot a server',
                     aliases=['restart'])
  pp.add_argument('--force', '-f', action='store_true', default=False,
                  help='Force hard reboot')
  pp.add_argument('server', nargs='+', help='Server name(s)')
  pp.set_defaults(recipe_cb=reboot_ecs)


parsers.register_parser('ecs', parser)

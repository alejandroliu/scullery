#
# Curler recipe
#
'''
## Curler recipes

Does curl style command calls but will use the currently configured
authentication.

```bash
scullery GET URL
```

'''

import argparse

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from scullery import cloud
from scullery import formatters
from scullery import parsers

def run(args: argparse.Namespace) -> None:
  cc = cloud(scoped=args.scoped)

  if args.verb == 'GET':
    resp = cc.get(args.url)
  elif args.verb == 'DELETE':
    resp = cc.delete(args.url)
  elif args.verb == 'PUT':
    resp = cc.put(args.url, data=args.body)
  elif args.verb == 'POST':
    resp = cc.post(args.url, data=args.body)
  else:
    raise NotImplementedError(args.verb)

  # Validate
  try:
    resp.raise_for_status()
  except Exception:
    print(resp.text, end='' if resp.text.endswith('\n') else '\n')
    raise

  # Format output
  body = resp.text
  if body:
    try:
      data = resp.json()
    except Exception:
      data = body
    formatters.write_single_output(data, args.format)
  else:
    print(resp.status_code)

def parser_factory(subp: argparse.ArgumentParser, verb:str, has_body:bool = False) -> None:
  '''Register `curler` sub parsers'''
  pr = subp.add_parser(verb,
                       help=f'Raw {verb} API call'
                       )
  scope_grp = pr.add_mutually_exclusive_group()
  scope_grp.add_argument('--scoped',
                          dest='scoped',
                          action='store_const',
                          const=True,
                          default=None,
                          help='Use scoped credentials (default project)')
  scope_grp.add_argument('--unscoped',
                          dest='scoped',
                          action='store_const',
                          const=None,
                          help='Use Unscoped credentials')
  scope_grp.add_argument('--project',
                          dest='scoped',
                          type=str,
                          help='Use scoped credentials for specific project')
  pr.add_argument('url',
                  help='URL to reach')
  if has_body:
    pr.add_argument('body',
                  help='Body for API call')
  formatters.add_single_format_arg(pr, default='yaml')
  pr.set_defaults(recipe_cb=run, verb = verb)



parsers.register_parser('GET', lambda subp: parser_factory(subp, 'GET'))
parsers.register_parser('DELETE', lambda subp: parser_factory(subp, 'DELETE'))
parsers.register_parser('PUT', lambda subp: parser_factory(subp, 'PUT', True))
parsers.register_parser('POST', lambda subp: parser_factory(subp, 'POST', True))


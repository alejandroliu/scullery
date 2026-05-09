'''Show proxy config

'''

import argparse
import os

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from scullery import parsers


def show_proxy(autocfg:bool, debug:bool = False) -> None:
  '''Handle show proxy sub-command

  :param autocfg: Perform auto configuration
  :param debug: Show extra details
  '''
  if autocfg:
    proxy, url, jstext = proxycfg.proxy_auto_cfg()
    print(f'Auto config URL: {url}')
    print(f'Proxy: {proxy}')
    if debug: print(f'Javascript:\n{jstext}')
  else:
    print('No proxy autoconfiguration')
    if 'http_proxy' in os.environ: print('http_proxy:  {http_proxy}'.format(http_proxy=os.environ['http_proxy']))
    if 'https_proxy' in os.environ: print('https_proxy: {https_proxy}'.format(https_proxy=os.environ['https_proxy']))

def run(args:argparse.Namespace):
  '''Entry point for this recipe
  '''
  show_proxy(args.autocfg, args.debug)

def parser(subp):
  pr = subp.add_parser('show-proxy-cfg',
            help = 'Show proxy auto configuration',
            aliases = ['spc','showproxy'])
  pr.set_defaults(recipe_cb = run)


parsers.register_parser('showproxy',parser)



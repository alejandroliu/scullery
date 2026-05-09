#!/usr/bin/env python3
''' Scullery command line

'''
import os
import sys

from argparse import ArgumentParser

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

if '__file__' in globals():
  sys.path.append(os.path.join(os.path.dirname(__file__),'..'))

import scullery
from scullery import proxycfg
from scullery import parsers
from scullery import api

from scullery import rcp_buckets
from scullery import rcp_ims
from scullery import rcp_groups
from scullery import rcp_kermit
from scullery import rcp_projects
from scullery import rcp_rms
from scullery import rcp_roles
from scullery import rcp_showcfg
from scullery import rcp_tms
from scullery import rcp_users
from scullery import rcp_deh
from scullery import rcp_ecs

from scullery import cloud

def cmd_cli():
  ''' Command Line Interface argument parser '''
  cli = ArgumentParser(
                        prog=scullery.__meta__.name,
                        description=scullery.__meta__.description,
                        fromfile_prefix_chars = '@',
                      )

  cli.add_argument('-A','--autocfg',help='Use WinReg to configure proxy', action='store_true', default = False)
  cli.add_argument('-C','--cloud', help='Specify default cloud config')
  cli.add_argument('-V','--version', action='version', version='%(prog)s '+ scullery.VERSION)
  cli.add_argument('-d', '--debug', help='Turn on debugging options', action='store_true', default = False)

  subp = cli.add_subparsers(
                    title ='recipe',
                    description = 'Recipe to execute',
                    required = False,
                    help = 'Run a recipe')
  for _, fact in sorted(parsers.PARSER_FACTORY.items()):
    fact(subp)

  return cli

def main(argv:list[str]) -> None:
  '''Main script entry point

  :param argv: Command line arguments
  '''
  cli = cmd_cli()
  args = cli.parse_args(argv)

  if args.debug: api.http_logging()
  if args.cloud is not None: scullery.defaults['cloud'] = args.cloud

  if not hasattr(args,'recipe_cb'):
    cli.print_help()
  else:
    args.recipe_cb(args)
  scullery.clean_up()

###################################################################
#
# Main command line
#
###################################################################

if __name__ == '__main__':
  main(sys.argv[1:])

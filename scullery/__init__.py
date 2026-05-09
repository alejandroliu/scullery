#!/usr/bin/env python3
''' Recipe runner

'''

import os
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

saved_path = list(sys.path)
''' _private_
:meta private:
'''
sys.path.append(os.path.dirname(__file__))

from version import VERSION
import __meta__

import creds
import api

sys.path = saved_path
del saved_path

clouds = {}
'''Dictionary keeping cloud connections'''

defaults = {
  'cloud': None,
}
'''Default options'''
#
# Support functions
#
def cloud(cloud_name: str = '', scoped=None, **kwargs) -> api.ApiSession:
  '''Return connections to clouds

  :param cloud_name: Cloud to configure
  :param scoped: ``None`` for unscoped token, ``True`` for token scoped to
                 the root region project, or a project name string to scope
                 the token to that specific project.
  :param **kwargs: optional credentials to use
  :returns: An API session
  '''
  if scoped is True:
    scoped_key = ':scoped'
  elif isinstance(scoped, str):
    scoped_key = f':scoped={scoped}'
  elif scoped is None or scoped is False:
    scoped_key = ''
  else:
    raise TypeError(f'Invalid scoped value: {scoped!r}')

  cloud_id = f'{cloud_name if cloud_name != "" else defaults["cloud"]}{scoped_key}'

  if not cloud_id in clouds:
    fopts = dict(kwargs)
    if cloud_name != '':
      fopts['cloud_name'] = cloud_name
    elif 'cloud_name' not in fopts:
      fopts['cloud_name'] = defaults['cloud'] # Default cloud
    cloud_creds = creds.creds(**fopts)
    clouds[cloud_id] = api.ApiSession(cloud_creds, scoped)

  return clouds[cloud_id]

def clean_up()->None:
  '''Clean-up all connections'''
  keys = list(clouds.keys())
  for k in keys:
    del clouds[k]

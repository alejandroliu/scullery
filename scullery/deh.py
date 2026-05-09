#!python3
#
# DeH functionality
#
'''Dedicated Hosts'''


try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

class Deh:
  '''Main class for DeH'''
  API_HOST = 'deh.{region}.otc.t-systems.com'
  '''API End-point'''

  def api_path(self, path) -> str:
    '''API URL path'''
    host = Deh.API_HOST.format(region = self.session.region)
    return f'https://{host}/{path}'

  def __init__(self, session) -> None:
    '''Constructor'''
    self.session = session

  def deh_types(self, az:str|int) -> list:
    '''Query Flavors

    :param az: AZ to query
    :returns: list of deh types
    :raises RuntimeError: on error

    Will query and return a list deh types.

    '''
    if isinstance(az,int):
      aznum = f'-{az:02}'
      azs = self.session.ecs.availability_zones()
      for i in azs:
        if i.endswith(aznum):
          az = i
          break
      else:
        raise KeyError(az)

    region_id = self.session.region_id()

    url = f'v1.0/{region_id}/availability-zone/{az}/dedicated-host-types'
    resp = self.session.get(self.api_path(url))
    resp.raise_for_status()
    data = resp.json()

    return data['dedicated_host_types']


if __name__ == '__main__':
  import api
  import creds
  import yaml
  cfg = creds.creds(cloud_name = 'otc-eu-de')
  # ~ ic(cfg)
  # ~ api.http_logging(1)
  api = api.ApiSession(cfg, True)
  deh = Deh(api)

  for deh_types in deh.deh_types(2):
    print('{host_type} {host_type_name}'.format(**deh_types))
  # ~ for img in ims.images(__imagetype = 'gold'):
    # ~ print('{name} - {id}'.format(**img))


  # ~ for tt in api.tms.tags():
    # ~ print(tt['key'],'=',tt['value'])


  del(api)



#!python3
#
# ECS functionality
#
'''Elastic Cloud servers'''

from typing import Any

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

class ACTION:
  START = { 'os-start': {} }
  SOFT_REBOOT = { 'reboot': { 'type' : 'SOFT' } }
  HARD_REBOOT = { 'reboot': { 'type' : 'HARD' } }
  SOFT_STOP = { 'os-stop': { 'type' : 'SOFT' } }
  HARD_STOP = { 'os-stop': { 'type' : 'HARD' } }

class Ecs:
  '''Main class for ECS'''
  API_HOST = 'ecs.{region}.otc.t-systems.com'
  '''API End-point'''

  def api_path(self, path) -> str:
    '''API URL path'''
    host = Ecs.API_HOST.format(region = self.session.region)
    return f'https://{host}/{path}'

  def __init__(self, session) -> None:
    '''Constructor'''
    self.session = session

  def availability_zones(self) -> dict[str,Any]:
    region_id = self.session.region_id()

    resp = self.session.get(self.api_path(f'v2/{region_id}/os-availability-zone'))
    resp.raise_for_status()
    res = dict()
    for zone in resp.json()['availabilityZoneInfo']:
      res[zone['zoneName']] = {
                        'available': zone['zoneState']['available'],
                        'hosts': zone['hosts'],
                      }
    return res

  def action(self, server_id:str, action:Any):
    project_id = self.session.project_id()
    url = f'v2.1/{project_id}/servers/{server_id}/action'
    resp = self.session.get(self.api_path(url), params = kwargs)
    resp.raise_for_status()
    data = resp.json()

  def servers(self, detail:bool = False, **kwargs) -> list:
    # https://docs.otc.t-systems.com/elastic-cloud-server/api-ref/native_openstack_nova_apis/lifecycle_management/querying_the_ecs_list.html#en-us-topic-0020212688
    # TODO: handle pagination
    # TODO: [flavor][id] -> [flavor_id]
    project_id = self.session.project_id()
    url = f'v2.1/{project_id}/servers'
    if detail: url += '/detail'
    # ~ ic(url, self.session.region_data)
    resp = self.session.get(self.api_path(url), params = kwargs)
    resp.raise_for_status()
    data = resp.json()
    # ~ ic(data)
    return data['servers']


  def flavors(self, **kwargs) -> list:
    '''Query Flavors

    :param kwargs: query args to pass
    :returns: list of flavors
    :raises RuntimeError: on error

    Will query and return a list flavors.

    See https://docs.otc.t-systems.com/elastic-cloud-server/dev-guide/creating_an_ecs.html
    '''
    region_id = self.session.region_id()

    url = f'v2/{region_id}/flavors/detail'
    resp = self.session.get(self.api_path(url), params = kwargs)
    resp.raise_for_status()
    data = resp.json()

    return data['flavors']


if __name__ == '__main__':
  import api
  import creds
  import yaml
  # ~ cfg = creds.creds(cloud_name = 'otc-eu-nl')
  cfg = creds.creds(cloud_name = 'test')
  # ~ ic(cfg)
  # ~ api.http_logging(1)
  api = api.ApiSession(cfg, True)
  ecs = Ecs(api)
  # ~ ic(ecs.availability_zones())

  # ~ for flavor in ecs.flavors():
    # ~ print('{name} {id} ram:{ram} vcpu:{vcpus}'.format(**flavor))
  for vm in ecs.servers(detail = True):
    print('{name} {id} {status}'.format(**vm))
    ic(vm)


  del(api)



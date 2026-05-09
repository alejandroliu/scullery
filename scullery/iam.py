#!python3
#
# IAM functionality
#
'''Implement Indentity and Access Management services'''

import random
import string
import json

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

class Iam:
  '''Main class for IAM'''
  API_HOST = 'iam.{region}.otc.t-systems.com'
  '''API End-point'''

  def api_path(self, path) -> str:
    '''API URL path'''
    host = Iam.API_HOST.format(region = self.session.region)
    return f'https://{host}/{path}'

  def __init__(self, session) -> None:
    '''Constructor'''
    self.session = session
    self.sys_roles = None
    self.usr_roles = None


  def system_roles(self) -> list:
    '''Create a list of system roles

    :returns: list of system roles
    :raises RuntimeError: on error

    Will query and return a list of system roles.  The list is cached
    within the process
    '''
    if self.sys_roles is None:
      resp = self.session.get(self.api_path('v3/roles'))
      if resp.status_code != 200 or not 'roles' in resp.json():
        raise RuntimeError(resp.text)
      self.sys_roles = resp.json()['roles']
    return self.sys_roles

  def custom_roles(self) -> list:
    '''Create a list of custom roles

    :returns: list of custom roles
    :raises RuntimeError: on error

    Will query and return a list of custom roles.  The list is cached
    within the process
    '''
    if self.usr_roles is None:
      resp = self.session.get(self.api_path('v3.0/OS-ROLE/roles'))
      if resp.status_code != 200 or not 'roles' in resp.json():
        raise RuntimeError(resp.text)
      self.usr_roles = resp.json()['roles']
    return self.usr_roles

  def get_role(self, name:str) -> dict:
    '''Returns the defintion of a role

    :param name: name or display_name of a role
    :returns: dict with role data
    :raises KeyError: if role does not exist.

    Returns a role from a `name`.  The role can be either a system
    or a custom role.
    '''
    self.custom_roles()
    for role in self.usr_roles:
      if role['name'] == name or ('display_name' in role and role['display_name'] == name): return role
    self.system_roles()
    for role in self.sys_roles:
      if role['name'] == name or ('display_name' in role and role['display_name'] == name): return role
    raise KeyError(f'Role "{name}" not found')

  def new_role(self, *, display_name:str, policy:dict|list, role_type:str = 'XA', description:str|None = None) -> dict:
    '''Create a new custom role

    :param display_name: custom role name
    :param policy: Policy specification
    :param role_type: `AX` (account level) or `XA` (project level).  Defaults to `XA`.
    :param description: Role description
    :raises RuntimeError: on error

    Will define a custom role.  See
    [REST API](https://docs.otc.t-systems.com/identity-access-management/api-ref/apis/custom_policy_management/creating_a_custom_policy.html)

    The policy specifcation can be specified as a `dict`, which then needs
    to contain:

    - `Version`: which must be set to `1.1`.
    - `Statement`:  list of policy statements.

    If the policy specification is a `list`, `Version` defaults as `1.1`
    and the list is used for `Statement` policy statements.

    Policy statements:

    - `Action`: array strings with specific operation permissions
    - `Effect`: string with `Allow` or `Deny` values
    - `Resource`: Optional resource reference
    '''
    if description is None: description = f'Custom policy {display_name}'
    if isinstance(policy,list):
      policy = { 'Statement': policy, 'Version': '1.1' }
    else:
      if not 'Version' in policy: policy['Version'] = '1.1'
    resp = self.session.post(self.api_path('v3.0/OS-ROLE/roles'), json = {
      'role': {
        'display_name': display_name,
        'type': role_type,
        'description': description,
        'policy': policy,
      }
    })
    if resp.status_code != 201 or not 'role' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['role']

  def del_role(self, role_id:str) -> None:
    '''Delete the role by ID

    :param role_id: role to delete
    '''
    resp = self.session.delete(self.api_path(f'v3.0/OS-ROLE/roles/{role_id}'))
    if not resp.status_code in [200, 204]:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def users(self, name:str|None = None) -> list:
    '''Get a list of users

    :param name: match users by name
    :returns: list of users
    :raises RuntimeError: on error

    Returns a list of all users.  If name is specified, only that user
    will be returned.
    '''
    params = dict() if name is None else { 'params': { 'name': name } }
    resp = self.session.get(self.api_path('v3/users'), **params)
    if resp.status_code != 200 or not 'users' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['users']

  def user_groups(self, usrid:str) -> list:
    '''Return the groups a user belongs to

    :param usrid: user to query
    :returns: list of groups the user belongs to
    :raises RuntimeError: on error
    '''
    resp = self.session.get(self.api_path(f'v3/users/{usrid}/groups'))
    if resp.status_code != 200 or not 'groups' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['groups']

  def new_user(self, **kwargs) -> str:
    '''Create a new user

    :params name: (Mandatory) new user name which consists of 1 to 32 characters. It can contain letters, digits, spaces, hyphens (-), underscores (_), and periods (.) and cannot start with a digit or space.
    :params domain_id: (Mandatory) Account ID to use.  You can use {py:obj}`scullery.iam.Iam.domain` or {py:obj}`scullery.iam.Iam.domains` to get a possible domain ids.
    :params password: Password.  Must be between 6 to 32 characters.  Contain at least two character types out of uppercase, lowercase, digits and special characters.
    :params email: Email address (max 255 characters)
    :params areacode: Telephone country code
    :params phone: Mobile phone (max 32 digits)
    :params enabled: Enabling status of user (defaults to True)
    :params pwd_status: If True the passwords needs to be reset on first login.  Defaults to True.
    :params description: Description of user
    :returns: ID of created user
    :raises RuntimeError: on error

    Creates a new IAM user using
    [REST API](https://docs.otc.t-systems.com/identity-access-management/api-ref/apis/user_management/creating_an_iam_user_recommended.html)

    Note that the paramaters `xuser_id` and `xuser_type` are available
    but this API does not implement them.
    '''
    resp = self.session.post(self.api_path('v3.0/OS-USER/users'), json = { 'user': kwargs })
    if resp.status_code != 201 or not 'user' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['user']['id']

  def del_user(self, usr_id:str) -> None:
    '''Delete user

    :param usr_id: ID of user to delete
    :raises RuntimeError: on error
    '''
    resp = self.session.delete(self.api_path(f'v3/users/{usr_id}'))
    if not resp.status_code in [200, 204]:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def reset_passwd(self, usr_id:str, password:str,pwd_status:bool = True):
    '''Used to reset a password for a user.

    :params usr_id: (Mandatory) ID of user to reset the password off
    :params password: Password.  Must be between 6 to 32 characters.  Contain at least two character types out of uppercase, lowercase, digits and special characters.
    :params pwd_status: If True the passwords needs to be reset on first login.  Defaults to True.
    :raises RuntimeError: on error
    '''
    ic(pwd_status)
    resp = self.session.patch(self.api_path(f'v3/users/{usr_id}'),
                                  json = {
                                    'user': {
                                      'password': password,
                                      'pwd_status': pwd_status,
                                    }
                                  })
    resp.raise_for_status()
    return resp.json()['user']

  def groups(self, name:str|None = None) -> list:
    '''Return a list of groups

    :param name: If specified only return the groups matching name
    :returns: List of groups
    :raises RuntimeError: on error
    '''
    params = dict() if name is None else { 'params': { 'name': name } }
    resp = self.session.get(self.api_path('v3/groups'), **params)
    if resp.status_code != 200 or not 'groups' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['groups']

  def group_users(self, grpid:str) -> list:
    '''Return the members of a group as a list of users

    :param grpid: ID of group to query
    :returns: list of users
    :raises RuntimeError: on error
    '''
    resp = self.session.get(self.api_path(f'v3/groups/{grpid}/users'))
    if resp.status_code != 200 or not 'users' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['users']

  def new_group(self, name:str, description:str|None = None) -> str:
    '''Create new group

    :param name: Name for new group
    :param description: Optional description of group
    :returns: ID of the newly created grouip
    :raises RuntimeError: on error

    Create a new group.  The group will not have any roles nor members
    and need to be assigned using:

    - {py:obj}`scullery.iam.Iam.grant_project_group_perms`
    - {py:obj}`scullery.iam.Iam.add_group_user`

    '''
    payload = { 'name': name }
    if not description is None: payload['description'] = description
    resp = self.session.post(self.api_path('v3/groups'), json=dict(group=payload))
    if resp.status_code != 201 or not 'group' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['group']['id']

  def del_group(self, grp_id:str) -> None:
    '''Delete group

    :param grp_id: group id to delete
    :raises RuntimeError: on error
    '''
    resp = self.session.delete(self.api_path(f'v3/groups/{grp_id}'))
    if not resp.status_code in [200, 204]:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def add_group_user(self, grp_id:str, usr_id:str) -> None:
    '''Add user member to group

    :param grp_id: Group ID to modify
    :param usr_id: User ID of new member to group
    :raises RuntimeError: on error
    '''
    resp = self.session.put(self.api_path(f'v3/groups/{grp_id}/users/{usr_id}'))
    if resp.status_code != 204:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def del_group_user(self, grp_id:str, usr_id:str) -> None:
    '''Delete user group member

    :param grp_id: Group ID to modify
    :param usr_id: User ID of new member to group
    :raises RuntimeError: on error
    '''
    resp = self.session.delete(self.api_path(f'v3/groups/{grp_id}/users/{usr_id}'))
    if resp.status_code != 204:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def domain(self, context:str|None = None, output:dict|None = None) -> str:
    '''Get the domain for a given project/region/or user default

    :param context: Either a project name, region name or None
    :returns: Domain ID
    :raises KeyError: If no matching project or record
    :raises RuntimeError: on API errors

    It will return a domain ID of a project or region.  If
    `context is **NOT** specified, it will return the default
    domain ID of the logged in user.
    '''
    if context is None:
      q = self.domains()
      for d in q:
        if d['name'] == self.session.domain_name: return d['id']
      if len(q) > 0: return q[0]['id']
    q = self.projects(context)
    if len(q) == 0: raise KeyError(f'Unable to match "{context}"')
    if output is not None: output.update(q[0])
    return q[0]['domain_id']

  def domains(self) -> list:
    '''Return domains that the current user has access to

    :returns: list of domains
    :raises RuntimeError: on error
    '''
    resp = self.session.get(self.api_path('v3/auth/domains'))
    if resp.status_code != 200 or not 'domains' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['domains']

  def get_domain_group_perms(self, domid:str, grpid:str) -> list:
    '''Returns domain permissions assigned to a group

    :param domid: Domain ID to query
    :param grpid: Group ID to query
    :returns: List of roles assigned to group in the given domain
    :raises RuntimeError: on error
    '''
    path = f'v3/domains/{domid}/groups/{grpid}/roles'
    resp = self.session.get(self.api_path(path))
    if resp.status_code != 200 or not 'roles' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['roles']

  def get_project_group_perms(self, prjid:str, grpid:str) -> list:
    '''Returns project permissions assigned to a group

    :param prjid: Project ID to query
    :param grpid: Group ID to query
    :returns: List of roles assigned to group in the given project
    :raises RuntimeError: on error
    '''
    path = f'v3/projects/{prjid}/groups/{grpid}/roles'
    resp = self.session.get(self.api_path(path))
    if resp.status_code != 200 or not 'roles' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['roles']

  def grant_project_group_perms(self, prjid:str, grpid:str, roleid:str):
    '''Grants a role on project to a group

    :param prjid: Project ID
    :param grpid: Group ID
    :param roleid: Role ID
    :raises RuntimeError: on error
    '''
    resp = self.session.put(self.api_path(f'v3/projects/{prjid}/groups/{grpid}/roles/{roleid}'))
    if resp.status_code != 204:
      raise RuntimeError(resp.text if resp.text else resp.reason)
  def revoke_project_group_perms(self, prjid:str, grpid:str, roleid:str):
    '''Revoke a role on project from a group

    :param prjid: Project ID
    :param grpid: Group ID
    :param roleid: Role ID
    :raises RuntimeError: on error
    '''
    resp = self.session.delete(self.api_path(f'v3/projects/{prjid}/groups/{grpid}/roles/{roleid}'))
    if resp.status_code != 204:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def projects(self, name:str|None = None) -> list:
    '''Return a list of projects

    :param name: Optional name to match
    :returns: List of matching projects
    :raises RuntimeError: on error
    '''
    params = dict() if name is None else { 'params': { 'name': name } }
    resp = self.session.get(self.api_path('v3/projects'), **params)
    if resp.status_code != 200 or not 'projects' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['projects']

  def get_project_details(self, prj_id:str) -> dict:
    '''Return a dictionary with project details

    :param prj_id: Project ID to query
    :returns: dictionary with project attributes
    :raises RuntimeError: on error

    Returns details for a project.  Note that {py:obj}`scullery.iam.Iam.projects`
    also returns some details, it does not show the project `status`
    accurately.  For that you need to use this REST API call.
    '''
    resp = self.session.get(self.api_path(f'v3-ext/projects/{prj_id}'))
    if resp.status_code != 200 or not 'project' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['project']

  def new_project(self, name:str, parent_id:str, description:str|None = None) -> str:
    '''Create a new project

    :param name: new project name
    :param parent_id: Parent project for the newly created project
    :param description: Project description
    :returns: ID of newly created project
    :raises RuntimeError: on error

    Create a new project.  The project name **must** include the region
    for example:  `eu-nl_newprojectname`.

    The `parent_id` is mandatory.  Nornally you would use hte ID of
    the project for the parent region, e.g. the Project ID or
    `eu-de` or `eu-nl`.
    '''
    payload = {
      'name': name,
      'parent_id': parent_id,
    }
    if not description is None: payload['description'] = description
    resp = self.session.post(self.api_path('v3/projects'), json = dict(project = payload))
    if resp.status_code != 201 or not 'project' in resp.json():
      raise RuntimeError(resp.text)
    return resp.json()['project']['id']

  def del_project(self, prj_id:str) -> None:
    '''Delete project

    :param prj_id: ID of project to delete
    :raises RuntimeError: on error

    *NOTE* deleting a project takes over 30 minutes to complete.
    '''
    resp = self.session.delete(self.api_path(f'v3/projects/{prj_id}'))
    if not resp.status_code in [200, 204]:
      raise RuntimeError(resp.text if resp.text else resp.reason)

  def gen_user_name(self, length = 8) -> str:
    '''Generate a random user name
    :param length: user name's length.  Defaults to 8
    :returns: generated random user
    '''
    return ''.join(random.sample(string.ascii_lowercase*length,length))
  def gen_user_password(self, length = 24) -> str:
    '''Generate a random password
    :param length: password's length.  Defaults to 24
    :returns: generated random password
    '''
    return ''.join(random.sample((string.ascii_lowercase + string.ascii_uppercase + string.digits)*length, length))

  def get_aksk(self, duration_seconds:int = 900):
    '''Issue a AK/SK pair

    :param duration_seconds: AK/SK validity (defaults to 900 seconds/15 minutes
    :returns: AK,SK token
    :raises RuntimeError: if the session has no token (e.g. AK/SK auth mode)
    '''
    if self.session.token is None:
      raise RuntimeError(
        'Cannot issue AK/SK: session has no bearer token. '
        'This session is using AK/SK or federated authentication.'
      )
    resp = self.session.post(self.api_path('v3.0/OS-CREDENTIAL/securitytokens'),
            data = json.dumps({
                'auth': {
                  'identity': {
                    'methods': [ 'token' ],
                    'token': {
                      'id': self.session.token,
                      'duration_seconds': duration_seconds,
                    },
                  }
                }
              }))
    resp.raise_for_status()
    return resp.json()['credential']



if __name__ == '__main__':
  import api
  import creds
  import yaml

  api.http_logging()
  cfg = creds.creds(cloud_name = 'otc-eu-de')
  api = api.ApiSession(cfg)
  iam = Iam(api)

  del(api)



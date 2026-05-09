#!python3
#
# API sessions
#
'''REST API session implementation'''
import datetime
import hashlib
import hmac
import json
import os
import requests
from requests.auth import AuthBase
from urllib.parse import urlparse, quote, urlencode, parse_qsl
import shlex
import subprocess
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

import deh
import ecs
import iam
import ims
import obs
import tms
import rms

from creds import STR as CRSTR

# ====================================================================
# Auth-type detection  (mirrors the logic in creds.py)
# ====================================================================

def _detect_auth_type(creds: dict) -> str | None:
  '''Determine the authentication method present in *creds*.

  Terraform / OTC precedence: ``token > aksk > agency > password``.

  .. note::
     Federated identities are **not** handled inside this module.
     Use a dedicated IdP script to obtain an unscoped token, then
     call :meth:`iam.Iam.get_aksk` to get temporary AK/SK credentials,
     which can be consumed via the ``aksk`` path with ``security_token``.
  '''
  if CRSTR.TOKEN in creds:
    return 'token'
  if CRSTR.ACCESS_KEY in creds and CRSTR.SECRET_KEY in creds:
    return 'aksk'
  if CRSTR.AGENCY_NAME in creds:
    return 'agency'
  if (CRSTR.USERNAME in creds or CRSTR.USER_ID in creds) and CRSTR.PASSWORD in creds:
    return 'password'
  return None


# ====================================================================
# OTC SDK-HMAC-SHA256 signer  (for AK/SK authentication)
# ====================================================================

class OTCAkSkAuth(AuthBase):
  '''OTC/Huawei Cloud SDK-HMAC-SHA256 request signer.

  Works with both permanent and temporary AK/SK credentials.
  Pass *security_token* when using temporary credentials from the
  metadata endpoint.

  :param ak: Access Key
  :param sk: Secret Key
  :param security_token: Optional temporary security token
  '''

  def __init__(self, ak: str, sk: str, security_token: str | None = None) -> None:
    self.ak = ak
    self.sk = sk
    self.security_token = security_token

  def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
    dt = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    r.headers['X-Sdk-Date'] = dt
    if self.security_token:
      r.headers['X-Security-Token'] = self.security_token

    parsed = urlparse(r.url)
    uri = quote(parsed.path or '/', safe='/-_.~')
    if not uri.endswith('/'):
      uri += '/'

    query_params = sorted(parse_qsl(parsed.query, keep_blank_values=True))
    canonical_query = urlencode(query_params)

    host = parsed.netloc
    headers_to_sign = {'host': host, 'x-sdk-date': dt}
    ct = r.headers.get('Content-Type', '')
    if ct:
      headers_to_sign['content-type'] = ct
    if self.security_token:
      headers_to_sign['x-security-token'] = self.security_token

    sorted_headers = sorted(headers_to_sign.items())
    canonical_headers = ''.join(f'{k}:{v}\n' for k, v in sorted_headers)
    signed_headers = ';'.join(k for k, _ in sorted_headers)

    body = r.body or b''
    if isinstance(body, str):
      body = body.encode('utf-8')
    payload_hash = hashlib.sha256(body).hexdigest()

    canonical_request = '\n'.join([
      r.method.upper(),
      uri,
      canonical_query,
      canonical_headers,
      signed_headers,
      payload_hash,
    ])

    hashed_cr = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
    string_to_sign = f'SDK-HMAC-SHA256\n{dt}\n{hashed_cr}'

    signature = hmac.new(
      self.sk.encode('utf-8'),
      string_to_sign.encode('utf-8'),
      hashlib.sha256,
    ).hexdigest()

    r.headers['Authorization'] = (
      f'SDK-HMAC-SHA256 Access={self.ak}, '
      f'SignedHeaders={signed_headers}, Signature={signature}'
    )
    return r


# ====================================================================
# Helpers
# ====================================================================

def http_logging(level: int = 1) -> None:
  '''Enable HTTP request logging

  :param level: Debug level (defaults to ``1``)
  '''
  import http.client
  http.client.HTTPConnection.debuglevel = level


def token_shutdown_posix(url: str, token: str) -> None:
  '''INTERNAL: Handle abnormal shutdown on POSIX systems'''
  os.system(shlex.join(['curl', '-k',
                        '-H', f'X-Auth-Token: {token}',
                        '-H', f'X-Subject-Token: {token}',
                        '-X', 'DELETE', url]))


def token_shutdown_win(url: str, token: str) -> None:
  '''INTERNAL: Handle abnormal shutdown on non-POSIX systems'''
  try:
    rc = subprocess.run(['curl', '-k',
                         '-H', f'X-Auth-Token: {token}',
                         '-H', f'X-Subject-Token: {token}',
                         '-X', 'DELETE', url])
    if rc.returncode != 0:
      sys.stderr.write(f'Exit code: {rc.returncode}\n')
  except Exception as e:
    sys.stderr.write(str(e) + '\n')


if os.name == 'posix':
  token_shutdown = token_shutdown_posix
else:
  token_shutdown = token_shutdown_win


def _parse_region_project(creds: dict) -> tuple[str, str | None]:
  '''Extract region and optional project_name from *creds*.

  Returns ``(region, project_name)``.
  '''
  project = creds.get(CRSTR.PROJECT_NAME) or creds.get(CRSTR.REGION_NAME) or ''
  if '_' in project:
    return project.split('_', 1)[0], project
  return project, None


# ====================================================================
# Main API session
# ====================================================================

class ApiSession:
  '''API Session — supports multiple authentication methods.

  Supported methods (matching the Terraform OpenTelekomCloud provider):

  * ``password`` — username + password (gets a token from IAM)
  * ``token``    — use an existing bearer token directly
  * ``aksk``     — Access Key / Secret Key (signs every request via
                   :class:`OTCAkSkAuth`).  Also used for temporary
                   credentials (with ``security_token``).
  * ``agency``   — assume-role flow using agency credentials

  .. note::
     **Federated identities** are not handled directly.  Use a dedicated
     IdP script to obtain an unscoped token, then call
     ``iam.get_aksk()`` to get temporary AK/SK + ``security_token``
     and pass those to ``aksk`` auth.
  '''

  IAM_HOST = 'iam.{region}.otc.t-systems.com'
  '''API Endpoint for creating session tokens'''

  # ------------------------------------------------------------------
  # URL helpers
  # ------------------------------------------------------------------

  def tokens_api_path(self) -> str:
    '''URL of the IAM token endpoint for the current region.'''
    api_host = ApiSession.IAM_HOST.format(region=self.region)
    return f'https://{api_host}/v3/auth/tokens'

  # ------------------------------------------------------------------
  # Constructor
  # ------------------------------------------------------------------

  def __init__(self, creds: dict, scoped=None) -> None:
    '''Create an authenticated API session.

    :param creds:  Credential dictionary (as returned by :func:`creds.creds`)
    :param scoped: ``None`` or ``False`` for unscoped token, ``True`` for
                   token scoped to the root region project, or a project name
                   string to scope the token to that specific project.
                   (password/token/agency only – ignored for AK/SK)
    '''
    self.token = None
    self.aksk_auth = None
    self.auth_type: str | None = None  # 'password' | 'token' | 'aksk' | 'agency'
    self.cloud_name = creds.get(CRSTR.CLOUD_NAME)

    # 1. Detect the authentication method
    auth_type = _detect_auth_type(creds)
    if auth_type is None:
      raise ValueError(
        'Unrecognised credentials. '
        'Supported: password, token, AK/SK, or agency.'
      )

    # 2. Parse region / project (used by all methods)
    self.region, self.project_name = _parse_region_project(creds)

    # If a project name was explicitly requested via scoped, use it
    # so that project_id() resolves the correct project.
    if isinstance(scoped, str):
      self.project_name = scoped

    # 3. Authenticate
    if auth_type == 'password':
      self._auth_password(creds, scoped)
    elif auth_type == 'token':
      self._auth_token(creds, scoped)
    elif auth_type == 'aksk':
      self._auth_aksk(creds, scoped)
    elif auth_type == 'agency':
      self._auth_agency(creds, scoped)

    # 4. Common metadata
    self.user_name = creds.get(CRSTR.USERNAME) or creds.get(CRSTR.USER_ID, '')
    self.domain_name = (
      creds.get(CRSTR.USER_DOMAIN_NAME)
      or creds.get(CRSTR.PROJECT_DOMAIN_NAME)
      or creds.get(CRSTR.DOMAIN_NAME)
      or ''
    )

    # 5. Create service clients
    self.obs = obs.Buckets(self)
    self.deh = deh.Deh(self)
    self.ecs = ecs.Ecs(self)
    self.iam = iam.Iam(self)
    self.ims = ims.Ims(self)
    self.tms = tms.Tms(self)
    self.rms = rms.Rms(self)

    self.region_data = None
    self.project_data = None

  # ------------------------------------------------------------------
  # Auth-method implementations
  # ------------------------------------------------------------------

  def _auth_password(self, creds: dict, scoped) -> None:
    '''Authenticate with username + password via the IAM token endpoint.'''
    jsdat: dict = {
      'auth': {
        'identity': {
          'methods': ['password'],
          'password': {
            'user': {
              'name': creds[CRSTR.USERNAME],
              'password': creds[CRSTR.PASSWORD],
              'domain': {'name': creds[CRSTR.USER_DOMAIN_NAME]},
            },
          },
        },
      },
    }

    if isinstance(scoped, str):
      # Scope to the specified project
      jsdat['auth']['scope'] = {'project': {'name': scoped}}
      self.scoped = True
    elif self.project_name:
      jsdat['auth']['scope'] = {'project': {'name': self.project_name}}
      self.scoped = True
    elif scoped:
      jsdat['auth']['scope'] = {'project': {'name': self.region}}
      self.scoped = True
    else:
      self.scoped = False

    resp = requests.post(self.tokens_api_path(), json=jsdat)
    if resp.status_code != 201 or 'X-Subject-Token' not in resp.headers:
      raise PermissionError(resp.text)
    self.token = resp.headers['X-Subject-Token']
    self.auth_type = 'password'

  def _auth_token(self, creds: dict, scoped) -> None:
    '''Use a pre-existing bearer token directly (no IAM call).'''
    self.token = creds[CRSTR.TOKEN]
    self.scoped = bool(self.project_name) or bool(scoped)
    self.auth_type = 'token'

  def _auth_aksk(self, creds: dict, scoped) -> None:
    '''Set up AK/SK signing for every API request.

    When using AK/SK no bearer token is obtained – every HTTP request is
    individually signed via :class:`OTCAkSkAuth`.

    Temporary credentials (e.g. from a federated identity flow or from
    :meth:`iam.Iam.get_aksk`) are supported via the *security_token*
    parameter.
    '''
    self.aksk_auth = OTCAkSkAuth(
      ak=creds[CRSTR.ACCESS_KEY],
      sk=creds[CRSTR.SECRET_KEY],
      security_token=creds.get(CRSTR.SECURITY_TOKEN),
    )
    self.token = None  # No token in this mode
    self.scoped = scoped
    self.auth_type = 'aksk'

  def _auth_agency(self, creds: dict, scoped) -> None:
    '''Authenticate via an agency (assume-role) flow.

    Currently a placeholder – raises an error until the agency token
    exchange is fully implemented.
    '''
    raise NotImplementedError(
      'Agency (assume-role) authentication is not yet implemented. '
      'Use password, token, or AK/SK auth instead.'
    )

  # ------------------------------------------------------------------
  # Token / project / region helpers
  # ------------------------------------------------------------------

  def project_id(self) -> str:
    if self.project_name is None:
      return self.region_id()
    if self.project_data is None:
      q = self.iam.projects(name=self.project_name)
      if len(q) != 1:
        raise KeyError(self.project_name)
      self.project_data = q[0]
    return self.project_data['id']

  def region_id(self) -> str:
    if self.region_data is None:
      q = self.iam.projects(name=self.region)
      if len(q) != 1:
        raise KeyError(self.region)
      self.region_data = q[0]
    return self.region_data['id']

  # ------------------------------------------------------------------
  # Cleanup
  # ------------------------------------------------------------------

  def __del__(self) -> None:
    '''Destructor — deletes the session token if one was obtained.'''
    if self.token is None:
      return
    if self.aksk_auth is not None:
      return  # AK/SK mode: nothing to clean up
    if sys.meta_path is None:
      sys.stderr.write('Deleting session while Python is shutting down\n')
      token_shutdown(self.tokens_api_path(), self.token)
    else:
      requests.delete(self.tokens_api_path(), headers={
        'X-Auth-Token': self.token,
        'X-Subject-Token': self.token,
      })

  # ------------------------------------------------------------------
  # REST helpers
  # ------------------------------------------------------------------

  def _request_headers(self) -> dict:
    '''Return the auth headers for the current session mode.'''
    if self.aksk_auth is not None:
      return {}
    return {'X-Auth-Token': self.token}

  def _auth_hook(self):
    '''Return the requests auth handler (OTCAkSkAuth) or None.'''
    return self.aksk_auth

  def get(self, api_url, **kwargs):
    '''HTTP GET'''
    return requests.get(
      api_url, auth=self._auth_hook(),
      headers=self._request_headers(), **kwargs,
    )

  def post(self, api_url, **kwargs):
    '''HTTP POST'''
    return requests.post(
      api_url, auth=self._auth_hook(),
      headers=self._request_headers(), **kwargs,
    )

  def put(self, api_url, **kwargs):
    '''HTTP PUT'''
    return requests.put(
      api_url, auth=self._auth_hook(),
      headers=self._request_headers(), **kwargs,
    )

  def patch(self, api_url, **kwargs):
    '''HTTP PATCH'''
    return requests.patch(
      api_url, auth=self._auth_hook(),
      headers=self._request_headers(), **kwargs,
    )

  def delete(self, api_url, **kwargs):
    '''HTTP DELETE'''
    return requests.delete(
      api_url, auth=self._auth_hook(),
      headers=self._request_headers(), **kwargs,
    )


if __name__ == '__main__':
  import creds
  cfg = creds.creds(cloud_name='otc-de-iam')
  api = ApiSession(cfg)
  ic(api)

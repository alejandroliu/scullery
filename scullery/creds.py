#!/usr/bin/env python3
#
# Credential resolution — Terraform-compatible authentication
#
# Supports the same authentication methods and environment variables as the
# Terraform OpenTelekomCloud provider:
#   Password  |  AK/SK (+ temporary)  |  Token  |  Assume Role  |  clouds.yaml
#
# Precedence (matching Terraform): Token > AK/SK > Password
# Precedence of sources: kwargs > env vars > clouds.yaml
#
import os
import yaml

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa


class STR:
  '''String constants – credential keys and well-known env vars / paths.

  Kept backward-compatible with the previous password-only version so that
  consumers like ``api.py`` continue to work unchanged.
  '''

  # ── Auth methods ──────────────────────────────────────────────
  AUTH_PASSWORD = 'password'
  AUTH_AKSK     = 'aksk'
  AUTH_TOKEN    = 'token'
  AUTH_AGENCY   = 'agency'

  # ── Canonical credential keys (used as dict keys internally) ──
  CLOUD_NAME        = 'cloud_name'
  USER_DOMAIN_NAME  = 'user_domain_name'
  USER_DOMAIN_ID    = 'user_domain_id'
  USERNAME          = 'username'
  USER_ID           = 'user_id'
  PASSWORD          = 'password'
  PROJECT_NAME      = 'project_name'
  PROJECT_ID        = 'project_id'
  PROJECT_DOMAIN_NAME  = 'project_domain_name'
  PROJECT_DOMAIN_ID    = 'project_domain_id'
  DOMAIN_NAME       = 'domain_name'
  DOMAIN_ID         = 'domain_id'
  AUTH_URL          = 'auth_url'
  REGION_NAME       = 'region_name'

  # ── AK/SK ─────────────────────────────────────────────────────
  ACCESS_KEY     = 'access_key'
  SECRET_KEY     = 'secret_key'
  SECURITY_TOKEN = 'security_token'

  # ── Token ─────────────────────────────────────────────────────
  TOKEN = 'token'

  # ── Assume Role ───────────────────────────────────────────────
  AGENCY_NAME        = 'agency_name'
  AGENCY_DOMAIN_NAME = 'agency_domain_name'
  DELEGATED_PROJECT  = 'delegated_project'

  # ── Misc provider options ─────────────────────────────────────
  INSECURE             = 'insecure'
  CACERT_FILE          = 'cacert_file'
  CERT                 = 'cert'
  KEY                  = 'key'
  ENDPOINT_TYPE        = 'endpoint_type'
  ENTERPRISE_PROJECT_ID = 'enterprise_project_id'
  PASSCODE             = 'passcode'
  MAX_RETRIES          = 'max_retries'
  ALLOW_REAUTH         = 'allow_reauth'

  # ── Environment variable names ────────────────────────────────
  ENV_PREFIX         = 'OS_'
  OS_CLIENT_CONFIG_FILE = 'OS_CLIENT_CONFIG_FILE'
  OS_CLOUD           = 'OS_CLOUD'

  # ── File-system paths ─────────────────────────────────────────
  HOME       = 'HOME'
  OS_CFG_HOME = '.config/openstack'
  ETC_CFG    = '/etc/openstack'
  CLOUDS_YAML = 'clouds.yaml'
  SECURE_YAML = 'secure.yaml'
  CLOUDS      = 'clouds'
  AUTH        = 'auth'


# ---------------------------------------------------------------------------
# Environment-variable mapping
#   Terraform config key -> list of OS_* env var names (first wins)
# ---------------------------------------------------------------------------
ENV_MAP = {
  STR.USERNAME:             ['OS_USERNAME'],
  STR.USER_ID:              ['OS_USER_ID'],
  STR.PASSWORD:             ['OS_PASSWORD'],
  STR.USER_DOMAIN_NAME:     ['OS_USER_DOMAIN_NAME', 'OS_PROJECT_DOMAIN_NAME', 'OS_DOMAIN_NAME'],
  STR.USER_DOMAIN_ID:       ['OS_USER_DOMAIN_ID', 'OS_PROJECT_DOMAIN_ID', 'OS_DOMAIN_ID'],
  STR.PROJECT_NAME:         ['OS_PROJECT_NAME', 'OS_TENANT_NAME'],
  STR.PROJECT_ID:           ['OS_PROJECT_ID', 'OS_TENANT_ID'],
  STR.PROJECT_DOMAIN_NAME:  ['OS_PROJECT_DOMAIN_NAME', 'OS_DOMAIN_NAME'],
  STR.PROJECT_DOMAIN_ID:    ['OS_PROJECT_DOMAIN_ID', 'OS_DOMAIN_ID'],
  STR.DOMAIN_NAME:          ['OS_DOMAIN_NAME'],
  STR.DOMAIN_ID:            ['OS_DOMAIN_ID'],
  STR.AUTH_URL:             ['OS_AUTH_URL'],
  STR.REGION_NAME:          ['OS_REGION_NAME', 'OS_REGION'],
  STR.CLOUD_NAME:           ['OS_CLOUD', 'OS_CLOUD_NAME'],
  STR.ACCESS_KEY:           ['OS_ACCESS_KEY'],
  STR.SECRET_KEY:           ['OS_SECRET_KEY'],
  STR.SECURITY_TOKEN:       ['OS_SECURITY_TOKEN'],
  STR.TOKEN:                ['OS_TOKEN', 'OS_AUTH_TOKEN'],
  STR.AGENCY_NAME:          ['OS_AGENCY_NAME'],
  STR.AGENCY_DOMAIN_NAME:   ['OS_AGENCY_DOMAIN_NAME'],
  STR.DELEGATED_PROJECT:    ['OS_DELEGATED_PROJECT'],
  STR.INSECURE:             ['OS_INSECURE'],
  STR.CACERT_FILE:          ['OS_CACERT'],
  STR.CERT:                 ['OS_CERT'],
  STR.KEY:                  ['OS_KEY'],
  STR.ENDPOINT_TYPE:        ['OS_ENDPOINT_TYPE'],
  STR.ENTERPRISE_PROJECT_ID: ['OS_ENTERPRISE_PROJECT_ID'],
  STR.PASSCODE:             ['OS_PASSCODE'],
  STR.MAX_RETRIES:          ['OS_MAX_RETRIES'],
  STR.ALLOW_REAUTH:         ['OS_ALLOW_REAUTH'],
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_env() -> dict:
  '''Collect all recognised OS_* environment variables into a dict.'''
  creds: dict = {}
  for key, env_vars in ENV_MAP.items():
    for var in env_vars:
      if var in os.environ:
        creds[key] = os.environ[var]
        break
  return creds


def _clouds_yaml_candidates() -> list[str]:
  '''Return candidate ``clouds.yaml`` paths in search order.'''
  paths = []
  if STR.OS_CLIENT_CONFIG_FILE in os.environ:
    paths.append(os.environ[STR.OS_CLIENT_CONFIG_FILE])
  paths.append(STR.CLOUDS_YAML)
  if STR.HOME in os.environ:
    paths.append(os.path.join(os.environ[STR.HOME], STR.OS_CFG_HOME, STR.CLOUDS_YAML))
  paths.append(os.path.join(STR.ETC_CFG, STR.CLOUDS_YAML))
  return paths


def _load_clouds(ydat: dict) -> dict | None:
  '''Return the ``clouds`` sub-dict from a parsed YAML document, or None.'''
  if isinstance(ydat, dict) and STR.CLOUDS in ydat:
    return ydat[STR.CLOUDS]
  return None


def _resolve_from_yaml(cloud_name: str | None) -> dict | None:
  '''Walk ``clouds.yaml`` files and return the first matching credential set.

  When *cloud_name* is ``None`` the first cloud entry that contains an ``auth``
  block wins.  Otherwise the named entry must exist.
  '''
  for cfgpath in _clouds_yaml_candidates():
    if not os.path.isfile(cfgpath):
      continue
    with open(cfgpath) as fp:
      clouds = _load_clouds(yaml.safe_load(fp))
    if clouds is None:
      continue

    # Collect candidate cloud *names* from this file
    candidates: list[str] = []
    if cloud_name is not None:
      if cloud_name in clouds:
        candidates = [cloud_name]
      else:
        continue  # named cloud not in this file → skip
    else:
      candidates = [
        cn for cn, cd in clouds.items()
        if isinstance(cd, dict) and STR.AUTH in cd
      ]

    for name in candidates:
      entry = clouds[name]
      if not isinstance(entry, dict):
        continue
      auth = entry.get(STR.AUTH, {})
      if not isinstance(auth, dict) or not auth:
        continue

      result = dict(auth)
      result[STR.CLOUD_NAME] = name

      # Promote selected top-level entry keys into the result
      for key in (STR.REGION_NAME, STR.AUTH_URL, STR.INSECURE,
                  STR.CACERT_FILE, STR.CERT, STR.KEY,
                  STR.ENDPOINT_TYPE, STR.ENTERPRISE_PROJECT_ID,
                  STR.PROJECT_NAME, STR.PROJECT_ID):
        if key not in result and key in entry:
          result[key] = entry[key]

      # If no project_name but a region_name is available, default to it
      # (legacy OTC convention)
      if STR.PROJECT_NAME not in result and STR.REGION_NAME in result:
        result[STR.PROJECT_NAME] = result[STR.REGION_NAME]

      # Overlay secure.yaml if it sits next to this clouds.yaml
      secure_path = os.path.join(os.path.dirname(cfgpath), STR.SECURE_YAML)
      if os.path.isfile(secure_path):
        with open(secure_path) as fp:
          sec = _load_clouds(yaml.safe_load(fp))
        if sec and name in sec and isinstance(sec[name], dict) and STR.AUTH in sec[name]:
          result.update(sec[name][STR.AUTH])

      return result

  return None


def _detect_auth_type(creds: dict) -> str | None:
  '''Determine the authentication method present in *creds*.

  Terraform precedence: Token > AK/SK > Agency > Password.
  '''
  if STR.TOKEN in creds:
    return STR.AUTH_TOKEN
  if STR.ACCESS_KEY in creds and STR.SECRET_KEY in creds:
    return STR.AUTH_AKSK
  if STR.AGENCY_NAME in creds:
    return STR.AUTH_AGENCY
  if (STR.USERNAME in creds or STR.USER_ID in creds) and STR.PASSWORD in creds:
    return STR.AUTH_PASSWORD
  return None


# ---------------------------------------------------------------------------
# Public API (kept backward-compatible)
# ---------------------------------------------------------------------------

def get_env_creds() -> dict:
  '''Return credentials discovered from ``OS_*`` environment variables.

  :returns: dictionary containing any recognised environment variables
  '''
  return _read_env()


attributes = [
  STR.USER_DOMAIN_NAME,
  STR.USERNAME,
  STR.PASSWORD,
  STR.PROJECT_NAME,
  STR.CLOUD_NAME,
]
'''Legacy: list of params needed for password-based authentication.'''


def check_kwargs(opts: dict) -> bool:
  '''Test that *opts* contains a complete set of password credentials.

  .. deprecated::
     Prefer the more flexible :func:`creds` which handles any auth method.

  :param opts: dictionary containing credentials
  :returns: True if all legacy attributes are present
  '''
  for arg in attributes:
    if arg not in opts:
      return False
  return True


def creds(cloud_name: str | None = None, **kwargs) -> dict:
  '''Resolve configured login credentials.

  Resolution order (first complete set wins):

    1. Explicit **kwargs** (any auth method)
    2. ``OS_*`` environment variables
    3. ``clouds.yaml`` / ``secure.yaml`` (respecting ``OS_CLOUD`` / *cloud_name*)

  The returned dict contains the key-value pairs needed by the resolved auth
  method.  See the ``STR`` class for the recognised key names.

  :param cloud_name: Explicit cloud name (overrides ``OS_CLOUD`` env var)
  :param kwargs:     Override individual credential values
  :returns:          Credential dictionary
  :raises ValueError: No complete configuration found
  '''
  # 1 – Keyword arguments (caller-provided)
  if _detect_auth_type(kwargs):
    return dict(kwargs)

  # 2 – Environment variables
  env_creds = _read_env()
  if cloud_name is None and STR.CLOUD_NAME in env_creds:
    cloud_name = env_creds[STR.CLOUD_NAME]
  if _detect_auth_type(env_creds):
    return env_creds

  # 3 – clouds.yaml (with optional secure.yaml overlay)
  result = _resolve_from_yaml(cloud_name)
  if result is not None and _detect_auth_type(result):
    return result

  raise ValueError(
    'No valid credentials found. '
    'Provide credentials via keyword arguments, OS_* environment variables, '
    'or a clouds.yaml file. Supported methods: password, AK/SK, token'
  )


if __name__ == '__main__':
  args = creds(cloud_name='otc-de-iam')
  ic(args)

if __name__ == '__main__':
  args = creds(cloud_name = 'otc-de-iam')
  ic(args)

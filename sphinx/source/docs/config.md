# Configuration

scullery supports the same authentication methods as the
[Terraform OpenTelekomCloud provider][tf-provider].
Credentials are resolved from three sources, in order of precedence:

1. **Keyword arguments** passed directly to {func}`scullery.creds.creds`
2. **`OS_*` environment variables**
3. **`clouds.yaml` / `secure.yaml`** configuration files

The resolved credential set is then consumed by {class}`scullery.api.ApiSession`,
which dispatches to the appropriate authentication method.

(tf-provider)=
## Authentication methods

```{list-table}
:header-rows: 1
:widths: 15 30 30 25

* - Method
  - Required credentials
  - Session behaviour
  - Use case

* - `password`
  - `username` + `password` + `user_domain_name` + `project_name`
  - Calls IAM token endpoint, stores the bearer token, attaches it to every
    request via `X-Auth-Token`.
  - Standard user login.

* - `token`
  - `token` + `project_name`
  - Uses the token directly as a bearer token (no IAM call).
  - Re-using an existing token (e.g. from `otc-auth`).

* - `aksk`
  - `access_key` + `secret_key` \
    *(optional `security_token` for temporary credentials)*
  - Creates an {class}`scullery.api.OTCAkSkAuth` signer. Every HTTP request
    is signed with `SDK-HMAC-SHA256`. No bearer token is obtained.
  - Permanent or temporary AK/SK.

* - `agency`
  - `agency_name` + `agency_domain_name` + `delegated_project`
  - *(Not yet implemented — placeholder.)*
  - Cross-account assume-role.
```

```{note}
Authentication precedence when multiple credential types are present:
**Token > AK/SK > Agency > Password**.

If both a `token` and `access_key`/`secret_key` are present, the `token` is
treated as a bearer token (plain `token` mode), not as a federated token.
```

## Environment variables

Credentials and session options are read from `OS_*` environment variables.
The mapping follows the Terraform OpenTelekomCloud provider conventions.

| scullery key              | Environment variable(s)                                          |
|---------------------------|------------------------------------------------------------------|
| `username`                | `OS_USERNAME`                                                    |
| `user_id`                 | `OS_USER_ID`                                                     |
| `password`                | `OS_PASSWORD`                                                    |
| `user_domain_name`        | `OS_USER_DOMAIN_NAME` / `OS_PROJECT_DOMAIN_NAME` / `OS_DOMAIN_NAME` |
| `user_domain_id`          | `OS_USER_DOMAIN_ID` / `OS_PROJECT_DOMAIN_ID` / `OS_DOMAIN_ID`     |
| `project_name`            | `OS_PROJECT_NAME` / `OS_TENANT_NAME`                             |
| `project_id`              | `OS_PROJECT_ID` / `OS_TENANT_ID`                                 |
| `project_domain_name`     | `OS_PROJECT_DOMAIN_NAME` / `OS_DOMAIN_NAME`                      |
| `project_domain_id`       | `OS_PROJECT_DOMAIN_ID` / `OS_DOMAIN_ID`                          |
| `domain_name`             | `OS_DOMAIN_NAME`                                                 |
| `domain_id`               | `OS_DOMAIN_ID`                                                   |
| `auth_url`                | `OS_AUTH_URL`                                                    |
| `region_name`             | `OS_REGION_NAME` / `OS_REGION`                                   |
| `cloud_name`              | `OS_CLOUD` / `OS_CLOUD_NAME`                                     |
| `access_key`              | `OS_ACCESS_KEY`                                                  |
| `secret_key`              | `OS_SECRET_KEY`                                                  |
| `security_token`          | `OS_SECURITY_TOKEN`                                              |
| `token`                   | `OS_TOKEN` / `OS_AUTH_TOKEN`                                     |
| `agency_name`             | `OS_AGENCY_NAME`                                                 |
| `agency_domain_name`      | `OS_AGENCY_DOMAIN_NAME`                                          |
| `delegated_project`       | `OS_DELEGATED_PROJECT`                                           |
| `insecure`                | `OS_INSECURE`                                                    |
| `cacert_file`             | `OS_CACERT`                                                      |
| `cert`                    | `OS_CERT`                                                        |
| `key`                     | `OS_KEY`                                                         |
| `endpoint_type`           | `OS_ENDPOINT_TYPE`                                               |
| `enterprise_project_id`   | `OS_ENTERPRISE_PROJECT_ID`                                       |
| `passcode`                | `OS_PASSCODE`                                                    |
| `max_retries`             | `OS_MAX_RETRIES`                                                 |
| `allow_reauth`            | `OS_ALLOW_REAUTH`                                                |

Where multiple env var names are listed, the first one found wins.

### Typical `.ostackrc` example

```bash
# --- Password auth ---
export OS_USERNAME="<USER_NAME>"
export OS_USER_DOMAIN_NAME="OTC00000000001000000XYZ"
export OS_PASSWORD="<PASSWORD>"
export OS_PROJECT_NAME="eu-de_PROJECT_NAME"

# --- Alternatively: AK/SK auth (permanent or temporary) ---
# export OS_ACCESS_KEY="<AK>"
# export OS_SECRET_KEY="<SK>"
# export OS_SECURITY_TOKEN="<security-token>"  # temporary only

# --- Alternatively: token auth ---
# export OS_TOKEN="<bearer-token>"

# --- Region ---
# export OS_REGION_NAME="eu-de"
```

## Configuring via `clouds.yaml`

Configuration files follow the [OpenStack clouds.yaml][osdoccfg] format,
extended for OTC. The credential resolver searches these paths in order:

1. `OS_CLIENT_CONFIG_FILE` (if set)
2. `./clouds.yaml` (current directory)
3. `~/.config/openstack/clouds.yaml`
4. `/etc/openstack/clouds.yaml`

### Password auth example

```yaml
clouds:
  otc:
    auth:
      user_domain_name: 'OTC00000000001000000xxx'
      username: '<USER_NAME>'
      password: '<PASSWORD>'
      project_name: 'eu-de_project'
    region_name: eu-de
```

### AK/SK auth example

```yaml
clouds:
  otc:
    auth:
      access_key: '<AK_VALUE>'
      secret_key: '<SK_VALUE>'
    region_name: eu-de
```

### Token auth example

```yaml
clouds:
  otc:
    auth:
      token: '<bearer-token>'
    region_name: eu-de
```

### Multiple clouds

```yaml
clouds:
  production:
    auth:
      username: '<USER_NAME>'
      password: '<PASSWORD>'
      user_domain_name: 'OTC00000000001000000xxx'
      project_name: 'eu-de_prod'
    region_name: eu-de
  staging:
    auth:
      username: '<USER_NAME>'
      password: '<PASSWORD>'
      user_domain_name: 'OTC00000000001000000xxx'
      project_name: 'eu-de_staging'
    region_name: eu-de
```

Select a cloud with the `-C`/`--cloud` CLI flag or the `OS_CLOUD` environment
variable.

### Splitting secrets into `secure.yaml`

Sensitive values (passwords, secret keys) can be stored in a separate
`secure.yaml` file alongside `clouds.yaml`:

```yaml
# clouds.yaml
clouds:
  otc:
    auth:
      username: '<USER_NAME>'
      user_domain_name: 'OTC00000000001000000xxx'
      project_name: 'eu-de_project'
    region_name: eu-de
```

```yaml
# secure.yaml
clouds:
  otc:
    auth:
      password: '<PASSWORD>'
```

Values from `secure.yaml` are merged on top of `clouds.yaml`, so they take
precedence.

```{note}
You must specify either a `region_name` or a `project_name`. If a
`project_name` is given (e.g. `eu-de_myproject`), the token is scoped to
that project and will **not** have access to domain-level services such as
IAM or RMS.
```

## Resolution order

When {func}`scullery.creds.creds` is called, it follows this order:

1. **Keyword arguments** — if they form a complete credential set for any
   auth method, return immediately.
2. **Environment variables** — all `OS_*` variables are collected into a
   dict. If it forms a complete credential set, return.
3. **`clouds.yaml` / `secure.yaml`** — walk the candidate paths in order.
   For each file, try the named cloud (or the first cloud with an `auth`
   block). Merge `secure.yaml` values and return if complete.

If no source yields a usable credential set, {class}`ValueError` is raised.


[osdoccfg]: https://docs.openstack.org/openstacksdk/latest/user/guides/connect_from_config.html
[otcsdkdoccfg]: https://docs.otc.t-systems.com/python-otcextensions/install/configuration.html#clouds-yaml
[tf-provider]: https://registry.terraform.io/providers/opentelekomcloud/opentelekomcloud/latest/docs

# scullery

Utility for executing Cloud related recipes

Most of the recipes in scullery require admin access.

## Authentication

scullery supports the same authentication methods as the
[Terraform OpenTelekomCloud provider](https://registry.terraform.io/providers/opentelekomcloud/opentelekomcloud/latest/docs):

| Method       | How it works                                                       |
|--------------|--------------------------------------------------------------------|
| `password`   | username + password → IAM token → bearer token for all requests    |
| `token`      | existing bearer token used directly                                |
| `aksk`       | Access Key / Secret Key signs every request via SDK-HMAC-SHA256    |

Credentials are resolved from **environment variables** (`OS_*`),
**`clouds.yaml`** / **`secure.yaml`**, or **keyword arguments**.

### Quick start — password auth

```bash
export OS_USERNAME="<username>"
export OS_USER_DOMAIN_NAME="OTC00000000001000000XXX"
export OS_PASSWORD="<password>"
export OS_PROJECT_NAME="eu-de_project"
export OS_REGION_NAME="eu-de"
```

### Quick start — AK/SK auth

```bash
export OS_ACCESS_KEY="<AK>"
export OS_SECRET_KEY="<SK>"
export OS_REGION_NAME="eu-de"
```

See [Configuration Reference](docs/config.md) for the full configuration reference.

## Available Recipes

| Command | Module | Description |
|---------|--------|-------------|
| `scullery bucket` | `rcp_buckets.py` | **OBS** – list, create, delete buckets; manage tags and access policies |
| `scullery GET` / `DELETE` / `PUT` / `POST` | `rcp_curler.py` | Raw HTTP(S) API calls using the configured authentication |
| `scullery deh` | `rcp_deh.py` | List available **Dedicated Host** types |
| `scullery ecs` | `rcp_ecs.py` | **ECS** – list, inspect, start, stop, reboot servers; query flavors |
| `scullery groups` | `rcp_groups.py` | **IAM Groups** – list, get details, create, delete |
| `scullery images` | `rcp_ims.py` | **IMS** – list and filter images, get image details |
| `scullery project` | `rcp_projects.py` | **Project** – list, get details, create, delete, grant/revoke role assignments |
| `scullery resources` | `rcp_rms.py` | **RMS** – list cloud resources, optionally filtered by project |
| `scullery roles` | `rcp_roles.py` | **IAM Roles** – list custom/system roles, get details, create, delete |
| `scullery tags` | `rcp_tms.py` | **TMS** – list, create, delete pre-defined tags |
| `scullery users` | `rcp_users.py` | **IAM Users** – list, get, create, delete; manage group membership and passwords |

Run any recipe with `-h` / `--help` for full usage details.

# Issues

* Credentials handling is a mess

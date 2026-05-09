# Buckets — Object Storage (OBS) Management

```{eval-rst}
.. module:: scullery.rcp_buckets
   :synopsis: List, create, delete, and manage tags and access policies for OBS buckets.
```

Manage OBS (Object Storage Service) buckets: list, create, delete, tag,
and control access policies.

## Usage

| Command                                                          | Description                             |
|-----------------------------------------------------------------|-----------------------------------------|
| `scullery buckets`                                              | List all buckets (with tags)            |
| `scullery buckets ls`                                           | Same as above                           |
| `scullery buckets ls env=prod`                                  | List buckets filtered by tag            |
| `scullery buckets ls env=prod --tag env`                        | Filtered, showing tag column            |
| `scullery buckets create <name>`                                | Create a new bucket                     |
| `scullery buckets delete <name>`                                | Delete a bucket                         |
| `scullery buckets tag <name>`                                   | List bucket tags                        |
| `scullery buckets tag <name> key=value ...`                     | Set (replace) tags                      |
| `scullery buckets untag <name> key ...`                         | Delete tags by key                      |
| `scullery buckets untag --all <name>`                           | Delete all tags                         |
| `scullery buckets access <name>`                                | Show access policy                      |
| `scullery buckets access <name> grant <who> <perm>`             | Grant access (IAM user)                 |
| `scullery buckets access <name> revoke <who> <perm>`            | Revoke access (IAM user)                |

## Access policies

Access is managed via bucket policies. Only IAM **users** are supported
as policy principals — IAM groups are **not** supported by the OBS/S3 API.

The bucket API automatically acquires temporary AK/SK credentials if
the session uses password or token authentication.

### Permissions

| Permission      | Description                        |
|-----------------|------------------------------------|
| `READ`          | Read objects and list bucket       |
| `WRITE`         | Write objects                      |
| `FULL_CONTROL`  | Read, write, and manage ACLs       |

## Output formats

The `ls` and `access` commands support `-f`/`--format`:

| Format       | Description                         |
|--------------|-------------------------------------|
| `terminal`   | Aligned columns for your terminal   |
| `json`       | JSON array/object                   |
| `yaml`       | YAML output                         |
| `csv`        | Comma-separated values              |
| `tsv`        | Tab-separated values                |
| `markdown`   | Markdown / pipe table               |

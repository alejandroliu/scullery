# Roles — IAM Role Management

```{eval-rst}
.. module:: scullery.rcp_roles
   :synopsis: List, create, delete and inspect IAM roles.
```

Manage IAM roles: list custom and system roles, create new custom roles
from policy documents, and delete custom roles.

## Usage

| Command                                         | Description                        |
|-------------------------------------------------|------------------------------------|
| `scullery roles`                                | List custom roles                  |
| `scullery roles system`                         | List system (built-in) roles       |
| `scullery roles custom`                         | List custom roles                  |
| `scullery roles get <name>`                     | Show role details                  |
| `scullery roles add <name> [policy.yaml]`       | Create a custom role               |
| `scullery roles del <name>`                     | Delete a custom role               |

### Listing options

| Flag          | Description                                      |
|---------------|--------------------------------------------------|
| `-l`/`--long` | Show Name and ID columns in human-readable output |

## Creating custom roles

Roles are defined using a YAML policy document. If no file is specified,
the policy is read from stdin.

Example policy:

```yaml
- Action:
  - 'ecs:*:get*'
  - 'ecs:*:list*'
  - 'ecs:*:stop*'
  - 'ecs:*:start*'
  - 'ecs:*:reboot*'
  Effect: Allow
```

See {py:meth}`scullery.iam.Iam.new_role` for more details.

### Options for `add`

| Option                        | Description                                      |
|-------------------------------|--------------------------------------------------|
| `-d`/`--description`/`--desc` | Description for this role                        |
| `-p`/`--project`/`--proj`     | Include project name in description              |

## Role types

| Type code | Description          |
|-----------|----------------------|
| `AX`      | Account-level role   |
| `XA`      | Project-level role   |
| `AA`      | Both account/project |
| `XX`      | None                 |

## Output formats

The `list` and `get` commands support `-f`/`--format` with the usual
formats (`terminal`, `json`, `yaml`, `csv`, `tsv`, `markdown`).

## Aliases

- `scullery role`

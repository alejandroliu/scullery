# Groups — IAM Group Management

```{eval-rst}
.. module:: scullery.rcp_groups
   :synopsis: List, create, delete and inspect IAM groups.
```

Manage IAM groups: list, inspect, create, and delete.

## Usage

| Command                              | Description                          |
|--------------------------------------|--------------------------------------|
| `scullery groups`                    | List all groups                      |
| `scullery groups get <name>`         | Show group details, roles, members   |
| `scullery groups add <name>`         | Create a new group                   |
| `scullery groups add <name> -d "desc"` | Create group with description      |
| `scullery groups del <name>`         | Delete a group                       |

## Group details

The `get` command shows:
- Group ID, name, and description
- Assigned domain roles
- Member users

## Output formats

The `list` command supports `-f`/`--format`. The `get` command supports
`-f json` or `-f yaml` for structured output.

## Aliases

- `scullery group`
- `scullery grp`
- `scullery g`

# Users — IAM User Management

```{eval-rst}
.. module:: scullery.rcp_users
   :synopsis: List, create, delete and manage IAM users, their group membership and passwords.
```

Manage IAM users: list, inspect, create, delete, manage group membership,
and set passwords.

## Usage

| Command                                        | Description                             |
|------------------------------------------------|-----------------------------------------|
| `scullery users`                               | List all users                          |
| `scullery users get <name>`                    | Show user details and group membership  |
| `scullery users add [options]`                 | Create a new user                       |
| `scullery users del <name>`                    | Delete a user                           |
| `scullery users group <group> add <user>`      | Add user to a group                     |
| `scullery users group <group> del <user>`      | Remove user from a group                |
| `scullery users passwd <user>`                 | Reset user password (random)            |
| `scullery users passwd <user> <password>`      | Set user password                       |
| `scullery users passwd -S <user>`              | Set password and require change on login |

### User creation options

| Flag                              | Description                                      |
|-----------------------------------|--------------------------------------------------|
| `-n`/`--name`/`--user`           | User name (random if not specified)               |
| `-P`/`--password`/`--passwd`     | Password (random if not specified)                |
| `-m`/`-e`/`--email`/`--mail`    | Email address                                    |
| `-d`/`--description`/`--desc`    | Description for this user                         |
| `-p`/`--project`/`--proj`        | Include project name in description               |
| `-g`/`--group`/`--grp`           | Assign to group (repeatable)                      |

### Password options

| Flag   | Description                                        |
|--------|----------------------------------------------------|
| `-S`   | Mark password for change on first login            |

## Output formats

The `list` command supports `-f`/`--format`:

| Format       | Description                         |
|--------------|-------------------------------------|
| `terminal`   | Aligned columns for your terminal   |
| `json`       | JSON array of users                 |
| `yaml`       | YAML output                         |
| `csv`        | Comma-separated values              |
| `tsv`        | Tab-separated values                |
| `markdown`   | Markdown / pipe table               |

The `get` command supports `-f json` or `-f yaml` for structured output.

## Aliases

- `scullery user`
- `scullery usr`
- `scullery u`

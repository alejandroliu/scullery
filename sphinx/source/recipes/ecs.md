# ECS — Elastic Cloud Server Management

```{eval-rst}
.. module:: scullery.rcp_ecs
   :synopsis: List, inspect and control ECS servers, and query available flavors.
```

List, inspect, and control ECS (Elastic Cloud Server) instances, and
query available flavors.

## Usage

| Command                                   | Description                        |
|-------------------------------------------|------------------------------------|
| `scullery ecs`                            | List servers in current project    |
| `scullery ecs get <server>`               | Show detailed server info          |
| `scullery ecs flavors`                    | List available flavors             |
| `scullery ecs start <server>`             | Start a server                     |
| `scullery ecs stop <server>`              | Stop (soft) a server               |
| `scullery ecs stop -f <server>`           | Force hard shutdown                |
| `scullery ecs reboot <server>`            | Reboot (soft) a server             |
| `scullery ecs reboot -f <server>`         | Force hard reboot                  |

Multiple server names can be specified for `start`, `stop`, `reboot`,
and `get`.

## Flavors

The `flavors` command accepts optional filters:

| Option       | Description                 |
|--------------|-----------------------------|
| `--ram=N`    | Minimum memory in GB        |
| `--disk=N`   | Minimum disk size in GB     |

## Output formats

The `list` and `flavors` commands support `-f`/`--format`:

| Format       | Description                         |
|--------------|-------------------------------------|
| `terminal`   | Aligned columns for your terminal   |
| `json`       | JSON array/object                   |
| `yaml`       | YAML output                         |
| `csv`        | Comma-separated values              |
| `tsv`        | Tab-separated values                |
| `markdown`   | Markdown / pipe table               |

The `get` command supports `-f json` and `-f yaml` for structured output.

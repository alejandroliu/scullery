# TMS — Tag Management Service

```{eval-rst}
.. module:: scullery.rcp_tms
   :synopsis: Create, list and delete pre-defined tags.
```

Manage pre-defined tags via the Tag Management Service (TMS).

## Usage

| Command                                          | Description                        |
|--------------------------------------------------|------------------------------------|
| `scullery tags`                                  | List all pre-defined tags          |
| `scullery tags --add key=value`                  | Create a pre-defined tag           |
| `scullery tags --del key=value`                  | Delete a pre-defined tag           |

## Notes

- Pre-defined tags are global and apply across all projects in the account.
- Tags are defined as `key=value` pairs.
- Multiple key=value pairs can be specified for the `--add` and `--del`
  operations.

## Aliases

- `scullery tms`

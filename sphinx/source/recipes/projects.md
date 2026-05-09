# Projects — Project Management

```{eval-rst}
.. module:: scullery.rcp_projects
   :synopsis: List, create, delete and manage IAM projects and their role assignments.
```

Manage IAM projects: list, inspect, create, delete, and manage role
assignments.

## Usage

| Command                                                              | Description                              |
|----------------------------------------------------------------------|------------------------------------------|
| `scullery projects`                                                  | List all projects                        |
| `scullery projects get region_projectname`                           | Show project details and role assignments |
| `scullery projects add region_projectname [description]`             | Create a new project                     |
| `scullery projects del region_projectname`                           | Delete a project                         |
| `scullery projects grant role on project to group`                   | Grant a role to a group on a project     |
| `scullery projects revoke role on project from group`                | Revoke a role from a group on a project  |

## Important notes

- Project names **must** follow the `region_name` convention (e.g. `eu-de_testprj`).
- Project deletion takes more than 30 minutes to complete.
- The `del` command checks for active resources via RMS before deleting.
  Use `--force` to bypass this check.
- When deleting a project, associated users, groups, and roles that were
  created via the Kermit recipe are also cleaned up.

## Grant / Revoke syntax

The `grant` and `revoke` commands accept a flexible argument syntax.
The keywords `on`, `to`, and `from` are optional:

```bash
scullery projects grant te_admin on eu-de_testprj to my_admin_group
scullery projects grant te_admin eu-de_testprj my_admin_group

scullery projects revoke te_admin on eu-de_testprj from my_admin_group
scullery projects revoke te_admin eu-de_testprj my_admin_group
```

## Output formats

| Format       | Description                         |
|--------------|-------------------------------------|
| `terminal`   | Aligned columns for your terminal   |
| `json`       | JSON array/object                   |
| `yaml`       | YAML output                         |
| `csv`        | Comma-separated values              |
| `tsv`        | Tab-separated values                |
| `markdown`   | Markdown / pipe table               |

## Aliases

- `scullery project`
- `scullery prj`
- `scullery p`

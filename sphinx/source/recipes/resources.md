# RMS — Resource Management Service

```{eval-rst}
.. module:: scullery.rcp_rms
   :synopsis: List cloud resources across projects.
```

List cloud resources across all projects or filtered by a specific
project and resource type.

## Usage

```bash
scullery resources                          # list all resources across all projects
scullery resources --project eu-de_testprj  # list resources for a specific project
scullery resources --type ecs.cloudservers   # filter by resource type
scullery resources --project eu-de_testprj --type ecs.cloudservers
```

## Output formats

| Format       | Description                         |
|--------------|-------------------------------------|
| `terminal`   | Aligned columns for your terminal   |
| `json`       | JSON array of resources             |
| `csv`        | Comma-separated values              |
| `tsv`        | Tab-separated values                |
| `markdown`   | Markdown / pipe table               |

## Aliases

- `scullery rms`
- `scullery rsc`

## Columns

| Column          | Description                    |
|-----------------|--------------------------------|
| Project         | Project name                   |
| Provider        | Service provider               |
| Type            | Resource type                  |
| Name            | Resource name                  |
| Region          | Region ID                      |

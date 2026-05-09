# DeH — Dedicated Host Types

```{eval-rst}
.. module:: recipes.deh
   :synopsis: List available dedicated host types.
```

List the available dedicated host types in a given availability zone.

```bash
scullery deh [AZ]
```

The `AZ` can be a numeric index (`2`) or a full AZ name (`eu-de-02`).
If omitted it defaults to the first available availability zone.

## Output formats

Supports `-f`/`--format` with the usual formats (`terminal`, `json`,
`yaml`, `csv`, `tsv`, `markdown`).

# IMS — Image Management Service

```{eval-rst}
.. module:: recipes.ims
   :synopsis: List and inspect cloud images.
```

List and inspect cloud images from the Image Management Service (IMS).

## Usage

| Command                                        | Description                           |
|------------------------------------------------|---------------------------------------|
| `scullery images`                              | Show help (subcommand required)       |
| `scullery images list`                         | List all images                       |
| `scullery images list key=value`               | List images with filter               |
| `scullery images list --os Ubuntu`             | Filter by OS platform                 |
| `scullery images list --type Linux`            | Filter by OS type                     |
| `scullery images get <name>`                   | Show detailed image info              |

### Filters

| Option          | Description                                      |
|-----------------|--------------------------------------------------|
| `--os`          | OS platform (`Windows`, `Ubuntu`, `Red Hat`, etc.) |
| `--type`        | OS type (`Linux`, `Windows`, `Other`)              |
| `key=value`     | Arbitrary query parameters (repeatable)           |

Refer to the
[IMS API documentation](https://docs.otc.t-systems.com/image-management-service/api-ref/native_openstack_apis/image_native_openstack_apis/querying_images_native_openstack_api.html)
for supported filter parameters.

## Output formats

The `list` command supports `-f`/`--format`. The `get` command supports
`-f json` or `-f yaml` for structured output.

## Aliases

- `scullery ims`
- `scullery im`

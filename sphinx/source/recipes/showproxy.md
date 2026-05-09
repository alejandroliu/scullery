# Show Proxy — Proxy Configuration Display

```{eval-rst}
.. module:: scullery.rcp_showcfg
   :synopsis: Display proxy auto-configuration and environment variables.
```

Display the current proxy configuration, including proxy auto-config
(PAC) resolution and environment variables.

## Usage

```bash
scullery show-proxy-cfg              # show proxy config
scullery show-proxy-cfg --autocfg    # attempt PAC auto-detection
scullery show-proxy-cfg --debug      # show extra details (with --autocfg)
```

## Options

| Flag          | Description                                        |
|---------------|----------------------------------------------------|
| `--autocfg`   | Perform proxy auto-configuration (PAC lookup)      |
| `--debug`     | Show extra details (e.g. PAC JavaScript content)   |

Without `--autocfg` the command shows the `http_proxy` and
`https_proxy` environment variables if set.

## Aliases

- `scullery spc`
- `scullery showproxy`

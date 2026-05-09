# Curler — Raw HTTP API Calls

```{eval-rst}
.. module:: scullery.rcp_curler
   :synopsis: Make authenticated HTTP requests to the OpenTelekomCloud API.
```

Performs curl-style HTTP calls using the currently configured cloud
authentication. Tokens or AK/SK signing are handled automatically.

| Command                    | Description                     |
|----------------------------|---------------------------------|
| `scullery GET <url>`       | Raw GET request                 |
| `scullery DELETE <url>`    | Raw DELETE request              |
| `scullery PUT <url> <body>` | Raw PUT request with body      |
| `scullery POST <url> <body>` | Raw POST request with body    |

## Scoping

| Flag           | Description                                    |
|----------------|------------------------------------------------|
| `--scoped`     | Use scoped credentials (default project scope) |
| `--unscoped`   | Use unscoped credentials                       |
| `--project=X`  | Scope credentials to a specific project        |

Output is formatted as YAML by default. Use `-f json` for JSON output.

## Notes

- The body for `PUT` and `POST` is passed as a single string argument.
- Responses are parsed as JSON if possible, otherwise shown as raw text.
- Status codes for empty responses are printed directly.

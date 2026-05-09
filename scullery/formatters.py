'''
Reusable output formatting utilities for recipes.

Provides formatters for terminal (aligned columns), JSON, YAML, CSV,
TSV, and Markdown tables.  Each formatter works on a list of dicts
(rows) with columns declared as ``(key, label)`` pairs.

Typical usage::

    from scullery import formatters

    COLUMNS = [
        ('name', 'Name'),
        ('region_id', 'Region'),
    ]

    rows = formatters.extract_rows(raw_data, COLUMNS)
    formatters.write_output(rows, COLUMNS, args.format)

Your recipe can add the ``--format`` / ``-f`` argument via
:func:`add_format_arg`.
'''

import argparse
import csv
import io
import json
import sys
from typing import Callable, Optional, TextIO

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

try:
  from tabulate import tabulate
  HAS_TABULATE = True
except ImportError:
  HAS_TABULATE = False

try:
  import yaml
  HAS_YAML = True
except ImportError:
  HAS_YAML = False

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

Columns = list[tuple[str, str]]
'''A list of ``(dict_key, display_label)`` pairs describing output columns.'''

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def add_format_arg(parser: argparse.ArgumentParser, *, default: str = 'terminal') -> None:
  '''Add ``--format`` / ``-f`` argument to an argparse sub-parser.

  :param parser: An ``ArgumentParser`` (typically a sub-parser).
  :param default: The default format (``'terminal'``).
  '''
  parser.add_argument('-f', '--format',
                      help='Output format',
                      choices=list(FORMATTERS),
                      default=default)


def extract_rows(data: list[dict], columns: Columns) -> list[dict]:
  '''Filter a list of dicts to contain only the keys declared in *columns*.

  :param data: Raw records from an API.
  :param columns: Desired output columns as ``(key, label)`` pairs.
  :returns: A list of dicts containing only the requested keys.
  '''
  keys = [k for k, _ in columns]
  out = []
  for rec in data:
    row = {}
    for k in keys:
      row[k] = rec.get(k, '')
    out.append(row)
  return out


def write_output(rows: list[dict], columns: Columns, fmt: str,
                 stream: TextIO = sys.stdout) -> None:
  '''Format *rows* using the named formatter and write to *stream*.

  :param rows: List of row dicts (keys must match *columns* keys).
  :param columns: Column definitions.
  :param fmt: One of ``'terminal'``, ``'json'``, ``'yaml'``, ``'csv'``, ``'tsv'``,
              ``'markdown'``.
  :param stream: Output stream (default ``sys.stdout``).
  '''
  fmt_fn = FORMATTERS.get(fmt, FORMATTERS['terminal'])
  output = fmt_fn(rows, columns)

  if output and not output.endswith('\n'):
    output += '\n'

  stream.write(output)


# ---------------------------------------------------------------------------
# Built-in formatters
# ---------------------------------------------------------------------------

FORMATTERS: dict[str, callable] = {}
'''Registry of available formatters.  Maps format name to function.
Populated at module load time via :func:`_register_formatters`.
'''


def fmt_terminal(rows: list[dict], columns: Columns) -> str:
  '''Aligned columns for terminal display (uses *tabulate* if available).'''
  if not HAS_TABULATE:
    return _fmt_simple(rows, columns)
  headers = [label for _k, label in columns]
  keys = [k for k, _label in columns]
  data = [[r.get(k, '') for k in keys] for r in rows]
  return tabulate(data, headers=headers, tablefmt='simple')


def fmt_markdown(rows: list[dict], columns: Columns) -> str:
  '''Markdown / pipe table (uses *tabulate* if available).'''
  if not HAS_TABULATE:
    return _fmt_simple(rows, columns)
  headers = [label for _k, label in columns]
  keys = [k for k, _label in columns]
  data = [[r.get(k, '') for k in keys] for r in rows]
  return tabulate(data, headers=headers, tablefmt='github')


def fmt_json(rows: list[dict], columns: Columns) -> str:
  '''JSON array of objects.'''
  return json.dumps(rows, indent=2, default=str)


def fmt_csv(rows: list[dict], columns: Columns, dialect: str = 'excel') -> str:
  '''CSV output (comma-separated).'''
  keys = [k for k, _label in columns]
  out = io.StringIO()
  writer = csv.DictWriter(out, fieldnames=keys, dialect=dialect)
  writer.writeheader()
  writer.writerows(rows)
  return out.getvalue()


def fmt_tsv(rows: list[dict], columns: Columns) -> str:
  '''TSV output (tab-separated).'''
  return fmt_csv(rows, columns, dialect='excel-tab')


def fmt_yaml(rows: list[dict], columns: Columns) -> str:
  '''YAML document (a list of mappings).

  Falls back to JSON if PyYAML is not installed.
  '''
  if HAS_YAML:
    return yaml.dump(rows, default_flow_style=False, sort_keys=False)
  # Fallback: valid YAML is a superset of JSON only for basic types,
  # but this is a reasonable approximation for our data.
  return fmt_json(rows, columns)


# ---------------------------------------------------------------------------
# Single-object formatters (for detail / get commands)
# ---------------------------------------------------------------------------

SINGLE_FORMATTERS: dict[str, callable] = {}
'''Registry of single-object formatters.  Populated at module load time.'''


def fmt_single_json(obj: dict) -> str:
  '''Format a single dict as JSON.'''
  return json.dumps(obj, indent=2, default=str)


def fmt_single_yaml(obj: dict) -> str:
  '''Format a single dict as YAML.

  Falls back to JSON if PyYAML is not installed.
  '''
  if HAS_YAML:
    return yaml.dump(obj, default_flow_style=False, sort_keys=False)
  return fmt_single_json(obj)


def add_single_format_arg(parser: argparse.ArgumentParser, *, default: str = 'terminal') -> None:
  '''Add ``--format`` / ``-f`` argument for single-object (detail) commands.

  :param parser: An ``ArgumentParser`` (typically a sub-parser).
  :param default: The default format (``'terminal'``).
  '''
  parser.add_argument('-f', '--format',
                      help='Output format',
                      choices=list(SINGLE_FORMATTERS) + ['terminal'],
                      default=default)


def write_single_output(obj: dict, fmt: str,
                        stream: TextIO = sys.stdout,
                        terminal_fn: Optional[Callable[[dict], str]] = None) -> None:
  '''Format a single dict using the named formatter and write to *stream*.

  :param obj: The dict to format.
  :param fmt: One of ``'terminal'``, ``'json'``, ``'yaml'``.
  :param stream: Output stream (default ``sys.stdout``).
  :param terminal_fn: Optional callable that renders *obj* as a
      human-readable string.  Called when *fmt* is ``'terminal'``.
      If not provided, ``'terminal'`` falls back to YAML.
  '''
  if fmt == 'terminal':
    if terminal_fn is not None:
      output = terminal_fn(obj)
    else:
      output = fmt_single_yaml(obj)
  else:
    fmt_fn = SINGLE_FORMATTERS.get(fmt, SINGLE_FORMATTERS['json'])
    output = fmt_fn(obj)

  if output and not output.endswith('\n'):
    output += '\n'
  stream.write(output)


# ---------------------------------------------------------------------------
# Fallback when tabulate is not installed
# ---------------------------------------------------------------------------

def _register_formatters() -> None:
  '''Populate the formatter registries with the built-in formatters.'''
  for name, fn in (
    ('terminal', fmt_terminal),
    ('json',     fmt_json),
    ('yaml',     fmt_yaml),
    ('csv',      fmt_csv),
    ('tsv',      fmt_tsv),
    ('markdown', fmt_markdown),
  ):
    FORMATTERS[name] = fn

  for name, fn in (
    ('json', fmt_single_json),
    ('yaml', fmt_single_yaml),
  ):
    SINGLE_FORMATTERS[name] = fn


def _fmt_simple(rows: list[dict], columns: Columns) -> str:
  '''Minimal aligned output without *tabulate*.

  Uses plain string formatting so it works without extra dependencies.
  '''
  if not rows:
    return ''
  keys = [k for k, _ in columns]
  labels = [label for _k, label in columns]
  # Calculate column widths from data + header
  widths = [len(str(l)) for l in labels]
  for r in rows:
    for i, k in enumerate(keys):
      widths[i] = max(widths[i], len(str(r.get(k, ''))))
  # Build format string
  fmt_str = '  '.join(f'{{:<{w}}}' for w in widths)
  lines = [fmt_str.format(*labels)]
  lines.append('  '.join('-' * w for w in widths))
  for r in rows:
    vals = [str(r.get(k, '')) for k in keys]
    lines.append(fmt_str.format(*vals))
  return '\n'.join(lines)


# Populate the formatter registry at module load time.
_register_formatters()

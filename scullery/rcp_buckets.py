#
# Bucket / OBS recipes
#
'''
## Object Storage Bucket recipes

List, create, delete, manage tags and access policies for OBS buckets.

```bash
scullery buckets                                      # list all buckets (with tags)
scullery buckets ls                                   # same as above
scullery buckets ls env=prod                          # list buckets filtered by tag
scullery buckets ls env=prod --tag env                # filtered, showing tag column
scullery buckets create <name>                        # create a new bucket
scullery buckets delete <name>                        # delete a bucket
scullery buckets tag <name>                           # list bucket tags
scullery buckets tag <name> key=value ...             # set (replace) tags
scullery buckets untag <name> key ...                 # delete tags by key
scullery buckets untag --all <name>                   # delete all tags
scullery buckets access <name>                        # show access policy
scullery buckets access <name> grant <who> <perm>     # grant access (IAM user/group)
scullery buckets access <name> revoke <who> <perm>    # revoke access (IAM user/group)
```

Access is managed via bucket policies.  Only IAM **users** are supported
as policy principals — IAM groups are **not** supported by the OBS/S3 API.

The bucket API automatically acquires temporary AK/SK credentials if
the session uses password or token authentication.

***
'''

import argparse
import sys

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa

from scullery import cloud
from scullery import formatters
from scullery import parsers


# ── Column definitions ─────────────────────────────────────────────

COLUMNS_BUCKETS: formatters.Columns = [
    ('name',          'Name'),
    ('creation_date', 'Created'),
]


# ── Commands ───────────────────────────────────────────────────────

def _list_buckets(args: argparse.Namespace,
                  tag_filters: dict[str, str] | None = None) -> None:
    '''List OBS buckets, optionally filtered by tag KEY=VALUE pairs.

    :param args:        Parsed arguments (uses *format*, *list_tags*).
    :param tag_filters: Optional dict of ``{key: value}`` to filter by.
    '''
    cc = cloud(scoped=True)
    data = cc.obs.list()

    # Format creation_date to just the date part.
    for bucket in data:
        if 'creation_date' in bucket and bucket['creation_date']:
            bucket['creation_date'] = bucket['creation_date'][:10]

    cols = list(COLUMNS_BUCKETS)

    # Always fetch tags for every bucket.
    for bucket in data:
        try:
            tags = cc.obs.get_tagging(bucket['name'])
            bucket['tags'] = {t['key']: t['value'] for t in tags}
        except Exception:
            bucket['tags'] = {}

    # Apply tag filters if given.
    if tag_filters:
        filtered = []
        for bucket in data:
            tag_map = bucket.get('tags', {})
            if all(tag_map.get(k) == v for k, v in tag_filters.items()):
                filtered.append(bucket)
        data = filtered

    list_tags = getattr(args, 'list_tags', None)

    if list_tags:
        # Specific tag keys requested — show individual columns.
        for tag_key in list_tags:
            cols.append((f'tag:{tag_key}', f'Tag:{tag_key}'))
        for bucket in data:
            tag_map = bucket.pop('tags', {})
            for tag_key in list_tags:
                bucket[f'tag:{tag_key}'] = tag_map.get(tag_key, '')
    else:
        # Combined "Tags" column.
        # Keep as a dict for structured formats; flatten for tabular/human ones.
        if args.format not in ('json', 'yaml'):
            for bucket in data:
                tag_map = bucket.pop('tags', {})
                bucket['tags'] = ', '.join(
                    f'{k}={v}' for k, v in sorted(tag_map.items())
                )
        cols.append(('tags', 'Tags'))

    rows = formatters.extract_rows(data, cols)
    formatters.write_output(rows, cols, args.format)


def list_buckets(args: argparse.Namespace) -> None:
    '''List all OBS buckets (no filtering)'''
    _list_buckets(args)


def list_buckets_filtered(args: argparse.Namespace) -> None:
    '''List OBS buckets filtered by tag KEY=VALUE pairs.'''
    tag_filters: dict[str, str] = {}
    for f in args.filter:
        if '=' not in f:
            sys.stderr.write(f'[error] Invalid filter "{f}": expected KEY=VALUE\n')
            sys.exit(1)
        k, v = f.split('=', 1)
        tag_filters[k.strip()] = v.strip()
    _list_buckets(args, tag_filters)


def create_bucket(args: argparse.Namespace) -> None:
    '''Create an OBS bucket'''
    cc = cloud(scoped=True)
    cc.obs.create(args.name, location=args.location)
    print(f'Bucket "{args.name}" created.')


def delete_bucket(args: argparse.Namespace) -> None:
    '''Delete an OBS bucket'''
    cc = cloud(scoped=True)
    cc.obs.delete(args.name)
    print(f'Bucket "{args.name}" deleted.')


# ── Tag helpers ─────────────────────────────────────────────────────

def _parse_kvp(kvp: str) -> tuple[str, str]:
    '''Split a ``key=value`` string into ``(key, value)``.

    If no ``=`` is present, both key and value are set to the same string.
    '''
    if '=' in kvp:
        k, v = kvp.split('=', 1)
    else:
        k = v = kvp
    return k.strip(), v.strip()


# ── Tag commands ───────────────────────────────────────────────────

def show_tags(args: argparse.Namespace) -> None:
    '''Show or set tags on a bucket.

    When *args.tag* is provided (one or more ``key=value`` pairs), the
    tags are replaced.  Otherwise the current tags are displayed.
    '''
    cc = cloud(scoped=True)

    # If key=value pairs given, switch to set mode.
    if args.tag:
        tags = [_parse_kvp(kvp) for kvp in args.tag]
        tag_dicts = [{'key': k, 'value': v} for k, v in tags]
        cc.obs.set_tagging(args.name, tag_dicts)
        print(f'Tags set on bucket "{args.name}".')
        return

    # Otherwise display current tags.
    tags = cc.obs.get_tagging(args.name)

    if args.format == 'terminal':
        if not tags:
            print(f'No tags on bucket "{args.name}".')
            return
        for t in tags:
            print(f'{t["key"]}={t["value"]}')
    else:
        formatters.write_single_output({'tags': tags}, args.format)


def delete_tags(args: argparse.Namespace) -> None:
    '''Delete tags from a bucket'''
    cc = cloud(scoped=True)

    if args.all:
        cc.obs.delete_tagging(args.name)
        print(f'All tags removed from bucket "{args.name}".')
        return

    # Read current tags, remove matching keys, write back.
    current = cc.obs.get_tagging(args.name)
    keys_to_remove = set(args.key)
    remaining = [t for t in current if t['key'] not in keys_to_remove]

    if len(remaining) == len(current):
        print(f'None of the specified keys found on bucket "{args.name}".')
        return

    cc.obs.set_tagging(args.name, remaining)
    removed = len(current) - len(remaining)
    print(f'Removed {removed} tag(s) from bucket "{args.name}".')


# ── Access helpers ──────────────────────────────────────────────────

def _resolve_principal(cc, who: str) -> tuple[str, str]:
    '''Resolve an IAM user name to *(principal_type, principal_arn)*.

    The OTC OBS bucket policy API (like AWS S3) does **not** support IAM
    groups as policy principals.  If *who* matches a group instead of a
    user, an error is raised.

    :param cc:  An :class:`~scullery.api.ApiSession`.
    :param who: IAM user name.
    :returns:   ``(type, arn)`` where *type* is always ``'user'``.
    :raises SystemExit: If *who* cannot be resolved.
    '''
    # IAM lookups need an unscoped session.
    iam_cc = cloud(scoped=False)
    domain_id = ''

    # Try as user.
    try:
        users = iam_cc.iam.users(who)
        if len(users) == 1:
            domain_id = users[0].get('domain_id', '')
            if domain_id:
                urn = cc.obs._principal_urn(domain_id, 'user', who)
                return 'user', urn
    except Exception:
        pass

    # Try as group (only to give a better error message).
    try:
        groups = iam_cc.iam.groups(who)
        if len(groups) == 1:
            sys.stderr.write(
                f'[error] "{who}" is an IAM group, but OBS bucket policies '
                f'do not support group principals.\n'
                f'       Grant access to individual IAM users instead.\n'
            )
            sys.exit(1)
    except Exception:
        pass

    sys.stderr.write(
        f'[error] Could not resolve "{who}" to an IAM user.\n'
    )
    sys.exit(1)


# ── Access commands ────────────────────────────────────────────────

def show_access(args: argparse.Namespace) -> None:
    '''Display the bucket access policy, or dispatch grant/revoke.'''
    if args.op == 'grant':
        grant_access(args)
        return
    if args.op == 'revoke':
        revoke_access(args)
        return

    # Show the current policy.
    cc = cloud(scoped=True)
    policy = cc.obs.get_policy(args.name)

    if args.format == 'terminal':
        stmts = policy.get('Statement', [])
        if not stmts:
            print(f'No bucket policy on "{args.name}".')
            return
        for s in stmts:
            principals = s.get('Principal', {}).get('AWS', [])
            if isinstance(principals, str):
                principals = [principals]
            actions = s.get('Action', [])
            if isinstance(actions, str):
                actions = [actions]
            effect = s.get('Effect', '?')
            for p in principals:
                # Shorten URN to just the name part.
                short = p.rsplit(':', 1)[-1] if ':' in p else p
                print(f'  {effect:5s}  {short:30s}  {", ".join(actions)}')
    else:
        formatters.write_single_output(policy, args.format)


def grant_access(args: argparse.Namespace) -> None:
    '''Grant bucket access to an IAM user (groups not supported)'''
    if not args.who or not args.permission:
        sys.stderr.write('[error] Usage: access <name> grant <who> <perm>\n')
        sys.exit(1)
    cc = cloud(scoped=True)
    ptype, principal_urn = _resolve_principal(cc, args.who)
    cc.obs.grant_policy(args.name, principal_urn, args.permission.upper())
    print(f'Granted "{args.permission.upper()}" on "{args.name}" to {ptype} "{args.who}".')


def revoke_access(args: argparse.Namespace) -> None:
    '''Revoke bucket access from an IAM user (groups not supported)'''
    if not args.who or not args.permission:
        sys.stderr.write('[error] Usage: access <name> revoke <who> <perm>\n')
        sys.exit(1)
    cc = cloud(scoped=True)
    ptype, principal_urn = _resolve_principal(cc, args.who)
    cc.obs.revoke_policy(args.name, principal_urn, args.permission.upper())
    print(f'Revoked "{args.permission.upper()}" on "{args.name}" from {ptype} "{args.who}".')


# ── Parser ─────────────────────────────────────────────────────────

def parser(subp: argparse.ArgumentParser) -> None:
    '''Register the ``bucket`` sub-parser'''
    pr = subp.add_parser('bucket',
                         help='Object Storage Bucket management',
                         aliases=['obs', 'buckets'])
    pr.set_defaults(recipe_cb=list_buckets)
    formatters.add_format_arg(pr)

    sp = pr.add_subparsers(title='op',
                           description='Operation.  If not specified, list buckets.',
                           required=False,
                           help='Operation')

    # -- create ----------------------------------------------------------
    pp = sp.add_parser('create',
                       help='Create a new bucket',
                       aliases=['mk', 'new'])
    pp.add_argument('name', help='Bucket name (globally unique)')
    pp.add_argument('--location', '-l', default=None,
                    help='Bucket location (region). Defaults to session region.')
    pp.set_defaults(recipe_cb=create_bucket)

    # -- delete ----------------------------------------------------------
    pp = sp.add_parser('delete',
                       help='Delete a bucket (must be empty)',
                       aliases=['del', 'rm', 'remove'])
    pp.add_argument('name', help='Bucket name')
    pp.set_defaults(recipe_cb=delete_bucket)

    # -- ls ----------------------------------------------------------------
    pp = sp.add_parser('ls',
                       help='List buckets, optionally filtered by tag',
                       aliases=['list', 'filter'])
    pp.add_argument('filter',
                    nargs='*',
                    help='Tag filter as KEY=VALUE (repeatable)')
    pp.add_argument('--tag',
                    action='append',
                    default=[],
                    dest='list_tags',
                    metavar='KEY',
                    help='Display specific tag KEY as a column (repeatable; '
                         'default: all tags in a combined column)')
    pp.set_defaults(recipe_cb=list_buckets_filtered)
    formatters.add_format_arg(pp)

    # -- tag -------------------------------------------------------------
    pp = sp.add_parser('tag',
                       help='Show or set tags on a bucket',
                       aliases=['tags'])
    pp.add_argument('name', help='Bucket name')
    pp.add_argument('tag',
                    nargs='*',
                    help='Tag as key=value (if omitted, list existing tags)')
    pp.set_defaults(recipe_cb=show_tags)
    formatters.add_single_format_arg(pp)

    # -- untag -----------------------------------------------------------
    pp = sp.add_parser('untag',
                       help='Delete tags from a bucket',
                       aliases=['tag-del', 'rmtag'])
    pp.add_argument('name', help='Bucket name')
    pp.add_argument('key',
                    nargs='*',
                    help='Tag key(s) to remove')
    pp.add_argument('--all', '-a',
                    action='store_true',
                    default=False,
                    help='Delete all tags from the bucket')
    pp.set_defaults(recipe_cb=delete_tags)

    # -- access ----------------------------------------------------------
    pp = sp.add_parser("access",
                       help="Manage bucket access policy (IAM users/groups)",
                       aliases=["policy"])
    pp.add_argument("name", help="Bucket name")
    pp.add_argument("op", nargs="?",
                    choices=["grant", "revoke"],
                    help="Operation (grant or revoke)")
    pp.add_argument("who", nargs="?",
                    help="IAM user or group name")
    pp.add_argument("permission", nargs="?",
                    choices=["READ", "WRITE", "FULL_CONTROL"],
                    help="Permission to grant/revoke")
    pp.set_defaults(recipe_cb=show_access)
    formatters.add_single_format_arg(pp)


parsers.register_parser('bucket', parser)

# Kermit — Project Environment Setup

```{eval-rst}
.. module:: recipes.kermit
   :synopsis: Set up and dismantle project environments.
```

The Kermit recipe automates the creation and deletion of entire project
environments: projects, custom roles, groups, and users with credentials.

(setup)=

## setup

Setting up a project will:

1. Create a project to scope the work.
2. Create groups and assign them project-related roles. By default it
   creates the following groups:
   - `admin` — Full resource admin access
   - `guest` — Read-only access
3. Create users for the created groups. By default it creates random
   users with random passwords.

Additional users and credentials can be created with the {doc}`users` recipe
and assigned to the created groups.

### Minimal setup with defaults

```bash
scullery kermit setup --defaults=region_project-name --output=info.yaml
```

### Setup with a spec file

```bash
scullery kermit setup --spec=input.yaml --output=info.yaml
```

Example YAML spec file:

```yaml
# project is the only mandatory configuration item
project: eu-de_testprj

# Everything from here on is optional
description: testprj description

# If domain_id is not specified it will use one from the region
# or the default for the logged-in user
domain_id: '*change_me*'
# If parent_id is not specified it will use the one from the region
parent_id: '*change_me*'

#
# If groups section does not exist, a default set of groups will be
# created
#
# Groups section contains a base group name, and the role that it
# will be assigned
#
groups:
  admin: te_admin
  guest: readonly
  ops: ACME-kermit-jump

#
# If the users section does not exists a users section will be
# generated with one random user for each group defined earlier
#
# Users should contain a "User_name" and a "group_name" that the
# user will be assigned to.
users:
  my_admin: admin
  my_guest: guest

#
# The creds section is used to define initial password for newly
# created users.
#
# It should contain mappings of "user: password"
#
# if a user defined in users does not have a matching password in
# the creds section a random password will be assigned.
#
creds:
  my_admin: change_Me123
```

## delete

Delete a previously set-up project environment:

```bash
scullery kermit del region_project-name [--force] [--execute]
```

This will reverse all operations performed by `setup`.

The recipe uses the Resource Management service to check for active
resources associated with the project. If any exist, it stops unless
the `--force` option is used.

By default, only a dry-run is shown. Use `--execute` to actually
perform the changes.

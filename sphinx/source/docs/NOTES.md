# NOTES

# TODO

- [x] format specification/JSON/YAML
- [x] Terraform-compatible authentication (password, token, AK/SK, agency)
- [x] kurotc ops -- shouldn't require admin access
  - start, stop, list-status
- [x] list flavors, deh types
- [x] list OS images
- [x] Include curler as a recipe
- [x] Better table output
- [x] reset password
  - seems to work *once* and need to wait before re-use.
- [x] manage OBS buckets
- [x] Add `--scope` option so that we can choose the project scope
***
- [ ] Revamp the credential workflow
- [ ] Get temp AK/SK/Token
  - login like functionality.  Input username/password and updating
    .config/openstack/clouds.yaml file.
- [ ] Phase out kermit -> terraform project factory pattern
  - https://github.com/iits-consulting/terraform-opentelekomcloud-project-factory
  - https://github.com/iits-consulting/terraform-opentelekomcloud-projects
  - Waiting for CASIO Closure

# ADRs

- Functionality that can be done on TerraForm not to be replicated.
  - i.e. kermit recipes
- Functionality that can be done with S3cmd not to be replicated.  But maybe
  something to login to s3cmd would be good.  (Writting to s3cmd config)
- Will **NOT** implement agency authentication
- Will **NOT** implement Federated Identity support
- will **NOT** import OS images, assuming an existing OBS object.
  This is possible from Terraform.  TF supports the full
  cycle, including creating buckets, upload object etc.

Authentication is done via

* SCL_USERNAME
* SCL_PASSWORD
* SCL_TENANT = OTC0000xxxx
* SCL_REGION = eu-de|eu-nl -- test if we can auth in DE and then use
  a eu-nl project

or

.config/scullery/creds.yaml

rcp_curler uses that or can override with CLI args ak/sk/token

login

* Files
  * user clouds.yaml/CLI specified file/OS_CLIENT_CONFIG_FILE
  * ~/.s3cfg
* Scoped
  * Create clouds.yaml in current directory or CLI spcified or OS_CLIENT_CONFIG_FILE
  * Option to write a hcl file with authentication variables
  * Warn: Environment AK/SK or Username or Token
  * Create backend.hcl in current directory (unless overriden)
* Unscoped
  * Warn: Environment AK/SK, just use Environment Username
  * CLI specified file|OS_CLIENT_CONFIG_FILE
  * If not overridenn we write to user .config/openstack/clouds.yaml
    and ~/.s3cfg
* Login always uses temp AK/SK

REF: https://python-otcextensions.readthedocs.io/en/latest/install/configuration.html

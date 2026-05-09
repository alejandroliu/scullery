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

Authentication

enviroment
OS_USERNAME
OS_USER_DOMAIN_NAME
OS_PASSWORD

Assumes eu-de unless OS_TENANT_NAME

Otherwise uses file:
- /etc/openstack/{clouds,secure}.yaml
- ~/.config/openstack/{clouds,secure}.yaml
- current dir ./{clouds,secure}.yaml)

If using clouds.yaml

```yaml
clouds:
  scullery:
    auth:
      username: '<USER_NAME>'
      password: '<PASSWORD>'
      user_domain_name: 'OTC00000000001000000xxx'
```
Will only look for `scullery` as the project key.
assumes eu-de.

Show a warning if user has OS_TENANT_NAME or OS_PROJECT_NAME
or has (clouds)(scullery)(auth)(project_name) defined in clouds.yaml
and a scope is requested on command line.

> We have code to do AK/SK reuqests, but these are not allowed to do
> IAM calls, TMS is also not working with AK/SK.  They are scoped
> at creation time (to the scope of the token that created the AK/SK)
> so they can not change scope after creation.
>
> Most of the recipes do not work with those restrictions.  The only
> recipes that work well with those restrictions are the buckets recipes
> and the raw REST API recipes.

* login - configures ~/.config/openstack ... Default `scullery` key,
  Complains if environment is set.
  Can configure via CLI or interactively.
  `pip install questionary` for interaction.
  Or use to configure other clouds in ~/.config/openstack via
  CLI or interactively.

* s3login configures ~/.s3cfg with temporary keys only.  Permanent
  keys should be done manually.  Also should accept a token
  or OS_AUTH_TOKEN/OS_TOKEN to get the AK/SK.
  ```ini
  [default]
  access_key = <your-temporary-AK>
  secret_key = <your-temporary-SK>
  access_token = <your-security-token>

  host_base = obs.eu-de.otc.t-systems.com
  host_bucket = %(bucket)s.obs.eu-de.otc.t-systems.com

  use_https = True
  signature_v2 = False

  region = eu-de
  ```
  Use `pip install configupdater` instead of the built-in `configparser`
  because it keeps comments.

* Generate auth files
  * HCL or ENV's
  * output temp AK/SK, scoped bearer token
  * accepts OS_AUTH_TOKEN/OS_TOKEN or OS_USERNAME, or CLI args or
    --metadata server


REF: https://python-otcextensions.readthedocs.io/en/latest/install/configuration.html

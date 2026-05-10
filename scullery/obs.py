#!python3
#
# OBS (Object Storage Service) bucket management
#
from __future__ import annotations

'''OBS Bucket API — list, create, and delete buckets.

The OBS API requires **AWS Signature V4** (AWS4-HMAC-SHA256) signing for
every request.  This module implements the signer (:class:`OBSAuth`) and
automatically handles credential acquisition:

* If the :class:`~scullery.api.ApiSession` was created with **AK/SK** auth,
  those credentials are reused directly (converted to ``OBSAuth``).
* If the session uses **password** or **token** auth, a temporary AK/SK
  pair (with *security_token*) is obtained from IAM via
  :meth:`~scullery.iam.Iam.get_aksk` before making any OBS call.

Usage::

    from scullery import cloud
    cc = cloud()
    buckets = cc.buckets.list()
    cc.buckets.create('my-new-bucket')
    cc.buckets.delete('my-old-bucket')
'''

import datetime
import hashlib
import hmac
import json
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, quote, urlencode, parse_qsl

import requests
from requests.auth import AuthBase

try:
  from icecream import ic
except ImportError:  # Graceful fallback if IceCream isn't installed.
  ic = lambda *a: None if not a else (a[0] if len(a) == 1 else a)  # noqa


# ====================================================================
# AWS Signature V4 signer  (for OBS / S3-compatible API)
# ====================================================================

_SERVICE = 's3'
_ALGORITHM = 'AWS4-HMAC-SHA256'


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac_sha256(key: bytes, msg: bytes | str) -> bytes:
    if isinstance(msg, str):
        msg = msg.encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).digest()


def _signing_key(secret_key: str, date_stamp: str, region: str) -> bytes:
    '''Derive the AWS Signature V4 signing key.'''
    k_secret = ('AWS4' + secret_key).encode('utf-8')
    k_date = _hmac_sha256(k_secret, date_stamp)
    k_region = _hmac_sha256(k_date, region)
    k_service = _hmac_sha256(k_region, _SERVICE)
    return _hmac_sha256(k_service, 'aws4_request')


class OBSAuth(AuthBase):
    '''AWS Signature V4 request signer for OBS (S3-compatible API).

    Supports both permanent and temporary (STS) credentials.

    :param ak:             Access Key
    :param sk:             Secret Key
    :param region:         OBS region (e.g. ``'eu-de'``)
    :param security_token: Optional temporary security token (from IAM)
    '''

    def __init__(self, ak: str, sk: str, region: str,
                 security_token: str | None = None) -> None:
        self.ak = ak
        self.sk = sk
        self.region = region
        self.security_token = security_token

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        # 1. Timestamps
        now = datetime.datetime.now(datetime.timezone.utc)
        amz_date = now.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = now.strftime('%Y%m%d')

        r.headers['X-Amz-Date'] = amz_date
        if self.security_token:
            r.headers['X-Amz-Security-Token'] = self.security_token

        # 2. Payload hash
        body = r.body or b''
        if isinstance(body, str):
            body = body.encode('utf-8')
        payload_hash = _sha256_hex(body)
        r.headers['X-Amz-Content-Sha256'] = payload_hash

        # 3. Canonical URI
        parsed = urlparse(r.url)
        uri = quote(parsed.path or '/', safe='/-_.~')

        # 4. Canonical query string
        query_params = sorted(parse_qsl(parsed.query, keep_blank_values=True))
        canonical_query = urlencode(query_params)

        # 5. Canonical headers (sorted, lowercase keys)
        host = parsed.netloc
        headers_to_sign = {
            'host': host,
            'x-amz-content-sha256': payload_hash,
            'x-amz-date': amz_date,
        }
        if self.security_token:
            headers_to_sign['x-amz-security-token'] = self.security_token

        # Also pick up content-type if set
        ct = r.headers.get('Content-Type', '')
        if ct:
            headers_to_sign['content-type'] = ct

        sorted_headers = sorted(headers_to_sign.items())
        canonical_headers = ''.join(f'{k}:{v}\n' for k, v in sorted_headers)
        signed_headers = ';'.join(k for k, _ in sorted_headers)

        # 6. Canonical request
        canonical_request = '\n'.join([
            r.method.upper(),
            uri,
            canonical_query,
            canonical_headers,
            signed_headers,
            payload_hash,
        ])

        # 7. String to sign
        credential_scope = f'{date_stamp}/{self.region}/{_SERVICE}/aws4_request'
        hashed_cr = _sha256_hex(canonical_request.encode('utf-8'))
        string_to_sign = '\n'.join([
            _ALGORITHM,
            amz_date,
            credential_scope,
            hashed_cr,
        ])

        # 8. Signature
        s_key = _signing_key(self.sk, date_stamp, self.region)
        signature = hmac.new(
            s_key, string_to_sign.encode('utf-8'), hashlib.sha256
        ).hexdigest()

        # 9. Authorization header
        r.headers['Authorization'] = (
            f'{_ALGORITHM} Credential={self.ak}/{credential_scope}, '
            f'SignedHeaders={signed_headers}, Signature={signature}'
        )
        return r


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

def _ns(root: ET.Element) -> str:
    '''Extract the XML namespace from *root* (or empty string).'''
    tag = root.tag
    if '}' in tag:
        return tag.split('}')[0].strip('{')
    return ''


def _text(parent: ET.Element | None, tag: str, ns: str = '') -> str:
    '''Return the text content of *tag* inside *parent*, or empty string.'''
    if parent is None:
        return ''
    child = parent.find(f'{{{ns}}}{tag}' if ns else tag)
    return child.text if child is not None else ''


# ---------------------------------------------------------------------------
# Location-constraint XML body builder
# ---------------------------------------------------------------------------

def _location_body(region: str) -> bytes:
    '''Build the ``CreateBucketConfiguration`` XML body.

    Required when creating a bucket in a region that differs from the
    endpoint's default region (per the S3 / OBS specification).
    '''
    # OBS namespace used for create-bucket config
    return (
        b'<CreateBucketConfiguration'
        b' xmlns="http://obs.otc.t-systems.com/doc/2014-01-01/">'
        b'<LocationConstraint>' + region.encode('utf-8') +
        b'</LocationConstraint>'
        b'</CreateBucketConfiguration>'
    )


# ---------------------------------------------------------------------------
# Buckets class
# ---------------------------------------------------------------------------

class Buckets:
    '''OBS bucket management — list, create, delete, and ACL management.'''

    API_HOST = 'obs.{region}.otc.t-systems.com'
    '''OBS API endpoint template.'''

    # Well-known group URIs for OBS ACLs.
    GROUP_ALL_USERS = 'http://acs.amazonaws.com/groups/global/AllUsers'
    '''All users group URI.'''
    GROUP_AUTHENTICATED_USERS = 'http://acs.amazonaws.com/groups/global/AuthenticatedUsers'
    '''Authenticated users group URI.'''

    # Valid ACL permissions.
    PERMISSIONS = frozenset({'READ', 'WRITE', 'READ_ACP', 'WRITE_ACP', 'FULL_CONTROL'})

    OBS_XML_NS = 'http://obs.otc.t-systems.com/doc/2014-01-01/'
    '''XML namespace used in OBS responses.'''

    XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
    '''XML Schema Instance namespace (for grantee type attribute).'''

    def api_path(self, path: str = '') -> str:
        '''Build the full OBS API URL for *path*.'''
        host = Buckets.API_HOST.format(region=self.session.region)
        return f'https://{host}{path}'

    def __init__(self, session) -> None:
        '''Constructor.

        :param session: An :class:`~scullery.api.ApiSession` instance.
        '''
        self.session = session
        self._auth = None
        '''Cached :class:`OBSAuth` (or *None*).'''

    # ------------------------------------------------------------------
    # Credential handling
    # ------------------------------------------------------------------

    def _ensure_auth(self) -> OBSAuth:
        '''Return an :class:`OBSAuth` for signing OBS requests.

        * If the session was created with **AK/SK** auth, the same
          credentials are reused via a new ``OBSAuth`` instance.
        * If the session uses **password** or **token** auth, a
          temporary AK/SK pair (with ``security_token``) is obtained
          from IAM via :meth:`~scullery.iam.Iam.get_aksk`.
        '''
        if self._auth is not None:
            return self._auth

        ak: str
        sk: str
        security_token: str | None = None

        # Session is already using AK/SK — extract credentials.
        if self.session.aksk_auth is not None:
            ak = self.session.aksk_auth.ak
            sk = self.session.aksk_auth.sk
            security_token = self.session.aksk_auth.security_token
        else:
            # Password or token auth — get temporary AK/SK from IAM.
            cred = self.session.iam.get_aksk()
            ak = cred['access']
            sk = cred['secret']
            security_token = cred.get('securitytoken')

        self._auth = OBSAuth(
            ak=ak,
            sk=sk,
            region=self.session.region,
            security_token=security_token,
        )
        return self._auth

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs):
        '''Make an OBS API request and return the response.

        :param method: HTTP method (``'get'``, ``'put'``, ``'delete'``, …)
        :param path:   URL path relative to the OBS endpoint
        :param kwargs: Forwarded to ``requests.request``
        :returns:      ``requests.Response``
        :raises requests.HTTPError: On non-2xx status
        '''
        auth = self._ensure_auth()
        url = self.api_path(path)
        fn = getattr(requests, method.lower())
        resp = fn(url, auth=auth, **kwargs)
        if not resp.ok:
            raise RuntimeError(
                f'OBS API error {resp.status_code}: {resp.text[:2000]}'
            )
        return resp

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list(self) -> list[dict]:
        '''List all OBS buckets for the current project.

        :returns: List of dicts with keys ``name`` and ``creation_date``.
        :raises RuntimeError: On API errors.

        Calls ``GET /`` on the OBS endpoint and parses the XML response.
        '''
        resp = self._request('get', '/')
        root = ET.fromstring(resp.content)
        namespace = _ns(root)

        buckets: list[dict] = []
        buckets_elem = root.find(f'{{{namespace}}}Buckets' if namespace else 'Buckets')
        if buckets_elem is not None:
            for bucket_elem in buckets_elem.findall(
                f'{{{namespace}}}Bucket' if namespace else 'Bucket'
            ):
                buckets.append({
                    'name': _text(bucket_elem, 'Name', namespace),
                    'creation_date': _text(bucket_elem, 'CreationDate', namespace),
                })
        return buckets

    def create(self, name: str, location: str | None = None) -> None:
        '''Create a new OBS bucket.

        :param name:     Bucket name (must be globally unique).
        :param location: Optional bucket location (region).  If omitted the
                         default region for the session is used.
        :raises RuntimeError: On API errors.

        When *location* differs from the endpoint region (or when the
        endpoint region is not the default), the standard
        ``CreateBucketConfiguration`` XML body is included.
        '''
        headers: dict[str, str] = {}
        body: bytes | None = None

        obs_region = location or self.session.region

        # The S3 / OBS specification requires the location constraint
        # in the PUT body, not (just) a header.
        body = _location_body(obs_region)
        headers['Content-Type'] = 'application/xml'

        self._request('put', f'/{name}', headers=headers, data=body)

    def delete(self, name: str) -> None:
        '''Delete an OBS bucket.

        The bucket **must** be empty before it can be deleted.

        :param name: Bucket name.
        :raises RuntimeError: On API errors.
        '''
        self._request('delete', f'/{name}')

    # ------------------------------------------------------------------
    # ACL helpers
    # ------------------------------------------------------------------

    def _parse_acl(self, root: ET.Element) -> dict:
        '''Parse an ``AccessControlPolicy`` XML element into a structured dict.

        :param root: The root ``<AccessControlPolicy>`` element.
        :returns: A dict with keys ``owner`` and ``grants``.
        '''
        ns = _ns(root) or Buckets.OBS_XML_NS

        # -- Owner --
        owner_el = root.find(f'{{{ns}}}Owner' if ns else 'Owner')
        owner = {
            'id': _text(owner_el, 'ID', ns),
            'display_name': _text(owner_el, 'DisplayName', ns),
        }

        # -- Grants --
        grants: list[dict] = []
        acl_el = root.find(f'{{{ns}}}AccessControlList' if ns else 'AccessControlList')
        if acl_el is not None:
            for grant_el in acl_el.findall(
                f'{{{ns}}}Grant' if ns else 'Grant'
            ):
                grantee_el = grant_el.find(
                    f'{{{ns}}}Grantee' if ns else 'Grantee'
                )
                grantee: dict = {}
                if grantee_el is not None:
                    # Grantee type is stored as xsi:type attribute
                    gtype = grantee_el.get(f'{{{Buckets.XSI_NS}}}type', 'CanonicalUser')
                    grantee['type'] = gtype
                    if gtype == 'CanonicalUser':
                        grantee['id'] = _text(grantee_el, 'ID', ns)
                        dn = _text(grantee_el, 'DisplayName', ns)
                        if dn:
                            grantee['display_name'] = dn
                    elif gtype == 'Group':
                        grantee['uri'] = _text(grantee_el, 'URI', ns)

                permission = _text(grant_el, 'Permission', ns)
                grants.append({
                    'grantee': grantee,
                    'permission': permission,
                })

        return {
            'owner': owner,
            'grants': grants,
        }

    def _build_acl_xml(self, acl: dict) -> bytes:
        '''Build an ``AccessControlPolicy`` XML body from a structured dict.

        :param acl: Dict with keys ``owner`` and ``grants`` (same format as
                    returned by :meth:`_parse_acl`).
        :returns: XML bytes suitable for ``PUT /{bucket}?acl``.
        '''
        ns = Buckets.OBS_XML_NS
        xsi = Buckets.XSI_NS

        # Register namespaces so OBS accepts the XML — default namespace
        # without prefix, and xsi: for the type attribute.
        ET.register_namespace('', ns)
        ET.register_namespace('xsi', xsi)

        root = ET.Element(f'{{{ns}}}AccessControlPolicy')

        # -- Owner --
        owner_el = ET.SubElement(root, f'{{{ns}}}Owner')
        oid = ET.SubElement(owner_el, f'{{{ns}}}ID')
        oid.text = acl['owner']['id']
        if acl['owner'].get('display_name'):
            odn = ET.SubElement(owner_el, f'{{{ns}}}DisplayName')
            odn.text = acl['owner']['display_name']

        # -- AccessControlList --
        acl_el = ET.SubElement(root, f'{{{ns}}}AccessControlList')

        for grant in acl['grants']:
            grant_el = ET.SubElement(acl_el, f'{{{ns}}}Grant')
            grantee_el = ET.SubElement(grant_el, f'{{{ns}}}Grantee')
            gtype = grant['grantee']['type']
            grantee_el.set(f'{{{xsi}}}type', gtype)

            if gtype == 'CanonicalUser':
                gid = ET.SubElement(grantee_el, f'{{{ns}}}ID')
                gid.text = grant['grantee']['id']
                if grant['grantee'].get('display_name'):
                    gdn = ET.SubElement(grantee_el, f'{{{ns}}}DisplayName')
                    gdn.text = grant['grantee']['display_name']
            elif gtype == 'Group':
                guri = ET.SubElement(grantee_el, f'{{{ns}}}URI')
                guri.text = grant['grantee']['uri']

            perm = ET.SubElement(grant_el, f'{{{ns}}}Permission')
            perm.text = grant['permission']

        return ET.tostring(root, encoding='utf-8')

    # ------------------------------------------------------------------
    # ACL public API
    # ------------------------------------------------------------------

    def get_acl(self, bucket: str) -> dict:
        '''Get the Access Control List for a bucket.

        :param bucket: Bucket name.
        :returns: Dict with keys ``owner`` and ``grants`` (list of grant dicts).
        :raises RuntimeError: On API errors.

        Calls ``GET /{bucket}?acl`` on the OBS endpoint and parses the XML.
        '''
        resp = self._request('get', f'/{bucket}?acl')
        root = ET.fromstring(resp.content)
        return self._parse_acl(root)

    def set_acl(self, bucket: str, acl: dict) -> None:
        '''Set the Access Control List for a bucket.

        :param bucket: Bucket name.
        :param acl:    Dict with keys ``owner`` and ``grants`` (same format
                       as returned by :meth:`get_acl`).
        :raises RuntimeError: On API errors.

        Calls ``PUT /{bucket}?acl`` with the ACL XML body.
        '''
        xml_body = self._build_acl_xml(acl)
        headers = {'Content-Type': 'application/xml'}
        self._request('put', f'/{bucket}?acl', headers=headers, data=xml_body)

    def grant(self, bucket: str, grantee_type: str, grantee_id: str,
              permission: str, display_name: str | None = None) -> None:
        '''Grant a permission on a bucket.

        Reads the current ACL, appends the new grant (if not already present),
        and writes it back.

        :param bucket:       Bucket name.
        :param grantee_type: ``'CanonicalUser'`` or ``'Group'``.
        :param grantee_id:   For ``CanonicalUser``: the domain/account ID.
                             For ``Group``: the group URI (e.g.
                             ``http://acs.amazonaws.com/groups/global/AllUsers``).
        :param permission:   One of ``READ``, ``WRITE``, ``READ_ACP``,
                             ``WRITE_ACP``, ``FULL_CONTROL``.
        :param display_name: Optional display name (e.g. the original username).
                             Only meaningful for ``CanonicalUser`` grantees.
        :raises RuntimeError: On API errors.
        :raises ValueError:   On invalid grantee type or permission.
        '''
        if grantee_type not in ('CanonicalUser', 'Group'):
            raise ValueError(
                f'Invalid grantee type "{grantee_type}". '
                f'Expected "CanonicalUser" or "Group".'
            )
        if permission not in Buckets.PERMISSIONS:
            raise ValueError(
                f'Invalid permission "{permission}". '
                f'Valid values: {", ".join(sorted(Buckets.PERMISSIONS))}'
            )

        acl = self.get_acl(bucket)

        # Check if the exact grant already exists.
        for g in acl['grants']:
            if g['permission'] == permission and g['grantee'].get('type') == grantee_type:
                if grantee_type == 'CanonicalUser' and g['grantee'].get('id') == grantee_id:
                    print(f'Grant already exists for "{grantee_id}" with "{permission}".')
                    return
                if grantee_type == 'Group' and g['grantee'].get('uri') == grantee_id:
                    print(f'Grant already exists for "{grantee_id}" with "{permission}".')
                    return

        new_grant: dict
        if grantee_type == 'CanonicalUser':
            new_grant = {
                'grantee': {'type': 'CanonicalUser', 'id': grantee_id},
                'permission': permission,
            }
            if display_name:
                new_grant['grantee']['display_name'] = display_name
        else:
            new_grant = {
                'grantee': {'type': 'Group', 'uri': grantee_id},
                'permission': permission,
            }

        acl['grants'].append(new_grant)
        self.set_acl(bucket, acl)

    def revoke(self, bucket: str, grantee_type: str, grantee_id: str,
               permission: str) -> None:
        '''Revoke a permission from a bucket.

        Reads the current ACL, removes any matching grant, and writes it back.

        :param bucket:       Bucket name.
        :param grantee_type: ``'CanonicalUser'`` or ``'Group'``.
        :param grantee_id:   For ``CanonicalUser``: the domain/account ID.
                             For ``Group``: the group URI.
        :param permission:   One of ``READ``, ``WRITE``, ``READ_ACP``,
                             ``WRITE_ACP``, ``FULL_CONTROL``.
        :raises RuntimeError: On API errors.
        :raises ValueError:   On invalid grantee type or permission.
        '''
        if grantee_type not in ('CanonicalUser', 'Group'):
            raise ValueError(
                f'Invalid grantee type "{grantee_type}". '
                f'Expected "CanonicalUser" or "Group".'
            )
        if permission not in Buckets.PERMISSIONS:
            raise ValueError(
                f'Invalid permission "{permission}". '
                f'Valid values: {", ".join(sorted(Buckets.PERMISSIONS))}'
            )

        acl = self.get_acl(bucket)

        original_count = len(acl['grants'])
        acl['grants'] = [
            g for g in acl['grants']
            if not (
                g['permission'] == permission
                and g['grantee'].get('type') == grantee_type
                and (
                    (grantee_type == 'CanonicalUser' and g['grantee'].get('id') == grantee_id)
                    or (grantee_type == 'Group' and g['grantee'].get('uri') == grantee_id)
                )
            )
        ]

        if len(acl['grants']) == original_count:
            print(f'No matching grant found for "{grantee_id}" with "{permission}".')
            return

        self.set_acl(bucket, acl)

    # ------------------------------------------------------------------
    # Tagging
    # ------------------------------------------------------------------

    def _parse_tagging(self, root: ET.Element) -> list[dict]:
        '''Parse a ``Tagging`` XML element into a list of ``{key, value}`` dicts.

        :param root: The root ``<Tagging>`` element.
        :returns: List of tag dicts.
        '''
        ns = _ns(root) or Buckets.OBS_XML_NS
        tag_set = root.find(f'{{{ns}}}TagSet' if ns else 'TagSet')
        if tag_set is None:
            return []

        tags: list[dict] = []
        for tag_el in tag_set.findall(f'{{{ns}}}Tag' if ns else 'Tag'):
            tags.append({
                'key': _text(tag_el, 'Key', ns),
                'value': _text(tag_el, 'Value', ns),
            })
        return tags

    def _build_tagging_xml(self, tags: list[dict]) -> bytes:
        '''Build a ``Tagging`` XML body from a list of ``{key, value}`` dicts.

        :param tags: List of tag dicts.
        :returns: XML bytes suitable for ``PUT /{bucket}?tagging``.
        '''
        ns = Buckets.OBS_XML_NS
        ET.register_namespace('', ns)

        root = ET.Element(f'{{{ns}}}Tagging')
        tag_set = ET.SubElement(root, f'{{{ns}}}TagSet')
        for tag in tags:
            tag_el = ET.SubElement(tag_set, f'{{{ns}}}Tag')
            k = ET.SubElement(tag_el, f'{{{ns}}}Key')
            k.text = tag['key']
            v = ET.SubElement(tag_el, f'{{{ns}}}Value')
            v.text = tag['value']
        return ET.tostring(root, encoding='utf-8')

    def get_tagging(self, bucket: str) -> list[dict]:
        '''Get the tags on a bucket.

        :param bucket: Bucket name.
        :returns: List of ``{'key': ..., 'value': ...}`` dicts.  Returns an
                  empty list if the bucket has no tags.
        :raises RuntimeError: On API errors (other than 404 — no tags).
        '''
        try:
            resp = self._request('get', f'/{bucket}?tagging')
        except RuntimeError as exc:
            # OBS returns 404 when there are no tags at all.
            if '404' in str(exc):
                return []
            raise
        root = ET.fromstring(resp.content)
        return self._parse_tagging(root)

    def set_tagging(self, bucket: str, tags: list[dict]) -> None:
        '''Set the tags on a bucket (replaces any existing tags).

        :param bucket: Bucket name.
        :param tags:   List of ``{'key': ..., 'value': ...}`` dicts.
        :raises RuntimeError: On API errors.

        Calls ``PUT /{bucket}?tagging`` with the tagging XML body.
        '''
        xml_body = self._build_tagging_xml(tags)
        headers = {'Content-Type': 'application/xml'}
        self._request('put', f'/{bucket}?tagging', headers=headers, data=xml_body)

    def delete_tagging(self, bucket: str) -> None:
        '''Delete all tags from a bucket.

        :param bucket: Bucket name.
        :raises RuntimeError: On API errors.

        Calls ``DELETE /{bucket}?tagging``.
        '''
        self._request('delete', f'/{bucket}?tagging')

    # ------------------------------------------------------------------
    # Bucket policy (IAM user / group access)
    # ------------------------------------------------------------------

    POLICY_VERSION = '2008-10-17'
    '''The only policy version accepted by the OBS / S3 API.'''

    @staticmethod
    def _principal_urn(domain_id: str, principal_type: str, name: str) -> str:
        '''Build an IAM principal ARN for a user or group (S3-compatible format).

        :param domain_id:      The domain/account ID.
        :param principal_type: ``'user'`` or ``'group'``.
        :param name:           The IAM user or group name.
        :returns:              An ARN string suitable for use in a bucket
                               policy ``Principal`` element.
        '''
        return f'arn:aws:iam::{domain_id}:{principal_type}/{name}'

    @staticmethod
    def _bucket_arn(bucket: str) -> str:
        '''Build the OBS ARN for *bucket* and its objects (S3-compatible format).'''
        return f'arn:aws:s3:::{bucket}'

    @staticmethod
    def _object_arn(bucket: str) -> str:
        '''Build the OBS ARN for objects inside *bucket*.'''
        return f'arn:aws:s3:::{bucket}/*'

    @staticmethod
    def _permission_actions(permission: str) -> list[str]:
        '''Map a short permission name to a list of S3 actions.

        :param permission: ``'READ'``, ``'WRITE'``, or ``'FULL_CONTROL'``.
        :returns:          List of S3 action strings.
        :raises ValueError: On unknown permission.
        '''
        _MAP = {
            'READ': [
                's3:ListBucket',
                's3:GetObject',
                's3:GetObjectVersion',
            ],
            'WRITE': [
                's3:PutObject',
                's3:DeleteObject',
                's3:DeleteObjectVersion',
            ],
            'FULL_CONTROL': ['s3:*'],
        }
        if permission not in _MAP:
            raise ValueError(
                f'Unknown permission "{permission}". '
                f'Valid values: {", ".join(_MAP)}'
            )
        return _MAP[permission]

    def get_policy(self, bucket: str) -> dict:
        '''Get the bucket policy.

        :param bucket: Bucket name.
        :returns: The policy dict (empty policy ``{"Version":"2008-10-17","Statement":[]}``
                  if no policy exists).
        :raises RuntimeError: On API errors other than 404.
        '''
        try:
            resp = self._request('get', f'/{bucket}?policy')
            return resp.json()
        except RuntimeError as exc:
            if '404' in str(exc):
                return {'Version': self.POLICY_VERSION, 'Statement': []}
            raise

    def set_policy(self, bucket: str, policy: dict) -> None:
        '''Set the bucket policy (replaces any existing policy).

        :param bucket: Bucket name.
        :param policy: Policy dict.
        :raises RuntimeError: On API errors.
        '''
        headers = {'Content-Type': 'application/json'}
        self._request('put', f'/{bucket}?policy',
                      headers=headers, data=json.dumps(policy))

    def delete_policy(self, bucket: str) -> None:
        '''Delete the bucket policy.

        :param bucket: Bucket name.
        :raises RuntimeError: On API errors.
        '''
        self._request('delete', f'/{bucket}?policy')

    def grant_policy(self, bucket: str, principal_urn: str,
                     permission: str) -> None:
        '''Grant a permission to an IAM user or group via bucket policy.

        Reads the current policy, adds (or merges into) an ``Allow``
        statement for *principal_urn*, and writes it back.

        :param bucket:        Bucket name.
        :param principal_urn: The IAM user/group URN (see :meth:`_principal_urn`).
        :param permission:    ``'READ'``, ``'WRITE'``, or ``'FULL_CONTROL'``.
        :raises RuntimeError: On API errors.
        :raises ValueError:   On invalid permission.
        '''
        actions = self._permission_actions(permission)
        policy = self.get_policy(bucket)

        # Look for an existing Allow statement that matches this principal.
        found = False
        for stmt in policy['Statement']:
            if stmt.get('Effect') != 'Allow':
                continue
            principals = stmt.get('Principal', {}).get('AWS', [])
            if isinstance(principals, str):
                principals = [principals]
            if principal_urn in principals:
                # Merge actions into the existing statement.
                existing = set(stmt.get('Action', []))
                merged = existing | set(actions)
                if merged != existing:
                    stmt['Action'] = list(merged)
                    found = True
                break
        else:
            # No existing statement — append a new one.
            sid = f'Grant-{principal_urn.split(":")[-1]}-{permission}'
            policy['Statement'].append({
                'Sid': sid,
                'Effect': 'Allow',
                'Principal': {'AWS': [principal_urn]},
                'Action': actions,
                'Resource': [
                    self._bucket_arn(bucket),
                    self._object_arn(bucket),
                ],
            })
            found = True

        if found:
            self.set_policy(bucket, policy)
        else:
            print(f'Permission "{permission}" already fully granted for '
                  f'"{principal_urn}".')

    def revoke_policy(self, bucket: str, principal_urn: str,
                      permission: str) -> None:
        '''Revoke a permission from an IAM user or group via bucket policy.

        Reads the current policy, removes matching actions from the
        principal's ``Allow`` statement, and writes it back.  If the
        statement becomes empty it is removed entirely.

        :param bucket:        Bucket name.
        :param principal_urn: The IAM user/group URN.
        :param permission:    ``'READ'``, ``'WRITE'``, or ``'FULL_CONTROL'``.
        :raises RuntimeError: On API errors.
        :raises ValueError:   On invalid permission.
        '''
        actions = set(self._permission_actions(permission))
        policy = self.get_policy(bucket)
        changed = False

        for stmt in list(policy['Statement']):
            if stmt.get('Effect') != 'Allow':
                continue
            principals = stmt.get('Principal', {}).get('AWS', [])
            if isinstance(principals, str):
                principals = [principals]
            if principal_urn not in principals:
                continue

            current_set = set(stmt.get('Action', []))
            remaining_set = current_set - actions
            if remaining_set != current_set:
                changed = True
                if remaining_set:
                    stmt['Action'] = list(remaining_set)
                else:
                    policy['Statement'].remove(stmt)
            break

        if changed:
            if not policy['Statement']:
                self.delete_policy(bucket)
            else:
                self.set_policy(bucket, policy)
        else:
            print(f'No matching grant found for "{principal_urn}" '
                  f'with "{permission}".')


if __name__ == '__main__':
    import scullery.creds as creds

    cfg = creds.creds(cloud_name='otc')
    from scullery.api import ApiSession

    api = ApiSession(cfg)
    buckets = Buckets(api)
    for b in buckets.list():
        print(b['name'], b['creation_date'])
    del api

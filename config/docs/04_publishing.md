# publishing YAMLs

Publishing is configured indirectly from `infra.yaml` through two file paths:

- `output.archive_config`
- `output.client_config`

This document describes the actual IaC contracts behind those files.

Source of truth:

- `src/pfp_runtime/publishing/archivers/{local_archiver,s3_archiver,s3_compat_archiver,noop_archiver}.py`
- `src/pfp_runtime/publishing/clients/{http_client,streaming_http_client,sftp_client,noop_client}.py`
- `src/pfp_runtime/publishing/support/transport_policy.py`
- `src/pfp_utils/security/{secret_types,secret_resolver}.py`

## Where Publishing Is Selected

In `infra.yaml`:

```yaml
output:
  archive_type: local
  archive_config: ./archive/local.yaml
  client_type: http
  client_config: ./clients/http.yaml
```

Current archive tokens:

- `local`
- `s3`
- `s3_compat`
- `noop`

Current client tokens:

- `http`
- `http_streaming`
- `sftp`
- `noop`

## Transport Policy Blocks

Several archivers/clients embed a nested transport policy.

### `TlsTransportPolicy`

Used by:

- `S3ArchiverIaC`
- `S3CompatArchiverIaC`
- `HttpClientIaC`

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `timeout_seconds` | `float > 0` | no | `60.0` | Timeout for one transport operation. |
| `max_retries` | `int` | no | `3` | Retry budget after the initial failure. |
| `retry_backoff_seconds` | `float >= 0` | no | `0.0` | Fixed delay between retries. |
| `verify_tls` | `bool` | no | `true` | Whether TLS certificates are verified. |

### `SftpTransportPolicy`

Used by `SftpClientIaC`.

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `timeout_seconds` | `float > 0` | no | `60.0` | Timeout for one transport operation. |
| `max_retries` | `int` | no | `3` | Retry budget after the initial failure. |
| `retry_backoff_seconds` | `float >= 0` | no | `0.0` | Fixed delay between retries. |
| `verify_ssh_host_key` | `bool` | no | `true` | Whether remote SSH host key must be verified. |
| `ssh_ciphers` | `list[str] \| null` | no | `null` | Optional allowlist of SSH ciphers. |
| `ssh_macs` | `list[str] \| null` | no | `null` | Optional allowlist of SSH MAC algorithms. |
| `ssh_kex` | `list[str] \| null` | no | `null` | Optional allowlist of SSH key-exchange algorithms. |
| `ssh_key_types` | `list[str] \| null` | no | `null` | Optional allowlist of SSH server key types. |

## SecretRef Mechanism

Secret-bearing fields in publishing YAMLs use `SecretRef`.

Current `SecretRef` shape:

```yaml
kind: env | file | provider
value: <string>
```

Important publishing-specific limitation:

- the base security layer knows three kinds: `env`, `file`, `provider`
- but publishing code resolves secrets through `resolve_secret_ref()` without a provider callback
- in practice, publishing YAMLs should use only `kind: env` or `kind: file`
- `kind: provider` will fail during secret resolution in current publishing code

Recommended forms:

```yaml
api_key_ref:
  kind: env
  value: MY_API_KEY
```

```yaml
private_key_ref:
  kind: file
  value: /run/secrets/sftp_key
```

## Archivers

### `local`

Template: [config/archive/local.yaml.template](../archive/local.yaml.template)

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `output_dir` | `str` | yes | — | Destination directory. It must already exist. |
| `filename_base` | `str` | yes | — | Base name for the output file. Runtime appends `_YYYYMMDD_HHMMSS` in UTC. |

Behavior:

- writes to a temporary file first, then atomically replaces into final path
- does not create `output_dir`
- final filename is generated on each `open()` call

Example:

```yaml
output_dir: ./sent
filename_base: product_feed
```

### `s3`

Template: [config/archive/s3.yaml.template](../archive/s3.yaml.template)

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `bucket` | `str` | yes | — | S3 bucket name. |
| `filename_base` | `str` | yes | — | Base name for generated object key. |
| `key_prefix` | `str` | no | `""` | Optional prefix prepended to generated object key. |
| `region` | `str \| null` | no | `null` | Optional AWS region. When omitted, boto3 resolves region from environment/config. |
| `transport` | `TlsTransportPolicy` | no | default object | Retry/timeout/TLS settings. |

Behavior:

- uses multipart upload
- credentials are not part of IaC; boto3 uses standard AWS credential chain
- generated key is `{key_prefix}{filename_base}_{YYYYMMDD_HHMMSS}`

### `s3_compat`

Template: [config/archive/s3_compat.yaml.template](../archive/s3_compat.yaml.template)

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `endpoint` | `str` | yes | — | Endpoint URL for compatible object storage. |
| `bucket` | `str` | yes | — | Bucket name. |
| `filename_base` | `str` | yes | — | Base name for generated object key. |
| `key_prefix` | `str` | no | `""` | Optional prefix prepended to generated object key. |
| `access_key_ref` | `SecretRef` | yes | — | Access key reference. Use `env` or `file`. |
| `secret_key_ref` | `SecretRef` | yes | — | Secret key reference. Use `env` or `file`. |
| `transport` | `TlsTransportPolicy` | no | default object | Retry/timeout/TLS settings. |

Behavior:

- credentials are resolved fail-fast during object construction
- generated key is `{key_prefix}{filename_base}_{YYYYMMDD_HHMMSS}`
- uses multipart upload like the AWS S3 archiver

### `noop`

Template: [config/archive/noop.yaml.template](../archive/noop.yaml.template)

Contract:

- no fields
- YAML body is simply `{}`

Behavior:

- archiving is intentionally skipped
- runtime returns `ArchiveResult(skipped=True, location=None)`

## Clients

### `http`

Template: [config/clients/http.yaml.template](../clients/http.yaml.template)

Specialized templates in the same directory:

- [config/clients/http_openai.yaml.template](../clients/http_openai.yaml.template)
- [config/clients/http_stripe_product.yaml.template](../clients/http_stripe_product.yaml.template)
- [config/clients/http_stripe_inventory_price.yaml.template](../clients/http_stripe_inventory_price.yaml.template)

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `endpoint` | `str` | yes | — | Full HTTP(S) endpoint URL. |
| `api_key_ref` | `SecretRef \| null` | no | `null` | Optional Bearer token source for API key style auth. Mutually exclusive with `token_ref`. |
| `token_ref` | `SecretRef \| null` | no | `null` | Optional Bearer token source. Mutually exclusive with `api_key_ref`. |
| `content_type` | `str \| null` | no | `null` | Optional `Content-Type` header. |
| `max_body_bytes` | `int > 0` | no | `104857600` | Maximum buffered body size in bytes. |
| `transport` | `TlsTransportPolicy` | no | default object | Retry/timeout/TLS settings. |

Behavior:

- buffers the entire payload in memory
- sends a single POST in `finalize()`
- retries retryable transport failures and 5xx according to `transport`
- both `api_key_ref` and `token_ref` are sent as `Authorization: Bearer ...`

### `http_streaming`

Template: [config/clients/http.yaml.template](../clients/http.yaml.template)

YAML contract:

- exactly the same `HttpClientIaC` schema as `http`

Behavior difference:

- payload is streamed chunk-by-chunk using queue + background thread
- request uses chunked transfer instead of buffering full body
- no retry is applied, because partially sent streaming requests cannot be replayed safely

Use `http_streaming` for large payloads; use `http` when you want retryable buffered POST behavior.

### `sftp`

Template: [config/clients/sftp.yaml.template](../clients/sftp.yaml.template)

Specialized template:

- [config/clients/sftp_openai.yaml.template](../clients/sftp_openai.yaml.template)

| Field | Type | Required | Default | Meaning |
|---|---|---|---|---|
| `host` | `str` | yes | — | SFTP server hostname or IP. |
| `port` | `int` | no | `22` | SSH/SFTP port. |
| `username` | `str` | yes | — | Remote username. |
| `remote_path` | `str` | yes | — | Destination path including filename. |
| `password_ref` | `SecretRef \| null` | no | `null` | Password auth. Exactly one of `password_ref` / `private_key_ref` must be set. |
| `private_key_ref` | `SecretRef \| null` | no | `null` | Private-key auth. Exactly one of `password_ref` / `private_key_ref` must be set. |
| `host_key_ref` | `SecretRef \| null` | no | `null` | Expected server host key. Required when `transport.verify_ssh_host_key=true`. |
| `atomic_write` | `bool` | no | `true` | Write to temporary remote path first, then rename into final target. |
| `transport` | `SftpTransportPolicy` | no | default object | Retry/timeout/SSH policy settings. |

Behavior:

- resolves credentials fail-fast during object construction
- verifies host key by default
- current code exposes SSH allowlists as `ssh_ciphers`, `ssh_macs`, `ssh_kex`, `ssh_key_types`
- `atomic_write` is a real IaC field even though some older docs/templates do not explain it fully

### `noop`

Template: [config/clients/noop.yaml.template](../clients/noop.yaml.template)

Contract:

- no fields
- YAML body is simply `{}`

Behavior:

- delivery is intentionally skipped
- runtime returns `DeliveryResult(skipped=True, status_code=None)`

## Combination Matrix

Archive and client are independent. Any pair of valid tokens is allowed.

Typical combinations:

| `archive_type` | `client_type` | Result |
|---|---|---|
| `noop` | `noop` | No archive copy, no delivery. |
| `local` | `noop` | Local archive only. |
| `s3` | `noop` | AWS S3 archive only. |
| `s3_compat` | `noop` | Compatible-object-store archive only. |
| `noop` | `http` | Buffered HTTP delivery only. |
| `noop` | `http_streaming` | Streaming HTTP delivery only. |
| `noop` | `sftp` | SFTP delivery only. |
| `local` | `http` | Local archive plus buffered HTTP delivery. |
| `local` | `http_streaming` | Local archive plus streaming HTTP delivery. |
| `local` | `sftp` | Local archive plus SFTP delivery. |
| `s3` | `http` | AWS S3 archive plus buffered HTTP delivery. |
| `s3` | `http_streaming` | AWS S3 archive plus streaming HTTP delivery. |
| `s3` | `sftp` | AWS S3 archive plus SFTP delivery. |
| `s3_compat` | `http` | Compatible-object-store archive plus buffered HTTP delivery. |
| `s3_compat` | `http_streaming` | Compatible-object-store archive plus streaming HTTP delivery. |
| `s3_compat` | `sftp` | Compatible-object-store archive plus SFTP delivery. |

## Related Documents

- `01_infra.md` — how archive/client YAMLs are referenced from `infra.yaml`

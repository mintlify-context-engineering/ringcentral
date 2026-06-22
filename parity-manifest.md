# Parity Manifest — API Reference

Tracks the conversion of the RingCentral API Reference (`https://developers.ringcentral.com/api-reference`)
into the Mintlify site at `docs/`.

The live API Reference is rendered from a single machine-readable OpenAPI specification covering the
entire RingCentral Platform API (one product). It is reproduced in Mintlify by referencing that spec
directly from `docs.json`, which auto-generates one page per operation grouped by OpenAPI tag.

## Source spec

| source_url | normalized_path | converted_file | nav_section | status | notes |
|---|---|---|---|---|---|
| https://developers.ringcentral.com/api-reference | /api-reference | docs/openapi/rc-platform.yml | API Reference (tab) | done | Official RingCentral Platform OpenAPI 3.0.3 spec (v1.0.58-20240529), fetched from `https://netstorage.ringcentral.com/dpw/api-reference/specs/rc-platform.yml`. 337 paths / 487 operations across 74 tags. Validated with `mint openapi-check` (valid). |

## Wiring

- `docs.json` navigation converted from a flat `groups` list to `tabs`:
  - `Guides` tab — all previously-existing guide groups (unchanged).
  - `API Reference` tab — `"openapi": "openapi/rc-platform.yml"`, which generates pages for all 487 operations.
- Root-level `api` config added: interactive playground + curl/javascript/python/php/ruby/java/csharp code samples.
- Root-level `contextual` config added (was previously absent).
- Removed the redundant external `topbarLinks`/`navbar` "API Reference" link (now an internal tab);
  navbar now carries a Support link and a "Developer Console" CTA.

## Coverage

All 487 operations in the spec are surfaced automatically by Mintlify from the single referenced spec.
No per-endpoint MDX files are hand-authored (avoids duplication per the OpenAPI conversion guidance).
Endpoint slugs are derived from operation summaries by Mintlify (e.g. `Send SMS` → `api-reference/sms/send-sms`).

## Validation

- `python3 -c "import json; json.load(open('docs.json'))"` → valid JSON.
- `mint openapi-check openapi/rc-platform.yml` → OpenAPI definition is valid.
- `mint broken-links` → 0 MDX parser errors; no broken links introduced by the API Reference.
  (Pre-existing relative-`.md` link warnings in the guide content are unrelated to this change.)
- `mint dev` → preview ready; `/` returns 200, `/api-reference/sms` redirects to
  `/api-reference/sms/send-sms` (200), and the endpoint page renders method (POST), path
  (`/restapi/v1.0/account/{accountId}/extension/{extensionId}/sms`), OAuth auth, and the
  `platform.ringcentral.com` server in the playground.

## Completion criteria

- discovered_pages_count (1 spec / 487 operations) == converted (487) + excluded (0).
- Every discovered operation is `done`.
- Spec is referenced from `docs.json` via `openapi` and paired with root-level `api` config.
- `docs.json` includes root-level `contextual` config.
- Repo is parser-clean for the API Reference addition.

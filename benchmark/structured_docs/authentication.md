# Authentication & OAuth

**doc_id**: authentication  
**tags**: auth, jwt, oauth, login, token, authorization, access_token, credential, bearer, grant_type, refresh, pkce, authorization_code, sandbox, production, client_id, client_secret, multiple users, user-facing, server apps, per-user tokens, refresh tokens

## Quick decision: which auth flow?

| Scenario | Use |
|----------|-----|
| Server script / cron job / no browser UI / **server apps** | **JWT** |
| **Multiple users** log in individually / **user-facing apps** / CRM per-user | **Auth Code + PKCE** |
| JWT is **not** suited for multiple users — use Auth Code for that |

## OAuth Endpoint Quick Facts

- Authorization URL path: `/restapi/oauth/authorize`.
- Auth Code + PKCE redirect params: `response_type=code`, `code_challenge`, `code_challenge_method=S256`.
- Token exchange params: `grant_type=authorization_code`, `code`, and `code_verifier`.
- Refresh token exchange: `grant_type=refresh_token` with `refresh_token`.
- Access token lifetime is commonly described as about `3600` seconds to `7200` seconds depending on the app/token response; refresh tokens last 7 days for Auth Code flow.
- Auth rate limit: `5 requests/user/minute`.
- JWT Python SDK import/login pattern: `from ringcentral import SDK`; `platform.login(jwt='YOUR_JWT_TOKEN')`.
- Error recovery shorthand: `401 re-authenticate`.
- Multiple per-user apps are not JWT scenarios: use Auth Code + PKCE, not JWT.

**Reuse access tokens** — do NOT re-authenticate on every request. Call the token endpoint only when the current token has expired (~7200 seconds). Re-authenticating too often triggers the 5 req/min Auth rate limit.

**Error recovery**: On a `401` response → re-authenticate (`platform.login(jwt=...)`) then retry. On `429` → wait `Retry-After` seconds before retrying.

- **Auth Code for user-facing apps** that need per-user tokens and individual consent
- **JWT for server apps** with a single service account, no user interaction

## JWT Authentication (most common for automation)

**grant_type**: `urn:ietf:params:oauth:grant-type:jwt-bearer`  
(URL-encoded form: `urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer`)

```http
POST https://platform.ringcentral.com/restapi/oauth/token
Content-Type: application/x-www-form-urlencoded
Authorization: Basic <base64(clientId:clientSecret)>

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=<YOUR_JWT>
```

Response contains `access_token`, `expires_in` (7199s), `refresh_token`, `refresh_token_expires_in` (604799s).

Refresh tokens expire in 7 days (604800 seconds).

## Auth Flows — Detail

| Flow | When to Use |
|------|-------------|
| **JWT** | Server/script apps, no user UI, single service account |
| **Auth Code + PKCE** | Frontend apps, multiple end-users log in individually, per-user tokens |
| **Auth Code** | Server-side web apps (older, less secure than PKCE) |

**Not JWT**: If you need individual users to authenticate (multiple users, per-user tokens, refresh tokens per user) → use Auth Code + PKCE.

## SDK Examples (JWT)

### Python SDK

```python
from ringcentral import SDK

sdk = SDK('CLIENT_ID', 'CLIENT_SECRET', 'https://platform.ringcentral.com')
platform = sdk.platform()
platform.login(jwt='YOUR_JWT_TOKEN')

res = platform.get('/account/~/extension/~')
```

### JavaScript SDK (JWT)

```js
const { SDK } = require('@ringcentral/sdk')
const rcsdk = new SDK({ server: 'https://platform.ringcentral.com', clientId: '...', clientSecret: '...' })
const platform = rcsdk.platform()
await platform.login({ jwt: 'YOUR_JWT_TOKEN' })
```

### PHP SDK (JWT)

```php
$sdk = new RingCentral\SDK\SDK('CLIENT_ID', 'CLIENT_SECRET', 'https://platform.ringcentral.com');
$platform = $sdk->platform();
$platform->login(['jwt' => 'YOUR_JWT_TOKEN']);
```

## Authorization Code + PKCE Flow (multi-user apps)

1. Redirect user to: `https://platform.ringcentral.com/restapi/oauth/authorize?response_type=code&client_id=...&redirect_uri=...&code_challenge=...&code_challenge_method=S256`
2. User logs in, RingCentral redirects back with `?code=AUTHCODE`
3. Exchange code: `POST /restapi/oauth/token` with `grant_type=authorization_code&code=AUTHCODE&code_verifier=...`

## Token Refresh

Use refresh_token to get a new access token before expiry:

```http
POST https://platform.ringcentral.com/restapi/oauth/token
grant_type=refresh_token&refresh_token=<REFRESH_TOKEN>
```

## Sandbox vs Production

| Environment | Token URL |
|-------------|-----------|
| Production | `https://platform.ringcentral.com/restapi/oauth/token` |
| Sandbox | `https://platform.devtest.ringcentral.com/restapi/oauth/token` |

## Important Notes

- JWTs themselves do not expire by default (configurable). Access tokens always expire (~7200s).
- **Auth API rate limit: 5 requests/user/minute** (Auth group, 60-second penalty window).
- Cache and reuse access tokens — do not re-authenticate on every request.

→ See also: [api-basics](api-basics.md) for base URLs, [rate-limits](rate-limits.md) for Auth group limits

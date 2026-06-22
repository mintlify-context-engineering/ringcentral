# Authentication & OAuth

**doc_id**: authentication  
**tags**: auth, jwt, oauth, login, token, authorization, access_token, credential, bearer, grant_type

## Overview

RingCentral uses OAuth 2.0. Every API call requires a Bearer access token in the `Authorization` header.

## Auth Flows

| Flow | When to Use |
|------|-------------|
| **JWT** | Server/script apps, no user UI, single service account |
| **Auth Code + PKCE** | Frontend apps, multiple end-users log in individually |
| **Auth Code** | Server-side web apps (older, less secure than PKCE) |

## JWT Authentication (most common for automation)

**Best for**: scripts, cron jobs, server-to-server, chatbots, call log downloaders.

### Step 1 — Exchange JWT for an access token

```http
POST https://platform.ringcentral.com/restapi/oauth/token
Content-Type: application/x-www-form-urlencoded
Authorization: Basic <base64(clientId:clientSecret)>

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=<YOUR_JWT>
```

Response:
```json
{
  "access_token": "U1BCMDFUMDRKV1MwMX...",
  "token_type": "bearer",
  "expires_in": 7199,
  "refresh_token": "U1BCMDFUMDRKV1MwMX...",
  "refresh_token_expires_in": 604799,
  "scope": "AccountInfo CallLog ExtensionInfo Messages SMS"
}
```

### Python SDK (JWT)

```python
from ringcentral import SDK

sdk = SDK('CLIENT_ID', 'CLIENT_SECRET', 'https://platform.ringcentral.com')
platform = sdk.platform()
platform.login(jwt='YOUR_JWT_TOKEN')

# Now call the API
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

Access tokens expire in ~7200 seconds. Use the refresh token to get a new one:

```http
POST https://platform.ringcentral.com/restapi/oauth/token
Content-Type: application/x-www-form-urlencoded
Authorization: Basic <base64(clientId:clientSecret)>

grant_type=refresh_token&refresh_token=<REFRESH_TOKEN>
```

Refresh tokens expire in 7 days (604800 seconds).

## Important Notes

- JWTs themselves do not expire by default (configurable). Access tokens always expire.
- JWT is **not** designed for authenticating many individual users — use Auth Code for that.
- Auth API calls are rate-limited to **5 requests/user/minute** (Auth group).
- Re-use access tokens until they expire; do not re-authenticate on every request.

## Sandbox vs Production

| Environment | Token URL |
|-------------|-----------|
| Production | `https://platform.ringcentral.com/restapi/oauth/token` |
| Sandbox | `https://platform.devtest.ringcentral.com/restapi/oauth/token` |

→ See also: [api-basics](api-basics.md) for base URLs, [rate-limits](rate-limits.md) for Auth group limits

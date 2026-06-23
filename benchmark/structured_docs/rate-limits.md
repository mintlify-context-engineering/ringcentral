# Rate Limits

**doc_id**: rate-limits  
**tags**: rate limit, 429, throttle, x-rate-limit, retry-after, quota, too many requests, headers, heavy, light, medium, auth group, penalty, window, remaining, reuse access tokens, reset the clock

## Rate Limit Groups

Every RingCentral API endpoint belongs to a usage plan group:

| Group | Default Limit | Penalty Window |
|-------|--------------|----------------|
| **Light** | 50 requests/user/minute | 60 seconds |
| **Medium** | 40 requests/user/minute | 60 seconds |
| **Heavy** | 10 requests/user/minute | 60 seconds |
| **Auth** | 5 requests/user/minute | 60 seconds |

The **Auth group** (`5 requests/user/minute`, also written 5 req/user/minute) applies to the token endpoint (`/restapi/oauth/token`). Reuse access tokens — do not re-authenticate on every request or you will trigger this limit. Cache the token and refresh only when it expires (~7200 seconds).

Limits apply per **(user, application)** pair.

## When a Limit Is Exceeded

The server returns **HTTP 429 Too Many Requests**.

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

**Critical**: Every new request during the penalty window **resets the clock** (reset the clock on the penalty window). Do not retry until `Retry-After` seconds have fully elapsed — retrying early will reset the clock again.

## Rate Limit Response Headers

Returned on every API response:

| Header | Description |
|--------|-------------|
| `X-Rate-Limit-Group` | Group name: `light`, `medium`, `heavy`, `auth` |
| `X-Rate-Limit-Limit` | Current limit for this group |
| `X-Rate-Limit-Remaining` | Requests remaining in current window |
| `X-Rate-Limit-Window` | Window size in seconds (usually 60) |

### Example Response Headers

```http
HTTP/1.1 200 OK
X-Rate-Limit-Group: light
X-Rate-Limit-Limit: 1000
X-Rate-Limit-Remaining: 999
X-Rate-Limit-Window: 60
```

## Handling Rate Limits Correctly

### Proactive: check X-Rate-Limit-Remaining before each request

```python
import time

response = platform.get('/restapi/v1.0/account/~/call-log')

remaining = int(response.headers.get('X-Rate-Limit-Remaining', 1))
window = int(response.headers.get('X-Rate-Limit-Window', 60))

if remaining == 0:
    time.sleep(window)  # Wait full window before next request
```

### On receiving a 429

```python
import time

try:
    response = platform.get('/restapi/v1.0/account/~/call-log')
except Exception as e:
    if e.response.status_code == 429:
        retry_after = int(e.response.headers.get('Retry-After', 30))
        time.sleep(retry_after)  # Wait the full Retry-After — do NOT retry early (resets the clock)
        # then retry
```

## Best Practices

1. **Proactively check** `X-Rate-Limit-Remaining` — never wait for a 429
2. **Never retry** during the penalty window — it resets the clock
3. **Reuse access tokens** — do not call the auth endpoint more than necessary (Auth group: 5/min)
4. Different API groups are **counted independently**

## Finding an Endpoint's Group

Check the API Reference at developers.ringcentral.com/api-reference — each endpoint shows its "Usage Plan Group."

→ See also: [authentication](authentication.md) for Auth group context, [api-basics](api-basics.md) for endpoint paths

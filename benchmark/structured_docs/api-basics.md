# API Basics — URLs, Paths, Pagination

**doc_id**: api-basics  
**tags**: base url, sandbox, production, restapi, path, accountid, extensionid, tilde, pagination, page, perPage, navigation, endpoint, uri, version, v1.0

## Base URLs

**Production host / SDK server URL:** `https://platform.ringcentral.com`  
**Sandbox host / SDK server URL:** `https://platform.devtest.ringcentral.com`  
**Full production REST API prefix:** `https://platform.ringcentral.com/restapi/v1.0/`  
**Full sandbox REST API prefix:** `https://platform.devtest.ringcentral.com/restapi/v1.0/`

When asked for the **sandbox base URL**, answer with the host only: `https://platform.devtest.ringcentral.com`. Add `/restapi/v1.0/` only when the question asks for the full REST API prefix or a complete endpoint URL.

| Environment | Host | Full REST API prefix |
|-------------|------|---------------------|
| **Production** | `https://platform.ringcentral.com` | `https://platform.ringcentral.com/restapi/v1.0/` |
| **Sandbox** | `https://platform.devtest.ringcentral.com` | `https://platform.devtest.ringcentral.com/restapi/v1.0/` |

All REST API paths begin with `/restapi/v1.0/`.

Full production example:
```
https://platform.ringcentral.com/restapi/v1.0/account/~/extension/~/call-log
```

## Path Shortcuts: `~` (Tilde)

You can use `~` in place of `accountId` or `extensionId` to reference the authenticated user's own account/extension.

| Explicit | Shortcut |
|---------|---------|
| `/restapi/v1.0/account/159048008/extension/171857008/call-log` | `/restapi/v1.0/account/~/extension/~/call-log` |
| `/restapi/v1.0/account/159048008/service-info` | `/restapi/v1.0/account/~/service-info` |

## Key Resource Paths

```
/restapi/v1.0/account/{accountId}                          # Account info
/restapi/v1.0/account/{accountId}/extension/{extensionId}  # Extension info
/restapi/v1.0/account/~/extension/~/call-log               # Call log
/restapi/v1.0/account/~/extension/~/message-store          # Messages (SMS, fax, voicemail)
/restapi/v1.0/account/~/extension/~/sms                    # Send SMS
/restapi/v1.0/subscription                                  # Webhook/WebSocket subscriptions
/restapi/oauth/token                                        # Auth token endpoint
```

## Pagination

List endpoints use `page` and `perPage` query parameters. The response includes a `navigation` object.

### Request
```
GET /restapi/v1.0/account/~/extension/~/call-log?page=1&perPage=100&dateFrom=2024-01-01T00:00:00Z
```

### Response Shape
```json
{
  "records": [...],
  "navigation": {
    "firstPage": { "uri": "...?page=1&perPage=100" },
    "nextPage":  { "uri": "...?page=2&perPage=100" },
    "lastPage":  { "uri": "...?page=5&perPage=100" }
  },
  "paging": {
    "page": 1,
    "perPage": 100,
    "pageStart": 0,
    "pageEnd": 99,
    "totalElements": 487,
    "totalPages": 5
  }
}
```

### Python Pagination Pattern
```python
page = 1
all_records = []
while True:
    res = platform.get('/restapi/v1.0/account/~/extension/~/call-log',
                       {'page': page, 'perPage': 100, 'dateFrom': '2024-01-01T00:00:00Z'})
    data = res.json()
    all_records.extend(data['records'])
    if 'nextPage' not in data.get('navigation', {}):
        break
    page += 1
```

## HTTP Methods

| Method | Use |
|--------|-----|
| `GET` | Retrieve resource |
| `POST` | Create resource |
| `PUT` | Replace resource (full update) |
| `PATCH` | Partial update |
| `DELETE` | Remove resource |

## Common Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (1-based) |
| `perPage` | int | Results per page (max varies by endpoint, commonly 100-1000) |
| `dateFrom` | ISO8601 | Filter records from this date |
| `dateTo` | ISO8601 | Filter records to this date |
| `direction` | string | `Inbound` or `Outbound` for call log |
| `type` | string | Message type: `SMS`, `Fax`, `VoiceMail` |

## Error Codes

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 400 | Bad request — check parameters | Fix request params |
| 401 | Unauthorized — token expired or invalid | **401: re-authenticate** — call `platform.login(jwt=...)` again to get a fresh token |
| 403 | Forbidden — insufficient permissions/scope | Check app scopes |
| 404 | Resource not found | Check path/IDs |
| 429 | Rate limit exceeded | Wait `Retry-After` seconds — see [rate-limits](rate-limits.md) |
| 503 | Service unavailable | Retry with exponential backoff |

## User-Agent Header

Always send a `User-Agent` header:
```
User-Agent: MyApp/1.0 (Linux; Python/3.9)
```

→ See also: [authentication](authentication.md) for Bearer tokens, [rate-limits](rate-limits.md) for 429 handling

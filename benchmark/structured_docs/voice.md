# Voice — Call Log, RingOut, Call Control

**doc_id**: voice  
**tags**: call-log, ringout, webrtc, telephony, call-recording, call-control, call-forwarding, voicemail, presence, ring-out, two-leg-call, one-leg-call, telephony-session, call-status, caller-status, callee-status, uri-scheme, rcmobile, tel-scheme, softphone, webphone, sip, e164, call-flip, call-park, call-transfer, call-mute, call-hold

## Quick reference — key endpoints

| Operation | Endpoint |
|-----------|----------|
| Get call log (extension) | `GET /restapi/v1.0/account/~/extension/~/call-log` |
| Get call log (account) | `GET /restapi/v1.0/account/~/call-log` |
| Get single call log record | `GET /restapi/v1.0/account/~/extension/~/call-log/{callRecordId}` |
| Initiate RingOut call | `POST /restapi/v1.0/account/~/extension/~/ring-out` |
| Get RingOut call status | `GET /restapi/v1.0/account/~/extension/~/ring-out/{ringOutId}` |
| Cancel RingOut call | `DELETE /restapi/v1.0/account/~/extension/~/ring-out/{ringOutId}` |
| List extension phone numbers | `GET /restapi/v1.0/account/~/extension/~/phone-number` |
| Get presence | `GET /restapi/v1.0/account/~/extension/~/presence` |

## RingOut — Two-Leg Outbound Calling

RingOut places an outbound call from any outside number through the RingCentral account. The platform first calls the **from** number (leg 1), then bridges it to the **to** number (leg 2). Both legs must connect for the call to be `Success`.

### POST /restapi/v1.0/account/~/extension/~/ring-out

**Request body**:

```json
{
  "from": { "phoneNumber": "+16501112222" },
  "to":   { "phoneNumber": "+14155559999" },
  "playPrompt": true,
  "callerId": { "phoneNumber": "+16501110000" }
}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `from.phoneNumber` | Conditional | Calling party number (E.164). Required only if no default forwarding number is set. |
| `to.phoneNumber` | Yes | Called party number (E.164). Missing value returns `400 Bad Request`. |
| `playPrompt` | No | When `true`, system plays "press 1 to connect" prompt to calling party. |
| `callerId.phoneNumber` | No | Caller ID to display. Must support `CallerId` feature. Defaults to main company number. |

### GET /restapi/v1.0/account/~/extension/~/ring-out/{ringOutId}

Poll this endpoint to check status of an in-progress RingOut.

### DELETE /restapi/v1.0/account/~/extension/~/ring-out/{ringOutId}

Cancels a RingOut **before** both legs are connected. Returns `204 No Content` on success. Once the first leg (caller) is fully established and the call is bridged, DELETE will not terminate the call.

### RingOut status values

#### callStatus (combined both legs)

| Value | Description |
|-------|-------------|
| `InProgress` | Connection is being established |
| `Success` | Both legs connected (answered) |
| `CannotReach` | Failure — one or both legs invalid |
| `NoAnsweringMachine` | Internal server failure |

#### callerStatus / calleeStatus (per leg)

| Value | Description |
|-------|-------------|
| `InProgress` | Connection to target leg being established |
| `Busy` | Target device is busy |
| `NoAnswer` | Call dropped due to timeout |
| `Rejected` | RingOut canceled by user, or user dropped leg 1 while leg 2 was ringing |
| `Success` | Call party answered |
| `Finished` | Call terminated (InProgress → Success → Finished) |
| `GenericError` | PSTN error or internal server error |
| `InternationalDisabled` | International, domestic, or internal calling disabled |
| `NoSessionFound` | Session does not exist (already closed) |
| `Invalid` | Unknown state due to internal failure |

### Python example — initiate and poll a RingOut

```python
import time
import ringcentral

sdk = ringcentral.SDK(
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    server='https://platform.ringcentral.com'
)

platform = sdk.platform()
platform.login(jwt='YOUR_JWT_TOKEN')

# Initiate RingOut
response = platform.post(
    '/restapi/v1.0/account/~/extension/~/ring-out',
    {
        'from': {'phoneNumber': '+16501112222'},
        'to':   {'phoneNumber': '+14155559999'},
        'playPrompt': False
    }
)

ring_out = response.json()
ring_out_id = ring_out['id']
print(f'RingOut initiated, id={ring_out_id}')

# Poll until connected or terminal state
terminal = {'Success', 'CannotReach', 'NoAnsweringMachine', 'Finished', 'GenericError'}
while True:
    status_resp = platform.get(
        f'/restapi/v1.0/account/~/extension/~/ring-out/{ring_out_id}'
    ).json()
    call_status = status_resp['status']['callStatus']
    print(f'Status: {call_status}')
    if call_status in terminal:
        break
    time.sleep(2)

# Cancel if still in progress
if call_status == 'InProgress':
    platform.delete(
        f'/restapi/v1.0/account/~/extension/~/ring-out/{ring_out_id}'
    )
    print('RingOut canceled')
```

## Call Log API

The Call Log is the authoritative record of all calls across the network. Used for analytics, compliance, reporting, and accessing call recordings.

### GET /restapi/v1.0/account/~/extension/~/call-log

**Key query parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `dateFrom` | string (ISO 8601) | Filter records from this date/time |
| `dateTo` | string (ISO 8601) | Filter records to this date/time |
| `direction` | enum | `Inbound` or `Outbound` |
| `type` | enum | `Voice`, `Fax` |
| `page` | integer | Page number (default: 1) |
| `perPage` | integer | Records per page (default: 100, max: 1000) |
| `withRecording` | boolean | Return only records with recordings |
| `sessionId` | string | Filter by telephony session ID |

### Call log record — key response fields

```json
{
  "id": "Kgu0dDpEBxFmHMy",
  "uri": "https://platform.ringcentral.com/restapi/v1.0/account/~/extension/~/call-log/Kgu0dDpEBxFmHMy",
  "sessionId": "1234567890",
  "startTime": "2024-01-15T14:30:00.000Z",
  "duration": 245,
  "type": "Voice",
  "direction": "Inbound",
  "action": "Phone Call",
  "result": "Accepted",
  "from": {
    "phoneNumber": "+16501112222",
    "name": "John Doe"
  },
  "to": {
    "phoneNumber": "+14155559999",
    "extensionNumber": "101"
  },
  "recording": {
    "id": "rec_abc123",
    "uri": "https://platform.ringcentral.com/restapi/v1.0/account/~/recording/rec_abc123",
    "type": "OnDemand",
    "contentUri": "https://media.ringcentral.com/.../recording.mp3"
  },
  "legs": [
    {
      "type": "Accept",
      "direction": "Inbound",
      "startTime": "2024-01-15T14:30:00.000Z",
      "duration": 245,
      "from": { "phoneNumber": "+16501112222" },
      "to": { "phoneNumber": "+14155559999" }
    }
  ]
}
```

**Key fields**:

| Field | Description |
|-------|-------------|
| `id` | Unique call log record ID |
| `sessionId` | Telephony session ID shared across legs |
| `direction` | `Inbound` or `Outbound` |
| `type` | `Voice` or `Fax` |
| `startTime` | ISO 8601 UTC timestamp of call start |
| `duration` | Call duration in seconds |
| `result` | `Accepted`, `Missed`, `Voicemail`, `Rejected`, `Busy`, `NoAnswer` |
| `recording.contentUri` | Direct URL to download the MP3 recording |
| `legs` | Array of call legs (useful for transferred/conferenced calls) |

### Pagination

Response includes a `navigation` object:

```json
{
  "navigation": {
    "firstPage": { "uri": "..." },
    "nextPage":  { "uri": "..." },
    "previousPage": { "uri": "..." },
    "lastPage":  { "uri": "..." }
  },
  "paging": {
    "page": 1,
    "perPage": 100,
    "totalPages": 5,
    "totalElements": 487
  }
}
```

## Call Control API

The Call Control API manipulates **active** calls in progress. Available operations on a live telephony session:

| Operation | Description |
|-----------|-------------|
| Start/stop recording | Toggle call recording on demand |
| Mute/unmute | Mute or unmute a participant |
| Hold/resume | Place call on hold or resume it |
| Transfer | Transfer the call to another number or extension |
| Park | Park the call to a park orbit |
| Flip | Flip the call to another registered device/number |
| Supervise/monitor | Listen in on a call (supervisor monitoring) |
| Terminate | Hang up the call |
| Forward (pre-connect) | Forward to another extension before answering |
| Forward to voicemail | Send incoming call to voicemail |
| Reject | Reject an incoming ringing call |

### Incoming call interception (while ringing)

Before a call connects, the Voice API allows:
- Forward to another extension
- Forward to voicemail
- Reject the call

## WebRTC — Browser-Based Calling

WebRTC enables peer-to-peer voice calls directly from a browser without plugins.

**Key characteristics**:
- **One-legged dial** (vs. RingOut's two-legged) — browser IS one of the endpoints
- Supports voice only (no data or video currently in RingCentral's implementation)
- Protected via RingCentral OAuth2 Authorization Code flow
- Call Recording is available
- Requires extension with a **Digital Line** to authenticate
- Officially supported browsers: Google Chrome, Mozilla Firefox

**Required app configuration** (Developer Console):
- Application Type: **Private**
- Platform Type: **Browser-Based** (required)
- Authorization Flows: Authorization Flow + Refresh
- Permissions: **VoIP Calling** + others as needed

**Libraries**:
- `ringcentral-web-phone` — Official WebPhone client library (GitHub: `ringcentral/ringcentral-web-phone`). Wraps SIP.js, provides full call controls.
- `ringcentral-call-js` — Higher-level library combining WebPhone SDK + Call Control REST API. Supports getting and controlling calls across all devices.

**Troubleshooting**:
- Ensure OAuth redirect URI is correctly configured for 3-legged flow
- VoIP permission must be added to the application
- Extension must have a digital line attached
- Browser must have microphone permission granted

## URI Scheme — Click-to-Dial

Trigger a dial-out from the RingCentral Desktop softphone using a URI scheme.

### Supported schemes

| Scheme | Example |
|--------|---------|
| `rcmobile://` (recommended) | `rcmobile://call?number=16501112222` |
| `tel://` | `tel:+16501112222` |

Prefer `rcmobile://` — it is RingCentral-specific and avoids conflicts with other apps that register `tel://`.

**HTML**:
```html
<a href="rcmobile://call?number=16501112222">1-650-111-2222</a>
<a href="tel:+16501112222">1-650-111-2222</a>
```

**Google Chrome** (requires JavaScript — Chrome does not follow `href` for custom schemes):
```javascript
var w = (window.parent) ? window.parent : window;
w.location.assign('rcmobile://call?number=16501112222');
```

Numbers must use E.164 format (`+` followed by country code + number, no spaces or dashes).

## Presence API

Reports user availability across the network.

**Endpoint**: `GET /restapi/v1.0/account/~/extension/~/presence`

**Reports**:
- Is the user currently on a call?
- Is the user in a meeting?
- Has the user set Do Not Disturb (DND)?

## Call Recording

Call recordings are surfaced via the Call Log API. The `recording.contentUri` field in a call log record provides a direct URL to download the MP3 audio file. Only records where a recording exists will have this field populated; use the `withRecording=true` query parameter to filter for only recorded calls.

## Key Concepts

| Concept | Detail |
|---------|--------|
| Two-leg call (RingOut) | Platform calls `from` number first, then bridges to `to` number |
| One-leg call (WebRTC) | Browser is an endpoint; platform connects it directly to destination |
| Telephony session | Identified by `sessionId`; shared across all legs of a single call |
| E.164 format | Phone numbers must be in format `+[country code][number]`, e.g. `+16501112222` |
| Base URL | `https://platform.ringcentral.com/restapi/v1.0/` |
| Sandbox URL | `https://platform.devtest.ringcentral.com/restapi/v1.0/` |
| Rate limits | Returned in `X-Rate-Limit-*` response headers |
| Pagination | `page` + `perPage` query params; response includes `navigation` and `paging` objects |

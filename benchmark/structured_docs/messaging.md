# Messaging — SMS, Fax, MMS, Voicemail

**doc_id**: messaging  
**tags**: sms, fax, mms, voicemail, message-store, a2p, high-volume, opt-out, batch, send-sms, instant-message, push-notification, pager, receive-sms, receive-fax, message-filter, message-sync, a2p-sms, tcr, 10dlc, toll-free-sms, multipart-form, send-fax, mms-attachment, opt-in, unsubscribe, campaign-registry, jwt-auth, ringcentral-sdk

## Quick reference — key endpoints

| Operation | Endpoint |
|-----------|----------|
| Send SMS (P2P) | `POST /restapi/v1.0/account/~/extension/~/sms` |
| Send High Volume SMS batch (A2P) | `POST /restapi/v1.0/account/~/a2p-sms/batches` |
| Send Fax | `POST /restapi/v1.0/account/~/extension/~/fax` |
| List messages (message store) | `GET /restapi/v1.0/account/~/extension/~/message-store` |
| List inbound faxes | `GET /restapi/v1.0/account/~/extension/~/message-store?direction=Inbound&messageType=Fax` |
| Filter faxes by date | `GET /restapi/v1.0/account/~/extension/~/message-store?messageType=Fax&dateFrom=YYYY-MM-DD&dateTo=YYYY-MM-DD` |
| List assigned phone numbers | `GET /restapi/v1.0/account/~/extension/~/phone-number` |
| Read opted-out numbers (A2P) | `GET /restapi/v1.0/account/~/a2p-sms/opt-outs?from=+1XXXXXXXXXX` |
| Subscribe to instant SMS events | `POST /restapi/v1.0/subscription` (eventFilter: `/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS`) |
| Delete/cancel scheduled fax | `DELETE /restapi/v1.0/account/~/extension/~/message-store/{messageId}` |

## Messaging Quick Facts

- P2P SMS fields: `from.phoneNumber`, `to.phoneNumber` in the `to` array, and `text`.
- SMS sender numbers must belong to the authenticated user extension and include the `SmsSender` feature; a super admin cannot send on behalf of another extension.
- Inbound SMS event fields include `from.phoneNumber`, `to.phoneNumber`, `subject`, `direction=Inbound`, `type=SMS`, `readStatus=Unread`, and `messageStatus=Received`.
- High Volume SMS batch endpoint: `POST /restapi/v1.0/account/~/a2p-sms/batches`; supports US and Canada local 10DLC and toll-free sending, with about `50 MB` max batch size.
- A2P limitations: no MMS, no group messaging, no international SMS from US numbers, no scheduled SMS, and no 10DLC US-to-Canada.
- Fax endpoint: `POST /restapi/v1.0/account/~/extension/~/fax` using `multipart/form-data` or `multipart/mixed`; include a JSON root attachment and optional `sendTime`. Fax limits: `50 MB` total attachments and `200` pages.

## SDK install commands

| Language | Command |
|----------|---------|
| Python | `pip install ringcentral python-dotenv` |
| JavaScript | `npm install @ringcentral/sdk dotenv --save` |
| PHP | `php composer.phar require ringcentral/ringcentral-php vlucas/phpdotenv` |
| Ruby | `gem install ringcentral_sdk dotenv` |
| C# | NuGet: `RingCentral.Net` (6.2.0+) |

## Authentication setup

- Auth flow: JWT (recommended for server apps)  
- Required permissions: `SMS`, `ReadAccounts`  
- App type: Private REST API App  
- Sandbox base URL: `https://platform.devtest.ringcentral.com`  
- Production base URL: `https://platform.ringcentral.com`  
- TCR registration required before sending SMS on production accounts

## Message types overview

| Type | Description |
|------|-------------|
| **SMS** | Text and multimedia (MMS) messages over cell networks or RingCentral Soft Phone |
| **Fax** | Document transmission via phone lines; fully digitized via Fax API |
| **Voicemail** | Recorded messages left at individual or group extensions |
| **Pager** | One-way announcements from desk or mobile phones (retail/warehouse use) |

> Glip/Team Messaging messages are a separate system — see the Team Messaging section of the Developer Guide.

---

## Sending SMS (P2P — person-to-person)

### Rules and constraints

1. SMS can only be sent from phone numbers **owned by the authenticated user extension** (assigned as a direct number or digital line).
2. Retrieve available numbers first: `GET /restapi/v1.0/account/~/extension/~/phone-number` — check that the `features` field includes `"SmsSender"`.
3. A super admin **cannot** send on behalf of other user extensions.
4. SMS to Disabled or Frozen extensions is dropped (saved only in the sender's outbox).
5. Company numbers (main number, site number) may have SMS enabled — only one designated extension is authorized per number. Configured via Admin Portal → Auto-Receptionist General Settings.
6. Call queue numbers: SMS must be explicitly assigned to a user extension in the Admin Portal; messages are stored in the call queue's message store, not the user's.

### Python example — send SMS

```python
from ringcentral import SDK
import os
from dotenv import load_dotenv

load_dotenv()

sdk = SDK(
    os.environ['RC_APP_CLIENT_ID'],
    os.environ['RC_APP_CLIENT_SECRET'],
    'https://platform.ringcentral.com'
)
platform = sdk.platform()
platform.login(jwt=os.environ['RC_USER_JWT'])

response = platform.post(
    '/restapi/v1.0/account/~/extension/~/sms',
    {
        'from': {'phoneNumber': os.environ['RC_FROM_NUMBER']},
        'to': [{'phoneNumber': os.environ['SMS_RECIPIENT']}],
        'text': 'Hello from the RingCentral SMS API!'
    }
)
print(response.json_dict())
```

Install: `pip install ringcentral python-dotenv`  
Run: `python sms.py`

---

## Receiving SMS and MMS

### Subscribe to instant SMS notifications

Event filter for inbound SMS:
```
/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS
```

Steps:
1. Authenticate the user extension that owns the phone number.
2. POST a subscription with the event filter above.
3. Implement a Webhook server (`POST` endpoint) or WebSocket connection to receive payloads.

Super admin can receive on behalf of multiple extensions by listing multiple event filters:
```
/restapi/v1.0/account/~/extension/[extensionId]/message-store/instant?type=SMS
```

### Inbound SMS event payload (key fields)

- `from.phoneNumber` — sender's number  
- `to.phoneNumber` — recipient's number  
- `subject` — text message body  
- `direction`: `"Inbound"`  
- `type`: `"SMS"`  
- `readStatus`: `"Unread"`  
- `messageStatus`: `"Received"`  

### MMS attachments

MMS notifications include one or more `MmsAttachment` entries in the `attachments` array. Download binary content using the attachment `uri` with a valid `access_token` as Bearer.

### Token management for long-running subscribers

- `access_token` valid for 1 hour  
- `refresh_token` valid for 7 days  
- Call `platform.refresh()` at least every 6 days to keep tokens alive, or re-authorize using JWT

---

## High Volume SMS (A2P — application-to-person)

Use `POST /restapi/v1.0/account/~/a2p-sms/batches` to send bulk messages.

### Key features
- No recipient limit per batch; max batch size: ~50 MB  
- Broadcast the same message to multiple recipients, or different messages to different recipients in one request  
- Supports local (10DLC) and toll-free numbers  
- US and Canada only  
- Opt-in/opt-out handled automatically by RingCentral  

### Limitations (A2P does NOT support)
- MMS (images, vcards, files)  
- Group messaging  
- International SMS from US numbers  
- Scheduling SMS in advance  
- 10DLC numbers for US↔Canada (use toll-free for cross-border)  

### HTTP example

```http
POST /restapi/v1.0/account/~/a2p-sms/batches
Content-Type: application/json

{
  "from": "+16505550100",
  "messages": [
    { "to": ["+14155550101"], "text": "Hello from the batch API!" },
    { "to": ["+14155550102"], "text": "Hello from the batch API!" }
  ]
}
```

The response includes a `rejected` field listing any invalid numbers (with index, error code, and reason).

### Opt-in / Opt-out handling

RingCentral automatically enforces opt-out per sender–recipient pair.

| Action | Keywords |
|--------|---------|
| Opt-out | STOP, UNSUBSCRIBE, QUIT, CANCEL, END |
| Opt-in | START, SUBSCRIBE, RESUME, CONTINUE, UNSTOP |

Read opted-out numbers:
```http
GET /restapi/v1.0/account/~/a2p-sms/opt-outs?from=+16505550100
```

Subscribe to opt-out events to receive real-time notifications; the `active` attribute is `true` on opt-out, `false` on opt-in.

---

## Sending Fax

```http
POST /restapi/v1.0/account/~/extension/~/fax
Content-Type: multipart/form-data  (or multipart/mixed)
```

- The API packages the message and each document as separate MIME attachments  
- Root attachment: JSON with recipient(s), quality, cover page text  
- Subsequent attachments: documents to transmit (in order)  
- `from` phone number is set automatically from the extension's outbound fax settings (configure via service.ringcentral.com)  
- Schedule with `sendTime` parameter (ISO 8601); cancel by deleting the message from the message store  

### Supported fax file types

PDF, PSD, DOC/DOCX, XLS/XLSX, PPT/PPTX, VSD, TIF/TIFF, GIF, JPG, BMP, PNG, RTF, TXT, CSV, HTML, XML, and more.

### Fax limits

| Limit | Value |
|-------|-------|
| Max total attachment size | 50 MB |
| Max pages | 200 |
| Special chars in filenames | Not allowed (`& @ # $ % ^ * etc.`) |
| Transmission speed (text) | ~1 min/page |
| Transmission speed (graphics) | 5+ min/page |

### JavaScript — attach local file

```javascript
const form = new FormData();
form.append('fax-document-1', require('fs').createReadStream('test.pdf'));
```

---

## Receiving Fax

```http
GET /restapi/v1.0/account/~/extension/~/message-store?direction=Inbound&messageType=Fax
```

- Returns paginated list (100 per page) of received faxes (default: yesterday)  
- Each fax is a single PDF attachment containing all pages  
- Filter by date range: add `dateFrom` and `dateTo` query params (format: `YYYY-MM-DD`)  

Subscribe to push notifications for real-time fax receipt:  
Event filter: `/restapi/v1.0/account/~/extension/~/message-store`

---

## Message Store

The Message Store captures every message sent or received. Capabilities:

- Download messages and attachments  
- Resend messages (useful for failed faxes)  
- Inspect delivery status  
- Delete/remove messages  
- Change read/unread status  
- Change message priority  
- Pagination: `page` and `perPage` query params; response includes a `navigation` object  

### Common message-store filters

| Filter | Query param |
|--------|-------------|
| Message type | `messageType=SMS` / `messageType=Fax` / `messageType=VoiceMail` |
| Direction | `direction=Inbound` / `direction=Outbound` |
| Date from | `dateFrom=YYYY-MM-DD` |
| Date to | `dateTo=YYYY-MM-DD` |

---

## TCR / Compliance requirements

- RingCentral is a TCR (The Campaign Registry) CSP  
- Production SMS requires TCR registration: complete the TCR process in the Admin Portal  
- Review RingCentral SMS/MMS content policies before production use  
- Sandbox accounts can test without TCR registration  

---

## Quick-start checklist

1. Create REST API App in Developer Console → select JWT auth → add `SMS` and `ReadAccounts` permissions  
2. Download and populate `.env` with `RC_APP_CLIENT_ID`, `RC_APP_CLIENT_SECRET`, `RC_USER_JWT`, `SMS_RECIPIENT`  
3. Install SDK for your language (see table above)  
4. Call `GET /restapi/v1.0/account/~/extension/~/phone-number` — confirm `SmsSender` in `features`  
5. `POST /restapi/v1.0/account/~/extension/~/sms` with `from`, `to`, and `text`  
6. For production: complete TCR registration and switch server URL to `https://platform.ringcentral.com`

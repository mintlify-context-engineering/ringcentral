# Webhooks & Event Subscriptions

**doc_id**: webhooks  
**tags**: webhook, websocket, subscription, event, notification, push, eventfilter, validation-token, real-time, SUB-525, expiration, renewal

## Two Delivery Methods

| | Webhook | WebSocket |
|--|---------|-----------|
| **Best for** | Always-on server apps | Mobile/browser clients, low-latency push |
| **Requires** | Public HTTPS server | No public server needed |
| **Protocol** | HTTPS POST to your URL | WebSocket connection |
| **Offline handling** | Events queue and deliver when server returns | Lost if connection drops |

**Rule of thumb**: Use WebSocket for real-time client notifications (e.g., incoming call alerts on mobile). Use webhooks for server-side event processing (e.g., logging all calls to a database).

## Creating a Webhook Subscription

### API Endpoint

```
POST https://platform.ringcentral.com/restapi/v1.0/subscription
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Request Body

```json
{
  "eventFilters": [
    "/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS",
    "/restapi/v1.0/account/~/extension/~/presence"
  ],
  "deliveryMode": {
    "transportType": "WebHook",
    "address": "https://your-server.com/webhook-handler"
  },
  "expiresIn": 604800
}
```

### Validation — Required Step

When you create a subscription, RingCentral sends a **validation request** to your URL before activating it. Your server MUST:

1. Respond with **HTTP 200 OK** within **3000ms**
2. Echo back the `Validation-Token` header from the request
3. Respond with body **< 1024 bytes** (including headers)
4. Your server must be **publicly accessible** (TLS 1.2+ required in production)

```python
# Flask example
from flask import Flask, request, make_response

app = Flask(__name__)

@app.route('/webhook-handler', methods=['POST'])
def webhook():
    validation_token = request.headers.get('Validation-Token')
    if validation_token:
        # Validation request — echo the token back
        resp = make_response('', 200)
        resp.headers['Validation-Token'] = validation_token
        return resp
    
    # Real event — process it
    event = request.get_json()
    print('Received event:', event['event'])
    return '', 200
```

## Available Event Filters

Common event filter paths:

| Event | Filter Path |
|-------|-------------|
| SMS received | `/restapi/v1.0/account/~/extension/~/message-store/instant?type=SMS` |
| Voicemail received | `/restapi/v1.0/account/~/extension/~/message-store?type=VoiceMail` |
| Call started/ended | `/restapi/v1.0/account/~/telephony/sessions` |
| Missed call | `/restapi/v1.0/account/~/extension/~/missed-calls` |
| Presence changed | `/restapi/v1.0/account/~/extension/~/presence` |
| Subscription expiring | `/restapi/v1.0/subscription/~?threshold=3600&interval=3600` |

## WebSocket Subscriptions

Base WebSocket URL: `wss://platform.ringcentral.com/restapi/ws/net/v1.0/`

The RingCentral JS SDK's `@ringcentral/subscriptions` package handles WebSocket subscriptions:

```js
const { Subscriptions } = require('@ringcentral/subscriptions')
const subs = new Subscriptions({ sdk: rcsdk })
const subscription = subs.createSubscription()

subscription.setEventFilters(['/restapi/v1.0/account/~/extension/~/presence'])
subscription.on(subscription.events.notification, (event) => {
    console.log('Event received:', event)
})
await subscription.register()
```

## Renewing Subscriptions

Subscriptions expire (default TTL varies). To auto-renew, subscribe to the expiration reminder:

```json
"eventFilters": [
  "/restapi/v1.0/subscription/~?threshold=3600&interval=3600"
]
```

When you receive this reminder event, call:
```
PUT https://platform.ringcentral.com/restapi/v1.0/subscription/{subscriptionId}
```

## Listing Active Subscriptions

```
GET https://platform.ringcentral.com/restapi/v1.0/subscription
```

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `SUB-525` | Validation response > 1024 bytes or missing Content-Type | Ensure body is empty or tiny; add `Content-Type: application/json` |
| Subscription not created | Server not publicly accessible | Use ngrok for local dev |
| Events stop arriving | Subscription expired | Implement renewal logic |

→ See also: [authentication](authentication.md) for access tokens, [api-basics](api-basics.md) for base URLs

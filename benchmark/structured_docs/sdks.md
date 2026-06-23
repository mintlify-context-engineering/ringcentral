# SDKs — Installation & Quick Start

**doc_id**: sdks  
**tags**: sdk, install, npm, pip, gem, composer, maven, gradle, package, python, javascript, node, ruby, php, java, go, dotnet, csharp, swift, chatbot, quick start, sms, send sms, call log, websocket subscriptions, ringcentral-chatbot-js, routing, skill, higher-level, same platform apis, pagination, nextPage, navigation

## SDK Matrix

**All 7 major SDKs support JWT authentication**: Python, JavaScript, PHP, Ruby, Java, Go, .NET.

| Language | Package | Install command |
|----------|---------|----------------|
| **Python** | `ringcentral` | `pip3 install ringcentral` |
| **JavaScript/Node** | `@ringcentral/sdk` | `npm install @ringcentral/sdk` |
| **JavaScript Subscriptions** | `@ringcentral/subscriptions` | `npm install @ringcentral/subscriptions` |
| **PHP** | `ringcentral/ringcentral-php` | `composer require ringcentral/ringcentral-php` |
| **Ruby** | `ringcentral_sdk` | `gem install ringcentral_sdk` |
| **Java** | `com.ringcentral:ringcentral` | Maven: `com.ringcentral:ringcentral` |
| **Go** | `github.com/ringcentral/ringcentral-go` | `go get github.com/ringcentral/ringcentral-go` |
| **.NET/C#** | `RingCentral.Net` | `dotnet add package RingCentral.Net` |
| **Swift (iOS)** | `ringcentral-swift` | Swift Package Manager |

## Chatbot Framework (JavaScript)

The **`ringcentral-chatbot-js`** framework is a higher-level wrapper around `@ringcentral/sdk` that adds skill routing, state management, and webhook handling for Team Messaging bots. It uses the same platform APIs underneath as the core SDK.

```bash
npm install ringcentral-chatbot
```

Key concepts: **skill** (a handler for a specific command/intent), **routing** (matching messages to skills), state persistence. The chatbot framework uses the same platform APIs as `@ringcentral/sdk` — it just adds the higher-level bot infrastructure on top.

---

## Python

```python
pip3 install ringcentral
```

```python
from ringcentral import SDK

sdk = SDK('CLIENT_ID', 'CLIENT_SECRET', 'https://platform.ringcentral.com')
platform = sdk.platform()
platform.login(jwt='YOUR_JWT_TOKEN')

# Get account info
res = platform.get('/account/~/extension/~')

# Send SMS
platform.post('/restapi/v1.0/account/~/extension/~/sms', {
    'from': {'phoneNumber': '+15551234567'},
    'to': [{'phoneNumber': '+15559876543'}],
    'text': 'Hello from RingCentral!'
})

# Paginate all call log records (handle nextPage / navigation)
# Error recovery: on 401 re-authenticate; on 429 wait Retry-After
page = 1
all_records = []
while True:
    res = platform.get('/restapi/v1.0/account/~/extension/~/call-log',
                       {'page': page, 'perPage': 100, 'dateFrom': '2024-01-01T00:00:00Z'})
    data = res.json()
    all_records.extend(data['records'])
    # navigation object contains nextPage when more pages exist
    if 'nextPage' not in data.get('navigation', {}):
        break
    page += 1
```

---

## JavaScript / Node.js

```bash
npm install @ringcentral/sdk dotenv
```

```js
require('dotenv').config()
const { SDK } = require('@ringcentral/sdk')

const rcsdk = new SDK({
    server: process.env.RC_SERVER_URL || 'https://platform.ringcentral.com',
    clientId: process.env.RC_CLIENT_ID,
    clientSecret: process.env.RC_CLIENT_SECRET
})

const platform = rcsdk.platform()
await platform.login({ jwt: process.env.RC_JWT })

// Send SMS
await platform.post('/restapi/v1.0/account/~/extension/~/sms', {
    from: { phoneNumber: '+15551234567' },
    to: [{ phoneNumber: '+15559876543' }],
    text: 'Hello!'
})
```

### .env file

```
RC_SERVER_URL=https://platform.ringcentral.com
RC_CLIENT_ID=<your_client_id>
RC_CLIENT_SECRET=<your_client_secret>
RC_JWT=<your_jwt>
```

---

## Ruby

```bash
gem install ringcentral_sdk
```

```ruby
require 'ringcentral'

rc = RingCentral.new('CLIENT_ID', 'CLIENT_SECRET', 'https://platform.ringcentral.com')
rc.authorize(jwt: 'YOUR_JWT_TOKEN')

r = rc.get('/restapi/v1.0/account/~/extension/~')
puts r.body['name']
```

---

## PHP

```bash
composer require ringcentral/ringcentral-php
```

```php
<?php
require('vendor/autoload.php');
use RingCentral\SDK\SDK;

$sdk = new SDK('CLIENT_ID', 'CLIENT_SECRET', 'https://platform.ringcentral.com');
$platform = $sdk->platform();
$platform->login(['jwt' => 'YOUR_JWT_TOKEN']);

$r = $platform->get('/account/~/extension/~');
echo $r->json()->name;
```

---

## Java

```xml
<!-- pom.xml -->
<dependency>
    <groupId>com.ringcentral</groupId>
    <artifactId>ringcentral</artifactId>
    <version>LATEST</version>
</dependency>
```

```java
import com.ringcentral.*;
import com.ringcentral.definitions.*;

RestClient rc = new RestClient("CLIENT_ID", "CLIENT_SECRET", "https://platform.ringcentral.com");
rc.authorize("YOUR_JWT_TOKEN");

ExtensionInfo info = rc.restapi().account().extension().get();
```

---

## Go

```bash
go get github.com/ringcentral/ringcentral-go
```

```go
import rc "github.com/ringcentral/ringcentral-go"

client, _ := rc.NewRestClient("CLIENT_ID", "CLIENT_SECRET", "https://platform.ringcentral.com")
client.Authorize("YOUR_JWT_TOKEN", "", "")
```

---

## .NET / C#

```bash
dotnet add package RingCentral.Net
```

```csharp
using RingCentral;

var rc = new RestClient("CLIENT_ID", "CLIENT_SECRET", new Uri("https://platform.ringcentral.com"));
await rc.Authorize("YOUR_JWT_TOKEN");
var ext = await rc.Restapi().Account().Extension().Get();
```

---

## REST SDKs vs. Dedicated Real-Time Libraries

All major REST SDKs support JWT, Auth Code, SMS, call log, and other REST API calls. WebSocket subscriptions and SIP/WebRTC calling require dedicated real-time libraries beyond the standard REST SDKs.

| Real-time need | Dedicated library |
|----------------|-------------------|
| WebSocket push subscriptions for Node.js | `@ringcentral/subscriptions` (`npm install @ringcentral/subscriptions`) |
| Java WebSocket client | `ringcentral-websocket-java` |
| SIP/WebRTC softphone for TypeScript | `ringcentral-softphone-ts` / `npm install ringcentral-softphone` |
| SIP/WebRTC softphone for JavaScript | `ringcentral-softphone-js` |
| SIP/WebRTC softphone for Go | `ringcentral-softphone-go` |
| Full WebRTC browser phone SDK | `ringcentral-web-phone` |

Do not add extra dedicated WebSocket libraries for Python, PHP, Ruby, .NET, or the standard Java REST SDK unless they are explicitly published and documented. The standard REST SDKs are for REST calls; use the dedicated libraries above for WebSocket subscriptions or SIP/WebRTC calling.

→ See also: [authentication](authentication.md) for JWT details, [webhooks](webhooks.md) for subscription setup

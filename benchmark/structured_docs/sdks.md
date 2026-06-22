# SDKs — Installation & Quick Start

**doc_id**: sdks  
**tags**: sdk, install, npm, pip, gem, composer, maven, gradle, package, python, javascript, node, ruby, php, java, go, dotnet, csharp, swift, chatbot, quick start, getting started

## SDK Matrix

| Language | Package | Install |
|----------|---------|---------|
| **Python** | `ringcentral` | `pip3 install ringcentral` |
| **JavaScript/Node** | `@ringcentral/sdk` | `npm install @ringcentral/sdk` |
| **JavaScript Subscriptions** | `@ringcentral/subscriptions` | `npm install @ringcentral/subscriptions` |
| **PHP** | `ringcentral/ringcentral-php` | `composer require ringcentral/ringcentral-php` |
| **Ruby** | `ringcentral_sdk` | `gem install ringcentral_sdk` |
| **Java** | `com.ringcentral:ringcentral` | Maven/Gradle (see below) |
| **Go** | `github.com/ringcentral/ringcentral-go` | `go get github.com/ringcentral/ringcentral-go` |
| **.NET/C#** | `RingCentral.Net` | `dotnet add package RingCentral.Net` |
| **Swift (iOS)** | `ringcentral-swift` | Swift Package Manager |

All SDKs support JWT authentication.

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
print(res.json().name)

# Send SMS
platform.post('/restapi/v1.0/account/~/extension/~/sms', {
    'from': {'phoneNumber': '+15551234567'},
    'to': [{'phoneNumber': '+15559876543'}],
    'text': 'Hello from RingCentral!'
})

# Get call log
res = platform.get('/restapi/v1.0/account/~/extension/~/call-log', {
    'dateFrom': '2024-01-01T00:00:00Z',
    'perPage': 100
})
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

## Chatbot Framework (JavaScript)

The chatbot framework (`ringcentral-chatbot-js`) wraps the main JS SDK with skill routing, state management, and webhook handling for Team Messaging bots.

```bash
npm install ringcentral-chatbot
```

It's separate from `@ringcentral/sdk` but uses the same platform APIs underneath.

---

## Which SDKs Support Which Features?

| Feature | Python | JS | PHP | Ruby | Java | Go | .NET |
|---------|--------|-----|-----|------|------|-----|------|
| JWT Auth | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Auth Code | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WebSocket Subs | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ |
| SMS | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Call Control | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

→ See also: [authentication](authentication.md) for JWT details, [webhooks](webhooks.md) for subscription setup

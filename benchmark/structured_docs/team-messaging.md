# Team Messaging API (Glip) — Bots, Posts, Cards, Groups

**doc_id**: team-messaging  
**tags**: team messaging, glip, glip api, bot, chatbot, add-in, post message, adaptive card, card, group, team, direct message, webhook, ringcentral-chatbot-js, bot framework, POST /restapi/v1.0/glip/posts, GET /restapi/v1.0/glip/groups, glip/chats, glip/persons, message type, Message4Bot, bot app type, developer portal, interactive message, form, task, event, note, team collaboration

## Key Endpoints

| Action | Method | Path |
|--------|--------|------|
| Post a message | POST | `/restapi/v1.0/glip/posts` |
| List groups/chats | GET | `/restapi/v1.0/glip/groups` |
| Get a group | GET | `/restapi/v1.0/glip/groups/{groupId}` |
| Create a team | POST | `/restapi/v1.0/glip/teams` |
| List teams | GET | `/restapi/v1.0/glip/teams` |
| Post to a chat | POST | `/restapi/v1.0/glip/chats/{chatId}/posts` |
| List chats | GET | `/restapi/v1.0/glip/chats` |
| Get person info | GET | `/restapi/v1.0/glip/persons/{personId}` |
| List events | GET | `/restapi/v1.0/glip/groups/{groupId}/events` |
| List tasks | GET | `/restapi/v1.0/glip/chats/{chatId}/tasks` |
| List notes | GET | `/restapi/v1.0/glip/chats/{chatId}/notes` |

**Required permission**: `TeamMessaging`  
**Auth flow**: JWT (recommended for server apps), OAuth 2.0 Authorization Code for user-context apps  
**App type for bots**: Must be created as a **Bot** app type in the RingCentral Developer Portal (not a plain REST API app)

## Bots vs Regular API Apps

Bots require a dedicated **Bot** app type selected in the Developer Portal. This is the critical difference from standard REST API apps:

- **Regular REST API app** — acts on behalf of a user; uses JWT or Authorization Code flow.
- **Bot app** — has its own bot user identity; installs into team messaging accounts; receives `Message4Bot` events when users address it by name (e.g., `@BotName ping`).

Bots receive webhook events of type `Message4Bot` containing the message text. They respond by calling the posts API.

## Bot Quick Start — ringcentral-chatbot-js

The official JavaScript bot framework is **ringcentral-chatbot-js** (repo: `ringcentral/ringcentral-chatbot-js`).

Install:
```bash
npm install ringcentral-chatbot dotenv
```

Minimal "Ping Bot" (10 lines):
```js
const createApp = require('ringcentral-chatbot/dist/apps').default

const handle = async event => {
  const { type, text, group, bot } = event
  if (type === 'Message4Bot' && text === 'ping') {
    await bot.sendMessage(group.id, { text: 'pong' })
  }
}

const app = createApp(handle)
app.listen(process.env.RINGCENTRAL_CHATBOT_EXPRESS_PORT)
```

The framework handles OAuth installation, webhook subscription, and token refresh automatically. Developers only implement the `handle` function.

## Creating a Team (REST API)

```bash
POST /restapi/v1.0/glip/teams
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "public": true,
  "name": "My New Team",
  "description": "A team created via API",
  "members": [
    { "email": "user@example.com" }
  ]
}
```

Response includes the new team's `id`, which can be used as the `groupId` for subsequent calls.

## Posting a Message

```bash
POST /restapi/v1.0/glip/posts
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "groupId": "{groupId}",
  "text": "Hello from the API!"
}
```

To post to a specific chat (newer chats API):
```bash
POST /restapi/v1.0/glip/chats/{chatId}/posts
```

## Adaptive Cards (Interactive Messages)

Adaptive Cards add buttons, forms, and input elements to messages. Users can submit data directly from within a message without leaving RingCentral.

Post an adaptive card:
```bash
POST /restapi/v1.0/glip/chats/{chatId}/adaptive-cards
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "type": "AdaptiveCard",
  "version": "1.3",
  "body": [
    { "type": "TextBlock", "text": "Please fill out the form:" },
    { "type": "Input.Text", "id": "userName", "placeholder": "Your name" }
  ],
  "actions": [
    { "type": "Action.Submit", "title": "Submit" }
  ]
}
```

When a user submits, the bot receives an `AdaptiveCardAction` event with the submitted data.

## App Setup (Developer Portal)

1. Log in at [https://developers.ringcentral.com](https://developers.ringcentral.com).
2. Go to **Console → Apps → Create App**.
3. Select app type:
   - **REST API App** for integrations/add-ins (uses JWT or Authorization Code).
   - **Bot** for conversational bots (receives `Message4Bot` events).
4. Under **Authentication**, select **JWT auth flow** (for server apps) or **Authorization Code** (for user-facing apps).
5. Under **Permissions**, add **Team Messaging**.
6. Note the **Client ID** and **Client Secret** from the app dashboard.

## Groups vs Chats vs Teams vs Direct Messages

| Concept | Description | API Path |
|---------|-------------|----------|
| **Team** | Named group, can be public or private | `/glip/teams` |
| **Group** | Generic group or direct message conversation (legacy Glip API) | `/glip/groups` |
| **Chat** | Unified conversation (teams, DMs, groups — newer API) | `/glip/chats` |
| **Direct Message** | 1:1 conversation between two persons | `/glip/chats` (type=Direct) |

## Webhooks for Team Messaging

Subscribe to team messaging events via the standard subscription API:

```bash
POST /restapi/v1.0/subscription
Content-Type: application/json

{
  "eventFilters": [
    "/restapi/v1.0/glip/posts",
    "/restapi/v1.0/glip/groups"
  ],
  "deliveryMode": {
    "transportType": "WebHook",
    "address": "https://your-server.com/webhook"
  }
}
```

For bots, the framework handles subscriptions automatically. Common event filters:
- `/restapi/v1.0/glip/posts` — new messages posted
- `/restapi/v1.0/glip/groups` — group/team membership changes

## Add-ins

Add-ins extend team messaging with:
- Automated installation flow (OAuth-based).
- Interactive messages with buttons and calls to action.
- Embedded forms for data collection.

Add-ins are ideal for notifying teams of external events (CI/CD failures, CRM updates, etc.) and letting users act on them without leaving RingCentral.

## Tasks, Events, and Notes APIs

| Resource | API Reference |
|----------|--------------|
| Tasks | `GET /restapi/v1.0/glip/chats/{chatId}/tasks` |
| Events | `GET /restapi/v1.0/glip/groups/{groupId}/events` |
| Notes | `GET /restapi/v1.0/glip/chats/{chatId}/notes` |

## SDK Installation (Multi-language)

| Language | Install |
|----------|---------|
| JavaScript | `npm install @ringcentral/sdk dotenv` |
| Python | `pip install ringcentral python-dotenv` |
| PHP | `php composer.phar require ringcentral/ringcentral-php` |
| Ruby | `gem install ringcentral-sdk dotenv` |
| Java | Add `com.ringcentral:ringcentral` to `build.gradle` |
| C# | NuGet: `RingCentral.Net` |

## Verify Created Team

After creating a team via API, log in at [https://app.ringcentral.com](https://app.ringcentral.com) to confirm the team appears in the sidebar.

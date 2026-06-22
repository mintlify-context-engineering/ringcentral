# RingCentral Open Source Monorepo

This monorepo aggregates RingCentral's open-source GitHub repositories, organized by product area. It is used for a Mintlify demo showing how to create excellent developer documentation — both user-facing docs and structured context for internal AI agents.

RingCentral has 184 public repositories. This monorepo includes the ~50 most active and representative ones, curated by stars, activity, and documentation surface area.

## Structure

```
ringcentral/
├── sdks/               Core language SDKs + communication primitives
├── embeddable/         Pre-built UI widgets and web components
├── docs/               Official API documentation source repos
├── chatbots/           Chatbot frameworks and AI demos
├── video/              Video SDK samples across platforms
├── voice/              Engage Voice & Digital platform
├── crm/                CRM integrations (HubSpot, Pipedrive, Redtail)
├── integrations/       Add-ins, notifications, and tooling
└── infrastructure/     (reserved)
```

## Repositories

### SDKs (`sdks/`)

| Repo | Language | Stars | Description |
|------|----------|-------|-------------|
| ringcentral-js | TypeScript | 71 | Official JavaScript SDK |
| ringcentral-python | Python | 55 | Official Python SDK |
| ringcentral-php | PHP | 55 | Official PHP SDK |
| ringcentral-java | Java | 23 | Official Java SDK |
| ringcentral-net | C# | 25 | Official .NET SDK |
| ringcentral-swift | Swift | 22 | Official Swift SDK |
| ringcentral-go | Go | 5 | Official Go SDK |
| ringcentral-ruby | Ruby | 10 | Official Ruby SDK |
| ringcentral-extensible | TypeScript | 15 | Plugin-based extensible SDK |
| ringcentral-softphone-js | TypeScript | 23 | Softphone JS SDK (WebRTC) |
| ringcentral-softphone-ts | TypeScript | 14 | Softphone TypeScript SDK |
| ringcentral-softphone-go | Go | 23 | Softphone Go SDK |
| ringcentral-call-js | TypeScript | 12 | Call management SDK |
| ringcentral-call-control-js | TypeScript | 10 | Call control SDK |
| ringcentral-websocket-java | Java | 1 | WebSocket Java SDK |

### Embeddable UI (`embeddable/`)

| Repo | Language | Stars | Description |
|------|----------|-------|-------------|
| ringcentral-embeddable | TypeScript | 91 | Drop-in embeddable phone widget |
| ringcentral-js-widgets | TypeScript | 46 | React widget component library |
| ringcentral-web-phone | TypeScript | 124 | Web phone SDK (WebRTC) |
| juno | JavaScript | 30 | UI component design system |
| web-apps | TypeScript | 75 | Web application platform |

### Documentation (`docs/`)

| Repo | Stars | Description |
|------|-------|-------------|
| ringcentral-api-docs | 44 | Official RingCentral developer guide |
| engage-digital-api-docs | 7 | Engage Digital API docs |
| engage-voice-api-docs | 7 | Engage Voice API docs |
| ringcentral-mcp-docs | 1 | MCP (Model Context Protocol) integration docs |
| ringcentral-automator-docs | 1 | Automator workflow docs |
| ringcentral-api-specifications | 5 | OpenAPI specifications |

### Chatbots & AI (`chatbots/`)

| Repo | Language | Stars | Description |
|------|----------|-------|-------------|
| ringcentral-chatbot-js | TypeScript | 15 | Chatbot framework for JavaScript |
| ringcentral-chatbot-python | Python | 13 | Chatbot framework for Python |
| ringcentral-chatbot-core | TypeScript | 5 | Core chatbot utilities |
| rc-assistant | JavaScript | 5 | RC Assistant bot |
| ringcentral-conv-ai-demo | JavaScript | 3 | Conversational AI demo |

### Video (`video/`)

| Repo | Language | Stars | Description |
|------|----------|-------|-------------|
| ringcentral-videosdk-js-samples | TypeScript | 4 | Video SDK JavaScript samples |
| ringcentral-videosdk-react | HTML | 1 | Video SDK React samples |
| ringcentral-videosdk-android-samples | — | 6 | Video SDK Android samples |
| ringcentral-videosdk-ios-samples | — | 19 | Video SDK iOS samples |

### Voice & Digital Engagement (`voice/`)

| Repo | Language | Stars | Description |
|------|----------|-------|-------------|
| engage-voice-embeddable | TypeScript | 7 | Engage Voice embedded widget |
| engage-voice-js | TypeScript | 5 | Engage Voice JavaScript SDK |
| engage-digital-js | TypeScript | 3 | Engage Digital JavaScript SDK |
| engage-digital-chatbot-js | JavaScript | 8 | Engage Digital chatbot SDK |

### CRM Integrations (`crm/`)

| Repo | Language | Stars | Description |
|------|----------|-------|-------------|
| rc-unified-crm-extension | JavaScript | 13 | Unified CRM Chrome extension |
| hubspot-embeddable-ringcentral-phone | JavaScript | 13 | HubSpot embedded phone |
| pipedrive-embeddable-ringcentral-phone | JavaScript | 8 | Pipedrive embedded phone |
| redtail-embeddable-ringcentral-phone | JavaScript | 7 | Redtail CRM embedded phone |
| ringcentral-integration-for-hubspot | — | 9 | Full HubSpot integration |

### Integrations & Tooling (`integrations/`)

| Repo | Language | Stars | Description |
|------|----------|-------|-------------|
| ringcentral-add-in-framework-js | JavaScript | 12 | Add-in development framework |
| ringcentral-embeddable-electron-app | JavaScript | 42 | Embeddable as Electron desktop app |
| ringcentral-mfe | TypeScript | 14 | Micro-frontend framework |
| ringcentral-c2d | TypeScript | 7 | Click-to-dial integration |
| notification-app-js | JavaScript | 8 | Notification app template |
| github-add-in | JavaScript | 5 | GitHub add-in integration |
| vscode-openapi-linter | TypeScript | 9 | VS Code OpenAPI linter |

## RingCentral Platform Overview

RingCentral is a cloud communications platform offering:
- **Voice & SMS**: PSTN calling, SMS, fax via REST API
- **Team Messaging (Glip)**: Team chat, file sharing, task management
- **Video**: RingCentral Video conferencing SDK
- **Engage Digital**: Social/digital customer engagement
- **Engage Voice**: Contact center and outbound dialing
- **Developer Platform**: OAuth2, webhooks, WebSocket subscriptions, add-ins

The platform uses REST APIs documented at `docs/ringcentral-api-docs/` with OpenAPI specs at `docs/ringcentral-api-specifications/`.

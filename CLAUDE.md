# RingCentral Monorepo — Claude Context

This is a curated monorepo of RingCentral's open-source projects assembled for a **Mintlify documentation demo**. The goal is to show RingCentral how Mintlify can dramatically improve their developer docs — both for external developers and for internal AI agents consuming the docs as context.

## Purpose

Demonstrate to RingCentral:
1. How Mintlify can unify fragmented docs (currently spread across 184 repos) into a coherent developer portal
2. How structured docs enable AI agents (MCP, RAG, LLM tooling) to answer developer questions accurately
3. How docs-as-code workflows improve contribution and maintenance

## Repo Map

Each subdirectory is a shallow clone (`--depth=1`) of the corresponding GitHub repo under `github.com/ringcentral/`.

```
sdks/               15 repos — language SDKs (JS, Python, PHP, Java, .NET, Swift, Go, Ruby) + call/softphone
embeddable/          5 repos — UI widgets (embeddable phone, web-phone, widget library, design system)
docs/                6 repos — API docs, OpenAPI specs, MCP docs, automator docs
chatbots/            5 repos — chatbot frameworks (JS, Python) + AI demos
video/               4 repos — Video SDK samples (web, React, Android, iOS)
voice/               4 repos — Engage Voice/Digital SDKs and embeddables
crm/                 5 repos — CRM integrations (HubSpot, Pipedrive, Redtail)
integrations/        7 repos — Add-in framework, electron app, MFE, click-to-dial, notifications
```

## Key Repos for the Demo

The most docs-rich repos to highlight:

- `docs/ringcentral-api-docs` — Main developer guide (Python/MkDocs, 44 stars). Good candidate for Mintlify migration.
- `embeddable/ringcentral-embeddable` — 91-star embeddable widget. Has its own `docs/` folder with markdown.
- `sdks/ringcentral-js` — Core JS SDK. Inline JSDoc but sparse standalone docs.
- `chatbots/ringcentral-chatbot-js` — Popular chatbot framework with README-only docs.
- `docs/ringcentral-mcp-docs` — MCP integration docs (very new, thin coverage — high opportunity).
- `crm/rc-unified-crm-extension` — CRM extension; docs scattered across README and wiki.

## What to Look For

When auditing these repos for docs quality, check:
- Is there a dedicated `docs/` folder or just a README?
- Are API parameters/types documented inline or not at all?
- Are there code examples in multiple languages?
- Is there a getting-started guide separate from API reference?
- Are webhooks/events documented?
- Is the OAuth flow documented end-to-end?

## Platform Concepts (for AI agent context)

**Authentication**: OAuth 2.0 — Authorization Code, Password, Client Credentials, JWT flows.  
**Base URL**: `https://platform.ringcentral.com/restapi/v1.0/`  
**Sandbox**: `https://platform.devtest.ringcentral.com/`  
**Webhooks**: Push delivery via HTTPS or WebSocket (`/restapi/ws/net/v1.0/subscription`)  
**Rate limits**: Per-endpoint, returned in `X-Rate-Limit-*` headers.  
**Pagination**: `page`, `perPage` query params; response includes `navigation` object.  
**Key resources**: `/account/{accountId}`, `/extension/{extensionId}`, `/call-log`, `/message-store`, `/subscription`

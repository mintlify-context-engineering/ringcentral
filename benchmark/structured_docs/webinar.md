---
doc_id: webinar
tags:
  - webinar
  - webinar-api
  - webinar-creation
  - webinar-session
  - webinar-settings
  - webinar-registration
  - webinar-registrants
  - webinar-invitees
  - webinar-hosts
  - webinar-cohosts
  - webinar-panelists
  - webinar-attendees
  - webinar-events
  - webinar-webhooks
  - webinar-subscriptions
  - event-filters
  - registrationEnabled
  - externalId
  - POST /webinar/v1
  - GET /webinar/v1
  - rcwRegCreateRegistrant
  - rcwN11sCreateSubscription
  - rcwRegUpdateSession
---

# RingCentral Webinar API

## Key endpoints (memorize these)

| Action | Method + Path |
|---|---|
| Create a webinar | `POST /webinar/v1/accounts/{accountId}/webinars` |
| Get a webinar | `GET /webinar/v1/accounts/{accountId}/webinars/{webinarId}` |
| Create a session | `POST /webinar/v1/accounts/{accountId}/webinars/{webinarId}/sessions` |
| Get sessions | `GET /webinar/v1/accounts/{accountId}/webinars/{webinarId}/sessions` |
| Invite host/cohost/panelist | `POST /webinar/v1/accounts/{accountId}/webinars/{webinarId}/sessions/{sessionId}/invitees` |
| Create a registrant | `POST /webinar/v1/accounts/{accountId}/webinars/{webinarId}/sessions/{sessionId}/registrants` |
| List registrants | `GET /webinar/v1/accounts/{accountId}/webinars/{webinarId}/sessions/{sessionId}/registrants` |
| Update registration preferences | `PUT /webinar/v1/accounts/{accountId}/webinars/{webinarId}/sessions/{sessionId}/registration` |
| Create webhook subscription | `POST /webinar/v1/subscriptions` |

## Webinar vs. session — key distinction

A **webinar** is a top-level container (title, description, settings). A **session** is an individual scheduled occurrence of a webinar — it has a date/time and is what hosts, panelists, and registrants are associated with. One webinar can have multiple sessions.

## Creating a webinar — request body example

```http
POST /webinar/v1/accounts/{accountId}/webinars
Content-Type: application/json

{
  "title": "Product Launch Q3 2026",
  "description": "Quarterly product update webinar",
  "settings": {
    "recordingEnabled": true,
    "autoRecord": false,
    "registrationEnabled": true,
    "panelistWaitingRoom": true,
    "attendeeAuthentication": "Guest",
    "password": "s3cur3pass",
    "qnaEnabled": true,
    "pollsEnabled": true,
    "postWebinarRedirectUri": "https://acme.com/thank-you"
  }
}
```

## Webinar settings reference

| Setting | Type | Description |
|---|---|---|
| `recordingEnabled` | boolean | Enables recording. Must be `true` for any other recording settings to apply. |
| `autoRecord` | boolean | Starts recording automatically when the webinar goes live. |
| `panelistWaitingRoom` | boolean | Panelists are placed in a waiting room after joining. |
| `attendeeAuthentication` | string | `Guest` (no auth), `AuthenticatedUser`, or `AuthenticatedCoworker`. |
| `password` | string | Password attendees must enter to access the webinar. |
| `qnaEnabled` | boolean | Enables Q&A feature for the webinar. |
| `pollsEnabled` | boolean | Enables polls feature for the webinar. |
| `registrationEnabled` | boolean | `true` for marketing/external webinars (unique join URL per attendee). `false` for internal all-hands (single shared join URL). |
| `postWebinarRedirectUri` | string | URL to redirect attendees to when the webinar ends. |

### When to use `registrationEnabled`

- **`false` (internal/all-hands)**: Single shared join URL for all attendees. Attendees enter name on join but skip registration questions. Easiest to distribute via email or calendar invite.
- **`true` (marketing/external)**: Each attendee gets a unique join URL for tracking and analytics. More overhead — separate invite per attendee. Required for registrant tracking and follow-up campaigns.

## Creating a session

After creating a webinar, create a session by `POST`ing to the sessions endpoint with a scheduled date/time. The session is the entity that hosts, cohosts, panelists, and registrants are attached to.

## Inviting hosts, co-hosts, and panelists

Call `POST /webinar/v1/accounts/{accountId}/webinars/{webinarId}/sessions/{sessionId}/invitees` with the invitee's role (`Host`, `CoHost`, or `Panelist`). Accepted invitees gain elevated privileges: video, screen sharing, and audio during the live session.

## Registering an attendee

Call the [create registrant](https://developers.ringcentral.com/api-reference/Registrants/rcwRegCreateRegistrant) operation:

```http
POST /webinar/v1/accounts/{accountId}/webinars/{webinarId}/sessions/{sessionId}/registrants
Content-Type: application/json

{
  "firstName": "Jane",
  "lastName": "Smith",
  "email": "jane@example.com",
  "externalId": "lid=123&oid=456",
  "source": "customer-invite",
  "joinUri": "https://acme.com/webinar/1234/join?id=5678",
  "cancellationUri": "https://acme.com/webinar/1234/cancel?id=5678"
}
```

### `externalId` — correlate registrants to external systems

Use `externalId` to link a registrant to a CRM contact, lead, or opportunity. There are few constraints on the value — you can encode multiple values using query-string syntax, e.g. `"lid=123&oid=4%4056"` to store both a lead ID and an opportunity ID in a single field. Reverse the encoding to read individual values.

### `source` — campaign attribution

Use `source` to record which campaign drove the registration (e.g. `"customer-invite"`, `"search-ad"`). Useful for post-webinar funnel analysis.

### Custom join/cancel pages

To host your own join or cancel pages, set `joinUri` and `cancellationUri` on the registrant. RingCentral will surface these URLs to attendees instead of the default hosted pages. Your server is then responsible for handling those URLs and calling the API to process joins or cancellations.

### Tracking attendance

- Every registrant gets a unique `id`.
- When a registrant joins, they are assigned a `participantId`.
- If a registrant record has both `id` and `participantId`, they attended. If `participantId` is absent, they never joined.

## Registration preferences (per session)

Call `PUT /webinar/v1/accounts/{accountId}/webinars/{webinarId}/sessions/{sessionId}/registration` to manage:

| Preference | Description |
|---|---|
| `registrationStatus` | Turn registration on or off. |
| `registrantCount` | Read-only count of registered attendees. |
| `autoCloseLimit` | Automatically close registration after N registrants. |
| `suppressEmails` | Prevent RingCentral from sending registration confirmation emails. |
| `preventMultipleDeviceJoins` | Block attendees from joining from more than one device. |

## Webhook subscriptions — events and filters

Create a subscription by calling the [create subscription](https://developers.ringcentral.com/api-reference/Webinar-Subscriptions/rcwN11sCreateSubscription) operation at `POST /webinar/v1/subscriptions`, specifying `eventFilters` and an expiration date.

### Available event filters

| Event Filter | Fires when… |
|---|---|
| `/webinar/configuration/v1/company/sessions` | A session is created or modified. |
| `/webinar/runtime/v1/company/sessions/state` | A session changes state (starts, ends). |
| `/webinar/registration/v1/company/sessions/state` | A session's registration setting is modified. |
| `/webinar/registration/v1/company/sessions/registrants` | A registrant is created or modified. |

### Narrowing event scope with filter parameters

By default, subscribing to a filter receives events for **all** webinars/sessions in the account. Append query parameters to narrow scope:

```
/webinar/registration/v1/company/sessions/registrants?webinarId=<WEBINAR_ID>
```

| Parameter | Description |
|---|---|
| `hostUserId` | Receive events only for a specific host. |
| `webinarId` | Receive events only for a specific webinar. |

## Required permissions

- `EditWebinars` — create/update webinars and sessions
- `ReadWebinars` — read webinar data, registrants, attendees

## Developer program

Partners building customer-facing integrations can apply to the **Webinar Partner Developer Program** for a free developer license to RingCentral Webinar and App Gallery promotion.

---
doc_id: analytics
tags:
  - analytics
  - business-analytics
  - call-analytics
  - aggregate-report
  - timeline-report
  - groupBy
  - groupByMembers
  - Users
  - Queues
  - IVRs
  - Sites
  - Departments
  - UserGroups
  - timeRange
  - timeSettings
  - advancedTimeSettings
  - callFilters
  - directions
  - counters
  - timers
  - responseOptions
  - pagination
  - call-performance
  - call-metrics
  - ringex
---

# RingCentral Business Analytics API

## Key Endpoints

```
POST /analytics/calls/v1/accounts/~/aggregation/fetch
POST /analytics/calls/v1/accounts/~/timeline/fetch
```

Host: `platform.ringcentral.com`  
Auth: `Authorization: Bearer {access_token}`  
Content-Type: `application/json`

## Analytics vs Call Log Quick Facts

- Analytics API is for aggregate business metrics, timelines, groupBy reporting, queues, users, IVRs, departments, counters, and timers.
- Analytics history covers up to `184 days`.
- Call Log API is for per-call records such as duration, direction, result, recording links, and timestamps. Use Call Log when you need per-call detail.

Pagination query params (append to URL):
- Aggregate: `?page=1&perPage=200` (max perPage: 200)
- Timeline: `?interval=Week&page=1&perPage=20` (max perPage: 20; interval values: `Hour`, `Day`, `Week`, `Month`)

## Minimal Request Body

```json
{
  "grouping": {
    "groupBy": "Users"
  },
  "timeSettings": {
    "timeZone": "America/New_York",
    "timeRange": {
      "timeFrom": "2024-01-01T00:00:00.000Z",
      "timeTo": "2024-01-31T23:59:59.999Z"
    }
  },
  "responseOptions": {
    "counters": {
      "allCalls": { "aggregationType": "Sum" },
      "callsByDirection": { "aggregationType": "Sum" },
      "callsByResponse": { "aggregationType": "Sum" }
    },
    "timers": {
      "allCallsDuration": { "aggregationType": "Sum" }
    }
  },
  "callFilters": {
    "directions": ["Inbound"],
    "companyHours": ["BusinessHours"]
  }
}
```

## groupBy Dimensions

`groupBy` (direct grouping — one type per request):

| Value | Description |
|---|---|
| `Company` | Entire company rollup |
| `CompanyNumbers` | Direct numbers under Phone Systems |
| `Users` | Individual mailboxes |
| `Queues` | Queue extensions |
| `IVRs` | IVR extensions |
| `SharedLines` | Shared-line groups (up to 16 phones per number) |
| `UserGroups` | User Groups from Admin Portal |
| `Sites` | Site extensions (multi-site accounts) |
| `Departments` | Users sharing the same Department label |

`groupByMembers` (individual users within a group — mutually exclusive with `groupBy`):

| Value | Description |
|---|---|
| `Department` | Users under specified department IDs |
| `UserGroup` | Users under specified user group IDs |
| `Queue` | Users under specified queue IDs |
| `Site` | Users under specified site IDs |

If `grouping` is omitted or null, returns a single record aggregated for the whole company.

## timeSettings Object

```json
"timeSettings": {
  "timeZone": "America/Los_Angeles",
  "timeRange": {
    "timeFrom": "2024-01-01T00:00:00.000Z",
    "timeTo": "2024-01-31T23:59:59.999Z"
  },
  "advancedTimeSettings": {
    "includeDays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    "includeHours": [{ "from": "09:00", "to": "17:00" }]
  }
}
```

- Data range: current date back to past 184 days
- A call is counted if it **started** within the `timeRange`
- `advancedTimeSettings.includeDays`: filter to specific weekdays
- `advancedTimeSettings.includeHours`: filter to custom hours (format `hh:mm`)

## callFilters

| Filter | Type | Description |
|---|---|---|
| `directions` | array[string] | `Inbound`, `Outbound` |
| `origins` | array[string] | `Internal`, `External` |
| `callResponses` | array[string] | First response action |
| `callResults` | array[string] | Nature of call result |
| `callSegments` | array[object] | Presence of segment: `hold`, `park`, `transfer` |
| `callActions` | array[object] | Specific action: `HoldOn`, `HoldOff`, `ParkOn`, `ParkOff`, `BlindTransfer`, `WarmTransfer`, `DtmfTransfer` |
| `companyHours` | array[string] | `BusinessHours`, `AfterHours` |
| `callDuration` | object | Filter by overall call length |
| `timeSpent` | object | Filter by time spent by mailbox on call |
| `extensionFilters.fromIds` | array[string] | Extension IDs that placed calls to groupBy members |
| `extensionFilters.toIds` | array[string] | Extension IDs that groupBy members called |
| `calledNumbers` | array[string] | Direct company numbers dialed (e.g., `"+16505551212"`) |
| `queueSla` | array[string] | `InSla`, `OutOfSla` (Queues grouping only) |
| `callTypes` | array[string] | `Direct`, `FromQueue`, `ParkRetrieval`, `Transferred`, `Outbound`, `Overflow` |

## responseOptions — counters and timers

### Counter metrics (call volume)

| Counter field | Timer equivalent | Description |
|---|---|---|
| `allCalls` | `allCallsDuration` | Total calls / total duration |
| `queueOpportunities` | N/A | Times a call was presented to an extension (Users grouping only) |
| `callsByDirection` | `callsDurationByDirection` | Inbound vs Outbound |
| `callsByOrigin` | `callsDurationByOrigin` | Internal vs External |
| `callsByResponse` | `callsDurationByResponse` | answered / notanswered / connected / notConnected |
| `callsByType` | `callsDurationByType` | direct / fromQueue / parkRetrieval / transferred / outbound / overflow |
| `callsByActions` | N/A | holdOn/Off, parkOn/Off, blindTransfer, warmTransfer, dtmfTransfer |
| `callsByResult` | `callsDurationByResult` | Completed / Abandoned / Voicemail / Missed / Accepted / Unknown |
| `callsSegments` | `callsSegmentsDuration` | setup / ringing / ivrPrompts / livetalk / holds / parks / transfers / vmGreeting / voicemail |
| `callsByCompanyHours` | `callsDurationByCompanyHours` | BusinessHours vs AfterHours |
| `callsByQueueSla` | `callsDurationByQueueSla` | inSla / outOfSla (Queues only) |

Aggregation types for each metric: `Sum`, `Average`, `Min`, `Max`, `Percent`

## Aggregate vs Timeline

| Feature | Aggregate | Timeline |
|---|---|---|
| Endpoint | `POST /analytics/calls/v1/accounts/~/aggregation/fetch` | `POST /analytics/calls/v1/accounts/~/timeline/fetch` |
| Output | Single aggregated totals per group | Totals split by time interval (Hour/Day/Week/Month) |
| Max perPage | 200 | 20 |
| interval param | N/A | `?interval=Hour\|Day\|Week\|Month` |
| Use case | Total answered calls per agent, abandonment rate | Peak call times by hour, daily handle time trends |

## Overview

The Business Analytics API is a **historical** call performance product for RingEX customers. It is distinct from the Call Log API:
- Call Log: metadata for individual calls (older data source)
- Analytics: aggregate analysis across teams, queues, users (different data source — 100% match with Call Log is not guaranteed)

Supported analyses: call volume, abandonment rate, average handle time, time-to-answer, call result breakdown, IVR traversal, hold/park/transfer actions, queue SLA compliance, business hours vs after-hours split.

Interactive API reference:
- Aggregate: `https://developers.ringcentral.com/api-reference/Business-Analytics/analyticsCallsAggregationFetch`
- Timeline: `https://developers.ringcentral.com/api-reference/Business-Analytics/performanceReportCallsTimeline`

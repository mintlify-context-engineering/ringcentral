---
doc_id: ringcentral-video-api
tags: [video, meetings, bridge, rcvideo, create-meeting, schedule-meeting, join-meeting, pin, pstn, personal-meeting-id, pmi, instant-meeting, scheduled-meeting, end-to-end-encryption, waiting-room, recording, transcription, screen-sharing, host-pin, participant-pin, meeting-delegate, discovery-url, rest-api]
---

# RingCentral Video REST API

The RingCentral Video REST API lets developers create and schedule meetings, join meetings via URL, and access meeting history and recordings. Base path: `/rcvideo/v2/`.

## Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/rcvideo/v2/bridges/` | Create a meeting bridge |
| `GET` | `/rcvideo/v2/bridges/` | List/retrieve bridge details |
| `GET` | `/rcvideo/v2/bridges/pin/web/{pin}` | Look up a bridge by its web PIN |
| `GET` | `/rcvideo/v2/bridges/pin/pstn/{pin}` | Look up a bridge by its PSTN PIN |
| `PATCH` | `/rcvideo/v2/bridges/{id}` | Update an existing bridge |
| `DELETE` | `/rcvideo/v2/bridges/{id}` | Delete a bridge |

## Meetings vs. Bridges

A **bridge** is a persistent virtual meeting room. A **meeting** is the live session that exists while at least one person is connected to a bridge. Creating a meeting means creating a bridge; the meeting begins when the first participant connects and ends when the last disconnects.

## Bridge Types (`type` parameter)

| Type | Behavior |
|------|----------|
| `Instant` | Retained for 3 days then deleted. Default. |
| `Scheduled` | Persists long-term; deleted after prolonged inactivity. Reusable. |
| `PMI` | Uses the host user's Personal Meeting ID (personal bridge). |

## Security Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `passwordProtected` | boolean | Require a password to enter. |
| `password` | string | Password; auto-generated if omitted when `passwordProtected` is true. |
| `noGuests` | boolean | Require attendees to authenticate before joining. |
| `sameAccount` | boolean | Restrict to attendees from the same RingCentral account. |
| `e2ee` | boolean | Enable end-to-end encryption. |

## Preferences Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `join.audioMuted` | boolean | Mute attendee audio by default. |
| `join.videoMuted` | boolean | Disable attendee video by default. |
| `join.waitingRoomRequired` | string | `"Nobody"` (default for Instant/Scheduled), `"Everybody"`, `"GuestsOnly"`, `"OtherAccount"` (default for PMI). |
| `join.pstn.promptAnnouncement` | boolean | Play "announce yourself" prompt. |
| `join.pstn.promptParticipants` | boolean | Play "there are N participants" prompt. |
| `playTones` | string | `"On"`, `"Off"`, `"ExitOnly"`, `"EnterOnly"`. |
| `musicOnHold` | boolean | Play music when only one person is waiting. |
| `joinBeforeHost` | boolean | Allow participants to join before host arrives. |
| `screenSharing` | boolean | Allow participants to share their screen. |
| `recordingsMode` | string | `"Auto"`, `"ForceAuto"`, `"User"`. |
| `transcriptionsMode` | string | `"Auto"`, `"ForceAuto"`, `"User"`. |

## PIN Codes

Two types of PSTN (phone dial-in) PIN codes are returned in the bridge response:

- **Host PIN (`hostCode`)**: Used by the meeting host when dialing in via phone. Grants additional host controls over the meeting.
- **Participant PIN**: Used by regular attendees when dialing in via phone.

PIN codes are only used for PSTN (phone) access; they are not required for web/app join.

To look up a bridge by its web PIN: `GET /rcvideo/v2/bridges/pin/web/{pin}`

## Join URL

The join URL for participants is found in the `discovery` element of the bridge creation response. This URL is what you share with meeting participants to let them join via browser or app.

## Time and Date

RingCentral Video does **not** store time/date/location for meetings. Scheduling is deferred to the user's calendar system (Google Calendar, Outlook, etc.) as the source of record. This eliminates sync complexity and simplifies compliance.

## Scheduling on Behalf of Another User

Use the meeting delegates API (see `meeting-delegates` documentation) to create a bridge on behalf of another user.

## Authentication Requirements

- Requires a RingCentral Video Pro account (free developer accounts do not support Video).
- Create an application in the Developer Console with the appropriate Video permissions.
- Authenticate via OAuth 2.0 before calling any `/rcvideo/v2/` endpoints.

## Quick Start Languages

Javascript, PHP, Python, Ruby, Java, C#

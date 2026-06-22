---
doc_id: ringcentral-ai-apis
tags:
  - ai
  - speech-to-text
  - transcription
  - speech-transcription
  - speaker-diarization
  - summarization
  - punctuation
  - interaction-analytics
  - async
  - asynchronous
  - job-polling
  - webhook
  - jobId
  - ace
  - ai-conversation-expert
  - ringsense
  - conversation-insights
  - sentiment-analysis
  - call-analytics
  - next-steps
  - highlighted-moments
  - deprecated-ai
  - audio-processing
  - nlp
---

# RingCentral AI APIs

## Key Endpoints (Deprecated Legacy AI + ACE)

### Legacy AI Async Endpoints (DEPRECATED — use ACE instead)
- `POST /ai/audio/v1/async/speech-to-text?webhook=<url>` — Submit audio for transcription
- `POST /ai/audio/v1/async/speaker-diarize?webhook=<url>` — Submit audio for speaker diarization
- `POST /ai/text/v1/async/summarize?webhook=<url>` — Submit text for summarization
- `POST /ai/text/v1/async/punctuate?webhook=<url>` — Submit text for smart punctuation
- `POST /ai/insights/v1/async/analyze-interaction?webhook=<url>` — Submit audio for interaction analytics
- `GET /ai/status/v1/jobs/{jobId}` — Poll job status; returns `Completed` when done

### ACE (AI Conversation Expert) Endpoints (RECOMMENDED)
- `GET /ai/ringsense/v1/public/accounts/~/domains/{domain}/records/{sourceRecordId}/insights` — Get insights by recording ID
- `GET /ai/ringsense/v1/public/accounts/~/domains/{domain}/sessions/{sourceSessionId}/insights` — Get insights by telephony session ID
- `GET /restapi/v1.0/account/~/extension/~/authz-profile/check?permissionId=ReadRingSenseInsights` — Check if user has ACE access

### Supported ACE Domains
- `pbx` — Voice calls via RingEX
- `rcv` — Video calls via RingEX
- `rcx` — Voice calls via RingCX
- `nice-incontact` — Voice calls via RingCentral Nice CXone integration
- `ms-teams` — Video conferences via MS Teams

---

## Async Job Pattern (Legacy AI API)

All legacy AI endpoints are asynchronous. The pattern:

1. **Submit** a POST request with `?webhook=<your-public-url>` query parameter.
2. **Receive** a `jobId` in the immediate HTTP response body: `{"jobId":"a919924e-ce4e-11ed-xxxx-0050568c48bc"}`
3. **Poll** `GET /ai/status/v1/jobs/{jobId}` until `status` equals `Completed`.
4. **Receive results** posted to your webhook URL when processing finishes.

Job IDs expire after **1 week**. Check `expirationTime` in the job status response for the exact time.

### Python Example — Submit + Poll

```python
import requests
import time

TOKEN = "YOUR_ACCESS_TOKEN"
BASE_URL = "https://platform.ringcentral.com"
WEBHOOK_URL = "https://your-ngrok-url.ngrok-free.app/webhook"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. Submit speech-to-text job
payload = {
    "contentUri": "https://example.com/call-recording.mp3",
    "encoding": "MP3",
    "languageCode": "en-US",
    "audioType": "CallCenter",
    "enableSpeakerDiarization": True,
    "speakerCount": 2,
    "enablePunctuation": True
}
resp = requests.post(
    f"{BASE_URL}/ai/audio/v1/async/speech-to-text?webhook={WEBHOOK_URL}",
    json=payload,
    headers=headers
)
job_id = resp.json()["jobId"]
print(f"Submitted job: {job_id}")

# 2. Poll for completion
while True:
    status_resp = requests.get(
        f"{BASE_URL}/ai/status/v1/jobs/{job_id}",
        headers=headers
    )
    status = status_resp.json().get("status")
    if status == "Completed":
        print("Done:", status_resp.json())
        break
    elif status == "Failed":
        print("Job failed")
        break
    time.sleep(5)
```

### JavaScript Example — Submit + Poll

```js
const axios = require("axios");

const TOKEN = "YOUR_ACCESS_TOKEN";
const BASE = "https://platform.ringcentral.com";
const WEBHOOK = "https://your-ngrok-url.ngrok-free.app/webhook";

async function transcribeAudio() {
  // Submit job
  const { data } = await axios.post(
    `${BASE}/ai/audio/v1/async/speech-to-text?webhook=${WEBHOOK}`,
    {
      contentUri: "https://example.com/call-recording.mp3",
      encoding: "MP3",
      languageCode: "en-US",
      audioType: "CallCenter",
      enableSpeakerDiarization: true,
      speakerCount: 2,
      enablePunctuation: true
    },
    { headers: { Authorization: `Bearer ${TOKEN}` } }
  );
  const jobId = data.jobId;

  // Poll until complete
  while (true) {
    const { data: status } = await axios.get(
      `${BASE}/ai/status/v1/jobs/${jobId}`,
      { headers: { Authorization: `Bearer ${TOKEN}` } }
    );
    if (status.status === "Completed") { console.log(status); break; }
    if (status.status === "Failed") { console.error("Failed"); break; }
    await new Promise(r => setTimeout(r, 5000));
  }
}
transcribeAudio();
```

---

## Speech-to-Text (DEPRECATED)

**Endpoint:** `POST /ai/audio/v1/async/speech-to-text?webhook=<url>`

**Status:** Deprecated. Migrate to ACE.

### Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `contentUri` | String | Publicly accessible URL of the media file |
| `encoding` | String | Audio encoding: `MP3`, `WAV`, etc. |
| `languageCode` | String | Language code. Default: `en-US`. English only. |
| `audioType` | String | `CallCenter` (2–3 speakers, default), `Meeting` (4–6 speakers), `EarningsCalls`, `Interview`, `PressConference` |
| `speakerCount` | Number | Number of speakers. Use `-1` if unknown. Used when `enableSpeakerDiarization=true`. |
| `source` | String | Audio source: `Phone`, `RingCentral`, `GoogleMeet`, `Zoom`, `Webex`, `GotoMeeting`. Enables specialized acoustic model. |
| `enableSpeakerDiarization` | Boolean | Tag each word with speaker ID. Default: `false`. |
| `separateSpeakerPerChannel` | Boolean | Set `true` for multi-channel audio with one speaker per channel. Default: `false`. |
| `enableVoiceActivityDetection` | Boolean | Remove silence/noise from diarization. Default: `false`. Recommend `true`. |
| `enablePunctuation` | Boolean | Apply Smart Punctuation API. Default: `true`. |

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `transcript` | String | Full transcript text |
| `confidence` | Number | Overall transcription confidence score |
| `speakerCount` | Number | Detected number of speakers (when diarization enabled) |
| `words` | List | Word-level segments with `speakerId`, `start`, `end`, `word`, `confidence` |
| `utterances` | List | Utterance segments with `speakerId`, `start`, `end`, `text`, `confidence`, `wordTimings` |

**Tip:** Set `enableSpeakerDiarization=false` for voicemail transcription — faster processing, no speaker tags needed.

---

## AI Conversation Expert (ACE) — RECOMMENDED

ACE (also marketed as **RingSense**) transcribes voice calls and video meetings and delivers post-call conversational insights.

### Requirements
- An **AI Conversation Expert license** must be purchased and assigned to a user extension.
- Accessing ACE data via API requires the **"AI Conversation Expert - Access Insights"** user permission (`ReadRingSenseInsights`).
- Any authorized user can access ACE data for any licensed user in the account.
- Default data retention: **1 year** (configurable in ACE admin settings).

### ACE Insight Types

| Insight | Type | Description |
|---------|------|-------------|
| `Transcript` | List | Speaker-identified utterances with timestamps |
| `Summary` | List | AI-generated summary paragraphs with timestamps |
| `HighLights` | List | Key utterances and notable moments |
| `NextSteps` | List | AI-generated action items for call participants |
| `AIScore` | Object | Numerical confidence score of AI analysis |
| `Sentiment` | Object | Overall conversation sentiment: `Positive`, `Negative`, or `Neutral` |
| `BulletedSummary` | List | Bullet-point summary sentences |
| `CallNotes` | Object | Notes captured during call via AI Notes feature (RingEX voice calls only) |

### Access Methods

**Method 1: Push notifications (recommended)** — Subscribe to ACE event filters via the RingCentral push notification service. Events fire when ACE finishes analyzing a recorded call.

**Method 2: REST API pull** — Query by `sourceRecordId` or `sourceSessionId` (obtained from call log data or ACE event payload).

### ACE API Response Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | String | Composed from caller/callee names |
| `domain` | String | Communication medium (`pbx`, `rcv`, `rcx`, etc.) |
| `sourceRecordId` | String | Recording identifier |
| `sourceSessionId` | String | Telephony session ID (voice) or same as `sourceRecordId` (video) |
| `callDirection` | String | `Inbound` or `Outbound` (voice calls only) |
| `ownerExtensionId` | String | Extension ID of the ACE license holder |
| `recordingDurationMs` | Integer | Recording length in milliseconds |
| `recordingStartTime` | String | ISO 8601 recording start timestamp |
| `speakerInfo` | List | Participant details: `speakerId`, `name`, `accountId`, `extensionId` |
| `insights` | Object | Contains all insight type objects listed above |

### Matching Speakers to Utterances

Use `speakerId` from `Transcript` utterances to look up the speaker's name in the `speakerInfo` list.

---

## Deprecation Summary

All endpoints under these paths are **deprecated** — no new features, limited bug fixes, no long-term support guarantee:

- `/ai/audio/v1/async/*` (speech-to-text, speaker-diarize)
- `/ai/text/v1/async/*` (summarize, punctuate)
- `/ai/insights/v1/async/*` (analyze-interaction)
- `/ai/status/v1/jobs/{jobId}`

**Migrate to:** `/ai/ringsense/v1/public/accounts/~/domains/{domain}/...`

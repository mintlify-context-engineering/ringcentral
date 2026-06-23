# Doc Structure Guide — AI-Agent-Optimized Documentation

How to structure docs for any monorepo so that AI agents answer questions with **fewer input tokens** and **higher accuracy**. Based on the autoresearch loop findings from the RingCentral benchmark.

## The Core Insight

The raw monorepo approach forces an AI agent to:
1. Search across 40+ scattered repos
2. Read 5–15 files averaging 5,000 chars each
3. Synthesize across disconnected READMEs

Result: ~40,000 chars read per question (~10,000 input tokens). Mintlify structured docs can answer the same questions with ~3,000–6,000 chars (~800–1,500 input tokens).

**That's a 70–85% input token reduction — and higher accuracy because structured docs are curated and complete.**

---

## The 6 Principles (Ranked by Impact)

### 1. Answer-First Content

Put the most-queried fact in the **first sentence** of each section. Don't build up to it.

```markdown
# BAD — makes the agent read 400 chars before finding the value
## Base URLs
RingCentral provides several server environments. The production environment is
the standard endpoint for live traffic. The base URL for the production server is:
`https://platform.ringcentral.com`

# GOOD — key fact is queryable in the first 80 chars
## Base URLs
**Production host / SDK server URL:** `https://platform.ringcentral.com`
**Sandbox host / SDK server URL:** `https://platform.devtest.ringcentral.com`
**Full production REST API prefix:** `https://platform.ringcentral.com/restapi/v1.0/`
**Full sandbox REST API prefix:** `https://platform.devtest.ringcentral.com/restapi/v1.0/`
```

**Why it works:** When chunk_size=2500, a single search hit can now answer T1-level questions without a follow-up `read_doc` call.

---

### 2. Complete Enumeration — No Gaps, No "etc."

Never omit items from a list. If there are 7 SDKs, list all 7 with their exact install commands in one place.

```markdown
# BAD — forces agent to follow link for Go and Swift
**Install the Python SDK:** `pip3 install ringcentral`  
See the [SDK list](sdks.md) for other languages.

# GOOD — all install commands in one scannable table
| Language | Install |
|----------|---------|
| Python   | `pip3 install ringcentral` |
| JS/Node  | `npm install @ringcentral/sdk` |
| PHP      | `composer require ringcentral/ringcentral-php` |
| Ruby     | `gem install ringcentral_sdk` |
| Java     | Maven: `com.ringcentral:ringcentral` |
| Go       | `go get github.com/ringcentral/ringcentral-go` |
| .NET     | `dotnet add package RingCentral.Net` |
```

**Why it works:** Agents scoring T3-level "cross-repo synthesis" questions can answer in one search call instead of reading 7 separate SDK READMEs.

---

### 3. Precise Values — Exact Strings Only

Use the exact string an agent would search for. Paraphrases fail exact-match ranking.

```markdown
# BAD — agent searches for "jwt grant type" and gets low relevance
The JWT bearer grant uses a special grant_type value (see RFC 7523).

# GOOD — exact OAuth grant_type string is in the doc
grant_type: `urn:ietf:params:oauth:grant-type:jwt-bearer`
```

**Key rule:** If the exact string appears in a request body, header name, status code, or URL path — write it verbatim in the doc.

---

### 4. Decision Tables Before Detail

For any "X vs Y" comparison, start with a decision table. Don't bury the recommendation.

```markdown
# BAD — 3 paragraphs of JWT, then Auth Code, then a comparison section
## JWT Authentication
[300 words]

## Authorization Code
[300 words]

## Which should I use?
[200 words]

# GOOD — decision table first
| Scenario | Use |
|----------|-----|
| Server script / cron job / no UI | **JWT** |
| Multiple users log in via browser | **Auth Code + PKCE** |
| Single service account for whole org | **JWT** |
| Per-user consent and visibility | **Auth Code** |

[then the detail sections follow]
```

**Why it works:** T3 questions like "which auth flow?" resolve in a single search hit against the decision table.

---

### 5. Inline Code Examples

Put code examples directly in the doc. Don't link to external repos.

```markdown
# BAD — doubles the agent's tool call cost
See the [Python quick-start sample](https://github.com/ringcentral/ringcentral-api-docs/blob/main/code-samples/auth/jwt.py)

# GOOD — agent gets the code in the same search result
```python
from ringcentral import SDK
sdk = SDK('CLIENT_ID', 'CLIENT_SECRET', 'https://platform.ringcentral.com')
platform = sdk.platform()
platform.login(jwt='YOUR_JWT_TOKEN')
```
```

**Why it works:** T2 how-to questions ("show me the code") can be answered in one tool call instead of two.

---

### 6. Semantic Tags — Rich and Precise

Every page needs a `tags` array with the exact strings developers and agents search for.

```markdown
# BAD tags — too generic
tags: ["auth", "login", "token"]

# GOOD tags — match exact search queries
tags: ["jwt", "oauth", "grant_type", "urn:ietf:params:oauth:grant-type:jwt-bearer",
       "authorization_code", "pkce", "refresh_token", "bearer", "client_id", 
       "client_secret", "access_token", "token_endpoint"]
```

**Why it works:** The `_score_doc` function in the search engine rewards exact tag matches (+10 per tag hit). Precise tags make the right doc surface on the first search call.

---

## Optimal Chunk Size: 2,000–3,000 Characters

Autoresearch loop findings on chunk_size impact:

| Chunk Size | Behavior | Token Cost | Accuracy |
|-----------|----------|-----------|---------|
| 400–800 | Answers cut off; agent makes extra `read_doc` calls | Low → Medium | Low–Medium |
| 1,500–3,000 | Fits most answers; minimal follow-up needed | Low | High |
| 5,000+ | Too much noise per search; high cost for small gain | High | High |

**Target:** 2,000–2,500 chars per search result. This fits the answer for ~80% of T1 and T2 questions in a single search hit.

---

## Page Structure Template

Use this template for every doc page:

```markdown
# [Topic Title]

**Quick answer / most common query:** [Key fact in ≤ 80 chars]

## Decision: When to Use [X] vs [Y]

| Scenario | Recommendation |
|----------|---------------|
| [case A] | [choice] |
| [case B] | [choice] |

## [Subtopic A]

**Key fact:** [exact value or command]

[Supporting context — 2–4 sentences]

[Code example — inline, not linked]

## [Subtopic B]

...

→ See also: [related-page](related.md) for [topic]
```

---

## What NOT to Do

| Anti-pattern | Why It Costs Tokens |
|-------------|-------------------|
| `pip install ringcentral` (missing `3`) | Agent's exact match for `pip3` fails; needs follow-up |
| "See the SDK list for all languages" | Forces another tool call to enumerate all SDKs |
| Auth caching guidance buried in "Important Notes" section | Agent reads entire page to find a T3 key fact |
| Separate "Quick Start" and "Reference" with same info | Doubles the chars the agent reads |
| Listing only the host URL without the full API path | Sends agent back for a follow-up search |

---

## Measuring the Improvement

### With `autoresearch_loop.py`
```bash
python autoresearch_loop.py --questions T1-01 T1-06 T2-01 T2-04 T3-01
```

Outputs:
- Input tokens per question (per config)
- % reduction vs raw monorepo baseline
- Composite score (accuracy × efficiency)
- Per-config breakdown showing which structure wins

### Expected results with answer-first docs

| Config | Avg Input Tokens | % vs Raw | Avg Score |
|--------|-----------------|---------|---------|
| raw baseline | ~10,500 | — | 1.85/2 |
| minimal | ~400 | −96% | 1.3/2 |
| standard | ~1,200 | −89% | 1.7/2 |
| **answer-first** | **~900** | **−91%** | **1.85/2** |
| full | ~4,500 | −57% | 1.9/2 |

Answer-first wins the composite score: it matches raw accuracy at 91% fewer tokens.

---

## Generalizing to Any Monorepo

These principles apply to any monorepo, regardless of domain. The recipe is:

1. **Identify the top 20 questions** developers ask (look at your support tickets, GitHub issues, Discord)
2. **Write a structured_docs/ directory** with one file per conceptual area (auth, errors, pagination, SDKs, etc.)
3. **Format each file in answer-first style** with decision tables, inline examples, and complete enumeration
4. **Build a search index** (`index.json`) with precise semantic tags per page
5. **Run the autoresearch loop** to find the optimal chunk_size for your domain
6. **Deploy to Mintlify** — the MCP server exposes `search_docs` and `read_doc` semantically

The autoresearch loop output tells you: "serve chunks of N chars, include examples, max M results per search" — and that setting becomes your Mintlify MCP configuration.

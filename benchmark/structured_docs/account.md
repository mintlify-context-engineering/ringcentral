---
doc_id: ringcentral-account-api
tags: [account, extension, phone-number, user, directory, address-book, internal-contacts, external-contacts, personal-contacts, presence, custom-fields, call-queue, ivr, usage-type, extension-type, admin, permissions, read-accounts, edit-extensions, edit-accounts, site, federation, directory-entries, rest-api]
---

# RingCentral Account API

The Account API provides access to account settings, extensions (users), phone numbers, and the company directory. Base path: `/restapi/v1.0/account/{accountId}/`. Use tilde (`~`) in place of `accountId` or `extensionId` to refer to the currently authenticated account/extension.

## Account Quick Facts

- List all account extensions/users: `GET /restapi/v1.0/account/{accountId}/extension`.
- List company directory entries: `GET /restapi/v1.0/account/~/directory/entries`.
- Filter directory entries by site: `GET /restapi/v1.0/account/~/directory/entries?siteId={site}`.
- List the authenticated extension's phone numbers: `GET /restapi/v1.0/account/~/extension/~/phone-number`.
- Phone number `features` can include `SmsSender` for SMS-capable sender numbers.
- Send SMS from the authenticated extension with `POST /restapi/v1.0/account/~/extension/~/sms`.
- A P2P SMS sender must belong to the authenticated user extension; a super admin cannot send from another user's direct number.

## Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/restapi/v1.0/account/{accountId}` | Get account info (billing, service plan, main number, status) |
| `GET` | `/restapi/v1.0/account/{accountId}/extension` | List all extensions in the account |
| `GET` | `/restapi/v1.0/account/{accountId}/extension/{extensionId}` | Get a specific extension |
| `POST` | `/restapi/v1.0/account/{accountId}/extension` | Create a new extension/user |
| `GET` | `/restapi/v1.0/account/{accountId}/phone-number` | List all phone numbers for the account |
| `GET` | `/restapi/v1.0/account/~/directory/entries` | List company directory entries |
| `GET` | `/restapi/v1.0/account/~/directory/entries?siteId={site}` | Filter directory by site |

## Required App Permissions

| Permission | Description |
|------------|-------------|
| `ReadAccounts` | Retrieve account and extension data. |
| `EditExtensions` | Modify extension settings (includes ReadAccounts). |
| `EditAccounts` | Modify account settings; create/modify/delete extensions (includes EditExtensions). |
| `Accounts` | Create new accounts (includes EditAccounts). |

## Access Control Rules

- Any user may access public account information and full details of their own extension.
- Only administrators may access all extensions and full account data.
- Non-admin users retrieving phone numbers receive only Direct Numbers of other extensions; the `features` set is not returned.

## Extension Types

| Extension Type | Description |
|----------------|-------------|
| `User` | A standard user extension. |
| `FaxUser` | Fax-only extension. |
| `VirtualUser` | Calls and faxes only. |
| `DigitalUser` | Calls, faxes, and desk phones. |
| `Department` | Distributes calls to member extensions (call queue). |
| `TakeMessageOnly` (Voicemail) | All calls routed to voicemail automatically. |
| `AnnouncementOnly` | Plays a recorded announcement to callers. |
| `SharedLinesGroup` | One number answered by multiple devices; calls can be handed off. |
| `PagingOnlyGroup` | Real-time announcements to desk phones/overhead paging. |
| `IvrMenu` | Auto-Receptionist with greeting and menu navigation. |
| `ParkLocation` | Private call park for a specific group. |

Note: The system extension (ID matches the account ID) has full administrator rights.

## Phone Number Usage Types (`usageType`)

| Usage Type | Description |
|------------|-------------|
| `MainCompanyNumber` | First local/toll-free number; one per account. |
| `AdditionalCompanyNumber` | Second company number; one per account. |
| `CompanyNumber` | Account-level number not mapped to a specific extension (e.g., Auto-Receptionist). |
| `DirectNumber` | Number mapped directly to an extension. |
| `CompanyFaxNumber` | Dedicated company fax number. |
| `ForwardedNumber` | External number configured to forward to a RingCentral number. |

## Phone Number Types (`type`)

| Type | Description |
|------|-------------|
| `VoiceAndFax` | Accepts voice and fax; SMS supported. |
| `VoiceOnly` | Accepts voice only; SMS supported. |
| `FaxOnly` | Accepts fax only; SMS not supported. |

## Phone Number Features

The `features` property lists capabilities per number:
- `CallerId` — can be exposed as caller ID for outbound calls.
- `SmsSender` — can be specified as sender in outbound SMS.

## Address Book and Company Directory

Contacts are divided into two categories:

### Internal Contacts (Company Directory)

Internal contacts come from your company's LDAP/directory server and are managed by external systems. You cannot add contacts to the directory via REST API, but you can:

- **Search** the directory: `GET /restapi/v1.0/account/~/directory/entries` (with search params)
- **List all entries**: `GET /restapi/v1.0/account/~/directory/entries`
- **Get a specific entry**: `GET /restapi/v1.0/account/~/directory/entries/{entryId}`
- **Discover federated accounts**: `GET /restapi/v1.0/account/~/directory/federation`

#### Filtering Directory Entries

**By site** (large multi-geography companies): use `?siteId=ATL` query parameter.

**By extension type**: use `?type=User&type=Department&type=Announcement&type=Voicemail&type=SharedLinesGroup`. Multiple values return a union.

**Filter unactivated extensions**: query for `status=NotActivated` and exclude those records from display.

**Hiding directory entries**: Administrators can hide individual users, mobile numbers, or contact numbers from the directory via RingCentral Service Web (Users > User Detail > General tab). Options: hide mobile phone, hide contact phone, or hide the user entirely.

### External / Personal Contacts

Each user maintains their own personal address book (max 10,000 records per user). REST APIs support:

- List personal contacts
- Create or update a personal contact
- Batch-create contacts
- Retrieve a single personal contact
- List and manage favorite contacts

Personal contacts are unique to each user and are not shared across the account.

## Pagination

All list endpoints use `page` and `perPage` query parameters. Responses include a `navigation` object with `lastPage` and a `paging` object with totals.

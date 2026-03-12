# OAuth 2.0 and OpenID Connect (OIDC)

## Overview

OAuth 2.0 is an **authorization** framework that allows applications to obtain limited access to user accounts on external services. OpenID Connect (OIDC) is an **authentication** layer built on top of OAuth 2.0.

These two concerns are distinct:

| Concern | Protocol | Question Answered |
|---|---|---|
| Authentication | OpenID Connect (OIDC) | Who is this user? |
| Authorization | OAuth 2.0 | What can this app do on behalf of the user? |

---

## Scopes

Scopes are space-separated strings requested during an OAuth flow that declare what access the application needs. A single flow can request both OIDC and resource scopes simultaneously.

### OIDC Scopes (Authentication)

These are **standardized** by the [OpenID Foundation](https://openid.net/specs/openid-connect-core-1_0.html) and work with any OIDC-compliant provider (Google, Microsoft, Okta, Auth0, Keycloak, GitHub, etc.).

| Scope | Required? | What it returns |
|---|---|---|
| `openid` | Yes — triggers OIDC flow | Subject identifier (`sub`) in the `id_token` |
| `email` | Optional | `email`, `email_verified` |
| `profile` | Optional | `name`, `given_name`, `picture`, `locale`, etc. |

### Resource Scopes (Authorization)

These are **provider-specific** and govern access to particular APIs. They vary by provider and service.

**Google examples:**

| Scope | Access granted |
|---|---|
| `gmail.readonly` | Read-only access to Gmail |
| `drive.file` | Access to files created or opened by the app |
| `calendar.events` | Read/write access to calendar events |

**Other provider examples:**

| Provider | Scope | Access granted |
|---|---|---|
| GitHub | `repo` | Full access to repositories |
| Slack | `channels:read` | Read channel list |
| Microsoft | `Mail.Read` | Read user mail |

---

## How They Work Together

A single authorization request can include both OIDC and resource scopes:

```
GET /authorize
  ?response_type=code
  &client_id=<client_id>
  &redirect_uri=<redirect_uri>
  &scope=openid email profile gmail.readonly
         └─────────────────────┘ └──────────┘
               OIDC (authn)       API (authz)
```

The provider returns:
- An **`id_token`** (JWT) — carries identity claims (`sub`, `email`, `name`, etc.), used for authentication
- An **`access_token`** — used as a Bearer token to call the authorized APIs
- A **`refresh_token`** — (if requested) used to obtain new access tokens without re-prompting the user

---

## OAuth 2.0 Flow (Authorization Code)

The most common and secure flow for web/server applications:

```
1. App redirects user to provider /authorize with requested scopes
2. User authenticates and consents
3. Provider redirects back with a short-lived authorization code
4. App exchanges code for tokens at provider /token endpoint
5. App uses access_token to call APIs
6. App uses id_token to establish user session
```

---

## Token Types

| Token | Format | Purpose | Lifetime |
|---|---|---|---|
| `id_token` | JWT (signed) | Prove user identity; contains claims | Short (1 hour typical) |
| `access_token` | Opaque or JWT | Authorize API calls | Short (1 hour typical) |
| `refresh_token` | Opaque | Obtain new access/id tokens | Long (days to months) |

### Verifying the id_token

The `id_token` is a JWT. Its claims should be verified:

1. Signature — using the provider's public keys (JWKS endpoint)
2. `iss` — matches the expected issuer (e.g., `https://accounts.google.com`)
3. `aud` — matches your client ID
4. `exp` — token is not expired

---

## Key Distinctions

### `openid` is not Google-specific

`openid email profile` are OIDC standard scopes. The same scopes behave identically across providers:

```python
# Google
SCOPES = ["openid", "email", "profile"]

# Okta — same scopes, same semantics
SCOPES = ["openid", "email", "profile"]

# Keycloak — same
SCOPES = ["openid", "email", "profile"]
```

### Resource scopes ARE provider-specific

`gmail.readonly` only means something to Google's APIs. Another provider would define its own scope strings for equivalent access.

---

## Example: Google OAuth with Both Scope Types

```python
from google_auth_oauthlib.flow import Flow

flow = Flow.from_client_secrets_file(
    "client_secret.json",
    scopes=[
        "openid",  # OIDC — authentication
        "email",  # OIDC — user's email
        "profile",  # OIDC — user's name/picture
        "https://www.googleapis.com/auth/gmail.readonly",  # API — authorization
    ],
)
```

After the flow completes:
- `credentials.id_token` — contains identity (`sub`, `email`, `name`)
- `credentials.token` — access token used to call Gmail API

---

## References

- [OpenID Connect Core 1.0 Specification](https://openid.net/specs/openid-connect-core-1_0.html)
- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749)
- [Google OAuth 2.0 Scopes](https://developers.google.com/identity/protocols/oauth2/scopes)
- [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)

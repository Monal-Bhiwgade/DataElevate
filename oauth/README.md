# Built-in Google sign-in: maintainer setup

DataElevate lets users open private Google Drive files by just signing in with Google.
For that, the app needs a **Desktop-app OAuth client**. Its config lives in this folder as
`gdrive-client.json`. It is **not** shipped in the PyPI package: installed copies fetch it
from

    https://raw.githubusercontent.com/Monal-Bhiwgade/DataElevate/main/oauth/gdrive-client.json

and cache it for 7 days. This lets you rotate the client at any time without a new release.

## Why this file is safe to be public

Google treats a Desktop-app client secret as **not confidential**: it cannot read anyone's
data by itself. Every user must still sign in and approve access, and their token stays on
their own machine (`~/.dataelevate/tokens/`). DataElevate only accepts a Desktop-app
(`"installed"`) config from this URL and refuses anything else, such as a service-account
key, which *would* be a real secret. A test enforces the same rule on this file.

**Never put a service-account key, refresh token or any user token in this folder.**

## One-time setup

1. Create a **new, dedicated** Google Cloud project (e.g. `dataelevate-signin`). Don't reuse
   the project behind the client that shipped in 1.0.7, and **delete that old client**.
2. APIs & Services → Library → enable **Google Drive API**.
3. APIs & Services → OAuth consent screen:
   - User type **External**, app name **DataElevate**, your support email.
   - Scopes: add only `https://www.googleapis.com/auth/drive.readonly`.
   - Publishing status: while in **Testing**, only test users you add can sign in (max 100).
4. APIs & Services → Credentials → Create credentials → **OAuth client ID** →
   Application type **Desktop app** → Download JSON.
5. Save it here as `oauth/gdrive-client.json`, commit, and push to `main`.

## Going beyond 100 users

`drive.readonly` is a **restricted** scope. Until Google verifies the app, users see a
"Google hasn't verified this app" screen and only 100 users in total can sign in. To lift
that, submit the consent screen for verification (Google requires a privacy policy, a
homepage, a demo video and, for restricted scopes, a security assessment). Users can
always bypass all of this by passing their own `credentials=` file.

## Rotating the client

If the client is abused or you need to replace it:

1. Create a new Desktop-app client (step 4) and replace `oauth/gdrive-client.json` on `main`.
2. Delete the old client in Google Cloud.

Installed copies pick up the new config within 7 days, or immediately when the old client
is rejected (DataElevate re-fetches on `deleted_client` / `invalid_client`). Users sign in
once more with the new client.

## Quotas

All built-in sign-ins share this project's Drive API quota. Check APIs & Services →
Google Drive API → Quotas occasionally, and set budget alerts on the project.

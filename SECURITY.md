# Security

## Reporting a vulnerability

Please email **3051monal@gmail.com** with details instead of opening a public issue.
You'll get a reply within a few days.

## Supported versions

Only the latest release receives fixes. Versions before 1.1.0 should not be used.

## How DataElevate handles credentials

- The package contains no credentials of any kind. A test fails the build if anything
  that looks like a secret is found in it.
- Google Drive: public links need no credentials. Private files use either the user's own
  OAuth client or service account, or the built-in sign-in. Access is always read-only, and
  sign-in tokens are stored only on the user's machine in `~/.dataelevate/tokens/` with
  owner-only permissions.
- The built-in sign-in uses a Desktop-app OAuth client, which Google treats as
  non-confidential. It is published in `oauth/gdrive-client.json`, not in the package, so it
  can be rotated without a release. DataElevate refuses any other kind of config from that
  location, and a test fails if that file ever holds anything but a Desktop-app client.
- Kaggle: handled by `kagglehub` using the user's own Kaggle API key.
- Databases: credentials are passed by the caller and only used to build the connection.
  Prefer reading passwords from environment variables rather than writing them in code.

# Security

## Reporting a vulnerability

Please email **3051monal@gmail.com** with details instead of opening a public issue.
You'll get a reply within a few days.

## Supported versions

Only the latest release receives fixes. Versions before 1.1.0 should not be used.

## How DataElevate handles credentials

- The package contains no credentials of any kind. A test fails the build if anything
  that looks like a secret is found in it.
- Google Drive: public links need no credentials. Private files use the user's own OAuth
  client or service account, with read-only access. Tokens are stored in
  `~/.dataelevate/tokens/` with owner-only permissions.
- Kaggle: handled by `kagglehub` using the user's own Kaggle API key.
- Databases: credentials are passed by the caller and only used to build the connection.
  Prefer reading passwords from environment variables rather than writing them in code.

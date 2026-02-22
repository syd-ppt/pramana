# Security Policy

## Scope

Pramana is a CLI tool that runs locally and submits results via HTTP POST. There is no server-side attack surface in this repository.

**In scope:** CLI code execution, dependency vulnerabilities, credential handling (API keys read from env vars).

**Out of scope:** The submission API backend (`pramana-api` repo), the dashboard (`pramana.pages.dev`).

## Reporting a Vulnerability

Report security issues via [GitHub Issues](https://github.com/syd-ppt/pramana/issues) with the `security` label.

For sensitive disclosures (e.g., credential leaks in published packages), email the maintainer directly. Contact information is in the GitHub profile of the repository owner.

## What to Include

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Suggested fix (if any)

## Response Timeline

- **Acknowledgment:** within 48 hours
- **Fix or mitigation:** within 7 days for critical issues

## Supported Versions

Only the latest release on PyPI is supported with security updates.

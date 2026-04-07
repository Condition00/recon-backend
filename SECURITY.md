# Security Policy

## Supported Versions

Recon Backend is an event-specific platform (VIT-AP, Apr 19–21). Only the latest version on `main` receives security patches.

| Branch   | Supported          |
| -------- | ------------------ |
| `main`   | :white_check_mark: |
| All others | :x:              |

## Reporting a Vulnerability

**Do not open a public issue for security vulnerabilities.**

Instead, report them privately:

1. **Email:** Send details to **recon2k26@gmail.com** with the subject line `[SECURITY] <brief description>`
2. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Affected endpoints or components
   - Potential impact
   - Suggested fix (if any)

### What to expect

- **Acknowledgement** within **24 hours**
- **Status update** within **72 hours** with severity assessment
- **Resolution** before the event (Apr 19) for critical/high severity issues
- Credit in the project (if desired) after the fix is deployed

### Scope

The following are **in scope**:

- Authentication/authorization bypasses (JWT, OAuth, RBAC)
- Participant data exposure (PII leaks via API responses or logs)
- Points economy manipulation (unauthorized point mutations, leaderboard tampering)
- NFC Lock Hunt state manipulation
- SQL injection, SSRF, or other injection attacks
- Redis key/pub-sub poisoning
- Presigned URL abuse (R2 storage)

The following are **out of scope**:

- CTFd vulnerabilities (separate platform — report to [CTFd](https://github.com/CTFd/CTFd/security))
- KOTH infrastructure (local VLAN, not this codebase)
- Luma registration/ticketing
- Rate limiting or DoS (not yet implemented)
- Issues requiring physical access to event infrastructure

## Security Design

For implementation details on how this backend handles auth, secrets, and data protection, see the **Security Rules** section in [`AGENTS.md`](./AGENTS.md).

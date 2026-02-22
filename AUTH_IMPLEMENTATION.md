# Authentication Implementation - Phase 2 (CLI)

## Summary

Implemented browser-based token authentication for the Pramana CLI. This allows users to link their submissions to their account for personalized feedback while maintaining anonymous mode as default.

## Changes Made

### New Files

1. **`src/pramana/auth.py`** - Authentication module
   - `login()` - Opens browser to get CLI token
   - `logout()` - Clears stored credentials
   - `whoami()` - Shows login status
   - `load_config()` / `save_config()` - Config persistence
   - `get_auth_header()` - Returns Authorization header if logged in
   - `get_api_url()` - Returns configured API URL

2. **`tests/test_auth.py`** - Comprehensive auth tests
   - Config save/load tests
   - Auth header generation tests
   - Login/logout flow tests

### Modified Files

1. **`src/pramana/cli.py`**
   - Added `pramana login [--api-url URL]` command
   - Added `pramana logout` command
   - Added `pramana whoami` command
   - Updated `pramana submit` to use configured API URL from login

2. **`src/pramana/submitter.py`**
   - Added Authorization header to requests when logged in
   - Maintains backward compatibility for anonymous submissions

3. **`src/pramana/protocol.py`** (already done)
   - Added `user_id: str | None` field
   - Added `is_authenticated: bool` field

## Usage

### Anonymous Mode (Default - No Changes)

```bash
# Works exactly as before
pramana run --tier cheap --model gpt-4
pramana submit results.json
# → Submitted as anonymous
```

### Authenticated Mode

```bash
# 1. Login (one-time setup)
pramana login
# → Opens https://pramana.pages.dev/cli-token in browser
# → User signs in with GitHub/Google (OAuth handled by API)
# → User copies token and pastes in terminal
# ✓ Logged in! Your submissions will now be linked to your account.

# 2. Check login status
pramana whoami
# Logged in (token: abc123def456...)
# API URL: https://pramana.pages.dev

# 3. Submit with authentication
pramana run --tier cheap --model gpt-4
pramana submit results.json
# → Submitted with user_id (extracted from JWT by API)

# 4. Logout
pramana logout
# ✓ Logged out
```

### Custom API URL

```bash
# For development or self-hosted instances
pramana login --api-url https://localhost:8000
pramana submit results.json --api-url https://localhost:8000
```

## Configuration Storage

- **Location**: `~/.pramana/config.json`
- **Format**:
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "api_url": "https://pramana.pages.dev"
  }
  ```
- **Security**: Config file is stored in user's home directory (not in repo)
- **Deletion**: `pramana logout` removes the config file

## Architecture

### Separation of Concerns

**CLI (Public Repo)** - NO OAuth secrets:
- Only handles token storage and HTTP headers
- Opens browser for user to authenticate
- Token is copy/pasted by user (browser-based flow)

**API (Private Repo)** - All OAuth logic:
- NextAuth.js handles GitHub/Google OAuth
- JWT token generation and validation
- User ID extraction from JWT
- All OAuth client secrets stored in Vercel environment

### Security Model

1. **No secrets in CLI**: Public repo contains no OAuth credentials
2. **JWT-based auth**: Tokens are signed JWTs (validated by API)
3. **Bearer token**: Standard HTTP Authorization header
4. **User control**: User explicitly logs in/out

## Testing

```bash
# Run auth tests
pytest tests/test_auth.py -v

# Manual testing
pramana login
pramana whoami
pramana logout
```

## Next Steps (Private API Repo)

The following needs to be implemented in the `pramana-api` private repository:

1. **NextAuth.js setup** (`/api/auth/[...nextauth]/route.ts`)
   - GitHub + Google OAuth providers
   - JWT session strategy (no database)
   - User ID hashing from OAuth provider ID

2. **Token display page** (`/app/cli-token/page.tsx`)
   - Shows JWT token for CLI use
   - Copy button for easy token transfer

3. **API validation** (`/api/routes/submit.py`)
   - JWT validation middleware
   - User ID extraction from token
   - Storage partitioning by user_id

4. **Personalized dashboard** (`/app/my-stats/page.tsx`)
   - "You vs Crowd" statistics
   - Aggregation filtered by user_id

5. **GDPR compliance** (`/api/routes/user.py`)
   - `DELETE /user/me` endpoint
   - Data deletion by user_id partition

## Backward Compatibility

✅ **Anonymous mode still works** - No breaking changes
- If not logged in, `get_auth_header()` returns `None`
- API treats missing Authorization header as anonymous
- Existing scripts and workflows unchanged

## Cost Impact

**$0** - No additional costs:
- No new dependencies (uses standard library)
- No database needed (JWT-only)
- Config stored locally
- All OAuth costs handled by free tier services (GitHub, Google, NextAuth.js, Vercel)

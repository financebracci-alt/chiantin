# Auth Router Extraction Plan

**Document Type:** Planning-Only (NO CODE CHANGES)  
**Version:** 1.0  
**Date:** December 2025  
**Author:** Automated Analysis  
**Status:** DRAFT - Awaiting Approval

---

## 1. Scope & Constraints

### 1.1 Planning-Only Mandate
This document is a **planning-only deliverable**. No code changes, route modifications, or schema alterations will be made during this planning phase.

### 1.2 Explicit Exclusions
- **P1 Transfer Restore Feature:** Explicitly deferred - no transfer-related logic to be touched
- **Non-auth business logic:** No banking, KYC, tickets, or ledger operations to be modified
- **Database schema changes:** No MongoDB collection structure changes

### 1.3 Extraction Goals
- Move all authentication endpoints from `server.py` to `backend/routers/auth.py`
- Maintain 100% behavioral parity (routes, status codes, response formats, error messages)
- Zero downtime during deployment
- Preserve existing test coverage

---

## 2. Auth Endpoint Inventory

### 2.1 Complete Auth Endpoint List

| # | Route | Method | Line # | Purpose | Access |
|---|-------|--------|--------|---------|--------|
| 1 | `/api/v1/auth/signup` | POST | 300 | User registration + email verification | Public |
| 2 | `/api/v1/auth/login` | POST | 390 | Email/password authentication + MFA + session | Public |
| 3 | `/api/v1/auth/logout` | POST | 544 | Session termination + cookie clearing | Authenticated |
| 4 | `/api/v1/auth/verify-email` | POST | 587 | Email verification via token | Public |
| 5 | `/api/v1/auth/resend-verification` | POST | 655 | Resend verification email | Public |
| 6 | `/api/v1/auth/me` | GET | 712 | Get current user info | Authenticated |
| 7 | `/api/v1/auth/mfa/setup` | POST | 737 | Generate MFA QR code | Authenticated |
| 8 | `/api/v1/auth/mfa/enable` | POST | 748 | Enable MFA after verification | Authenticated |
| 9 | `/api/v1/auth/change-password` | POST | 765 | Change password (with current password) | Authenticated |
| 10 | `/api/v1/auth/verify-password` | POST | 819 | Verify password for sensitive operations | Authenticated |
| 11 | `/api/v1/auth/forgot-password` | POST | 867 | Request password reset email | Public |
| 12 | `/api/v1/auth/reset-password` | POST | 909 | Reset password using token | Public |

### 2.2 Endpoint Classification

**Public Endpoints (No Auth Required):**
- signup, login, verify-email, resend-verification, forgot-password, reset-password

**Protected Endpoints (Auth Required - `get_current_user`):**
- logout, me, mfa/setup, mfa/enable, change-password, verify-password

### 2.3 Line Range in server.py
- **Start:** Line 271 (SignupRequest class definition)
- **End:** Line 976 (end of reset-password return statement)
- **Total Lines:** ~705 lines of auth-related code

---

## 3. Dependency Map

### 3.1 Database/Session Dependencies

| Dependency | Type | Used In | Notes |
|------------|------|---------|-------|
| `db.users` | Collection | All endpoints | User lookup, creation, updates |
| `db.email_verifications` | Collection | signup, verify-email, resend-verification | Token storage |
| `db.password_resets` | Collection | forgot-password, reset-password | Reset token storage |
| `db.sessions` | Collection | change-password, reset-password | Session revocation |
| `db.audit_logs` | Collection | login, logout, verify-email | Security audit trail |

### 3.2 Auth Helpers (Currently in server.py)

| Helper | Line # | Used By | Action |
|--------|--------|---------|--------|
| `get_current_user()` | 218-261 | logout, me, mfa/*, change-password, verify-password | **ALREADY EXISTS in dependencies.py** - Use existing |
| `require_admin()` | 264-268 | N/A for auth routes | **ALREADY EXISTS in dependencies.py** |
| `create_audit_log()` | 67-98 | login, logout, verify-email | **ALREADY EXISTS in dependencies.py** - Use existing |
| `security = HTTPBearer()` | 63 | get_current_user | **ALREADY EXISTS in dependencies.py** |
| `format_timestamp_utc()` | 23-35 | Various | **ALREADY EXISTS in dependencies.py** |

### 3.3 Request/Response Schemas

| Schema | File | Used By | Action |
|--------|------|---------|--------|
| `UserCreate` | schemas/users.py | signup | Keep as-is (external) |
| `UserLogin` | schemas/users.py | login | Keep as-is (external) |
| `UserResponse` | schemas/users.py | signup, login, me | Keep as-is (external) |
| `TokenResponse` | schemas/users.py | login | Keep as-is (external) |
| `MFASetupResponse` | schemas/users.py | mfa/setup | Keep as-is (external) |
| `MFAVerifyRequest` | schemas/users.py | mfa/enable | Keep as-is (external) |
| `ResendVerificationRequest` | schemas/users.py | resend-verification | Keep as-is (external) |
| `VerifyEmailRequest` | schemas/users.py | verify-email | Keep as-is (external) |
| `SignupRequest` | server.py:273-298 | signup | **MOVE to schemas/users.py** |
| `PasswordChangeRequest` | server.py:760-762 | change-password | **MOVE to schemas/users.py** |
| `VerifyPasswordRequest` | server.py:815-816 | verify-password | **MOVE to schemas/users.py** |
| `ForgotPasswordRequest` | server.py:856-858 | forgot-password | **MOVE to schemas/users.py** |
| `ResetPasswordRequest` | server.py:862-864 | reset-password | **MOVE to schemas/users.py** |

### 3.4 Service Dependencies

| Service | Import Path | Used By | Coupling |
|---------|-------------|---------|----------|
| `AuthService` | services/auth_service.py | signup, login, me, mfa/* | **HIGH** - Core dependency |
| `EmailService` | services/email_service.py | signup, resend-verification, forgot-password | **MEDIUM** |

### 3.5 Core/Auth Dependencies

| Module | Import Path | Used By | Notes |
|--------|-------------|---------|-------|
| `hash_password` | core/auth | signup (via service), change-password, reset-password | Direct import in server.py |
| `verify_password` | core/auth | change-password, verify-password | Direct import in server.py |
| `JWTHandler` | core/auth/jwt_handler.py | Used via AuthService | Indirect |
| `TOTPHandler` | core/auth/totp_handler.py | Used via AuthService | Indirect |

### 3.6 Config/Environment Dependencies

| Config | Source | Used By | Criticality |
|--------|--------|---------|-------------|
| `settings.SECRET_KEY` | config.py | JWT decode in get_current_user | **CRITICAL** |
| `settings.JWT_ALGORITHM` | config.py | JWT decode | HIGH |
| `settings.DEBUG` | config.py | Cookie secure flag | HIGH |
| `settings.REFRESH_TOKEN_EXPIRE_DAYS` | config.py | Cookie max_age | HIGH |
| `settings.FRONTEND_URL` | config.py | Via EmailService | MEDIUM |

### 3.7 Cookie Configuration

| Setting | Value | Location | Notes |
|---------|-------|----------|-------|
| Cookie key | `refresh_token` | login (set), logout (delete) | Fixed value |
| httponly | `True` | login | Security requirement |
| secure | `not settings.DEBUG` | login | Env-dependent |
| samesite | `"lax"` | login | CSRF protection |
| max_age | `REFRESH_TOKEN_EXPIRE_DAYS * 86400` | login | Config-dependent |

---

## 4. Risk Register

### 4.1 Critical Risks (P0)

| ID | Risk | Impact | Likelihood | Mitigation | Rollback Trigger |
|----|------|--------|------------|------------|------------------|
| R1 | **Circular import: auth.py ↔ dependencies.py** | Server fails to start | HIGH | Import inside function or restructure deps | Import error on startup |
| R2 | **get_current_user duplication** | Different auth behavior between routes | HIGH | Remove duplicate from server.py, use dependencies.py version ONLY | Any 401 inconsistency |
| R3 | **Cookie settings break** | Session/auth completely broken | CRITICAL | Test login flow end-to-end immediately after extraction | Login succeeds but frontend fails |
| R4 | **JWT algorithm mismatch** | Token validation fails | HIGH | Verify settings.JWT_ALGORITHM is consistent | All protected routes return 401 |

### 4.2 High Risks (P1)

| ID | Risk | Impact | Likelihood | Mitigation | Rollback Trigger |
|----|------|--------|------------|------------|------------------|
| R5 | **Missing audit logs** | Compliance violation, security gap | MEDIUM | Verify create_audit_log is called correctly | No audit entries for auth actions |
| R6 | **Schema import path breaks** | 500 errors on affected endpoints | MEDIUM | Test all endpoints individually | Any endpoint returns 500 |
| R7 | **ObjectId handling inconsistent** | User lookup fails for some users | MEDIUM | Keep identical try/except pattern | 401 for some users, not others |
| R8 | **Email service failures masked** | Users don't receive verification emails | LOW | Maintain try/except pattern from original | User complaints of no emails |

### 4.3 Medium Risks (P2)

| ID | Risk | Impact | Likelihood | Mitigation | Rollback Trigger |
|----|------|--------|------------|------------|------------------|
| R9 | **Response format changes** | Frontend parsing errors | LOW | Compare JSON responses byte-by-byte | Frontend console errors |
| R10 | **HTTP status code changes** | Frontend flow breaks | LOW | Document and verify each status code | Wrong UI behavior |
| R11 | **Validation behavior changes** | User-facing error messages differ | LOW | Test edge cases with invalid input | Different error messages |

### 4.4 Risk Decision Matrix

```
LIKELIHOOD →
              LOW         MEDIUM       HIGH
         ┌────────────┬────────────┬────────────┐
   HIGH  │  R10       │  R5        │  R1, R2    │
IMPACT   ├────────────┼────────────┼────────────┤
         │  R11       │  R6, R7    │  R4        │
 MEDIUM  ├────────────┼────────────┼────────────┤
         │  R9        │  R8        │            │
   LOW   └────────────┴────────────┴────────────┘
                                   
CRITICAL:  R3 (Cookie settings break) - REQUIRES IMMEDIATE ROLLBACK IF TRIGGERED
```

---

## 5. Safe Extraction Sequence

### Phase 0: Pre-Extraction Prep (LOW RISK)

**Step 0.1:** Move inline Pydantic models to schemas/users.py
- Move: `SignupRequest`, `PasswordChangeRequest`, `VerifyPasswordRequest`, `ForgotPasswordRequest`, `ResetPasswordRequest`
- **Verification:** Import in server.py still works, all routes respond
- **Commit boundary:** YES - "Move auth schemas to schemas/users.py"

### Phase 1: Create Auth Router File (ZERO RISK)

**Step 1.1:** Create `/app/backend/routers/auth.py` with router definition only
```python
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
```
- **Verification:** Backend starts, no routes registered yet
- **Commit boundary:** YES - "Create empty auth router"

### Phase 2: Extract ONE Endpoint (LOW RISK)

**Step 2.1:** Extract `/api/v1/auth/me` endpoint (simplest protected route)
- Copy endpoint code to auth.py
- Add necessary imports
- Register router in server.py
- Comment out (DO NOT DELETE) original in server.py
- **Verification:** 
  - `GET /api/v1/auth/me` returns user data
  - Verify with real login token
- **Commit boundary:** YES - "Extract /auth/me to auth router"

### Phase 3: Extract Public Read-Only Endpoints (MEDIUM RISK)

**Step 3.1:** Extract `/api/v1/auth/verify-email`
- **Verification:** Test with real verification token
- **Commit boundary:** YES

**Step 3.2:** Extract `/api/v1/auth/resend-verification`
- **Verification:** Call endpoint, check email is sent
- **Commit boundary:** YES

### Phase 4: Extract MFA Endpoints (MEDIUM RISK)

**Step 4.1:** Extract `/api/v1/auth/mfa/setup`
- **Verification:** Get QR code URI response
- **Commit boundary:** YES

**Step 4.2:** Extract `/api/v1/auth/mfa/enable`
- **Verification:** Test MFA enable flow (if test account has MFA secret)
- **Commit boundary:** YES

### Phase 5: Extract Password Management (HIGH RISK)

**Step 5.1:** Extract `/api/v1/auth/verify-password`
- **Verification:** Test with correct and incorrect passwords
- **Commit boundary:** YES

**Step 5.2:** Extract `/api/v1/auth/change-password`
- **Verification:** Change password, verify old one no longer works
- **Commit boundary:** YES

**Step 5.3:** Extract `/api/v1/auth/forgot-password`
- **Verification:** Request reset, check email
- **Commit boundary:** YES

**Step 5.4:** Extract `/api/v1/auth/reset-password`
- **Verification:** Use reset token, verify login with new password
- **Commit boundary:** YES

### Phase 6: Extract Critical Auth Endpoints (CRITICAL RISK)

**Step 6.1:** Extract `/api/v1/auth/logout`
- **Verification:** 
  - Cookie is cleared
  - Audit log created
- **Commit boundary:** YES

**Step 6.2:** Extract `/api/v1/auth/signup`
- **Verification:**
  - New user created in DB
  - Verification email sent
  - Response matches schema
- **Commit boundary:** YES

**Step 6.3:** Extract `/api/v1/auth/login` (HIGHEST RISK - LAST)
- **Verification:**
  - Login succeeds with valid credentials
  - Login fails with invalid credentials (same error format)
  - MFA flow works
  - Disabled account blocked
  - Unverified email blocked
  - Cookie set correctly
  - Audit log created
  - Token returned in response
- **Commit boundary:** YES - "Extract /auth/login to auth router"

### Phase 7: Cleanup (LOW RISK)

**Step 7.1:** Remove commented-out code from server.py
- **Verification:** All tests still pass
- **Commit boundary:** YES - "Remove migrated auth code from server.py"

**Step 7.2:** Update `routers/__init__.py` exports
- **Commit boundary:** YES

---

## 6. Regression Test Checklist

### 6.1 Pre-Extraction Baseline (Run Before ANY Changes)
```
[ ] All existing backend tests pass
[ ] Manual login with test account succeeds
[ ] Admin login with admin account succeeds
[ ] Capture response JSONs for all 12 auth endpoints
```

### 6.2 Per-Endpoint Verification

#### Login Flow Tests
```
[ ] Valid credentials → 200 + token + user data
[ ] Invalid email → 401 "Invalid credentials"
[ ] Invalid password → 401 "Invalid credentials"
[ ] Disabled account → 403 "Account is disabled. Please contact support."
[ ] Unverified email → 403 "EMAIL_NOT_VERIFIED"
[ ] MFA required (no token) → 401 "MFA token required"
[ ] MFA invalid token → 401 "Invalid MFA token"
[ ] MFA valid token → 200 + token
[ ] Refresh token cookie is set (httponly, samesite=lax)
[ ] Audit log created for success/failure
```

#### Logout Flow Tests
```
[ ] Valid token → 200 + cookie cleared
[ ] Invalid token → 401
[ ] Audit log created
```

#### Session/Token Tests
```
[ ] GET /auth/me with valid token → 200 + user data
[ ] GET /auth/me with expired token → 401 "Token expired"
[ ] GET /auth/me with invalid token → 401 "Invalid token"
[ ] GET /auth/me with missing token → 403 (FastAPI default)
```

#### MFA Tests
```
[ ] POST /auth/mfa/setup → 200 + secret + qr_code_uri
[ ] POST /auth/mfa/enable with valid token → 200
[ ] POST /auth/mfa/enable with invalid token → 400
```

#### Password Tests
```
[ ] POST /auth/verify-password correct → 200
[ ] POST /auth/verify-password incorrect → 401
[ ] POST /auth/change-password correct → 200 + sessions revoked
[ ] POST /auth/change-password wrong current → 400
[ ] POST /auth/change-password short new → 400
[ ] POST /auth/forgot-password existing email → 200 (+ email sent)
[ ] POST /auth/forgot-password non-existing → 200 (no email)
[ ] POST /auth/reset-password valid token → success
[ ] POST /auth/reset-password invalid token → 400
[ ] POST /auth/reset-password expired token → 400
```

#### Signup Flow Tests
```
[ ] Valid data → 201 + user created + email sent
[ ] Duplicate email → 400 "Email already registered"
[ ] Invalid email format → 422 validation error
[ ] Short password → 422 validation error
[ ] Missing phone → 422 validation error
```

#### Email Verification Tests
```
[ ] Valid token → 200 + email_verified=true
[ ] Used token → 400
[ ] Expired token → 400
[ ] Resend → 200 + new email sent
```

### 6.3 Frontend Smoke Tests
```
[ ] Login page loads
[ ] Login with test account succeeds → redirects to dashboard
[ ] Admin login succeeds → redirects to admin panel
[ ] Logout clears session
[ ] Protected pages redirect to login when not authenticated
[ ] Error messages display correctly for failed login
```

### 6.4 RBAC Verification
```
[ ] CUSTOMER cannot access admin routes
[ ] ADMIN can access admin routes
[ ] SUPER_ADMIN can access all routes
[ ] COMPLIANCE_OFFICER has correct permissions
[ ] FINANCE_OPS has correct permissions
```

---

## 7. Production Monitoring Additions (Auth-Specific)

### 7.1 Metrics to Monitor

| Metric | Alert Threshold | Severity |
|--------|-----------------|----------|
| Login failure rate (5min window) | > 10% of total logins | WARNING |
| Login failure rate (5min window) | > 25% of total logins | CRITICAL |
| Auth endpoint 4xx rate | > 5% increase from baseline | WARNING |
| Auth endpoint 5xx rate | ANY 5xx errors | CRITICAL |
| `/auth/login` p95 latency | > 2000ms | WARNING |
| `/auth/login` p95 latency | > 5000ms | CRITICAL |
| Token validation failures | > 5/min sustained | WARNING |
| MFA failures | > 10 consecutive failures | WARNING |

### 7.2 Rollback Trigger Thresholds

| Condition | Action |
|-----------|--------|
| ANY 500 error on `/auth/login` | IMMEDIATE ROLLBACK |
| > 50% login failures for 2 minutes | IMMEDIATE ROLLBACK |
| Any "Invalid token" spike (10x normal) | INVESTIGATE, ROLLBACK if confirms |
| Cookie not being set (client reports) | IMMEDIATE ROLLBACK |
| Session not persisting | IMMEDIATE ROLLBACK |

### 7.3 Post-Deploy Smoke Steps

**Immediately After Deploy (within 2 minutes):**
1. `curl -X POST $API/auth/login` with test credentials - expect 200
2. Verify cookie is set in response headers
3. `curl -X GET $API/auth/me` with returned token - expect 200
4. Check backend logs for any ERROR entries
5. Check audit_logs collection for new login entry

**5 Minutes After Deploy:**
1. Full frontend login flow with test account
2. Full admin login flow
3. Check monitoring dashboards for anomalies

**15 Minutes After Deploy:**
1. Compare login success rate to pre-deploy baseline
2. Review any support tickets or user complaints
3. Sample audit logs for correct formatting

---

## 8. Commit-Based Rollback Plan

### 8.1 Rollback Procedure

**If issues detected during extraction:**

```bash
# Step 1: Identify last known good commit
git log --oneline -10

# Step 2: Revert to previous commit
git revert HEAD

# Step 3: Restart backend
sudo supervisorctl restart backend

# Step 4: Verify health
curl $API/health

# Step 5: Test login flow
curl -X POST $API/auth/login -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"testpass"}'
```

### 8.2 Granular Revert by Phase

| Phase | Revert Command | Post-Revert Test |
|-------|----------------|------------------|
| Phase 7 | `git revert HEAD` | All tests pass |
| Phase 6.3 | `git revert HEAD~1` | Login flow works |
| Phase 6.2 | `git revert HEAD~2` | Signup flow works |
| Phase 6.1 | `git revert HEAD~3` | Logout flow works |
| Earlier | Continue reverting | Verify each endpoint |

### 8.3 Emergency Full Rollback

```bash
# Nuclear option: Revert ALL auth extraction commits
git log --oneline | grep -E "(auth|Auth)" 
git revert <first-auth-commit>..<latest-auth-commit>
sudo supervisorctl restart backend
```

---

## 9. Recommendation / Go-No-Go

### 9.1 Analysis Summary

| Factor | Assessment |
|--------|------------|
| Code coupling | **MODERATE** - Auth helpers already in dependencies.py |
| Schema coupling | **LOW** - Most schemas already external |
| Risk level | **MEDIUM-HIGH** - Login/session are critical paths |
| Test coverage | **GOOD** - Existing test suite covers auth |
| Rollback capability | **EXCELLENT** - Granular commit boundaries |

### 9.2 Go/No-Go Decision

**RECOMMENDATION: GO** - Auth extraction can be safely performed in one focused session, following the phased approach.

**Rationale:**
1. **Auth helpers already extracted:** `get_current_user`, `require_admin`, `create_audit_log` already exist in `dependencies.py` - this eliminates the #1 circular import risk
2. **Schemas mostly external:** Only 5 small Pydantic models need to move
3. **Clear extraction pattern:** Previous router extractions (tickets, kyc, admin_users) provide a proven template
4. **Strong rollback capability:** Commit-per-endpoint enables surgical rollback

### 9.3 Pre-Implementation Requirements

Before starting implementation:

1. **Run full test suite** - Capture baseline
2. **Capture all auth endpoint responses** - JSON snapshots for comparison
3. **Verify dependencies.py has all needed functions** - Confirm no duplication needed
4. **Set up monitoring alerts** - Pre-configure rollback triggers
5. **Communicate maintenance window** - If any, though this should be zero-downtime

### 9.4 Recommended Implementation Order

1. **First step in actual implementation:** Move 5 inline Pydantic schemas to `schemas/users.py` (lowest risk, unblocks everything)
2. **Second:** Create empty `routers/auth.py` and register it
3. **Third:** Extract `/auth/me` as proof-of-concept
4. **Then:** Follow Phase 3-6 in order, with `/auth/login` LAST

### 9.5 What Should NOT Be Done

- **DO NOT** copy `get_current_user` into auth.py - import from dependencies.py
- **DO NOT** modify JWT algorithm or secret key handling
- **DO NOT** change cookie configuration values
- **DO NOT** alter error message text (frontend may depend on exact strings)
- **DO NOT** change HTTP status codes
- **DO NOT** combine multiple endpoint extractions in one commit

---

## Appendix A: Current File Statistics

| File | Lines | Auth-Related Lines |
|------|-------|-------------------|
| server.py | 3227 | ~705 (22%) |
| services/auth_service.py | 178 | 178 (100%) |
| routers/dependencies.py | 134 | 98 (73%) |
| schemas/users.py | 154 | 154 (100%) |
| core/auth/* | ~200 | 200 (100%) |

**Post-Extraction Projection:**
- server.py: ~2522 lines (22% reduction)
- routers/auth.py: ~400 lines (new)
- schemas/users.py: ~180 lines (+26 lines for moved schemas)

---

## Appendix B: Test Account for Verification

**Test User:**
- Email: `ashleyalt005@gmail.com`
- Password: `123456789`
- Role: Customer + Admin access

**Testing Guidelines:**
- Use ONLY this test account for all verification
- Do NOT create test data that could affect real users
- Do NOT test with any other email addresses

---

## Appendix C: Related Documentation

- `/app/memory/MONITORING_PLAN.md` - General monitoring guidance
- `/app/memory/PRD.md` - Product requirements
- `/app/test_reports/` - Historical test results

---

**END OF DOCUMENT**

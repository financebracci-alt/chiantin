# ECOMMBX Banking Platform - PRD

## Original Problem Statement
Full-stack banking application with KYC, transfers, admin panel, and notification systems.

## Current Status: STABLE (Ready for Production Deploy)

## What's Been Implemented

### Core Features
- User authentication (signup, login, MFA)
- KYC application submission and admin review
- Banking transfers with admin queue
- Support ticket system
- Tax hold management
- Admin notification badge system (database-backed)
- Admin ledger operations (credit/debit accounts)
- User login activity history
- Client transaction history with professional banking details
- **Admin Create User** - Admins can create users directly with IBAN assignment (NEW)

### Recent Features (March 2026)
1. **Admin Create User Feature** - Complete implementation allowing admins to:
   - Create users with first name, last name, email, phone, password
   - Assign custom IBAN and BIC to the bank account
   - Option to skip KYC (auto-approve) or require user to complete KYC
   - User is immediately ACTIVE with email_verified=true (no verification email sent)
   - Backend: POST /api/v1/admin/users/create
   - Frontend: Create User button + modal on Admin Users page

### Recent Hotfixes (February 2026)
1. **KYC Admin Review Actions** - Fixed API contract mismatch
2. **Client KYC Submission** - Fixed endpoint routing
3. **Tax Hold Restrictions** - Restored frontend/backend enforcement
4. **Admin Panel UI Overflow** - Fixed CSS layout issues
5. **Admin Sidebar Badges** - Verified working, fixed KYC status query
6. **Admin Credit Account Blank Page** - Fixed amount→amount_cents field mismatch
7. **Login Activity Panel Empty** - Fixed to query audit_logs instead of auth_events
8. **Client Transaction Rendering** - Fixed admin credit/debit metadata storage for proper display

## Architecture

### Backend (FastAPI)
```
/app/backend/
├── server.py              # Main FastAPI app
├── routers/
│   ├── auth.py            # Authentication
│   ├── kyc.py             # KYC flows
│   ├── admin_users.py     # Admin user management + auth history + CREATE USER
│   ├── notifications.py   # Badge system
│   ├── accounts.py        # Ledger operations with professional metadata
│   ├── transfers.py       # Banking transfers
│   ├── tickets.py         # Support system
│   └── cards.py           # Card requests
├── services/
│   ├── kyc_service.py     # KYC business logic
│   └── ledger_service.py  # Ledger/transaction engine
└── utils/
    └── dependencies.py    # Auth & tax hold checks
```

### Frontend (React)
```
/app/frontend/src/
├── App.js                 # Main app with routing
├── components/
│   ├── AdminLayout.js     # Admin sidebar + badges
│   ├── AdminLedger.js     # Credit/Debit forms
│   ├── AdminUserDetails.js # User details + login activity
│   ├── AdminUsersPage.js  # User list + CREATE USER modal (UPDATED)
│   ├── ProfessionalDashboard.js # Client dashboard with transaction history
│   ├── KYC.js             # Client KYC flow
│   └── Admin/             # Admin pages
└── styles/
    └── AdminLayout.css
```

### Database (MongoDB)
- Collections: users, kyc_applications, transfers, tickets, admin_section_views, tax_holds, bank_accounts, ledger_accounts, ledger_entries, ledger_transactions, audit_logs

## Key API Endpoints
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/kyc/submit` - Submit KYC
- `POST /api/v1/admin/kyc/{id}/review` - Review KYC
- `GET /api/v1/admin/notification-counts` - Badge counts
- `POST /api/v1/admin/accounts/{id}/topup` - Credit account (with professional metadata)
- `POST /api/v1/admin/accounts/{id}/withdraw` - Debit account (with professional metadata)
- `GET /api/v1/accounts/{id}/transactions` - Client transaction history
- `GET /api/v1/admin/users/{id}/auth-history` - User login history
- `GET /api/v1/admin/audit-logs` - All audit logs

## Transaction Metadata Structure
### Credit (Top Up)
```json
{
  "display_type": "Bank Transfer",
  "sender_name": "ACME Corporation",
  "sender_iban": "FR7630006000011234567890189",
  "sender_bic": "AGRIFRPP",
  "reference": "INV-2026-001",
  "description": "Payment received",
  "status": "POSTED"
}
```

### Debit (Withdraw)
```json
{
  "display_type": "SEPA Transfer",
  "recipient_name": "John Smith",
  "to_iban": "GB29NWBK60161331926819",
  "reference": "PAY-OUT-2026",
  "description": "Outgoing payment",
  "status": "POSTED"
}
```

## Test Credentials
- **Admin:** admin@ecommbx.io / Admin@123456
- **Client:** ashleyalt005@gmail.com / 123456789

## Third-Party Integrations
- Resend (emails)
- Cloudinary (file storage)

## Deployment Notes
- Production URL: https://ecommbx.group
- Backend port: 8001
- Frontend port: 3000
- User needs to shut down old deployment first, then deploy from current task

## Known Issues
- None currently blocking

## Backlog / Future Tasks
- Mobile KYC ghost text issue (could not reproduce - needs user screenshots)
- Performance optimization for large user lists
- Cloudinary raw file handling: Consider migrating old raw files to include proper Content-Disposition headers

## Latest Changes (March 9, 2026)
### P0 Fix: PDF/Document Download from Support Tickets
- **Problem:** Non-image files (PDFs, docs) downloaded from support tickets were corrupted/saved without file extension
- **Root Cause:** Previous fix added file extensions to Cloudinary raw file public_ids, but this Cloudinary account has strict delivery settings that block raw files with extensions in URL (401 ACL failure). Old files without extensions in URL worked fine.
- **Fix (Backend):** Reverted `cloudinary_storage.py` to always strip extension from public_id for all file types. Cloudinary URL returned from upload is used as-is (without appending extension).
- **Fix (Frontend):** Blob-based download handler in `Support.js` fetches the raw URL, creates a Blob, and triggers download with `att.file_name` (which has the correct extension). This ensures the saved file has the proper extension regardless of what Cloudinary's Content-Disposition says.
- **Files Modified:** `backend/providers/cloudinary_storage.py`, `frontend/src/components/Support.js`
- **Testing:** Verified via testing agent (iteration_158) — all tests passed

### Feature: Inline File Viewing in Support Tickets (March 9, 2026)
- **Requirement:** Clicking a file name opens the file inline in a new tab (e.g., PDF in browser PDF viewer), while the download button saves the file
- **Problem:** Cloudinary raw files are served with `Content-Disposition: attachment`, forcing browser to download instead of display
- **Fix (Backend):** Added proxy endpoint `GET /api/v1/tickets/view-file` that fetches from Cloudinary and serves with `Content-Disposition: inline` and correct `Content-Type`. Security: only proxies from configured Cloudinary account, requires auth.
- **Fix (Frontend):** Changed file name link from `<a href>` to `<button>` with `handleViewFile` handler that fetches via proxy as blob and opens `blob:` URL in new tab. Images still open directly from Cloudinary.
- **Files Modified:** `backend/routers/tickets.py` (new endpoint at line 95), `frontend/src/components/Support.js` (handleViewFile handler)
- **Testing:** Verified via testing agent (iteration_159) — 100% pass rate on all 11 backend + all frontend tests

## Previous Changes (Feb 25, 2026)
- Fixed client transaction history rendering for admin-created credits/debits
- Root cause: Admin topup/withdraw not passing professional banking fields as metadata
- Now properly displays From/To names, IBANs, BIC, references in transaction detail modals

## Verification Log (Feb 25, 2026)
### Transaction Detail Modal Bug - NOT REPRODUCIBLE
- **Reported Issue:** Transaction detail modal not opening for old transactions on full history page
- **Test Results:** All 47 transactions tested (index 0, 10, 20, 46) - modal opens correctly for all
- **Testing Agent:** iteration_148 - 100% pass rate
- **Manual Verification:** Screenshot confirmed modal opens with transaction details
- **Conclusion:** Bug was either already fixed or was intermittent/browser-specific

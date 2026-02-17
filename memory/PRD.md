# ecommbx Banking Platform - Product Requirements Document

## Overview
ecommbx is a full-stack EU-licensed digital banking platform built with React frontend, FastAPI backend, and MongoDB database.

## Core Features
- User authentication (JWT)
- Bank accounts with ledger-based balance tracking
- P2P transfers
- Admin panel for user management
- KYC management
- Tax hold management
- Multi-language support (English, Italian)
- Balance visibility toggle
- **EU Currency Formatting (dot for thousands, comma for decimals)**
- **Professional Banking Transaction Display (colored status badges)**
- **Support Ticket File Attachments (clients and admins)**

## Technical Stack
- **Frontend:** React.js with TailwindCSS
- **Backend:** FastAPI (Python)
- **Database:** MongoDB
- **Authentication:** JWT tokens
- **Email:** Resend API
- **File Storage:** Cloudinary (for KYC docs and ticket attachments)

## Recent Changes (February 2025)

### Admin Dashboard Analytics Fix (Feb 17, 2025)
**Problem:** Admin Dashboard Overview page was showing all zeros for statistics (Total Users, Active Users, Pending KYC, Transactions).

**Root Cause:** `Analytics.js` was calling `/admin/users` expecting an array response, but the endpoint was enhanced with pagination and now returns `{users: [...], pagination: {...}}`. The code `users.length` and `users.filter()` failed on the object.

**Solution:**
- Updated `Analytics.js` to use the existing `/admin/analytics/overview` endpoint which provides aggregated stats
- Enhanced the backend endpoint to include:
  - `kyc.approved` count
  - `transfers.volume_cents` for total transaction volume
- Added 5th KPI card showing Total Volume in EU format (€29.257.373,54)

**Files Changed:**
- `/app/frontend/src/components/Analytics.js` - Updated `fetchAnalytics()` to use analytics/overview endpoint
- `/app/backend/server.py` - Enhanced `get_admin_analytics_overview()` with approved KYC and volume aggregation

**Verification:** 100% test pass rate (iteration_75.json) - All 5 stat tiles display correct values, all 4 charts render correctly

### Admin Accounts Tab - Real Balances, Search & Pagination (Feb 17, 2025)
**Problem:** 
1. Account balances showing €0,00 for all accounts
2. No search functionality
3. No pagination - all accounts shown in one page

**Root Cause:** The `/admin/accounts-with-users` endpoint was returning `balance_in_cents` from the bank_accounts collection, but this is a ledger-based system where **real balances must be calculated from ledger entries**.

**Solution:**
- Updated backend to calculate **real ledger balances** using `LedgerEngine.get_balance()`
- Added search functionality that searches by name, email, IBAN, or account number across **ALL** accounts
- Added pagination: 20/50/100 per page with 50 as default
- Search returns ALL matching results regardless of which page they're on

**Files Changed:**
- `/app/backend/server.py` - Enhanced `get_all_accounts_with_users()` with ledger balance calculation, search, and pagination
- `/app/frontend/src/components/AdminAccountsControl.js` - Added search bar, pagination controls, per-page selector

**API Response Format:**
```json
{
  "accounts": [...],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total_accounts": 57,
    "total_pages": 2,
    "has_next": true,
    "has_prev": false
  }
}
```

**Verification:** Screenshots and API tests confirm real balances (€29,950.00, €94,996.11, €132,088.24, etc.), search working across all accounts, and pagination functioning correctly.

### Admin Dashboard Charts - Real Data (Feb 17, 2025)
**Problem:** Charts were showing hardcoded fake data (Jan, Feb, Mar, Apr with fictional numbers) instead of real data from the database.

**Solution:**
- Created new backend endpoint `GET /api/v1/admin/analytics/monthly` that queries real data from MongoDB
- Returns last 6 months of actual user registrations and transactions grouped by month
- Includes cumulative user count for growth visualization

**Data Structure:**
```json
{
  "monthly_data": [
    {"month": "Sep", "year": 2025, "users": 0, "transactions": 0, "cumulative_users": 0},
    {"month": "Jan", "year": 2026, "users": 28, "transactions": 22, "cumulative_users": 28},
    {"month": "Feb", "year": 2026, "users": 83, "transactions": 57, "cumulative_users": 111}
  ]
}
```

**Files Changed:**
- `/app/backend/server.py` - Added `get_admin_analytics_monthly()` endpoint
- `/app/frontend/src/components/Analytics.js` - Updated to fetch and display real monthly data

**Verification:** Screenshots and API tests confirm real data is displayed

### Admin Default Page Fix (Feb 17, 2025)
**Problem:** Admin dashboard defaulted to "Users" page instead of "Overview" after login.

**Fix:** Changed `useState('users')` to `useState('overview')` in App.js line 1700.

### Support Ticket File Attachments (Feb 16, 2025)
**Feature:** Clients and admins can now attach files to support ticket messages.

**Specifications:**
- **File Types:** Images (png, jpg, jpeg, gif, webp, bmp), Documents (pdf, doc, docx, xls, xlsx, ppt, pptx, txt, rtf, odt, ods, odp), Other (csv, zip)
- **Max File Size:** 25 MB per file
- **Max Files per Message:** 5 files
- **Storage:** Cloudinary cloud storage

**Backend Changes:**
- `/app/backend/schemas/tickets.py` - Added `MessageAttachment` schema
- `/app/backend/services/ticket_service.py` - Added `upload_attachment()` method, file validation
- `/app/backend/server.py` - Added endpoints:
  - `POST /api/v1/tickets/{ticket_id}/messages/with-attachments` - Send message with files
  - `POST /api/v1/tickets/{ticket_id}/upload` - Upload files only

**Frontend Changes:**
- `/app/frontend/src/components/Support.js` - Added file upload UI:
  - Attach button with paperclip icon
  - File preview with remove option
  - Attachment display in messages with download links

**Verification:** 100% test pass rate (15/15 backend tests, all UI elements verified)

### Transaction Date Display Fix (Feb 16, 2025)
**Problem:** Bank Transfer transactions with sender names were missing their dates in the Recent Activity list.

**Root Cause:** Conditional logic `{!senderName && !description && (...)}` only showed dates when there was NO sender name AND NO description.

**Solution:** Changed to always show the date for all transactions, regardless of other fields present.

**Files Changed:**
- `/app/frontend/src/components/ProfessionalDashboard.js` - Removed conditional, date now always displays

**Verification:** Visual verification - all transactions now show dates consistently

### Recent Activity Layout Fix (Feb 16, 2025)
**Problem:** Large empty space on the right side of transaction rows in Recent Activity section.

**Solution:**
- Fixed transaction row layout to use full card width
- Applied proper Flexbox styling with `flex justify-between w-full gap-4`
- Transaction details (type, ref, date) aligned LEFT
- Amount and Credit/Debit badge aligned to FAR RIGHT
- Removed unnecessary CSS class overrides causing layout issues

**Files Changed:**
- `/app/frontend/src/components/ProfessionalDashboard.js` - Transaction row styling (lines 812-862)

**Verification:** Visual verification via screenshot - layout now uses full width with no empty space

### Professional Banking Transaction Display (Feb 16, 2025)
**Problem:** Transaction display showed processing status (Posted/Submitted) instead of transaction type.

**Solution:**
- Changed terminology:
  - "Posted" → **"Credit"** (EN) / **"Accredito"** (IT) - GREEN badge for incoming money
  - "Submitted" → **"Debit"** (EN) / **"Addebito"** (IT) - RED badge for outgoing money
- Credit amounts: **+€X.XXX,XX** in GREEN
- Debit amounts: **-€X.XXX,XX** in RED
- Badges show transaction TYPE, not processing status

**Files Changed:**
- `/app/frontend/src/translations.js` - Added credit/debit translations
- `/app/frontend/src/components/ProfessionalDashboard.js` - Customer transactions
- `/app/frontend/src/components/Transactions.js` - Transaction list and modal

**Verification:** 100% test pass rate

### EU Currency Formatting (Feb 16, 2025)
**Format:** €24.650,00 (dot for thousands, comma for decimals)
**Files Changed:** 12+ components updated to use currency utility

### Users Tab Pagination Fix (Feb 16, 2025)
- Removed 100 user limit, added pagination (20/50/100 per page)
- Search queries ALL users in database

## Known Issues / Backlog

### P0 - Critical
- ~~Admin Dashboard showing all zeros~~ **FIXED Feb 17, 2025**
- Domain SSL issue: `ecommbx.group` SSL certificate not provisioning

### P1 - High Priority
- **Dangerous transfer deletion endpoint without ledger reversal** - `DELETE /api/v1/admin/transfers/{transfer_id}` performs hard delete which risks data integrity. Should be refactored to soft delete or reversing ledger entry.

### P2 - Medium Priority
- Refactor `server.py` into smaller routers (admin.py, transfers.py, tickets.py)

## Database Schema (Key Collections)
- `users` - User accounts
- `bank_accounts` - Bank accounts
- `ledger_transactions` - Financial transactions
- `transfers` - Transfer records
- `tax_holds` - Tax hold information

## Test Files
- `/app/test_reports/` - Test reports directory

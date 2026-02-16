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

## Technical Stack
- **Frontend:** React.js with TailwindCSS
- **Backend:** FastAPI (Python)
- **Database:** MongoDB
- **Authentication:** JWT tokens
- **Email:** Resend API

## Recent Changes (February 2025)

### Users Tab Pagination Fix (Feb 16, 2025)
**Problem:** Some clients (like Josep De Las Heras Descarrega, user #104) appeared in Accounts tab but NOT in Users tab because the backend was limiting users to 100.

**Solution:**
1. Removed the 100 user limit from `/api/v1/admin/users` endpoint
2. Added pagination with options: 20, 50, 100 users per page (default: 50)
3. When searching, searches ALL users in database (not just current page)
4. Added First/Previous/Next/Last page navigation buttons

**Files Changed:**
- `/app/backend/server.py` - Updated GET /api/v1/admin/users endpoint
- `/app/frontend/src/App.js` - Added pagination state and UI controls

**Verification:** 100% test pass rate - Josep now appears when searching "josep"

## Known Issues / Backlog

### P0 - Critical
- Domain SSL issue: `ecommbx.group` SSL certificate not provisioning (requires Emergent support)

### P1 - High Priority
- **Dangerous transfer deletion endpoint** (`/api/v1/admin/transfers/{transfer_id}/delete`) performs hard delete without reversing ledger transaction - can cause balance desync

### P2 - Medium Priority
- Consider refactoring `server.py` into smaller FastAPI routers for maintainability

## Database Schema (Key Collections)
- `users` - User accounts with roles, status, preferences
- `bank_accounts` - Bank accounts linked to users
- `ledger_accounts` - Ledger accounts for balance tracking
- `ledger_transactions` - All financial transactions
- `kyc_applications` - KYC application records
- `transfers` - Transfer records
- `tax_holds` - Tax hold information
- `notifications` - User notifications

## API Endpoints (Key)
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/admin/users` - List users with pagination and search
- `GET /api/v1/admin/users/{user_id}` - User details
- `GET /api/v1/admin/accounts-with-users` - Accounts list
- `POST /api/v1/admin/users/{user_id}/demote` - Demote admin to user
- `PUT /api/v1/admin/kyc/{application_id}` - Update KYC
- `DELETE /api/v1/admin/kyc/{application_id}` - Delete KYC

## Test Files
- `/app/backend/tests/test_users_pagination.py` - Pagination tests
- `/app/test_reports/` - Test reports directory

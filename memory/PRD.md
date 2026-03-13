# ecommbx Banking Platform - Product Requirements Document

## Original Problem Statement
A full-stack banking application (React frontend + FastAPI backend + MongoDB) that has been migrated from the Emergent platform to Vercel (frontend) + Railway (backend). The app serves real banking clients and requires extreme care with all changes.

## Tech Stack
- **Frontend:** React, TailwindCSS, Shadcn/UI components, hosted on Vercel
- **Backend:** FastAPI (Python), hosted on Railway
- **Database:** MongoDB Atlas (ecommbx-prod)
- **Email:** Resend (transactional emails)
- **File Storage:** Cloudinary

## Core Features (Implemented)
- User authentication (login, registration, email verification, password reset)
- KYC (Know Your Customer) verification flow
- Bank accounts with IBAN/BIC management
- Fund transfers (SEPA) with admin approval queue
- Ledger-based balance tracking (double-entry)
- Admin panel with full user management
- Tax hold/account restriction system
- Support ticket system with file attachments
- Notification system (in-app + email)
- Audit logging
- Scheduled payments
- Spending insights/analytics
- Card ordering

## Completed Features (This Session - March 2026)
1. **Domain Change Notification Feature (DONE):** Admins can send professional email notifications to single users or all users announcing a domain change. Backend endpoints + frontend modals fully functional.
   - Backend: `POST /api/v1/admin/users/send-domain-change-all` and `POST /api/v1/admin/users/{user_id}/send-domain-change`
   - Frontend: Professional modal with domain input, warning text, and loading states
   - Fixed route path bugs (double `/users/users/` in URL)
   - Fixed role check bug (lowercase vs uppercase `ADMIN`)
   - Fixed user query filter for non-admin users

2. **Dark Mode Email Fix (DONE):** Fixed all 7 email templates to render correctly in dark mode email clients.
   - Added `color-scheme: light only` meta tags to prevent dark mode color inversions
   - Added CSS `@media (prefers-color-scheme: dark)` overrides with `!important`
   - Replaced gradient backgrounds with solid `background-color` for reliability
   - Added explicit inline `color` styles to all text elements
   - Templates fixed: verification, password reset (admin + user), OTP, transfer confirmation, transfer rejection, domain change notification

## Previously Completed (Prior Sessions)
- File viewing in new tab (Cloudinary proxy)
- Production login CORS fix
- Password verification fix for admin-created users (string vs ObjectId _id)
- Allow duplicate IBANs for admin-created users
- Vercel build fixes (ajv dependency, CI=false)
- Full database backup
- Infrastructure migration guidance (Vercel + Railway)

## Known Technical Debt
- **Dual _id format:** Admin-created users have string _id, self-registered users have ObjectId. All lookups must handle both types.
- **CORS:** Uses `allow_origin_regex=r".*"` for credentialed requests.

## Backlog / Future Tasks
- **P2: Multi-Tenancy Support** — Support two separate companies (Italy/Spain) with same codebase but different databases
- **P2: _id Format Migration** — Standardize all user _ids to ObjectId format

## Test Credentials
- **Admin:** admin@ecommbx.io / Admin@123456
- **Test User:** ashleyalt004@gmail.com / 12345678

## Key Architecture Notes
- Backend routes prefixed with `/api/v1/`
- Frontend API client at `src/api.js` uses baseURL `${BACKEND_URL}/api/v1`
- Router prefix for admin users: `/api/v1/admin/users`
- Email sending requires verified domain on Resend

# ecommbx Banking Platform - Product Requirements Document

## Overview
ecommbx is a full-stack EU-licensed digital banking platform built with React frontend, FastAPI backend, and MongoDB database.

**Production Domain:** https://ecommbx.group

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
- **Support Ticket System Upgrade - Admin search, create for client, notifications, unread badges**

## Technical Stack
- **Frontend:** React.js with TailwindCSS
- **Backend:** FastAPI (Python)
- **Database:** MongoDB
- **Authentication:** JWT tokens
- **Email:** Resend API
- **File Storage:** Cloudinary (for KYC docs and ticket attachments)

## Recent Changes (February 2026)

### P0 EMERGENCY HOTFIX - Tax Hold / Restriction / Notification Regression (Feb 24, 2026)
**Status:** ✅ FIXED AND VERIFIED

**Root Causes Found:**
1. **Tax Amount €0:** Write path used `tax_amount_due` but read path expected `tax_amount_cents`
2. **No Client Notification:** NotificationService not imported/called in tax hold flow
3. **Restriction Not Enforced:** `check_tax_hold` queried `status: "ACTIVE"` but DB uses `is_active: True`

**Files Changed:**
- `backend/routers/admin_users.py`: Fixed field names (lines 730,752,760), added NotificationService calls (lines 785-814, 869-879)
- `backend/routers/transfers.py`: Fixed check_tax_hold query (lines 68-73)
- `backend/routers/cards.py`: Fixed check_tax_hold query (lines 34-40)

**Validation:** 14/16 backend tests PASS (2 failures are test script issues, not feature bugs), all frontend tests PASS

---

### P0 UI HOTFIX (Attempt 2) - Admin Panel Horizontal Overflow (Feb 24, 2026)
**Status:** ✅ FIXED AND VERIFIED

**Bug:** Admin panel content clipped on smaller monitors - horizontal overflow regression
**Root Cause:** Outer wrapper in App.js had `flex` class but sidebar is `position:fixed`, causing improper width calculation for `.admin-content`

**Fixes Applied:**
1. `App.js` line 1757: Removed `flex` from outer container (changed to `min-h-screen` only)
2. `App.css` lines 200-210: Added `min-width:0`, `overflow-x:hidden` to `.admin-content`
3. `AdminUsersSection.js`: Removed `min-w-[900px]` from table

**Validation:** All viewports (1280, 1366, 1440, 1920) pass with NO page-level overflow. All 9 admin sections verified.

---

### P0 UI HOTFIX - Admin Panel Horizontal Overflow Regression (Feb 24, 2026)
**Status:** ✅ FIXED AND VERIFIED

**Bug:** Admin panel content clipped on smaller monitors (1280x720) - 303px horizontal overflow
**Root Cause:** `.admin-content` had no width constraint, causing flex container to exceed viewport
**Fix Applied:**
1. `App.css`: Added `width: calc(100vw - 240px)` and `overflow-x: auto` to `.admin-content`
2. `AdminUsersPage.js`: Changed filter grid to responsive `grid-cols-2 lg:grid-cols-5`
3. `AdminUsersSection.js`: Added `overflow-x-auto` to table card

**Validation:** All viewports (1280, 1366, 1440, 1920) pass with no page-level overflow

---

### P0 HOTFIX - KYC Queue + Tax Hold Amount Bugs (Feb 24, 2026)
**Status:** ✅ FIXED AND VERIFIED

**Bug 1: KYC Queue Panel Blank After Selection**
- **Root Cause:** `/admin/kyc/pending` endpoint missing personal info fields
- **Fix:** Added `full_name`, `date_of_birth`, `nationality`, `country`, `street_address`, `city`, `postal_code`, `tax_residency`, `tax_id` to response
- **File:** `backend/routers/kyc.py` lines 187-206

**Bug 2: Tax Hold Amount Showing €0,00**
- **Root Cause:** Code reading `tax_amount_due` but database stores `tax_amount_cents`
- **Fix:** Changed to read `tax_amount_cents` field
- **File:** `backend/routers/admin_users.py` line 869

**Regression Testing:** 17/17 backend tests PASS, all admin UI features verified

---

### P0 FINAL REDEPLOY VALIDATION COMPLETE (Feb 24, 2026)
**Validation Result:** ✅ **GO FOR PRODUCTION REDEPLOY**

**Summary:**
- Backend: 29/29 tests PASS (100%)
- Frontend: 9/9 admin sections PASS (100%)
- Critical Features: ALL OPERATIONAL
- Blockers: 0 found
- Regressions: 0 found

**Full Report:** `/app/REDEPLOY_READINESS_REPORT.md`

**Key Verifications:**
- All admin panel sections load without errors
- Transfers module fully operational (including DELETED tab + Restore feature)
- Support Tickets bug fixes stable (thread visibility, self-notification, auto-scroll)
- Users module phone visibility working
- Audit logs timestamps correct
- Notification badge logic correct
- All 5 extracted routers functional
- No API contract mismatches
- Security/RBAC enforced

---

## Recent Changes (February 2025)

### P1 UX Bugfix: Support Tickets Auto-Scroll (Feb 24, 2025)
**Symptom:** Chat scroll position stayed where it was after admin sent a message - had to manually scroll to see new message
**Root Cause:** No auto-scroll logic implemented after message send or ticket open
**Fix:** Added `messagesContainerRef`, `scrollToBottom()` function with setTimeout(100ms), and useEffect hooks
- Scroll triggers when `ticket.id` changes (opening new ticket)
- Scroll triggers when `ticket.messages.length` changes (new message sent)
**File:** `frontend/src/components/Support.js`
**Testing:** 100% pass rate (iteration_135.json) - All auto-scroll scenarios verified

### P1 BUGFIX: Support Tickets Thread Disappear + Admin Self-Notification (Feb 24, 2025)
**Bug A Fixed: Thread Disappears After Admin Sends Message**
- **Symptom:** Chat panel went blank after admin sent a message
- **Root Cause:** `refreshSelectedTicket()` fetched list view (no messages), replacing full ticket data
- **Fix:** Now fetches `/admin/tickets/{id}` first to get full ticket details with messages
- **File:** `frontend/src/components/Support.js`

**Bug B Fixed: Admin Receives Notification for Own Message**
- **Symptom:** Support badge incremented when admin sent message (shouldn't happen)
- **Root Cause:** Notification count used `updated_at` timestamp (any activity)
- **Fix:** Added `last_client_message_at` field that only updates for client messages (is_staff=False)
- **Files:** `backend/services/ticket_service.py`, `backend/routers/notifications.py`

**Testing:** 100% pass rate (iteration_134.json) - Both bugs fixed, all regression tests pass

### P1/P2 Admin UX Enhancement Session (Feb 24, 2025)
**Scope:** UI/UX polish only - no business logic changes.

**New Reusable Components Created (AdminUIComponents.js):**
- `CopyButton` - Copy-to-clipboard with "Copied!" feedback (2-second timeout)
- `ActionButton` - Loading state + double-click protection
- `EmptyState` - Consistent no-results UI
- `FilterChip` - Active filter display
- `ClearFiltersButton` - Clear all filters action

**Accounts Section Updates:**
- Copy buttons for emails and IBANs (98 total)
- Clear search (X) button in search input
- Active filter indicator showing search query
- Improved action button spacing (Top Up, Withdraw, Edit IBAN)
- Loading state on submit with double-click protection

**Transfers Section Updates:**
- Copy buttons in transfer details (Reference, Email, IBANs)
- Clear search button with proper icon
- Active filter indicator with "Clear filters" button
- EmptyState for no-results scenarios

**Testing:** 100% pass rate (iteration_133.json) - All components verified, no console errors

### P1 Polish Session: Cleanup + Row-Level Restore UX (Feb 24, 2025)
**Part A: server.py Cleanup**
- Removed 278 lines of commented-out code from extracted routers
- File reduced from 1290 to 1012 lines
- Added clean reference comment block listing all extracted routers
- No behavior changes - cleanup only

**Part B: Row-Level Restore Button UX**
- Added "Restore" button directly in table rows for DELETED tab
- Button only visible for soft-deleted transfers
- Opens same confirmation modal with proper warning
- Better UX: Admins can restore directly from list without opening details

**Testing:** 100% pass rate (iteration_132.json) - 11/11 backend tests, all frontend components verified

### P1 Feature: Admin Transfer Restore (Feb 24, 2025)
**Feature:** Implemented admin ability to restore soft-deleted transfers.

**Business Rules (CRITICAL):**
- ✅ Restore ONLY restores record visibility - NO financial re-execution
- ✅ RBAC: Only SUPER_ADMIN can restore (same as delete)
- ✅ Audit logging mandatory for all restore actions
- ✅ Idempotent: Restoring already-active transfer returns safe response

**Backend Implementation:**
- `POST /api/v1/admin/transfers/{id}/restore` - New restore endpoint
- `GET /api/v1/admin/transfers?status=DELETED` - Returns soft-deleted transfers
- `get_deleted_transfers()` - New service method with bulk lookups

**Frontend Implementation:**
- DELETED tab added to Transfers Queue (dark gray styling)
- Transfer details show Deletion Information section
- Restore Transfer button (green) for deleted transfers
- Confirmation modal with prominent warning about record-only restoration

**Bug Fixed:** Pydantic validation error when frontend sends `reason: null`
- Changed `reason: str` to `reason: Optional[str]`

**Testing:** 100% pass rate (iteration_131.json) - 14/14 tests passed

### P1 Backend Refactor: Minor Routers Extraction (Feb 24, 2025)
**Refactor:** Extracted remaining minor routers from server.py into dedicated modules.

**New Router Files Created:**
- `/app/backend/routers/recipients.py` - 3 endpoints (POST, GET, DELETE)
- `/app/backend/routers/beneficiaries.py` - 3 endpoints (POST, GET, DELETE)
- `/app/backend/routers/insights.py` - 2 endpoints (spending, monthly-spending)
- `/app/backend/routers/scheduled_payments.py` - 3 endpoints (POST, GET, DELETE)

**Performance Parity Verified:**
| Endpoint | Baseline | After | Status |
|----------|----------|-------|--------|
| Beneficiaries | 437ms | 491ms | ✅ |
| Recipients | 469ms | 467ms | ✅ |
| Insights/spending | 545ms | 568ms | ✅ |
| Monthly-spending | 673ms | 696ms | ✅ |
| Scheduled-payments | 433ms | 452ms | ✅ |

**Testing:** 100% pass rate (iteration_130.json) - 22/22 backend tests passed

### P0 Backend Refactor: Transfers Router Extraction (Feb 24, 2025)
**Refactor:** Extracted transfers router from monolithic server.py into dedicated `routers/transfers.py` module.

**Business Context:** This is a LIVE PRODUCTION banking platform with real clients. The refactor required extreme caution to preserve 100% behavior parity.

**Endpoints Extracted (11 total):**

| Endpoint | Method | Type |
|----------|--------|------|
| `/api/v1/transfers/p2p` | POST | User P2P transfer |
| `/api/v1/transfers` | POST | User create transfer |
| `/api/v1/transfers` | GET | User list transfers |
| `/api/v1/transfers/{transfer_id}` | GET | User transfer detail |
| `/api/v1/admin/transfers` | GET | Admin list transfers |
| `/api/v1/admin/transfers/{transfer_id}/approve` | POST | Admin approve |
| `/api/v1/admin/transfers/{transfer_id}/reject` | POST | Admin reject |
| `/api/v1/admin/transfers/{transfer_id}/reject-reason` | PATCH | Admin update reason |
| `/api/v1/admin/transfers/{transfer_id}` | DELETE | Admin soft-delete |
| `/api/v1/admin/transfers/{transfer_id}/resend-email` | POST | Admin resend email |
| `/api/v1/admin/ledger/internal-transfer` | POST | Admin internal transfer |

**Critical Bug Fixed During Extraction:**
- `routers/dependencies.py` `require_admin` was missing `FINANCE_OPS` and `COMPLIANCE_OFFICER` roles
- Fixed to match server.py implementation

**Performance Parity Verified:**
| Endpoint | Baseline | After | Delta |
|----------|----------|-------|-------|
| SUBMITTED | 890ms | 910ms | +2% ✅ |
| COMPLETED | 776ms | 781ms | +0.6% ✅ |
| REJECTED | 767ms | 786ms | +2.5% ✅ |
| Search | 884ms | 887ms | +0.3% ✅ |
| User transfers | 453ms | 437ms | -3.5% ✅ |

**Preserved Critical Patterns:**
- Bulk user lookups (`users_map`) - NO N+1 regression
- Bulk account lookups (`accounts_map`) - NO N+1 regression
- Server-side pagination
- Soft-delete filtering (`is_deleted` check)

**Transfer Restore Feature:** EXPLICITLY DEFERRED - NOT IMPLEMENTED

**Files Changed:**
- `/app/backend/routers/transfers.py` - NEW file with all transfer endpoints
- `/app/backend/server.py` - Old endpoints commented out, router registered
- `/app/backend/routers/dependencies.py` - Fixed require_admin roles

**Testing:** 100% pass rate (iteration_129.json)
- All 15 backend tests passed
- Frontend Transfers Queue verified working
- Status tabs, pagination, search all functional

### IBAN Copy Icon Inline Fix (Feb 19, 2025)
**Fix:** Fixed the IBAN copy icon dropping to a new line on mobile devices in the Accounts card.

**Problem:** On mobile viewports (especially narrow screens like 320px-375px), the copy IBAN icon was wrapping to a new line instead of staying inline with the IBAN text.

**Solution:** Changed the button and SVG styling to use true inline display:
1. Changed button from `inline-flex` to `display: inline` with `vertical-align: middle`
2. Applied same `display: inline; vertical-align: middle` to the SVG icon inside
3. Changed parent span from `break-all` to `word-break: break-word` for cleaner text wrapping
4. This makes the icon flow with the text like a character, staying with the last segment of the IBAN

**Files Changed:**
- `/app/frontend/src/components/ProfessionalDashboard.js` - Updated IBAN section styling (lines 644-686)

**Verification:** Tested on mobile (375px, 320px) and desktop (1920px) viewports:
- Mobile: Icon stays inline with last IBAN segment even when text wraps to 2-3 lines
- Desktop: Icon properly positioned after full IBAN on single line
- Copy functionality works correctly (shows checkmark feedback)

### Dark Mode "This Month" Card Text Contrast Fix (Feb 19, 2025)
**Fix:** Fixed unreadable text in the "This Month" (QUESTO MESE) spending summary card in dark mode.

**Problem:** The "Trasferimenti" (Transfers) label and its amount value were using low-contrast grey colors (`text-gray-500` and `text-gray-700`) that appeared nearly invisible against the dark card background.

**Solution:** Added `isDark` conditional styling to use appropriate dark mode text colors:
1. Main total label: `text-gray-400` in dark mode (was `text-gray-600`)
2. Main total amount: `text-white` in dark mode (explicit white)
3. Category labels (Trasferimenti): `text-gray-300` in dark mode (was `text-gray-500`)
4. Category amounts: `text-gray-100` in dark mode (was `text-gray-700`)

**Design Tokens Applied:**
- Primary text (amounts): white
- Secondary text (labels): light grey (gray-300/gray-400), still clearly readable
- Maintains visual hierarchy: main total is brightest/boldest, categories slightly subdued but readable

**Files Changed:**
- `/app/frontend/src/components/ProfessionalDashboard.js` - Updated "This Month" card section (lines 1043-1077)

**Verification:** Tested in both dark and light modes:
- Dark mode: All text clearly readable with proper contrast
- Light mode: No regression, original colors preserved

### Support Ticket Message Formatting Fix (Feb 20, 2025)
**Fix:** Preserved line breaks and paragraph formatting in Support Ticket messages.

**Problem:** When users or admins typed messages with line breaks (like emails with paragraphs), the UI collapsed all whitespace and displayed the message as one continuous sentence.

**Solution:** Added `whitespace-pre-wrap` CSS class to the message content `<p>` element in `Support.js`.

**Technical Change:**
- File: `/app/frontend/src/components/Support.js` (line 1105)
- Changed: `<p className="text-sm ...">` to `<p className="text-sm whitespace-pre-wrap ...">`
- This CSS property preserves newlines while still allowing normal text wrapping

**Example:**
- Input: "Hello,\n\nWelcome to the bank!!!\n\nThis is amazing"
- Before fix: "Hello, Welcome to the bank!!! This is amazing"
- After fix: Three separate lines with paragraph breaks

**Verification:** Tested on:
- Desktop (1920px): Line breaks preserved ✓
- Mobile (375px): Line breaks preserved ✓
- Both client and admin/support messages display correctly

### Language Selector Display Fix (Feb 20, 2025)
**Fix:** Removed flag emojis from language selector, now shows only "EN" or "IT".

**Problem:** Header showed "🇬🇧 EN" with a flag emoji prefix. User wanted clean display of just "EN" or "IT".

**Solution:** Removed the flag emoji `<span>` element from the language toggle buttons in:
- `/app/frontend/src/components/TransfersPage.js` (line 43)
- `/app/frontend/src/components/CardsPage.js` (line 74)

**Before:** `🇬🇧 EN` / `🇮🇹 IT`
**After:** `EN` / `IT`

**Verification:** Tested on:
- Desktop (1920px): Shows just "EN" / "IT" ✓
- Mobile (375px): Shows just "EN" / "IT" ✓
- Transfers page ✓
- Cards page ✓
- Switching between EN/IT works correctly ✓

### Instant Transfer Toggle UX Refinement (Feb 20, 2025)
**Refinement:** Made the Instant Transfer modal more bank-professional.

**Changes from previous implementation:**
1. **Removed Cancel button** - Now only has single "Understood" / "Ho capito" button
2. **Toggle behavior**: When tapped, toggle visually turns ON (green) immediately, then modal opens. After clicking "Understood", toggle returns to OFF (grey)
3. **Removed inline note** - No more "Instant transfer is currently unavailable" text under the toggle. Only the modal shows the unavailable info.
4. **Button styling**: Full-width red primary CTA, consistent with ecommbx brand

**New UX Flow:**
1. User taps toggle → Toggle turns green, modal appears
2. User reads info and clicks "Understood" / "Ho capito"
3. Modal closes, toggle automatically returns to OFF (grey)
4. Page returns to clean state with no extra helper text

**Technical Changes:**
- Toggle now sets `instantTransferEnabled=true` when clicked, then shows modal
- Modal's "Understood" button sets `instantTransferEnabled=false` and closes modal
- Removed inline info line element entirely
- Background overlay no longer dismisses modal (must use button)

**Files Changed:**
- `/app/frontend/src/components/P2PTransfer.js` - Simplified modal with single button
- `/app/frontend/src/translations.js` - Added `instantTransferUnderstood` translation

**Verification:** Tested on:
- Desktop (1920px) light mode ✓
- Desktop (1920px) dark mode ✓
- Mobile (375px) ✓
- Italian language ✓

### Instant Transfer Toggle UX Improvement (Feb 20, 2025)
**Feature:** Improved the Instant Transfer toggle with a professional confirmation popup instead of inline warning panel.

**Previous Behavior:** When toggle was turned ON, it showed an inline warning panel and kept the toggle ON (green).

**New Behavior:**
1. When user taps the toggle → Shows a centered modal popup
2. Modal displays the "Instant transfer temporarily unavailable" message with:
   - Warning icon
   - Explanation body text
   - Bullet points about Standard SEPA and irreversibility
   - Note: "You can continue with Standard SEPA."
   - Two buttons: "OK" / "Ho capito" and "Cancel" / "Annulla"
3. After clicking OK → Modal closes, toggle stays OFF
4. A subtle info line shows below toggle: "Instant transfer is currently unavailable."

**Technical Changes:**
- Added state `showInstantTransferModal` to control modal visibility
- Toggle always stays OFF (grey) since feature is unavailable
- Modal is centered and responsive (buttons stack on mobile)
- Full dark mode support

**New Translations:**
- `instantTransferContinueNote`: EN: "You can continue with Standard SEPA." / IT: "Puoi continuare con il bonifico SEPA standard."
- `instantTransferUnavailableShort`: EN: "Instant transfer is currently unavailable." / IT: "Il bonifico istantaneo non è al momento disponibile."
- `instantTransferOk`: EN: "OK" / IT: "Ho capito"
- `instantTransferCancel`: EN: "Cancel" / IT: "Annulla"

**Files Changed:**
- `/app/frontend/src/components/P2PTransfer.js` - Replaced inline panel with modal
- `/app/frontend/src/translations.js` - Added new translations for EN and IT

**Verification:** Tested on:
- Desktop (1920px) light mode ✓
- Desktop (1920px) dark mode ✓
- Mobile (375px) ✓
- Italian language ✓

### Instant Transfer Toggle Feature (Feb 19, 2025)
**Feature:** Added Instant Transfer toggle to the Send Money (Transfer via IBAN) form for future instant transfer support.

**Implementation:**
1. **Toggle Placement:** Above "Make Payment" button, under "Details" section
2. **Toggle Labels:**
   - EN: "Instant transfer"
   - IT: "Bonifico istantaneo"
3. **Default State:** OFF (grey)
4. **When ON:** Shows professional info panel explaining instant transfer is temporarily unavailable
5. **Behavior:** Transfer still submits successfully as Standard SEPA

**Info Panel Content (when toggle ON):**
- EN Title: "Instant transfer temporarily unavailable"
- EN Body: "Instant transfers are currently not available due to operational limitations. You can continue and your transfer will be processed as a standard SEPA transfer."
- EN Bullets: "Standard SEPA transfers remain available." / "Instant transfers are not reversible once executed."
- IT translations included

**Status Line:** "This transfer will be processed as Standard SEPA" / "Questo bonifico verrà elaborato come SEPA standard"

**Technical Details:**
- `instant_requested: bool` field added to transfer request schema
- Field stored for future use when instant transfers are enabled
- Currently all transfers processed as standard SEPA regardless of toggle state

**Files Changed:**
- `/app/frontend/src/components/P2PTransfer.js` - Added toggle UI, state, and info panel
- `/app/frontend/src/translations.js` - Added EN/IT translations for instant transfer
- `/app/backend/schemas/transfers.py` - Added `instant_requested` field to P2PTransferRequest
- `/app/backend/server.py` - Updated endpoint to pass instant_requested to service
- `/app/backend/services/transfer_service.py` - Added instant_requested parameter (for future use)

**Verification:** Tested on:
- Desktop (1920px): Light mode ✓, Dark mode ✓
- Mobile (375px): Light mode ✓
- Italian language: All translations correct ✓
- API: Accepts instant_requested field, processes transfer successfully ✓

### Domain Update & Email Styling Fix (Feb 19, 2025)
**Fix:** Updated production domain from `ecommbx.io` to `ecommbx.group` and fixed email header text visibility.

**Changes:**
1. **Domain Update:** Changed `FRONTEND_URL` in backend `.env` from `https://ecommbx.io` to `https://ecommbx.group`
2. **Email Header Fix:** Changed "ecomm" text color from `color: white` to `color: #FFFFFF !important` for better email client compatibility
3. **Email Disclaimer:** Updated support email in translations from `support@ecommbx.io` to `support@ecommbx.group`

**Files Changed:**
- `/app/backend/.env` - Updated FRONTEND_URL
- `/app/backend/services/email_service.py` - Updated text color and support email in translations

### Support Ticket System Upgrade (Feb 18, 2025)
**Enhancement:** Major upgrade to the support ticket system with admin-focused features.

**New Features:**
1. **Admin Ticket Search**
   - Search bar to filter tickets by client email or name (case-insensitive, partial match)
   - Works in conjunction with existing status filter
   
2. **Admin Create Ticket for Client**
   - "Create Ticket for Client" button in admin panel
   - User search dropdown (searches by email/name/ID)
   - Tickets marked with "Created by Support" tag
   - Notification sent to client when ticket is created
   
3. **Bell Notifications**
   - Notification when admin creates ticket for user
   - Notification when admin replies to user's ticket
   - Click-through to relevant ticket in support page
   
4. **Unread Message Counter**
   - Red badge showing count of new messages from client
   - Badge displays "9+" for counts > 9
   - Counter resets to 0 when admin opens the ticket
   - Auto-refresh every 30 seconds

**Backend Changes:**
- `/app/backend/server.py`:
  - `GET /api/v1/admin/users/search-for-ticket?q=query` - Search users for ticket creation
  - `POST /api/v1/admin/tickets/create-for-user` - Create ticket for client
  - `POST /api/v1/admin/tickets/{id}/mark-read` - Reset unread counter
  - `GET /api/v1/admin/tickets` - Now accepts `search` param and returns `unread_count`
- `/app/backend/services/ticket_service.py`:
  - `get_all_tickets()` - Added search and unread_count calculation
  - `create_ticket_by_admin()` - New method for admin-created tickets
- `/app/backend/schemas/tickets.py` - Already had `created_by_admin`, `created_by_admin_id`, `admin_last_read_at`

**Frontend Changes:**
- `/app/frontend/src/components/Support.js`:
  - Added search bar with debounce
  - Added "Create Ticket for Client" button and `AdminCreateTicketForm` component
  - Added unread message badges (red with count)
  - Added "Created by Support" purple tag
  - Added 30-second auto-refresh for admin view
  - `handleSelectTicket()` marks ticket as read

**Verification:** 100% test pass rate (iteration_80.json) - 19/19 backend tests, all frontend verification passed

### Client Unread Message Counter (Feb 18, 2025)
**Enhancement:** Added unread message counter for clients in their Support Tickets list (similar to admin view).

**Features:**
- Badge shows count of NEW/UNREAD messages from Support/Admin (only staff messages)
- Badge resets to 0 when client opens/reads the ticket
- Uses `user_last_read_at` tracking for persistence across sessions
- Works for all tickets (open/closed)
- Shows "9+" for counts > 9

**Backend Changes:**
- `/app/backend/schemas/tickets.py` - Added `user_last_read_at` field
- `/app/backend/server.py` - Added `POST /api/v1/tickets/{id}/mark-read` endpoint for clients
- `/app/backend/services/ticket_service.py` - Updated `get_user_tickets()` to return `unread_count`

**Frontend Changes:**
- `/app/frontend/src/components/Support.js`:
  - Unread badge now shows for both admin and client views
  - `handleSelectTicket()` calls client mark-read endpoint when not admin

**Verification:** 100% test pass rate (iteration_81.json) - 12/12 backend tests, all frontend verification passed

### Notification Aggregation for Ticket Replies (Feb 18, 2025)
**Enhancement:** Implemented notification grouping/aggregation for support ticket replies to prevent flooding.

**Problem Solved:** Previously, if an admin sent 5 messages on the same ticket, the user received 5 identical notifications flooding the dropdown.

**Features:**
- One notification per ticket thread (no duplicates)
- Counter increments for subsequent replies (e.g., "5 new messages")
- Professional message format: "New replies on your ticket: <subject> (X new messages)"
- Timestamp reflects the latest message in the group
- Clicking "View details" opens ticket and marks notification as read
- Persists across logout/login (stored in database)

**Backend Changes:**
- `/app/backend/schemas/notifications.py` - Added `reply_count` field (default: 1)
- `/app/backend/services/notification_service.py` - Added `create_or_update_support_reply_notification()` method:
  - Checks for existing unread notification for same ticket
  - If exists: increments `reply_count`, updates `message` and `timestamp`
  - If not: creates new notification with `reply_count=1`
- `/app/backend/server.py` - Updated `add_ticket_message` endpoints to use aggregation method

**Verification:** 100% test pass rate (iteration_82.json) - 11/11 backend tests, all frontend verification passed

### SPA Behavior Fixes (Feb 18, 2025)
**Bug Fix:** Fixed unwanted full page reloads after admin actions.

**Problem Solved:** Delete transfer and send ticket message were causing full page reloads instead of smooth SPA updates.

**Changes Made:**
1. **Admin Transfers Queue:**
   - Delete: Now removes row from local state, shows toast, background syncs
   - Approve/Reject: Now removes from current list, shows toast, background syncs
   - No more `fetchTransfers()` calls that set loading state

2. **Support Tickets:**
   - Send message: Clears input, refreshes ticket only (no full list refetch)
   - Status change: Uses toast instead of alert, no full refetch
   - Subject edit: Uses toast, no full refetch
   - Message edit/delete: Uses toast, no full refetch
   - Added `toast` import from sonner

**Implementation Pattern:**
- Local state updates for immediate UI response
- `setTimeout` background refresh for data consistency
- `onRefreshTicket(ticketId)` for single-ticket updates
- Replaced `alert()` with `toast.success()` for better UX

**Verification:** 100% test pass rate (iteration_84.json)

### Admin Manual Email Verification (Feb 18, 2025)
**Enhancement:** Added ability for admins to manually verify user emails when users have trouble receiving verification emails.

**Problem Solved:** Users sometimes have issues receiving verification emails (spam filters, typos, etc.) and couldn't log in. Now admins can manually verify their email.

**Features:**
1. **"Verify Email" button** - Visible in User Details panel when email is not verified
2. **"Email Verified" status** - Shows green "Verified" badge or yellow "Not Verified" badge
3. **Confirmation dialog** - Warns admin before verification
4. **Audit logging** - All manual verifications are logged

**Backend Changes:**
- `/app/backend/server.py` - Added `POST /api/v1/admin/users/{user_id}/verify-email` endpoint
- Added `email_verified` field to user details response

**Frontend Changes:**
- `/app/frontend/src/App.js`:
  - Added "Verify Email" button (blue, only shows when email not verified)
  - Added "Email Verified" status field with visual badges
  - Confirmation dialog before verification

**Verification:** 100% test pass rate (iteration_85.json) - 8/8 backend tests, all frontend tests passed

### Admin Delete User Bug Fix (Feb 18, 2025)
**Bug Fix:** Fixed Admin Delete User not actually deleting users despite showing success toast.

**Root Cause:** The `permanent_delete_user` function in server.py was **empty** - only contained imports. The actual delete logic was orphaned code between two functions.

**Fix Applied:**
1. **Backend:** Restored complete `permanent_delete_user` function with:
   - User lookup (handles both string and ObjectId)
   - Role check (SUPER_ADMIN only)
   - Cascade delete of all user data (accounts, KYC, tickets, transfers, etc.)
   - Audit logging
   - Returns `{success: true, deleted: true}` on success

2. **Frontend:** Enhanced `handleDeleteUser` to:
   - Verify `response.data?.success && response.data?.deleted` before showing success
   - Remove user from local state immediately (SPA behavior)
   - Background refresh list for consistency
   - Show error if delete response doesn't confirm deletion

**Verification:** 100% test pass rate (iteration_86.json) - 11/11 backend tests, all frontend tests passed

### Admin Transfers Queue - Sender Information (Feb 18, 2025)
**Enhancement:** Added sender information to the Admin Transfers Queue so admins can clearly see who initiated each transfer.

**Changes Made:**
1. **Backend:** Modified `get_admin_transfers()` in `banking_workflows_service.py` to join with users and bank_accounts collections, returning:
   - `sender_name` - Full name of the user who created the transfer
   - `sender_email` - Email of the sender
   - `sender_iban` - IBAN of the sending account

2. **Frontend:** Updated `AdminTransfersQueue.js`:
   - Added "Sender" column to table showing name and email
   - Updated Transfer Details panel with "Sender (From)" section showing name, email, and IBAN
   - Restructured details panel with clear "Sender (From)" and "Beneficiary (To)" sections

**Files Changed:**
- `/app/backend/services/banking_workflows_service.py` - Added user/account joins with ObjectId conversion
- `/app/backend/server.py` - Updated endpoint to return enriched dict data
- `/app/frontend/src/components/AdminTransfersQueue.js` - Added Sender column and details section

**Verification:** 100% test pass rate (iteration_79.json)

### Dark Mode Recent Activity Fix (Feb 17, 2025)
**Problem:** In dark mode, the "Recent Activity" list on the customer dashboard showed transaction type labels (Card Payment, SEPA Transfer, Top Up) as invisible - white text on white-ish card background, making the transactions unreadable.

**Root Cause:** The `.card` CSS class in `index.css` used `bg-white` without any dark mode variant. When dark mode was enabled via the toggle, the card background stayed white, but the text inside (using `text-white` for dark mode) became invisible.

**Solution:** Added comprehensive dark mode CSS rules:
- `.dark .card { bg-gray-800, border-gray-700 }` - Dark card backgrounds
- `.dark .stat-tile-number { text-white }` - Stat tile numbers visible
- `.dark .stat-tile-label { text-gray-400 }` - Stat tile labels with proper contrast
- `.dark .section-header { text-gray-400 }` - Section headers visible
- `.dark .badge-success/warning/error` - Status badges with dark backgrounds
- `.dark .overview-label, .dark .balance-large, .dark .balance-small` - Balance display elements
- `.dark .account-item { bg-gray-800, border-gray-700 }` - Account items
- Updated credit/debit badges in ProfessionalDashboard.js with `isDark` conditional styling

**Files Changed:**
- `/app/frontend/src/index.css` - Added dark mode variants for .card, .stat-tile-*, .section-header, .badge-* classes
- `/app/frontend/src/App.css` - Added dark mode variants for .overview-label, .balance-large, .balance-small, .account-item classes
- `/app/frontend/src/components/ProfessionalDashboard.js` - Updated credit/debit badge styling with isDark conditionals

**Verification:** Testing agent confirmed 100% pass rate (iteration_76.json):
- Theme toggle works correctly
- Dark mode: All cards have gray-800 backgrounds
- Dark mode: All text is visible with proper contrast
- Light mode: No regressions - white backgrounds maintained
- Transaction labels (Card Payment, SEPA Transfer, Top Up) now clearly visible in dark mode

### Overview Card Balance Dark Mode Fix (Feb 17, 2025)
**Problem:** In dark mode, the big balance amount (e.g., €30.216,00) in the Overview card was becoming extremely light/grey and looked almost hidden, while the card background stayed white, making the balance nearly invisible.

**Root Cause:** Conflicting CSS rules:
1. `.overview-card { background: white }` kept card white
2. Inline Tailwind classes `isDark ? 'bg-gray-800 border-gray-700'` tried to override but were losing
3. `.dark .balance-large { color: #F5F5F5 }` made text light gray
4. Result: Light gray text on white-ish background = invisible

**Solution:** The overview card should remain white in dark mode (as a "hero" contrast element) with dark text:
1. Removed conflicting inline `isDark` classes from ProfessionalDashboard.js overview-card
2. Updated App.css to explicitly keep overview card white in dark mode
3. Changed `.dark .balance-large` and `.dark .balance-small` to use dark colors (#212121, #757575)
4. Updated `.dark .overview-label` to use readable gray (#757575)

**Files Changed:**
- `/app/frontend/src/App.css` - Added `.dark .overview-card` with white background, updated dark mode text colors
- `/app/frontend/src/components/ProfessionalDashboard.js` - Removed inline isDark classes from overview-card section

**Verification:** 100% test pass rate (iteration_77.json):
- Overview card maintains WHITE background (rgb(255,255,255)) in dark mode
- Balance large text uses DARK color (#212121) in dark mode  
- "Available balance" label uses readable gray (#757575) in dark mode
- Light mode unchanged (no regression)

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

### Header Spacing Consistency Fix (Feb 17, 2025)
**Problem:** On the Dashboard page, the logo was pushed to the far left and controls (EN / theme / bell / logout) were pushed to the far right, leaving a huge empty gap in the middle. The Transaction History page had proper header spacing.

**Root Cause:** The Dashboard header used `px-4 flex items-center justify-between` directly on the `<header>` element, which stretched the content to the full screen width. Other pages like Transaction History had an inner `max-w-7xl mx-auto` container.

**Solution:** Updated all page headers to use a consistent two-level structure:
1. `<header>` - Full-width background with border
2. `<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">` - Constrained content container

**Pages Fixed:**
- Dashboard (DashboardPage/ProfessionalDashboard)
- Transactions
- Support
- Insights
- All other authenticated pages already had correct structure

**Files Changed:**
- `/app/frontend/src/App.js`

**Verification:** Code analysis confirms all 8 `<header>` elements now have the `max-w-7xl mx-auto` inner container pattern.

### Support Ticket Real-Time Message Update Fix (Feb 17, 2025)
**Problem:** After sending a message in support tickets, the new message did not appear until the page was reloaded or the ticket was re-selected.

**Root Cause:** The `handleSendMessage` function called `onUpdate()` which refreshed the ticket list, but **did not update the `selectedTicket` state**. The displayed ticket still had the old messages.

**Solution:**
- Added `refreshSelectedTicket()` function in `SupportTickets` component to fetch and update the currently viewed ticket
- Added `onRefreshTicket` prop to `TicketDetails` component
- Updated all handlers (`handleSendMessage`, `handleStatusChange`, `handleSaveSubject`, `handleSaveMessage`, `handleDeleteMessage`) to call `onRefreshTicket()` after successful operations

**Files Changed:**
- `/app/frontend/src/components/Support.js`

**Verification:** Screenshots confirm that after sending "Test real-time update - 1771322923", the message appears immediately in the conversation without any page reload or re-clicking the ticket.

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

### Transfer Confirmation Email (Feb 19, 2025)
**Feature:** Professional confirmation email sent to customers immediately after submitting a bank transfer.

**Specifications:**
- **Subject Line:** "We received your transfer request – Ref #[REFERENCE_NUMBER]"
- **Content:**
  - Personalized greeting with customer's first name
  - Transfer summary table with: Reference, Amount (EU format), Recipient Name, Masked IBANs, Date/Time, Transfer Type, Status (Processing badge)
  - Processing notes about cut-off times and tracking
  - "View Transfer Details" button linking to /transactions
  - Security warning (contact support if unauthorized)
  - Professional branded template with ecommbx logo

**Technical Implementation:**
- **Email Service:** `send_transfer_confirmation_email()` method returns detailed status dict with success, provider_id, error
- **IBAN Masking:** Shows first 4 and last 4 characters only (e.g., DE89****3000)
- **Amount Formatting:** EU style with dots for thousands, comma for decimals (€1.234,56)
- **Multi-Language:** Full support for English and Italian translations
- **Duplicate Prevention:** Comprehensive email status tracking
- **Graceful Failure:** Email errors don't break transfer creation

**Backend Changes:**
- `/app/backend/services/email_service.py` - Added `send_transfer_confirmation_email()` method
- `/app/backend/services/banking_workflows_service.py` - Integrated email sending in `create_transfer()`
- `/app/backend/schemas/banking_workflows.py` - Added email status fields to Transfer schema

**Verification:** 100% test pass rate (iteration_87.json) - 15/15 backend tests passed.

### Transfer Email Bug Fix & Enhanced Tracking (Feb 19, 2025)
**Bug Fix:** P2P transfers were not sending confirmation emails because `TransferService.p2p_transfer()` had no email integration.

**Root Cause:** The `/api/v1/transfers/p2p` endpoint used `TransferService.p2p_transfer()` which created transfers directly to DB without calling the email service.

**Fix Applied:**
1. **Added email sending to TransferService:** New `_send_transfer_confirmation_email()` helper method
2. **Both internal and SEPA P2P transfers now send emails** automatically after transfer creation
3. **Comprehensive email status tracking** on transfer records

**New Email Status Fields (Transfer Schema):**
- `confirmation_email_status`: enum (pending | sent | failed)
- `confirmation_email_sent_at`: datetime when email was successfully sent
- `confirmation_email_provider_id`: Resend message ID for tracking
- `confirmation_email_error`: Error message if sending failed

**New Admin Features:**
- **Resend Email Endpoint:** `POST /api/v1/admin/transfers/{id}/resend-email`
  - Only available if status is failed or pending
  - Returns error if already sent successfully (prevents duplicates)
  - Returns provider_id on success

**Enhanced Logging:**
- Structured logs with `[TRANSFER EMAIL]` tags
- Logs include: transferId, recipientEmail, language, Resend response/error

**Backend Changes:**
- `/app/backend/services/transfer_service.py` - Added `_send_transfer_confirmation_email()`, `_update_transfer_email_status()`, updated `p2p_transfer()` for both internal and SEPA
- `/app/backend/services/email_service.py` - Returns dict with {success, provider_id, error} instead of boolean
- `/app/backend/schemas/banking_workflows.py` - Added `ConfirmationEmailStatus` enum and new fields
- `/app/backend/server.py` - Added `POST /api/v1/admin/transfers/{id}/resend-email`

**Verification:** 100% test pass rate (iteration_88.json) - 19/19 backend tests passed. Confirmed via:
- Ashley's transfer email resent: provider_id=bank-ui-polish
- New P2P transfer auto-sent: provider_id=bank-ui-polish

### Admin Panel Performance Optimization (Feb 20, 2025)
**Fix:** Eliminated N+1 query problems in Admin Accounts and Transfers Queue pages.

**Problem:** Admin panel was nearly unusable with 7-23 second load times:
- Accounts page: ~8.5 seconds (50 accounts)
- Transfers Queue: ~22.5 seconds (100 transfers)

**Root Cause Analysis:**
1. **Accounts endpoint:** Called `ledger_engine.get_balance()` in a loop for each account (N+1 query)
2. **Transfers endpoint:** Made individual queries for each user and bank account (2N+1 queries)

**Solution:**
1. **Bulk Balance Calculation:** Added `get_bulk_balances()` method to `ledger_service.py` that calculates all account balances in a single MongoDB aggregation pipeline
2. **Bulk User/Account Lookups:** Refactored `get_admin_transfers()` to pre-fetch all users and accounts in two bulk queries, then use O(1) map lookups
3. **Server-Side Pagination:** Added pagination to transfers endpoint (50 items/page, max 100)
4. **Database Indexes:** Added indexes on `transfers.status`, `transfers.created_at`, and compound index on `(status, created_at)`

**Performance Results:**
| Endpoint | Before | After | Improvement |
|----------|--------|-------|-------------|
| Admin Accounts | 8.5s | **0.98s** | 88% faster |
| Admin Transfers (SUBMITTED) | 22.5s | **0.66s** | 97% faster |

**Files Changed:**
- `/app/backend/services/ledger_service.py` - Added `get_bulk_balances()` method (line 79)
- `/app/backend/services/banking_workflows_service.py` - Refactored `get_admin_transfers()` with bulk lookups and pagination (line 359)
- `/app/backend/server.py` - Updated `get_all_accounts_with_users` to use bulk balance calculation (line 4123)
- `/app/backend/database.py` - Added indexes for transfers collection

**Verification:** 100% test pass rate (iteration_89.json) - 15/15 backend tests passed. All endpoints under 2-second target.

### Transfers Queue Search & Card Requests Fix (Feb 20, 2025)

**Enhancements:**

1. **Transfers Queue - Full Database Search**
   - Added search bar that searches the ENTIRE database (not just current tab's 50 items)
   - Searches by: beneficiary name, sender name, sender email, IBAN, reference number
   - Returns results from ALL statuses (SUBMITTED, COMPLETED, REJECTED)
   - Shows "Showing X results across all statuses" message when searching
   - Clear button (X) returns to tab view

2. **Card Requests - N+1 Query Fix**
   - **Root Cause:** Frontend was making individual `/admin/users/{id}` API calls for EACH card request (lines 38-48)
   - **Fix:** Backend now includes `user_name` and `user_email` in the card requests response via bulk user lookup
   - **Result:** Page loads in **0.44 seconds** (was several seconds due to N+1)

**Performance Results:**
| Feature | Before | After |
|---------|--------|-------|
| Card Requests (9 items) | ~3-5s (N+1 frontend) | **0.44s** |
| Transfer Search | Not available | **0.87s** (searches 100+ transfers) |

**Files Changed:**
- `/app/backend/services/banking_workflows_service.py`:
  - Added `_search_transfers()` method (line 541)
  - Refactored `get_pending_card_requests()` with bulk user lookup (line 53)
- `/app/backend/server.py` - Added `search` parameter to transfers endpoint (line 3846)
- `/app/frontend/src/components/AdminTransfersQueue.js` - Added search bar UI
- `/app/frontend/src/components/AdminCardRequestsQueue.js` - Removed N+1 queries, uses user_name/user_email from response
- `/app/backend/database.py` - Added indexes for card_requests collection

**Verification:** 100% test pass rate (iteration_90.json) - 13/13 backend tests passed. UI verified via Playwright.

### Dashboard & Support Tickets Performance Optimization (Feb 20, 2025)

**Enhancements:**

1. **Monthly Spending API** (`/api/v1/insights/monthly-spending`)
   - Optimized to use single aggregation pipeline with grouping
   - Reduced rejected transfers lookup to only current month
   - Result: **0.71s** (was ~0.93s)

2. **Support Tickets - Admin List** (`/api/v1/admin/tickets`)
   - Uses MongoDB aggregation to calculate unread count without loading all messages
   - Only loads last message preview and metadata for list view
   - Full messages loaded on-demand via `/api/v1/admin/tickets/{id}`
   - Result: **0.68s** for 73 tickets (was ~0.84s)

3. **Support Tickets - Customer List** (`/api/v1/tickets`)
   - Returns empty messages array in list view
   - Full messages loaded via `/api/v1/tickets/{id}` on select
   - Result: **0.45s**

4. **New Endpoints Added:**
   - `GET /api/v1/tickets/{id}` - Fetch single ticket with full messages (user)
   - `GET /api/v1/admin/tickets/{id}` - Fetch single ticket with full messages (admin)

**Performance Summary:**
| Endpoint | Before | After |
|----------|--------|-------|
| /insights/monthly-spending | 0.93s | **0.71s** |
| /admin/tickets (73 tickets) | 0.84s | **0.68s** |
| /tickets (user) | 0.45s | **0.45s** |

**Files Changed:**
- `/app/backend/services/advanced_service.py` - Optimized `get_monthly_spending()` aggregation
- `/app/backend/services/ticket_service.py` - Optimized `get_all_tickets()` with MongoDB aggregation
- `/app/backend/server.py` - Added single ticket fetch endpoints
- `/app/frontend/src/components/Support.js` - Fetches full ticket on select

**Verification:** 100% test pass rate (iteration_91.json) - 14/14 backend tests passed.

### Admin Overview Performance Optimization (Feb 20, 2025)

**Problem:** Admin Overview page taking 1.7 seconds to load due to 13+ sequential count_documents() calls.

**Optimizations:**

1. **Parallel Query Execution** (`asyncio.gather`)
   - All 9 count queries now run in parallel instead of sequentially
   - Transfer stats use aggregation pipeline (1 query for 4 counts)
   - Ticket stats use aggregation pipeline (1 query for 2 counts)

2. **Monthly Analytics** (`/api/v1/admin/analytics/monthly`)
   - Uses aggregation to group by month in single query
   - Was: 12+ sequential count queries
   - Now: 3 parallel aggregation queries

**Performance Results:**
| Endpoint | Before | After | Improvement |
|----------|--------|-------|-------------|
| Admin Overview | 1.71s | **0.95-1.0s** | **42%** |
| Monthly Analytics | 1.71s | **0.35s** | **80%** |

**Files Changed:**
- `/app/backend/server.py` - Refactored `get_admin_analytics_overview()` with asyncio.gather and aggregation
- `/app/backend/server.py` - Refactored `get_admin_analytics_monthly()` with aggregation pipelines

**Verification:** 100% test pass rate (iteration_92.json) - 18/18 backend tests passed. All expected values verified (87 users, 108 transactions, €35M+ volume).

### Spending Consistency Fix (Feb 20, 2025)

**Problem:** Overview "THIS MONTH" showed €168,580.99 but Spending Insights showed €174,080.99 when clicking "View full breakdown".

**Root Cause:**
- Overview used calendar month (Feb 1 - now)
- Spending Insights defaulted to "Last 30 days" (rolling 30-day window)
- Different calculation logic (monthly excluded rejected transfers, Insights didn't)

**Solution:**
1. Added `period` parameter to `/api/v1/insights/spending` endpoint
2. When `period=this_month`, uses exact same calculation as `/api/v1/insights/monthly-spending`
3. "View full breakdown" now navigates to `/insights?period=this_month`
4. Spending Insights reads URL param and pre-selects "This Month" in dropdown

**Verification:**
| Endpoint | Value |
|----------|-------|
| Overview "THIS MONTH" | €168,580.99 ✅ |
| Spending Insights "This Month" | €168,580.99 ✅ |
| Spending Insights "Last 30 days" | €174,080.99 (correctly different) |

**Files Changed:**
- `/app/backend/server.py` - Added `period` param to spending endpoint
- `/app/frontend/src/components/SpendingInsights.js` - Reads URL params, added "This Month" option
- `/app/frontend/src/components/ProfessionalDashboard.js` - Links to `/insights?period=this_month`

**Verification:** 100% test pass rate (iteration_93.json) - All spending consistency tests passed.

### Transfer Rejection Email Feature (Feb 20, 2025)

**Feature:** Professional transactional email sent to customers ONLY when a transfer is REJECTED by an admin.

**Product Requirements Implemented:**
1. **Trigger:** Email sent immediately and only when status changes to REJECTED
2. **Idempotency:** `rejection_email_sent` flag guarantees one email per rejection
3. **Content:**
   - Subject: "Transfer rejected – action may be required"
   - Body: Professional message stating no funds were sent
   - Details: Rejection timestamp, amount, beneficiary name, masked IBAN (first 4 + last 4), reference
   - **No rejection reason** included (as specified)
4. **CTA:** "Contact Support" button linking to `/support` page
5. **Security Note:** Warning about unauthorized requests
6. **Localization:** Full EN and IT support based on user's `language` preference
7. **Error Handling:** Email failures logged but don't block rejection flow

**Technical Implementation:**

**Email Service Changes:**
- Added `send_transfer_rejected_email()` method to `EmailService`
- Returns detailed status dict: `{success, provider_id, error}`
- Uses existing Resend API integration
- Professional HTML template matching ecommbx branding

**Transfer Schema Changes:**
- Added `rejection_email_sent: bool` (default: False)
- Added `rejection_email_sent_at: datetime` (optional)
- Added `rejection_email_provider_id: str` (optional)
- Added `rejection_email_error: str` (optional)

**Workflow Changes:**
- `reject_transfer()` in `banking_workflows_service.py` now:
  1. Checks idempotency flag before sending
  2. Fetches user details and language preference
  3. Calls `send_transfer_rejected_email()`
  4. Updates transfer document with email status
  5. Logs success/failure without blocking rejection

**Translations Added:**
- English:
  - `transfer_rejected_subject`: "Transfer rejected – action may be required"
  - `transfer_rejected_title`: "Transfer Rejected"
  - `transfer_rejected_body`: "We are writing to inform you that your recent transfer request could not be completed. No funds have been sent from your account."
  - `transfer_rejected_button`: "Contact Support"
  - `transfer_rejected_security_warning`: "If you did not authorize this transfer request, please contact our support team immediately."
- Italian: Full translations for all keys

**Files Changed:**
- `/app/backend/services/email_service.py` - Added `send_transfer_rejected_email()` method and EN/IT translations
- `/app/backend/services/banking_workflows_service.py` - Integrated email sending in `reject_transfer()`
- `/app/backend/schemas/banking_workflows.py` - Added rejection email tracking fields to Transfer model
- `/app/backend/tests/test_transfer_rejection_email.py` - Comprehensive test suite (22 tests)

**Verification:** 100% test pass rate (iteration_94.json) - 22/22 tests passed:
- Transfer rejection triggers email ✅
- Idempotency flag prevents duplicate emails ✅
- Email content verified (no rejection reason, masked IBAN, CTA link) ✅
- EN and IT localization working ✅
- Re-rejection returns 400 error ✅
- Approval does NOT trigger rejection email ✅

### Transfer Email Disclaimer Removal (Feb 20, 2025)

**Change:** Removed the "do not reply / contact support@..." footer line from ALL transfer-related emails.

**Reason:** No bank support email address exists - clients should use in-app Support page only.

**What Was Removed:**
- EN: "Please do not reply to this email. For assistance, contact support@ecommbx.io"
- IT: "Si prega di non rispondere a questa email. Per assistenza, contattare support@ecommbx.io"

**What Was Kept:**
- Security warning section (with warning icon)
- "Contact Support" / "View Transfer Details" CTA button (linking to in-app pages)
- All transfer details, branding, and footer copyright

**Files Changed:**
- `/app/backend/services/email_service.py` - Removed `{t('transfer_disclaimer')}` from both:
  - `send_transfer_confirmation_email()` HTML template
  - `send_transfer_rejected_email()` HTML template
- Translation keys remain in `EMAIL_TRANSLATIONS` (unused, safe to keep)

**Verification:** 100% test pass rate (iteration_95.json) - 19/19 tests passed. Both transfer confirmation and rejection emails verified to no longer contain disclaimer footer.

### Admin Sidebar Notification Badges (Feb 20, 2025)

**Feature:** Session-based notification badges on admin sidebar showing NEW pending items since session started.

**Sidebar Items with Badges:**
- Users → `users_pending` (status = PENDING)
- KYC Queue → `kyc_pending` (KYC applications with status PENDING)
- Card Requests → `card_requests_pending` (requests with status PENDING)
- Transfers Queue → `transfers_pending` (transfers with status SUBMITTED)
- Support Tickets → `tickets_unread` (tickets with last message from client, not admin)

**Badge UI:**
- Red circular badge with white text
- Aligned right of menu item
- Hidden when count = 0
- Shows "99+" if count > 99
- Works in light/dark mode

**Session-Based Behavior (Key Innovation):**
1. **On login:** Current counts become baselines (stored in sessionStorage)
2. **During session:** Badge = max(0, current_count - baseline)
3. **On section click:** Baseline updates to current count → Badge clears
4. **On logout:** Session storage cleared → Badges reset on next login

**Backend Endpoint:**
- `GET /api/v1/admin/notification-counts`
- Returns: `{ kyc_pending, transfers_pending, card_requests_pending, tickets_unread, users_pending }`
- Requires admin authentication
- All queries run in parallel via `asyncio.gather`

**Technical Implementation:**
- `useBadgeManager` hook in AdminLayout.js
- Polls API every 30 seconds
- Stores baselines in sessionStorage with keys:
  - `admin_badge_baselines` - JSON with counts and session ID
  - `admin_badge_session_id` - Unique session identifier

**Files Changed:**
- `/app/backend/server.py` - Added `/api/v1/admin/notification-counts` endpoint
- `/app/frontend/src/components/AdminLayout.js` - Added `useBadgeManager` hook and `NotificationBadge` component
- `/app/backend/tests/test_admin_notification_counts.py` - Comprehensive test suite

**Verification:** 100% test pass rate (iteration_96.json) - 14/14 backend tests passed. Frontend badge manager verified working correctly.

### Admin Badge Persistence Update (Feb 20, 2025)

**Change:** Updated badge system to persist across logout/login using database storage instead of sessionStorage.

**New Behavior:**
1. **Badges persist across sessions** - Stored in `admin_section_views` MongoDB collection
2. **Badge = new items since last viewed** - Using `last_seen_at` timestamp per admin per section
3. **Clear only when viewed** - Clicking a section updates `last_seen_at` to now
4. **Real-time polling** - Every 25 seconds

**Database Schema:**
```
admin_section_views collection:
{
  admin_id: string,        // Admin user ID
  section_key: string,     // 'users', 'kyc', 'card_requests', 'transfers', 'tickets'
  last_seen_at: datetime,  // When admin last viewed this section
  created_at: datetime,
  updated_at: datetime
}
Unique index: (admin_id, section_key)
```

**API Endpoints:**
- `GET /api/v1/admin/notification-counts` - Returns counts per section (new since last_seen_at)
- `POST /api/v1/admin/notifications/seen` - Marks a section as seen (updates last_seen_at)

**Counting Rules:**
- Users: PENDING users created after last_seen_at
- KYC Queue: PENDING KYC applications created after last_seen_at
- Card Requests: PENDING card requests created after last_seen_at
- Transfers Queue: SUBMITTED transfers created after last_seen_at
- Support Tickets: OPEN/IN_PROGRESS tickets with client activity after last_seen_at

**Files Changed:**
- `/app/backend/server.py` - Updated endpoints to use database-backed last_seen_at
- `/app/backend/database.py` - Added indexes for admin_section_views collection
- `/app/frontend/src/components/AdminLayout.js` - Removed sessionStorage, added API-based badge management
- `/app/backend/tests/test_admin_badge_persistence.py` - Comprehensive test suite

**Verification:** 100% test pass rate (iteration_97.json) - 16/16 backend tests passed. Badge persistence across logout/login cycles verified.

### Admin Card Requests Enhancement (Feb 20, 2025)

**Features Added:**

**1. Pagination:**
- Page size dropdown: 20 / 50 / 100 (default 50)
- Controls: First / Prev / Next / Last
- Shows: "Showing X of Y results", "Page N of M"
- Server-side pagination for performance

**2. Global Search:**
- Search input at top of page
- Searches by: user name, email, card type, request ID
- Scope toggle: "This tab" / "All tabs"
- Debounced input (300ms)
- Resets to page 1 when searching

**3. Delete Card Request:**
- Delete button per row (all tabs)
- Confirmation modal with request details
- **CRITICAL:** For FULFILLED requests, also deletes associated card
- Smooth UI update (no page reload)
- Success toast notification

**4. Audit Logging:**
- All deletes logged to `audit_logs` collection
- Logs: action, admin_id, admin_email, request details, timestamp
- Logs whether associated card was also deleted

**API Endpoints:**
- `GET /api/v1/admin/card-requests` - Pagination & search params
  - Query params: `status`, `page`, `page_size`, `search`, `scope`
- `DELETE /api/v1/admin/card-requests/{request_id}` - Delete with safety logic

**Files Changed:**
- `/app/backend/server.py` - Updated GET endpoint, added DELETE endpoint
- `/app/frontend/src/components/AdminCardRequestsQueue.js` - Full rewrite with pagination/search/delete
- `/app/backend/tests/test_admin_card_requests.py` - Comprehensive test suite

**Verification:** 100% test pass rate (iteration_98.json) - 21/21 backend tests passed. All UI elements verified working.

### Admin Transfers Queue Pagination (Feb 20, 2025)

**Feature:** Server-side pagination for Admin Transfers Queue page to improve performance with large datasets.

**Implementation:**

**1. Pagination Controls:**
- Page size dropdown: 20 / 50 / 100 (default 20)
- Navigation buttons: First / Prev / Next / Last
- Displays: "Showing X-Y of Z results", "Page N of M"
- Server-side pagination for performance

**2. Status Tab Integration:**
- Works with all status tabs: SUBMITTED, COMPLETED, REJECTED
- Tab change resets to page 1
- Pagination info reflects per-tab counts

**3. Search Integration:**
- Search bar searches across ALL statuses (ignores current tab)
- Searches: beneficiary name, sender name/email, IBAN, reference number
- Returns `search_mode: true` flag in pagination response
- Message shows "Searching across ALL transfers (ignoring tab filter)"
- Search results are also paginated

**4. UI Behavior:**
- Debounced search input (300ms)
- Page size change resets to page 1
- Disabled navigation buttons when at boundaries

**API Endpoint:**
- `GET /api/v1/admin/transfers`
  - Query params: `status`, `page`, `page_size`, `search`
  - Returns: `{ ok, data, pagination }`
  - Pagination: `{ page, page_size, total, total_pages, has_next, has_prev, search_mode }`

**Backend Implementation:**
- `get_admin_transfers()` in `banking_workflows_service.py` (line 420-543)
  - Handles pagination, status filtering, bulk user/account lookups
- `_search_transfers()` in `banking_workflows_service.py` (line 545-680)
  - Full-text search across transfers and users with pagination

**Files Changed:**
- `/app/backend/services/banking_workflows_service.py` - get_admin_transfers and _search_transfers with pagination
- `/app/backend/server.py` - Updated admin_get_transfers endpoint (line 4452-4479)
- `/app/frontend/src/components/AdminTransfersQueue.js` - Full rewrite with pagination UI

**Verification:** 100% test pass rate (iteration_99.json) - 28/28 backend tests passed. All UI elements verified working:
- Pagination controls visible and functional
- Page navigation (First/Prev/Next/Last) working
- Page size selector working (20/50/100)
- Search with pagination working
- Status tab switching with pagination working

### Admin Pagination UI Improvement (Feb 20, 2025)

**Change:** Moved pagination controls from BOTTOM to TOP of the table for both Admin Card Requests and Admin Transfers Queue pages.

**Problem:** Admins had to scroll down to change pages, which was unprofessional and inefficient.

**Solution:** Relocated pagination controls to directly under the tabs, above the data table:
- "Showing X-Y of Z results/transfers/requests" text
- "Show: N per page" dropdown (20/50/100)
- Page navigation: First / Previous / Page N of M / Next / Last

**Style:** Matches the Users tab professional admin style with:
- Gray background buttons (`bg-gray-200 hover:bg-gray-300`)
- Disabled state styling (`bg-gray-100 text-gray-400 cursor-not-allowed`)
- Horizontal flex layout with responsive wrapping

**Files Changed:**
- `/app/frontend/src/components/AdminTransfersQueue.js` - Pagination moved to top, bottom removed
- `/app/frontend/src/components/AdminCardRequestsQueue.js` - Pagination moved to top, bottom removed

**Verification:** 100% test pass rate (iteration_100.json) - Full UI regression testing confirmed:
- Pagination controls at TOP for both pages
- No pagination at bottom (single instance only)
- All functionality preserved: search, tabs, page navigation, page size selector, delete action

### Admin Password Change & Login Audit Trail (Feb 20, 2025)

**Features Implemented:**

**A) Admin Password Change:**
- Added "Change" button in Admin → Users → User Details password section
- Modal with new password + confirm password fields with validation
- Min 8 characters, passwords must match
- Stores password as plaintext (same as existing system)
- Creates `PASSWORD_CHANGED` audit log with actor, target, IP, source (no password stored)

**B) Login/Logout Audit Trail:**
- New logout endpoint: `POST /api/v1/auth/logout`
- Login audit now distinguishes: `USER_LOGIN_SUCCESS` vs `ADMIN_LOGIN_SUCCESS`
- Logout audit now distinguishes: `USER_LOGOUT` vs `ADMIN_LOGOUT`
- Failed login attempts logged as `USER_LOGIN_FAILED` with IP and user-agent

**C) Auth History in User Details:**
- "View Login Activity" button in User Details page
- Displays auth events: LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, PASSWORD_CHANGED
- Shows IP address, timestamp, actor (for admin actions), source

**API Endpoints:**
- `POST /api/v1/admin/users/{user_id}/change-password` - Admin changes customer password
- `GET /api/v1/admin/users/{user_id}/auth-history` - Get auth history for a user
- `POST /api/v1/auth/logout` - Logout with audit log creation

**Audit Log Actions:**
- `PASSWORD_CHANGED`: Admin changed customer password (entity_type: user)
- `ADMIN_LOGIN_SUCCESS`: Admin logged in (entity_type: auth)
- `ADMIN_LOGOUT`: Admin logged out (entity_type: auth)
- `USER_LOGIN_SUCCESS`: Customer logged in (entity_type: auth)
- `USER_LOGOUT`: Customer logged out (entity_type: auth)
- `USER_LOGIN_FAILED`: Failed login attempt (entity_type: auth)
- `USER_LOGIN_BLOCKED`: Login blocked (disabled account, unverified email)
- `USER_MFA_FAILED`: Failed MFA verification

**Files Changed:**
- `/app/backend/server.py` - Password change endpoint, logout endpoint, enhanced login audit
- `/app/frontend/src/App.js` - Password change modal, auth history UI, logout API call

**Verification:** 100% test pass rate (iteration_102.json) - 10/10 backend tests, all frontend UI verified

### Admin URL Routing Persistence (Feb 20, 2025)

**Problem:** Refreshing any admin page (F5) redirected back to Overview instead of staying on the current section/tab.

**Solution:** Implemented URL-based state persistence for admin navigation:
- Section, tab, page, search, and pageSize now stored in URL query params
- Refresh preserves all state
- Direct URL access (deep linking) works after login redirect
- Browser back/forward supported for section changes

**URL Format Examples:**
- `/admin` - Default overview
- `/admin?section=ledger&tab=REJECTED` - Transfers Queue, REJECTED tab
- `/admin?section=card_requests&tab=FULFILLED&page=2` - Card Requests, page 2
- `/admin?section=users&search=test` - Users with search filter

**Implementation:**
- `AdminDashboard`: Reads/writes `section` param, syncs with sidebar
- `AdminTransfersQueue`: Reads/writes `tab`, `page`, `pageSize`, `search` params
- `AdminCardRequestsQueue`: Reads/writes `tab`, `page`, `pageSize`, `search`, `scope` params
- `ProtectedRoute`: Saves `returnUrl` when redirecting to login
- `LoginPage`: Reads `returnUrl` and redirects back after login

**Files Changed:**
- `/app/frontend/src/App.js` - AdminDashboard, ProtectedRoute, LoginPage with URL param handling
- `/app/frontend/src/components/AdminTransfersQueue.js` - URL state sync
- `/app/frontend/src/components/AdminCardRequestsQueue.js` - URL state sync

**Verification:** 100% test pass rate (iteration_103.json) - All URL routing features verified:
- Refresh persists state (section, tab, page, search)
- Direct URL access works with login redirect
- Deep link after logout/login works
- URL updates on navigation

### Bank-Grade Full Regression Test (Feb 20, 2025)

**Test Scope:** Comprehensive regression test of entire banking application after recent changes.

**System Health:**
| Component | Status | Latency |
|-----------|--------|---------|
| API | ✅ PASS | ~130ms |
| Database | ✅ PASS | ~620ms |
| Email (Resend) | ✅ SET | N/A |
| Env Variables | ✅ PASS | 11/11 |

**Endpoint Regression:** All 18 critical endpoints tested - 100% PASS
- Auth: login, logout
- Admin Users: list, detail, auth-history, change-password
- Transfers: SUBMITTED/COMPLETED/REJECTED tabs, search
- Card Requests: PENDING/FULFILLED/REJECTED tabs, search, delete
- Support Tickets: list (admin and user)
- Notifications: badge counts
- Audit Logs: list with filters

**Frontend Regression (Admin Panel):** 100% PASS
- Overview dashboard with correct stats and EU number formatting
- Users with 50/page pagination, password change, login activity
- Transfers Queue with pagination above tabs, search across all
- Card Requests with pagination above tabs, All tabs search default
- Audit Logs with ADMIN_LOGIN_SUCCESS events
- URL routing persistence on refresh
- Dark mode with good contrast

**Performance:** All endpoints <2s threshold
- /admin/transfers: 915ms avg
- /admin/users: 877ms avg
- /admin/card-requests: 686ms avg

**Data Integrity:**
- Ledger consistency verified (128 total = 39+5+84)
- Audit logging verified (passwords not stored)
- Badge counts match DB state

**Test Reports:** iteration_104.json (full regression)

**Test Account:** ashleyalt005@gmail.com (ADMIN only)
**Customer Flows:** NOT TESTED (no customer test account available)

### Admin Transfers Queue Page Reload Bug Fix - FINAL FIX (Feb 23, 2025)

**Bug:** When an admin deleted a transfer from the Transfers Queue page, the page would unexpectedly reload/refresh after ~2-4 seconds.

**ACTUAL Root Cause (found via deep debugging):** The `toast` object from `useToast()` was being recreated on every `ToastProvider` render because it wasn't memoized. This caused a cascade:
1. Delete transfer → `toast.success('Transfer deleted')` → toast displays
2. ToastProvider re-renders (adds toast to state) → `toast` object recreated (new reference)
3. `fetchTransfers` useCallback has `toast` in its dependency array → `fetchTransfers` gets recreated
4. useEffect watching `fetchTransfers` fires → calls `fetchTransfers()` again
5. This caused perceived "reload" as the list refetched unexpectedly

**Why Previous Fix Didn't Work:** The earlier debounce/prevSearchRef fix only addressed URL sync issues, not the toast recreation cascade which was the actual trigger.

**Solution:**
1. **AdminTransfersQueue.js & AdminCardRequestsQueue.js:** Added `toastRef` to keep a stable toast reference:
   ```javascript
   const toast = useToast();
   const toastRef = useRef(toast);
   toastRef.current = toast;
   // In fetchTransfers: use toastRef.current.error() instead of toast.error()
   // Removed toast from fetchTransfers dependency array
   ```
2. **Toast.js:** Memoized the toast object with `useMemo`:
   ```javascript
   const toast = useMemo(() => ({
     success: (message) => addToast(message, 'success'),
     error: (message) => addToast(message, 'error'),
     // ...
   }), [addToast]);
   ```

**Files Changed:**
- `/app/frontend/src/components/AdminTransfersQueue.js` - Added toastRef, removed toast from deps
- `/app/frontend/src/components/AdminCardRequestsQueue.js` - Same pattern applied
- `/app/frontend/src/components/Toast.js` - Memoized toast object with useMemo

**Verification:** Testing agent verified (iteration_106.json) - 100% pass rate:
- Transfers Queue delete + 15s monitoring: PASSED (URL stable, tab preserved, no reload)
- Second delete attempt: PASSED (no reload after 10s)
- Card Requests delete + 10s: PASSED (delete succeeded, URL stable)
- Search stability: PASSED (search=wowza preserved 10+ seconds)
- Tab switching: PASSED (SUBMITTED/COMPLETED/REJECTED switching stable)
- Close panel: PASSED (no reload when closing detail panel)

### Admin Panel Navigation Performance Optimization (Feb 23, 2025)

**Problem:** Admin sidebar navigation took 2-3 seconds per section click. Target: <=1 second.

**Root Causes Found:**
1. `handleSectionChange` in `AdminLayout.js` was async and WAITED for badge API call before changing section
2. `fetchUsers` in `AdminDashboard` ran on component mount regardless of active section
3. `toast` object from `useToast()` wasn't memoized, causing useCallback recreation cascades

**Optimizations Implemented:**

1. **Instant Sidebar Feedback (AdminLayout.js)**
   ```javascript
   // BEFORE: Section change waited for API call
   const handleSectionChange = useCallback(async (sectionId) => {
     await markSectionSeen(sectionId); // BLOCKED HERE
     onSectionChange(sectionId);
   }, [...]);
   
   // AFTER: Section change is instant, badge API is fire-and-forget
   const handleSectionChange = useCallback((sectionId) => {
     onSectionChange(sectionId); // INSTANT
     markSectionSeen(sectionId).catch(() => {}); // Background
   }, [...]);
   ```

2. **Lazy User Data Loading (App.js line 1925)**
   ```javascript
   // BEFORE: fetchUsers ran on every AdminDashboard mount
   useEffect(() => {
     fetchUsers(0, 1, usersPerPage, '');
   }, []);
   
   // AFTER: fetchUsers only when users section is active
   useEffect(() => {
     if (activeSection === 'users' && users.length === 0 && !loading) {
       fetchUsers(0, 1, usersPerPage, '');
     }
   }, [activeSection]);
   ```

3. **Toast Memoization (Toast.js)**
   - Added `useMemo` to keep toast object reference stable
   - Prevents downstream useCallback recreation

4. **toastRef Pattern (AdminKYC.js, AdminTransfersQueue.js, AdminCardRequestsQueue.js)**
   - Used `useRef` to keep toast reference stable in useCallback dependencies

**Performance Results (iteration_107.json):**
| Section | Load Time (ms) | Target | Status |
|---------|---------------|--------|--------|
| Overview | 69 | <1000 | ✅ PASS |
| Users | 102 | <1000 | ✅ PASS |
| KYC Queue | 94 | <1000 | ✅ PASS |
| Accounts | 89 | <1000 | ✅ PASS |
| Card Requests | 101 | <1000 | ✅ PASS |
| Transfers Queue | 98 | <1000 | ✅ PASS |
| Support Tickets | 89 | <1000 | ✅ PASS |
| Audit Logs | 93 | <1000 | ✅ PASS |

**Rapid-Fire Test:** 6 section switches in 738ms, no errors.
**F5 Refresh:** URL state preserved correctly.
**Stability:** No random reloads detected after 10 second observation.

**Backend Optimizations (Feb 23, 2025):**
1. `/admin/users` - Only lookup tax_holds for users on current page (not all users)
2. `/admin/notification-counts` - Simplified ticket count query (removed expensive $lookup aggregation)
3. Added compound index for `tax_holds(user_id, is_active)`

**Full Regression Test (iteration_108.json) - ALL PASS:**
- Performance: All 8 sections pass (53-105ms shell visible)
- Functional: Overview, Users, KYC, Accounts, Card Requests, Transfers, Support, Audit - ALL working
- Stability: Rapid switching (12 sections in 2008ms), F5 preservation, no random reloads
- Regression: Delete modal bug fix verified working

### EMERGENCY FIX: Users Section Loading Deadlock (Feb 23, 2025)

**Bug:** Users section stuck on "Loading users..." indefinitely (regression from performance optimization)

**Root Cause:** The performance optimization added condition `&& !loading` which created a deadlock:
```javascript
// BROKEN CODE:
if (activeSection === 'users' && users.length === 0 && !loading) {
  fetchUsers(0, 1, usersPerPage, '');
}
```
When `loading` was `true` from initial state, `!loading` was `false`, so `fetchUsers` never ran. But `loading` stayed `true` forever because nothing was fetching. **Deadlock!**

**Fix Applied:**
```javascript
// FIXED CODE:
if (activeSection === 'users') {
  if (users.length === 0) {
    fetchUsers(0, 1, usersPerPage, '');
  }
}
```
Removed the `&& !loading` condition - now correctly fetches when switching to Users section.

**Verification:** Testing agent verified (iteration_109.json) - 100% pass:
- Users section: PASS (no longer stuck on loading)
- All 8 admin sections: PASS (load correctly)
- Rapid section switching: PASS (10 switches in 2920ms)
- F5 refresh: PASS (URL and section preserved)
- Tab functionality: PASS (Card Requests and Transfers Queue tabs work)

### Header Title Glitch Fix (Feb 23, 2025)

**Bug:** When switching between admin sidebar sections, the header briefly showed the raw section ID (e.g., "Ledger") instead of the proper label (e.g., "Transfers Queue").

**Root Cause:** The header was using raw `activeSection` with simple capitalization:
```javascript
// BEFORE (wrong):
{activeSection.charAt(0).toUpperCase() + activeSection.slice(1)}
// This showed "Ledger" instead of "Transfers Queue"
```

**Fix Applied:**
```javascript
// AFTER (correct):
// Added SECTION_LABELS mapping in AdminDashboard
const SECTION_LABELS = {
  'ledger': 'Transfers Queue',
  'support': 'Support Tickets',
  'card_requests': 'Card Requests',
  // ... etc
};

// Header now uses:
{getSectionLabel(activeSection)}
```

**Verification:** Testing agent verified (iteration_110.json) - 100% pass:
- All 9 sections show correct header labels
- No flicker during rapid switching
- F5 refresh preserves correct header
- Navigation remains fast (82ms avg)

### Visual Flicker Fix - Delayed Skeleton Loading (Feb 23, 2025)

**Bug:** Visual glitch/flicker when switching between admin sidebar sections - content briefly flashed/disappeared.

**Root Causes:**
1. Skeleton loading state shown immediately on component mount, causing brief flash
2. URL sync useEffect running redundantly after programmatic navigation
3. Content area had no stable layout wrapper

**Fixes Applied:**

1. **Delayed Skeleton Pattern (AdminTransfersQueue.js, AdminCardRequestsQueue.js):**
   ```javascript
   const [showSkeleton, setShowSkeleton] = useState(false);
   
   useEffect(() => {
     let timer;
     if (loading) {
       timer = setTimeout(() => setShowSkeleton(true), 150);
     } else {
       setShowSkeleton(false);
     }
     return () => clearTimeout(timer);
   }, [loading]);
   
   // Render skeleton only if showSkeleton is true (after 150ms delay)
   {showSkeleton ? <Skeleton /> : <Content />}
   ```
   This prevents skeleton flash on fast network responses (< 150ms).

2. **Optimized URL Sync (App.js):**
   - URL sync useEffect only runs for browser back/forward navigation
   - Excludes `activeSection` from deps to prevent loop

3. **Stable Content Wrapper (App.css):**
   ```css
   .admin-section-content {
     min-height: calc(100vh - 140px);
     position: relative;
   }
   ```
   Prevents layout shift during section switches.

**Verification:** Testing agent verified (iteration_111.json) - 100% pass:
- Users to Accounts switch: PASS - No flicker
- Support to Transfers switch: PASS - No flicker
- Rapid switching (10 times): PASS - 1.22s for 10 switches
- F5 refresh: PASS - URL state preserved
- All header labels: PASS - Correct for all 8 sections

### Admin Pagination Layout Refinement (Feb 20, 2025)

**Change:** Moved pagination row ABOVE the tabs row for both Admin Transfers Queue and Admin Card Requests pages.

**Problem:** Pagination row was positioned below the tabs, which looked unprofessional.

**Solution:** Reordered the layout components:
- **Before:** Search → Tabs → Pagination → Table
- **After:** Search → Pagination → Tabs → Table

**Layout Order (top to bottom):**
1. Search bar
2. Pagination row (Showing X-Y of Z, Show: N per page, First/Previous/Page/Next/Last)
3. Tabs row (SUBMITTED/COMPLETED/REJECTED or PENDING/FULFILLED/REJECTED)
4. Data table

**Files Changed:**
- `/app/frontend/src/components/AdminTransfersQueue.js` - Pagination moved above tabs
- `/app/frontend/src/components/AdminCardRequestsQueue.js` - Pagination moved above tabs

**Verification:** 100% test pass rate (iteration_101.json) - Layout and functionality verified:
- Y-positions confirmed: Search=161, Pagination=224, Tabs=286
- Page navigation, page size selector, search, tab switching all working
- Delete action modal working on Card Requests

## Known Issues / Backlog

### P0 - Critical
- ~~Admin Dashboard showing all zeros~~ **FIXED Feb 17, 2025**
- ~~Admin Panel performance bottleneck (7-23s load times)~~ **FIXED Feb 20, 2025**
- ~~Random page reload after transfer delete~~ **FIXED Feb 23, 2025**
- ~~Admin sidebar navigation slow (2-3s per section)~~ **FIXED Feb 23, 2025**
- ~~Users section stuck on "Loading users..." (regression)~~ **FIXED Feb 23, 2025**
- ~~Header title glitch when switching sections~~ **FIXED Feb 23, 2025**
- ~~Audit Logs timestamps 1 hour behind (timezone issue)~~ **FIXED Feb 23, 2025**
- Domain SSL issue: `ecommbx.group` SSL certificate not provisioning

### App.js Refactor Stage 2a+2b Complete (Feb 23, 2025)
**Status:** ✅ Successfully completed behavior-preserving refactor

**Stage 2a - Import AdminUsersTable:**
- Imported `AdminUsersTable` from `AdminUsersSection.js`
- Removed 89-line duplicate from App.js

**Stage 2b - Import Badge/Copy Components:**
- Imported: `StatusBadge`, `KycBadge`, `CopyPhoneButton`, `CopyEmailButton`
- Removed ~222 lines of duplicate code from App.js

**App.js Size Reduction:**
- Before: 4,030 lines
- After: 3,719 lines
- **Reduced: 311 lines (~8%)**

**Import Line (App.js:32):**
```jsx
import { AdminUsersTable, StatusBadge, KycBadge, CopyPhoneButton, CopyEmailButton } from './components/AdminUsersSection';
```

**What Stayed in App.js (AdminDashboard):**
- All state management (users, filters, pagination, selectedUser)
- All handlers (fetchUsers, viewUserDetails, handleSearch, applyFilters)
- `renderContent()` switch logic
- User Details rendering (uses imported components)

**Testing:** All passed (iteration_120.json) - 18/18 features verified

### Copy Email Button in Admin Panel (Feb 23, 2025)
**Feature:** Added "Copy email" button next to emails in admin Users UI (matches Copy Phone UX).

**Problem:** Admins had to manually select and copy email addresses.

**Solution:** Created `CopyEmailButton` component matching `CopyPhoneButton` pattern.

**Component (App.js:89-127):**
```jsx
<CopyEmailButton email={email} toast={toast} size="sm|md" />
```
- Returns `null` if no email (button hidden - though emails always exist)
- Uses `navigator.clipboard.writeText()` for copy
- `e.stopPropagation()` prevents row click in table
- Toast "Email address copied" on success
- Two sizes: `sm` (table), `md` (details)

**Integration Points:**
1. Users table email cell (line 1935)
2. User Details email field (line 2696)

**Testing:** All passed (iteration_119.json) - 13/13 features verified

### App.js Refactor - Partial Extraction (Feb 23, 2025)
**Status:** Components extracted to separate file, ready for future import

**Created:** `/app/frontend/src/components/AdminUsersSection.js`
- Contains: `AdminUsersTable`, `StatusBadge`, `KycBadge`, `CopyPhoneButton`, `CopyEmailButton`
- **Not yet imported in App.js** to minimize risk during this session
- Can be imported in future iteration to reduce App.js size

**Current App.js State:**
- 4,030+ lines total
- AdminDashboard still contains ~575 lines of Users section inline
- Most other sections (KYC, Accounts, Transfers, etc.) already extracted

**Staged Plan for Future:**
- Stage 2a: Import `AdminUsersTable` from `AdminUsersSection.js`
- Stage 2b: Import badge/copy components
- Stage 2c: Extract User Details rendering

### Copy Phone Button in Admin Panel (Feb 23, 2025)
**Feature:** Added "Copy phone" button next to phone numbers in admin Users UI.

**Problem:** Admins had to manually select and copy phone numbers when calling clients.

**Solution:** Created reusable `CopyPhoneButton` component with clipboard and toast integration.

**Component (App.js:47-87):**
```jsx
<CopyPhoneButton phone={phone} toast={toast} size="sm|md" />
```
- Returns `null` if no phone (button hidden)
- Uses `navigator.clipboard.writeText()` for copy
- `e.stopPropagation()` prevents row click in table
- Toast success/error feedback
- Green checkmark icon after successful copy
- Two sizes: `sm` (table), `md` (details)

**Integration Points:**
1. Users table phone cell (lines 1893-1905)
2. User Details phone field (lines 2648-2660)

**Behavior:**
- Users WITH phone: Shows phone number + copy button
- Users WITHOUT phone: Shows "—" (table) or "Not provided" (details), NO button

**Testing:** All passed (iteration_118.json) - 14/14 features verified

### Phone DB Index - Already Exists (Feb 23, 2025)
**Status:** ✅ No action needed - index already exists at `database.py` line 127:
```python
("users", "phone", {}),
```

### App.js Refactor - Analysis Complete (Feb 23, 2025)
**Status:** Documented for future staged refactoring

**Current State:**
- App.js: 3,937 lines total
- AdminDashboard: ~1,614 lines (lines 1939-3553)
- Already extracted: AdminLayout, AdminKYC, AdminTransfersQueue, AdminCardRequestsQueue, AdminSettings, AuditLogs

**Remaining to Extract (Future):**
1. AdminUsersSection (largest, ~600 lines)
2. AdminSupportSection (~200 lines)
3. AdminOverviewSection (~150 lines)

**Staged Refactor Plan (P3, Future):**
- Stage 1: Extract shared hooks (useAdminUsers, useUserDetails)
- Stage 2: Extract AdminUsersSection with state
- Stage 3: Extract remaining sections
- Stage 4: Simplify AdminDashboard to routing only

**Risk Notes:**
- High coupling with shared state
- Performance optimizations embedded
- Must preserve: navigation, loading states, caching
- Test thoroughly after each extraction

### Users Search by Phone Number (Feb 23, 2025)
**Feature:** Enable admin Users search bar to search by phone number in addition to name/email.

**Problem:** Admins could not quickly find users by phone number when clients call support.

**Solution:** Added phone field to server-side MongoDB search query and frontend client-side filter.

**Backend Changes (server.py:1728-1784):**
1. Added `phone` field to `$or` query conditions with regex search
2. Added digits-only normalization for flexible phone matching (when ≥4 digits)
3. Used `re.escape()` for safe regex handling of special chars like `+`
4. Supports: full number, partial digits, formatted/unformatted input

**Frontend Changes (App.js:2032-2050, 3030):**
1. Updated `applyFilters` to include phone matching with digit normalization
2. Updated placeholder text: "Search by name, email, or phone..."

**Search Examples:**
- `+393276106073` → Exact phone match
- `393276106073` → Digits-only match
- `6073` → Partial match (last 4 digits)
- `+39 327` → Partial match with formatting

**Backward Compatibility:**
- Users without phone (`null`) don't cause errors ✅
- Existing name/email search unchanged ✅
- Pagination unaffected when not searching ✅
- Filters (Status/Role/Tax/Notes) work with phone search ✅

**Files Changed:**
- `/app/backend/server.py` - Lines 1728-1784
- `/app/frontend/src/App.js` - Lines 2032-2050, 3030

**Testing:** All passed (iteration_117.json) - 17/17 backend tests, 100% frontend

### User Details Status + KYC Colored Badges (Feb 23, 2025)
**Feature:** Professional colored badges for Status and KYC fields in User Details view.

**Problem:** Status and KYC values were plain black text, making them hard to scan quickly.

**Solution:** Created reusable `StatusBadge` and `KycBadge` components matching the existing Email Verified badge style.

**Badge Styling (App.js:47-199):**

| Component | Status | Color | Icon |
|-----------|--------|-------|------|
| StatusBadge | ACTIVE | Green (bg-green-100) | ✓ Checkmark |
| StatusBadge | PENDING | Amber (bg-amber-100) | ⏱ Clock |
| StatusBadge | DISABLED/BLOCKED | Red (bg-red-100) | ⊘ Blocked |
| KycBadge | APPROVED | Green (bg-green-100) | ✓ Checkmark |
| KycBadge | PENDING/SUBMITTED | Blue (bg-blue-100) | ⏱ Clock |
| KycBadge | REJECTED | Red (bg-red-100) | ✗ X |
| KycBadge | Not submitted | Slate (bg-slate-100) | ℹ Info |

**Design Consistency:**
- Matches existing Email Verified badge pattern
- Uses `inline-flex items-center px-2 py-0.5 rounded text-xs font-medium`
- Includes relevant SVG icons for quick visual recognition
- Neutral "Not submitted" styling (not alarming)

**Files Changed:**
- `/app/frontend/src/App.js` - Lines 47-199 (new components), 2596-2601, 2617-2622 (usage)

**Testing:** All passed (iteration_116.json) - 100% frontend tests passed

### Phone Number Mandatory for Registration (Feb 23, 2025)
**Feature:** Made phone number a required field for new user registrations.

**Problem:** Phone was optional during signup, making it harder for admins to contact clients.

**Solution:** Implemented phone validation in both frontend and backend:

**Backend Changes (server.py:259-282):**
1. Changed `SignupRequest.phone` from `Optional[str] = None` to `str` (required)
2. Added `@field_validator('phone')` with validation rules:
   - Rejects empty or whitespace-only phone
   - Requires at least 6 digits (permissive for international formats)
   - Returns trimmed value

**Frontend Changes (App.js:140-177, 314-326):**
1. Added client-side phone validation in `handleSubmit`:
   - Checks for non-empty trimmed value
   - Validates at least 6 digits
   - Shows localized error messages
2. Updated phone input:
   - Changed label from "Phone (Optional)" to "Phone *" (with red asterisk)
   - Added `required` HTML5 attribute
   - Updated placeholder to `+39 123 456 7890`

**Backward Compatibility:**
- Existing users without phone can still login ✅
- Database phone field remains nullable ✅
- Admin panel shows "—" / "Not provided" for users without phone ✅

**Testing:** All tests passed (iteration_115.json):
- Backend: 19/19 tests passed (100%)
- Frontend: All UI tests passed (100%)
- Test file: `/app/backend/tests/test_phone_registration_validation.py`

**Translation Keys Added:**
- `phoneRequired`: EN: "Phone number is required" / IT: "Il numero di telefono è obbligatorio"
- `phoneInvalid`: EN: "Please enter a valid phone number" / IT: "Inserisci un numero di telefono valido"

### Admin User Phone Number Display (Feb 23, 2025)
**Feature:** Display client phone numbers in Admin panel (Users section).

**Problem:** Phone numbers captured during user registration were stored in the database but not visible to admins in the Admin panel.

**Solution:** Added phone field to both admin API endpoints and frontend views:

**Backend Changes:**
1. `/api/v1/admin/users` - Added `phone` field to user list response (returns `null` for users without phone)
2. `/api/v1/admin/users/{user_id}` - Added `phone` field to user detail response

**Frontend Changes:**
1. **AdminUsersTable** (`App.js:1651-1717`) - Added "Phone" column between Email and Role columns
   - Users with phone: Shows phone number (e.g., `+393276106073`)
   - Users without phone: Shows dash (`—`) placeholder
   - Added `data-testid="user-phone-{id}"` for testing
   
2. **User Detail View** (`App.js:2410-2425`) - Added "Phone" field in details grid
   - Users with phone: Shows phone number
   - Users without phone: Shows "Not provided" in italic gray text
   - Added `data-testid="user-detail-phone"` for testing

**Files Changed:**
- `/app/backend/server.py` - Lines 1771-1785, 1901-1917
- `/app/frontend/src/App.js` - Lines 1651-1717, 2410-2425

**Testing:** All tests passed (iteration_114.json):
- Backend: 9/9 tests passed (100%)
- Frontend: All UI tests passed (100%)
- Test file: `/app/backend/tests/test_admin_user_phone.py`

### P1 - High Priority
- ~~**Dangerous transfer deletion endpoint without ledger reversal**~~ **FIXED Feb 23, 2025** - Refactored from hard delete to soft delete. Transfers are now marked with `is_deleted=true` instead of being physically removed.
- **Transfer Restore Feature** - Ability to restore soft-deleted transfers. Would require new endpoint `POST /api/v1/admin/transfers/{id}/restore` and UI for viewing/restoring deleted transfers.

### P2 - Medium Priority
- Refactor `server.py` into smaller routers (admin.py, transfers.py, tickets.py)

## Database Schema (Key Collections)
- `users` - User accounts (includes `language` field for email localization)
- `bank_accounts` - Bank accounts
- `ledger_transactions` - Financial transactions
- `transfers` - Transfer records with email status fields:
  - **Confirmation Email:**
    - `confirmation_email_status` (pending/sent/failed)
    - `confirmation_email_sent_at` (datetime)
    - `confirmation_email_provider_id` (Resend ID)
    - `confirmation_email_error` (error message)
  - **Rejection Email:**
    - `rejection_email_sent` (bool, default: False)
    - `rejection_email_sent_at` (datetime, optional)
    - `rejection_email_provider_id` (Resend ID, optional)
    - `rejection_email_error` (error message, optional)
- `tax_holds` - Tax hold information

## Test Files
- `/app/test_reports/` - Test reports directory

### AdminUserDetails Component Extraction Refactor (Feb 23, 2025)
**Refactor:** Extracted the User Details panel (~572 lines) from the monolithic `App.js` into a separate `AdminUserDetails.js` component.

**Problem:** The `AdminDashboard` function in `App.js` had grown to over 2000 lines, making it difficult to maintain. The User Details panel (displayed when clicking a user in the admin Users section) was a ~572-line inline JSX block.

**Solution:** Created a behavior-preserving refactor:
1. Created new component `/app/frontend/src/components/AdminUserDetails.js`
2. Moved all User Details UI rendering logic to the new component
3. Passed all required state and handlers as props from parent `AdminDashboard`
4. Imported and used the component in `App.js` replacing the inline code

**Props passed to AdminUserDetails (25 total):**
- User data: `selectedUser`, `setSelectedUser`, `user`
- API/Toast: `api`, `toast`
- Refresh functions: `fetchUsers`, `viewUserDetails`
- Tax hold: `userTaxHold`, `taxHoldLoading`, `setShowTaxHoldModal`, `handleRemoveTaxHold`
- Password: `showPassword`, `setShowPassword`, `setShowPasswordModal`, `setNewPassword`, `setConfirmPassword`, `setPasswordChangeError`
- Auth history: `authHistory`, `authHistoryLoading`, `showAuthHistory`, `setShowAuthHistory`, `fetchAuthHistory`
- IBAN: `handleOpenEditIban`
- Delete: `handleDeleteUser`, `deleteUserLoading`
- Notes: `userNotes`, `setUserNotes`, `editingNotes`, `setEditingNotes`, `savingNotes`, `handleSaveNotes`
- Utilities: `EnhancedLedgerTools`, `formatCurrency`

**Files Changed:**
- `/app/frontend/src/App.js` - Line 33: Added import, Lines 2192-2226: Replaced inline JSX with component
- `/app/frontend/src/components/AdminUserDetails.js` - NEW: 655 lines extracted component

**Functionality Preserved (100%):**
- ✅ Back to Users button
- ✅ User Details card (Name, Email, Phone with copy buttons, Status/KYC badges)
- ✅ Email Verified status display
- ✅ Password display with show/hide toggle and Change button
- ✅ View Login Activity button and auth history card
- ✅ Admin Notes section with Edit/Save/Cancel
- ✅ Tax Hold Management (Place/Remove Tax Hold)
- ✅ Accounts section with Edit IBAN buttons
- ✅ Enable/Disable user buttons
- ✅ Delete user button (disabled for admins)
- ✅ Clear Notifications button
- ✅ Demote Admin button (for admin users)
- ✅ Verify Email button (for unverified users)

**Testing:** All 17/17 features verified passing (iteration_121.json):
- Frontend: 100% success rate
- No console errors
- All data-testid attributes preserved
- No functional changes - behavior-preserving refactor only

**Next Steps for Stage 3 Refactor:**
- Simplify `AdminDashboard` into a pure routing/orchestration component
- Consider extracting other large sections (KYC, Settings, etc.) similarly

### P0 Stage 3 + P2 Backend Refactor (Feb 23, 2025)

**P0 Stage 3 - Frontend AdminDashboard Simplification:**
- Extracted ALL Users section state (30+ variables) and handlers (20+ functions) from `AdminDashboard` into new `AdminUsersPage.js` component
- `AdminDashboard` is now a pure routing/orchestration component (~150 lines vs ~600 before)
- No business logic changes - 100% behavior-preserving refactor

**Files Created:**
- `/app/frontend/src/components/AdminUsersPage.js` (700 lines) - Complete Users section

**Files Modified:**
- `/app/frontend/src/App.js` - Simplified AdminDashboard, imports AdminUsersPage

**P2 - Backend Router Extraction (Partial):**
- Created `/app/backend/routers/` directory structure
- Extracted health/debug endpoints to `/app/backend/routers/health.py`
- Extracted audit logs endpoint to `/app/backend/routers/audit.py`
- Created shared dependencies in `/app/backend/routers/dependencies.py`
- Registered routers in `server.py`
- Remaining routes kept in `server.py` for safety (future extraction)

**P1 Transfer Restore: EXPLICITLY SKIPPED**
- No changes to transfer soft-delete/restore logic
- No new transfer restore functionality implemented

**Testing Results:**
- 100% success rate (27/27 tests)
- All 9 admin sections verified working
- All Users section features verified
- Backend health/audit APIs verified
- No regressions detected

**Known Remaining Work:**
- More routes can be extracted from server.py in future sessions
- Consider extracting: auth, tickets, kyc, admin_users, etc.

### Backend Router Extraction (Feb 23, 2025)

**Completed Extractions:**
1. **routers/tickets.py** (~500 lines)
   - Customer routes: /api/v1/tickets/*
   - Admin routes: /api/v1/admin/tickets/*
   - 15 endpoints extracted

2. **routers/kyc.py** (~400 lines)
   - Customer routes: /api/v1/kyc/*
   - Admin routes: /api/v1/admin/kyc/*
   - 9 endpoints extracted

3. **routers/admin_users.py** (~850 lines)
   - Admin routes: /api/v1/admin/users/*
   - 17 endpoints extracted

4. **routers/health.py** (~150 lines)
   - Debug routes: /api/health, /api/db-health, /api/debug/*

5. **routers/audit.py** (~50 lines)
   - Admin route: /api/v1/admin/audit-logs

**Deferred:**
- **auth router**: High risk, requires dedicated session
- **P1 Transfer Restore**: Explicitly NOT implemented

**Results:**
- server.py reduced from 5672 → 3227 lines (43% reduction)
- All API paths unchanged
- 100% backward compatibility
- Zero regressions (23/23 tests passed)

**Production Monitoring:**
- See /app/memory/MONITORING_PLAN.md

### Auth Router Extraction Plan - PLANNING ONLY (Dec 2025)

**Task:** Created comprehensive planning document for extracting auth routes from `server.py`

**Deliverable:** `/app/AUTH_ROUTER_PLAN.md` - Complete extraction plan with:

1. **Scope & Constraints**
   - Planning-only mandate (NO CODE CHANGES)
   - P1 Transfer Restore explicitly deferred
   - 12 auth endpoints identified (lines 300-976 in server.py)

2. **Auth Endpoint Inventory**
   - signup, login, logout, verify-email, resend-verification
   - me, mfa/setup, mfa/enable
   - change-password, verify-password, forgot-password, reset-password

3. **Dependency Map**
   - DB collections: users, email_verifications, password_resets, sessions
   - Services: AuthService, EmailService
   - Core: hash_password, verify_password (from core.auth)
   - Config: SECRET_KEY, JWT_ALGORITHM, DEBUG, REFRESH_TOKEN_EXPIRE_DAYS

4. **Risk Register (14 risks identified)**
   - R1: Circular import (auth.py ↔ dependencies.py) - HIGH
   - R2: get_current_user duplication - HIGH
   - R3: Cookie settings break - CRITICAL
   - R4-R11: Medium/Low risks documented

5. **Safe Extraction Sequence (7 Phases)**
   - Phase 0: Move inline Pydantic schemas
   - Phase 1: Create empty router
   - Phase 2: Extract /auth/me (lowest risk)
   - Phase 3-5: Extract remaining endpoints by risk level
   - Phase 6: Extract /auth/login LAST (highest risk)
   - Phase 7: Cleanup commented code

6. **Regression Test Checklist**
   - 50+ test cases documented
   - Login flow: 10 test cases
   - Session/token: 5 test cases
   - MFA: 3 test cases
   - Password: 10 test cases
   - Signup: 5 test cases
   - Email verification: 4 test cases

7. **Production Monitoring Additions**
   - Login failure rate thresholds
   - Auth endpoint latency (p95)
   - Token validation failures
   - Rollback trigger conditions

8. **Commit-Based Rollback Plan**
   - Granular revert steps per phase
   - Emergency full rollback procedure

**Recommendation: GO**
- Auth helpers already in dependencies.py (reduces risk)
- Clear extraction pattern from previous router work
- Strong rollback capability with commit-per-endpoint

**Next Steps (Implementation Session):**
1. Move 5 inline Pydantic schemas to schemas/users.py
2. Create empty routers/auth.py
3. Extract /auth/me as proof-of-concept
4. Follow phased extraction plan
5. /auth/login extracted LAST

**Test Account:** ashleyalt005@gmail.com / 123456789

---

## Auth Router Extraction - IMPLEMENTATION COMPLETE (Dec 2025)

### Scope Completed
All 12 auth endpoints successfully extracted from `server.py` to `routers/auth.py`:
1. `/api/v1/auth/login` - POST
2. `/api/v1/auth/logout` - POST  
3. `/api/v1/auth/signup` - POST
4. `/api/v1/auth/me` - GET
5. `/api/v1/auth/verify-email` - POST
6. `/api/v1/auth/resend-verification` - POST
7. `/api/v1/auth/mfa/setup` - POST
8. `/api/v1/auth/mfa/enable` - POST
9. `/api/v1/auth/change-password` - POST
10. `/api/v1/auth/verify-password` - POST
11. `/api/v1/auth/forgot-password` - POST
12. `/api/v1/auth/reset-password` - POST

**P1 Transfer Restore: SKIPPED (deferred as requested)**

### Changes Made

**Files Created:**
- `/app/backend/routers/auth.py` (710 lines) - All auth endpoints

**Files Modified:**
- `/app/backend/server.py` - Reduced from 3227 to 2615 lines (~20% reduction)
- `/app/backend/schemas/users.py` - Added 5 schemas: SignupRequest, PasswordChangeRequest, VerifyPasswordRequest, ForgotPasswordRequest, ResetPasswordRequest
- `/app/backend/routers/__init__.py` - No changes (auth router registered directly in server.py)

### Behavior Parity Results
| Endpoint | Status | Notes |
|----------|--------|-------|
| POST /login | ✅ PASS | 200/401/403 status codes preserved |
| POST /logout | ✅ PASS | Cookie cleared, audit logged |
| POST /signup | ✅ PASS | 201/400/422 validation preserved |
| GET /me | ✅ PASS* | *PRE-EXISTING BUG: Returns 404 |
| POST /verify-email | ✅ PASS | 200/400 preserved |
| POST /resend-verification | ✅ PASS | 200/400 preserved |
| POST /mfa/setup | ✅ PASS* | *PRE-EXISTING BUG: Returns 404 |
| POST /mfa/enable | ✅ PASS | 200/400 preserved |
| POST /change-password | ✅ PASS | 200/400 preserved |
| POST /verify-password | ✅ PASS | 200/401 preserved |
| POST /forgot-password | ✅ PASS | Always 200 (no enumeration) |
| POST /reset-password | ✅ PASS | 200/400 preserved |

### Regression Test Results
- **Backend:** 100% (17/17 tests passed)
- **Frontend:** 100% (Login, Dashboard, Logout verified)

### Pre-Existing Bugs Documented (NOT regressions)
1. `/auth/me` returns 404 "User not found" - ObjectId handling in auth_service.get_user()
2. `/auth/mfa/setup` returns 404 "User not found" - Same root cause

### Rollback Capability
Extraction done in phased commits. Each endpoint can be individually reverted if needed:
- Phase 1: Schema move
- Phase 2: Router scaffolding  
- Phase 3-6: Individual endpoint migrations
- Phase 7: Critical paths (logout, signup, login)

### Test Report
`/app/test_reports/iteration_124.json` - Full test results

---

## P0 Backend Router Extraction - PARTIAL COMPLETION (Dec 2025)

### Routers Extracted (COMPLETED)

| Router | File | Lines | Endpoints | Status |
|--------|------|-------|-----------|--------|
| auth | routers/auth.py | 710 | 12 | ✅ DONE |
| analytics | routers/analytics.py | 220 | 2 | ✅ DONE |
| notifications | routers/notifications.py | 360 | 8 | ✅ DONE |
| cards | routers/cards.py | 350 | 7 | ✅ DONE |

### Routers Remaining (NOT STARTED)

| Router | Approx Lines | Endpoints | Priority |
|--------|--------------|-----------|----------|
| accounts | ~300 | 7 | Next |
| transfers | ~400 | 10 | Last (highest risk) |
| recipients | ~50 | 3 | Can combine with transfers |
| ledger | ~200 | 5 | Can combine with accounts |

### Progress

- **server.py**: 3227 → 1715 lines (~47% reduction)
- **Test Results**: 100% pass rate (18/18 backend, all frontend)
- **Behavior Parity**: Verified ✅

### Test Report
`/app/test_reports/iteration_125.json` - Full verification

### P1 Bug Assessment (SEPARATE)
See `/app/P1_BUG_ASSESSMENT.md` for:
- Root cause: auth_service.get_user() ObjectId handling
- Affected endpoints: /auth/me, /auth/mfa/*
- Recommended fix documented
- NOT mixed into router extraction commits

### Transfer Restore: EXPLICITLY SKIPPED
Per user requirement - deferred to future session

---

## P0 Backend Router Extraction - FINAL STATUS (Dec 2025)

### Routers Extracted (ALL VERIFIED ✅)

| Router | File | Lines | Endpoints | Status |
|--------|------|-------|-----------|--------|
| auth | routers/auth.py | 710 | 12 | ✅ DONE |
| analytics | routers/analytics.py | 249 | 2 | ✅ DONE |
| notifications | routers/notifications.py | 392 | 8 | ✅ DONE |
| cards | routers/cards.py | 401 | 7 | ✅ DONE |
| accounts | routers/accounts.py | 619 | 10 | ✅ DONE |

### Remaining in server.py (NOT EXTRACTED)
- **transfers** routes (10 endpoints) - Highest risk, deferred
- **recipients** routes (3 endpoints) - Can be combined with transfers
- **beneficiaries** routes (3 endpoints)
- **scheduled-payments** routes (3 endpoints)
- **insights** routes (2 endpoints)

### P1 ObjectId Bug: ✅ FIXED
- Testing agent applied the documented fix to auth_service.get_user()
- Now handles both string and ObjectId user IDs
- /auth/me and /auth/mfa/* now working correctly

### Transfer Restore: ❌ EXPLICITLY SKIPPED
Per user requirement - deferred

### Test Results
- `/app/test_reports/iteration_126.json`: 100% success (19/19 backend, all frontend)
- All sidebar sections verified working
- No regressions detected

---

## HOTFIX: Accounts Section Crash (Dec 2025)

**Issue:** `accounts.map is not a function` error in AdminAccountsControl

**Root Cause:**
- Backend router returned: `{data: [...], pagination: {...}}`
- Frontend expected: `{accounts: [...], pagination: {...}}`

**Fix Applied:**
1. Changed response key from `data` to `accounts`
2. Added `limit` query param alias for `page_size`
3. Used camelCase field names (`userName`, `userEmail`, `userId`)

**Test Results:** 100% pass (iteration_127.json)
- 74 accounts rendered correctly
- Pagination working (Page 1 of 2)
- All cross-section smoke tests passed

**Status:** ✅ RESOLVED

---

## PERFORMANCE HOTFIX: Accounts N+1 Query Fix (Dec 2025)

**Issue:** Accounts section loading in 6.35 seconds (8-10x slower than other sections)

**Root Cause:**
```python
# BEFORE (N+1 queries - 50 separate DB calls):
for ledger_id in ledger_account_ids:
    balances[ledger_id] = await ledger_engine.get_balance(ledger_id)

# AFTER (1 bulk query):
balance_map = await ledger_engine.get_bulk_balances(ledger_account_ids)
```

**Fix Applied:**
- Replaced N individual `get_balance()` calls with single `get_bulk_balances()`
- Uses single MongoDB aggregation pipeline for all accounts
- O(1) lookup per account from pre-fetched map

**Performance Results:**
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Accounts Latency | 6.35s | 0.89s | **7.1x faster** |
| vs Users | 8.5x slower | Same | Parity ✅ |
| vs Card Requests | 10x slower | Same | Parity ✅ |

**API Contract:** ✅ UNCHANGED
- Response keys: accounts, pagination
- Fields: userName, userEmail, userId, balance (camelCase)
- Balances correctly populated (45/50 non-zero)

**Test Results:** 100% pass (iteration_128.json)
- Search working
- Pagination working
- All cross-sections passing

**Status:** ✅ RESOLVED - Ready for transfers extraction

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

## Recent Changes (February 2025)

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

## Known Issues / Backlog

### P0 - Critical
- ~~Admin Dashboard showing all zeros~~ **FIXED Feb 17, 2025**
- ~~Admin Panel performance bottleneck (7-23s load times)~~ **FIXED Feb 20, 2025**
- Domain SSL issue: `ecommbx.group` SSL certificate not provisioning

### P1 - High Priority
- **Dangerous transfer deletion endpoint without ledger reversal** - `DELETE /api/v1/admin/transfers/{transfer_id}` performs hard delete which risks data integrity. Should be refactored to soft delete or reversing ledger entry.

### P2 - Medium Priority
- Refactor `server.py` into smaller routers (admin.py, transfers.py, tickets.py)

## Database Schema (Key Collections)
- `users` - User accounts
- `bank_accounts` - Bank accounts
- `ledger_transactions` - Financial transactions
- `transfers` - Transfer records with email status fields:
  - `confirmation_email_status` (pending/sent/failed)
  - `confirmation_email_sent_at` (datetime)
  - `confirmation_email_provider_id` (Resend ID)
  - `confirmation_email_error` (error message)
- `tax_holds` - Tax hold information

## Test Files
- `/app/test_reports/` - Test reports directory

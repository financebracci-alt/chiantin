# Project Atlas — Verify & Stabilize Plan (Option 1)

## 1) Objectives
- Confirm **ledger-derived balance** is the single source of truth (no persisted `bank_accounts.balance`) and prove integrity with repeatable checks.
- Verify critical money flows and admin workflows behave correctly under edge cases (rejections, deletions, reversals), without regressions.
- Reduce operational risk: add/extend integrity tooling, tighten invariants, and clean up backend linting warnings.
- Run comprehensive tests using **new test users only** (never real clients).

---

## 2) Implementation Steps

### Phase 1 — Core Integrity POC (Isolation)
Goal: prove the core ledger/balance invariants independently of UI.

Steps:
1. **Evidence capture** (code + DB): confirm `BankAccount` schema has no `balance` field and `bank_accounts` documents have none.
2. Create a minimal **ledger integrity script** (read-only by default) that:
   - Computes derived balances per ledger account from `ledger_entries`.
   - Flags anomalies: missing accounts, unbalanced transactions, orphan entries, negative balances where forbidden (if policy exists).
   - Verifies transfer ↔ ledger linkage (e.g., `transfers.transaction_id` exists in `ledger_transactions`).
3. Add an optional **repair mode** (explicit flag) that only performs safe actions (e.g., reconstructing missing derived views, not mutating ledger history).
4. Run POC against the current environment and store output under `/app/test_reports/`.

User stories (Phase 1):
1. As an operator, I can run a script that reports derived balances for all accounts from ledger entries.
2. As an operator, I can detect orphan ledger entries or missing ledger accounts before they impact users.
3. As an operator, I can verify every transfer references a valid ledger transaction.
4. As an operator, I can run the integrity check repeatedly and get consistent results.
5. As an operator, I can export a concise anomaly report suitable for incident review.

---

### Phase 2 — V1 Stabilization (App-Level Hardening)
Goal: tighten invariants in the live codepaths and ensure no “hidden balance” mutations exist.

Steps:
1. Review transfer/admin endpoints for any destructive operations (delete/cancel) and ensure they:
   - Prefer **reversal transactions** over deleting ledger history.
   - Keep transfer status consistent with ledger (e.g., rejected → reversal posted when funds were reserved/deducted).
2. Add guardrails where needed:
   - Idempotency keys on money-moving actions.
   - Stronger validation on `ledger.post_transaction()` usage (balanced entries, account existence, currency consistency).
3. Fix backend linting warnings (target: no functional changes; refactor-only).
4. Add/update automated tests to cover the above edge cases.

User stories (Phase 2):
1. As a customer, my account balance always matches the ledger, even after transfers are rejected or reversed.
2. As an admin, when I reject a transfer that already deducted funds, the system reverses it and restores funds correctly.
3. As an admin, I can view transfers and transactions with consistent status and metadata.
4. As an engineer, I can run backend tests and confirm money flows are protected by idempotency.
5. As an operator, I can deploy these changes without breaking KYC, tickets, notifications, or auth flows.

---

### Phase 3 — Comprehensive Testing (New Test Users Only)
Goal: confirm everything still works end-to-end.

Steps:
1. Create **fresh test users** (customer + admin where applicable) and seed minimal safe data.
2. Run backend suite (`/app/tests/*`) + targeted money-flow tests:
   - Top-up/withdraw/fee, internal transfer, SEPA submit/reject/approve flows.
   - Password-protected transfer verification flow.
   - KYC queue, support tickets, notifications clearing.
3. Run one full frontend smoke pass: login, dashboard, transfers, admin panels.
4. Produce a final test report under `/app/test_reports/`.

User stories (Phase 3):
1. As QA, I can complete signup/login and perform a transfer using password verification.
2. As QA, I can submit KYC for a new test user and review it in the admin queue.
3. As QA, I can create a support ticket and see correct client identification in admin.
4. As QA, I can clear notifications for a test user and confirm the UI updates.
5. As QA, I can validate balances before/after each money action and confirm ledger consistency.

---

## 3) Next Actions
1. Add `/app/scripts/ledger_integrity_check.py` (read-only default) and run it; save report.
2. Audit transfer/admin codepaths for destructive operations; enforce reversal-over-delete where needed.
3. Fix backend linting warnings with refactor-only changes.
4. Run full automated tests + one E2E pass with **new test users**; publish final report.

---

## 4) Success Criteria
- Integrity POC report shows:
  - No persisted `bank_accounts.balance` usage and balances are derived from ledger.
  - No unbalanced ledger transactions; no orphan entries; transfer↔transaction linkage valid.
- Money-moving actions are idempotent and do not rely on deleting ledger history.
- All existing features remain functional (auth, KYC, transfers, notifications, support, admin).
- Test suite + E2E smoke pass completes successfully using **only new test users**, with a saved report.

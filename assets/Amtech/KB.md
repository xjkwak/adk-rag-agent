# CoderoadERP AI Copilot — Knowledge Base (KB)

> **Version:** 1.0 | **Classification:** Internal — Demo Use  
> **Purpose:** Indexed reference library used by the AI Copilot to execute Route A (self-service resolution) responses. Each article maps to one or more user roles and contains a root cause analysis and a verified step-by-step resolution workflow.

---

## Index

| KB ID | Title | Affected Module | Primary Role |
|-------|-------|-----------------|--------------|
| KB-001 | Connection Timeout Error | All Modules | All Roles |
| KB-002 | PDF / Report Generation Failure | Billing, Logistics | Billing Clerk, Sales Manager |
| KB-003 | Greyed-Out / Inactive Button | All Modules | All Roles |
| KB-004 | Credit Limit Block on Sales Order | Billing, Sales | Billing Clerk, Sales Manager |
| KB-005 | Thermal Printer Routing Failure | Logistics | Logistics Manager |
| KB-006 | Stuck Roll Stock Inventory Allocation | Production | Plant Operator |
| KB-007 | User Account Lockout — Failed Login Attempts | Security / Admin | IT System Administrator |
| KB-008 | Module-to-Module Data Sync Failure | Integration Layer | IT System Administrator |
| KB-009 | Scheduled Nightly Job — Partial Execution Warning | IT Operations | IT System Administrator |
| KB-010 | Contract Price Table Mismatch on Sales Order | Sales, Billing | Sales & Account Manager |
| KB-011 | Customer Account Duplicate Entry Block | CRM, Billing | Sales & Account Manager, Billing Clerk |
| KB-012 | Dashboard / KPI Panel Not Loading — Browser Cache Issue | All Modules | All Roles |

---

## KB-001 — Connection Timeout Error

**Applies To:** All modules (CoderoadERP + CoderoadOPS)  
**Typical Trigger:** Automated server maintenance cycling or corporate VPN session expiration.  
**Environments Affected:** LIVE and TEST

### Root Cause Analysis

CoderoadERP uses persistent WebSocket connections to maintain real-time session state. When the corporate VPN client drops its tunnel — either due to idle timeout, a local network change, or a scheduled server maintenance window — the active session loses its authenticated route and returns a generic connection timeout screen.

### Step-by-Step Resolution

1. Close all active CoderoadERP / CoderoadOPS browser tabs completely.
2. Open the corporate VPN client and verify that the status indicator shows **Connected — Active**.
3. If the VPN shows disconnected, re-authenticate using your SSO corporate credentials.
4. Wait 30 seconds for the secure tunnel to re-establish.
5. Navigate back to the CoderoadERP environment URL and log in normally.
6. If the timeout persists after reconnection, contact the IT System Administrator — the server may be in a scheduled maintenance window.

---

## KB-002 — PDF / Report Generation Failure

**Applies To:** Billing module (invoice downloads), Logistics module (BOL documents), Sales module (customer statements)  
**Typical Trigger:** Web browser pop-up blocker preventing the document generation script from opening a new window.  
**Environments Affected:** LIVE and TEST

### Root Cause Analysis

CoderoadERP generates PDF documents (invoices, statements, bills of lading) by launching a secure background script that opens a temporary browser window. Most corporate browser security policies block third-party pop-up windows by default, silently canceling the generation event. The user sees no error — the button simply appears to do nothing.

### Step-by-Step Resolution

1. Look at the top-right corner of the browser address bar for a **small pop-up blocked icon** (a window with a red X or warning indicator).
2. Click the icon and select **"Always allow pop-ups and redirects from [site URL]"**.
3. Click **Done** to save the browser exception.
4. Return to the document (invoice, statement, BOL) and click the **Generate / Download** button again.
5. The PDF should now open in a new browser tab for download or printing.
6. If no pop-up icon appears and the issue persists, clear the browser cache (`Ctrl + Shift + Delete`) and repeat from step 1.

---

## KB-003 — Greyed-Out / Inactive Button

**Applies To:** All modules — any action button that appears non-clickable  
**Typical Trigger:** User role permissions do not meet the authorization threshold required for that specific action or document value.  
**Environments Affected:** LIVE and TEST

### Root Cause Analysis

CoderoadERP enforces a multi-tier security model. Each action button (Post, Approve, Release, Start, Transfer) is bound to a minimum authorization level. If the logged-in user's profile does not carry sufficient clearance — or if the document's value exceeds the user's delegated approval limit — the system automatically disables the button at the UI level to prevent unauthorized actions.

### Step-by-Step Resolution

1. Navigate to **My Profile → Permissions & Authorization Levels** in the top-right user menu.
2. Review the **Action Thresholds** table. Identify the specific action (e.g., "Post Sales Order", "Release Production Order") and the minimum clearance level required.
3. **Option A — Self-service:** If your role should grant access, click **"Request Temporary Elevation"** and submit a justification note. Your direct supervisor will receive an in-system approval request.
4. **Option B — Manager override:** Ask a floor manager or supervisor to enter their **on-screen override PIN** directly on your workstation to authorize the specific action for this session.
5. If neither option resolves the issue, create a support ticket — the permission table may require a system-level correction by the IT Administrator.

---

## KB-004 — Credit Limit Block on Sales Order

**Applies To:** Billing module, Sales module  
**Typical Trigger:** Customer account outstanding balance exceeds the approved credit threshold in the global credit matrix.  
**Environments Affected:** LIVE only (financial controls are not enforced in TEST)

### Root Cause Analysis

CoderoadERP applies a real-time credit check against the customer's account when a sales order or invoice is posted. If the customer's total open balance (including pending, partially paid, and overdue invoices) exceeds their approved credit line, the system triggers a soft block to prevent additional exposure. This is a financial control, not a system error.

### Step-by-Step Resolution

1. Navigate to **Finance Workspace → Customer Accounts → Credit & Aging Status**.
2. Search for the specific **Customer ID** to pull the full credit profile.
3. Review the **Open Balance** column and the **Approved Credit Line** field.
4. **Option A — Unallocated payments:** Check the **Unallocated Receipts** tab. If the customer has sent a wire transfer not yet applied, allocate it to reduce the open balance first.
5. **Option B — Temporary credit extension:** If the business justifies it, click **"Apply Temporary Credit Extension"**, enter the amount and expiration date, and submit for Finance Manager approval.
6. Once the credit check clears, return to the sales order or invoice and proceed with posting.

---

## KB-005 — Thermal Printer Routing Failure (Bill of Lading)

**Applies To:** Logistics module — Bill of Lading (BOL) and Load Guide printing  
**Typical Trigger:** The logistics workstation lost its direct connection mapping to the dock thermal printer's network IP address.  
**Environments Affected:** LIVE only

### Root Cause Analysis

CoderoadERP's logistics print routing system supports two modes: **Spooler Pool** (routes through the Windows print queue) and **Direct Network IP** (sends the print job directly to the thermal printer's IP). After a network restart or workstation reboot, the system sometimes reverts to Spooler Pool mode, which loses the direct connection to dock-specific thermal printers.

### Step-by-Step Resolution

1. On the affected logistics workstation, navigate to **Logistics Setup → Workstation Print Configuration → Local Print Routing**.
2. Check the **Default Printer Destination** field. If it reads **"Spooler Pool"**, this is the cause.
3. Change the destination to **"Direct Network IP"**.
4. In the **Printer IP Address** field, confirm the dock's thermal printer IP is correctly listed (check the printer's configuration label if uncertain).
5. Click **Save Configuration**.
6. Run a **Line-Feed Test Print** to confirm the connection is live.
7. Return to the BOL or Load Guide and proceed with printing.

---

## KB-006 — Stuck Roll Stock Inventory Allocation

**Applies To:** Production module (CoderoadOPS) — Roll Stock and Raw Material Inventory  
**Typical Trigger:** An aborted or force-closed paper optimization session left an unreleased database row lock on a batch record.  
**Environments Affected:** LIVE and TEST

### Root Cause Analysis

CoderoadOPS uses transactional row locks to ensure that no two optimization sessions can modify the same raw material batch simultaneously. If a session is interrupted (network drop, browser close, system crash), the lock remains active in the database even though no user is actively holding it. This causes the batch to appear permanently allocated to a "ghost" session.

### Step-by-Step Resolution

1. Navigate to **CoderoadOPS → Inventory Utilities → Active Session Monitor**.
2. In the search field, enter the specific **Item Code** or **Batch Number** (e.g., RB-9902).
3. The monitor will display all active locks. Identify the entry marked with **"Orphaned"** or **"No Active User"** status.
4. Highlight the orphaned session row.
5. Click **"Force Clear Stale Row Locks"** in the action toolbar.
6. Confirm the action in the dialog that appears. The batch will be released immediately.
7. Return to the production order or optimization screen and attempt the allocation again.

---

## KB-007 — User Account Lockout — Failed Login Attempts

**Applies To:** Security & Access Management (CoderoadERP Admin Panel)  
**Typical Trigger:** Three or more consecutive failed login attempts trigger an automatic security lockout on the user account.  
**Environments Affected:** LIVE and TEST (separate lockout counters per environment)

### Root Cause Analysis

CoderoadERP enforces a **3-strike lockout policy** on all user accounts to protect against unauthorized access attempts. After three failed attempts, the account is locked for 30 minutes or until an IT Administrator manually unlocks it. The user cannot reset this themselves. Lockouts are logged to the Security Audit Trail.

### Step-by-Step Resolution

1. Log in to the **CoderoadERP Administration Console** using an IT Administrator account.
2. Navigate to **Security → User Management → Active Directory Sync**.
3. Search for the locked user by **Employee ID** or **email address**.
4. The account will display a red **"Locked"** status badge. Click on the user record.
5. Select **"Unlock Account"** and confirm the action. The system will log the unlock event with the administrator's credentials.
6. Optionally, select **"Force Password Reset on Next Login"** if the lockout was caused by a suspected compromised credential.
7. Notify the user that their account is active and ask them to log in and immediately change their password.

---

## KB-008 — Module-to-Module Data Sync Failure

**Applies To:** Integration Layer between CoderoadERP (commercial) and CoderoadOPS (shop floor)  
**Typical Trigger:** A sync process stalled due to a message queue overflow, a malformed data payload, or a temporary network interruption between the two modules.  
**Environments Affected:** LIVE and TEST

### Root Cause Analysis

CoderoadERP and CoderoadOPS communicate through a real-time message queue (MQ) that transmits production orders, inventory updates, and completion receipts between modules. If the MQ encounters an unprocessable message (schema mismatch, null field, encoding error), it halts the queue to prevent data corruption. This causes a visible lag — records updated in CoderoadERP do not appear in CoderoadOPS, or vice versa.

### Step-by-Step Resolution

1. Log in to the **IT Operations Dashboard → Integration Health Monitor**.
2. Navigate to the **Message Queue Status** panel. Identify any queues marked **"Paused"** or **"Error State"**.
3. Click the affected queue to inspect the **Dead Letter Queue (DLQ)** — this shows the specific message(s) that caused the halt.
4. Review the error payload. If the record is identifiable (e.g., a Sales Order number), correct the data at the source in CoderoadERP first.
5. Once the source data is corrected, click **"Retry Failed Messages"** on the DLQ panel.
6. Monitor the queue for 2–3 minutes to confirm messages are flowing again.
7. If the queue does not clear after retry, escalate to a Level 2 database administrator — the issue may require a manual message purge.

---

## KB-009 — Scheduled Nightly Job — Partial Execution Warning

**Applies To:** IT Operations — Automated Batch Processing  
**Typical Trigger:** A nightly scheduled job (backup, report generation, data archival) exited before completion due to a server resource constraint or timeout.  
**Environments Affected:** LIVE primarily (TEST jobs are non-critical)

### Root Cause Analysis

CoderoadERP runs automated batch jobs during off-peak hours (typically 01:00–04:00 AM). If a job encounters a resource limit (CPU spike, disk space threshold, memory overflow), the job scheduler marks the task as **"Partial — Exit Code 2"** and terminates gracefully. No data is corrupted, but the job's output is incomplete.

### Step-by-Step Resolution

1. Log in to the **IT Operations Dashboard → Scheduled Job Manager**.
2. Locate the failed job in the **Last Run Results** panel. Jobs with **Exit Code 2** or **"Partial"** status are highlighted in yellow.
3. Click the job entry to view the **Execution Log**. Identify at which step the job exited.
4. Check the **Server Resource Monitor** panel for CPU, memory, and disk usage at the time of execution.
5. **Option A — Disk space:** If disk usage exceeded 85%, archive older log files from the `/var/coderoad/archive/` directory and re-run the job manually.
6. **Option B — Timeout:** Increase the job's maximum execution timeout in the **Job Configuration** panel (consult with the infrastructure team before modifying).
7. Click **"Manual Re-Run"** on the job entry to execute it immediately.
8. Monitor execution in real time using the **Live Job Console** view.

---

## KB-010 — Contract Price Table Mismatch on Sales Order

**Applies To:** Sales module, Billing module  
**Typical Trigger:** A sales order is pulling prices from the standard public rate table instead of the customer's approved contract price table.  
**Environments Affected:** LIVE only

### Root Cause Analysis

Each customer in CoderoadERP can be linked to a specific **Contract Price Schedule** that overrides the default product price table. If the contract link is missing or expired, the system silently falls back to the standard catalog price — which may be higher or lower than the negotiated rate — causing a discrepancy that is often only caught at invoice review.

### Step-by-Step Resolution

1. Navigate to **Sales → Customer Master Data → [Customer ID] → Pricing & Contracts**.
2. Check the **Active Contract Schedule** field. If it shows **"None"** or displays an expired date, the contract link is broken.
3. Click **"Assign Contract"** and search for the correct contract by contract number or negotiated date range.
4. Select the appropriate contract and click **Save**.
5. Return to the affected sales order and click **"Recalculate Prices"** — the system will now apply the correct contract rates.
6. Verify the updated line totals and confirm with the account manager before re-submitting.
7. If the correct contract does not exist in the system, escalate to the Contracts & Pricing team to load the agreement.

---

## KB-011 — Customer Account Duplicate Entry Block

**Applies To:** CRM module (CoderoadERP), Billing module  
**Typical Trigger:** The system detected a new customer record with a Tax ID, name, or address that matches an existing account, triggering a duplicate prevention block.  
**Environments Affected:** LIVE and TEST

### Root Cause Analysis

CoderoadERP's CRM module runs a real-time duplicate detection algorithm on three fields: **Tax Registration ID**, **Legal Company Name** (fuzzy match), and **Primary Address**. A match on any two of these three fields triggers a soft block. This prevents fragmented customer data and protects billing accuracy, but it can also block legitimate new accounts if data entry is imprecise.

### Step-by-Step Resolution

1. Navigate to **CRM → Customer Accounts → Duplicate Management Console**.
2. Search for the blocked customer record by Tax ID or company name.
3. The console will display both the **new entry** and the **existing potential duplicate** side by side.
4. Review both records carefully. If they are the same company, click **"Merge Records"** and designate the existing account as the primary record.
5. If they are different companies, click **"Confirm as Unique"** and enter a justification note (the system will log this for auditing).
6. After merging or confirming, the block is automatically released and you can proceed with the new order or invoice.
7. If you are unsure whether two records represent the same entity, escalate to the Finance or Legal team before proceeding.

---

## KB-012 — Dashboard / KPI Panel Not Loading — Browser Cache Issue

**Applies To:** All modules — management dashboards, KPI panels, reporting views  
**Typical Trigger:** A stale browser cache is serving an outdated version of the dashboard JavaScript, causing the panel to fail on render.  
**Environments Affected:** LIVE and TEST

### Root Cause Analysis

CoderoadERP's dashboards are built on a dynamic JavaScript rendering engine. After a system update, old cached scripts stored in the browser can conflict with the new version's API response format. The result is a blank panel, a spinning loader that never resolves, or a partial render showing incomplete data.

### Step-by-Step Resolution

1. Press `Ctrl + Shift + Delete` (Windows) or `Cmd + Shift + Delete` (Mac) to open the browser's **Clear Browsing Data** dialog.
2. Select **"Cached images and files"** and **"Cookies and other site data"** for the **CoderoadERP domain only**.
3. Set the time range to **"Last 7 days"** and click **Clear Data**.
4. Close all CoderoadERP tabs completely.
5. Open a new tab, navigate to the CoderoadERP URL, and log in again.
6. Navigate back to the affected dashboard. The panel should now load correctly with the latest data.
7. If the dashboard still does not load, try accessing CoderoadERP from a **Private / Incognito browser window** — this bypasses all cached data and confirms whether the issue is cache-related or server-side.

---

*End of Knowledge Base — Version 1.0*

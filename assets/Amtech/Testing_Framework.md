# CoderoadERP AI Copilot — Multi-Role Testing Framework

> **Version:** 1.0 | **Classification:** Internal — Demo Use  
> **Purpose:** Validates the AI Copilot's entity extraction, routing logic, and conversational quality across five operational roles. Each scenario includes the raw user input, the expected entity extraction, the routing decision, and the full expected AI response.

---

## Roles Covered

| # | Role | System Focus |
|---|------|--------------|
| 1 | Plant / Production Operator | CoderoadOPS — Shop Floor |
| 2 | Billing & Finance Clerk | CoderoadERP — Finance Module |
| 3 | Logistics & Warehouse Manager | CoderoadOPS — Logistics Module |
| 4 | IT System Administrator | CoderoadERP/OPS — Admin & Security |
| 5 | Sales & Account Manager | CoderoadERP — Sales & CRM |

---

## Routing Legend

| Code | Meaning |
|------|---------|
| **Route A** | Known KB article match → immediate self-service resolution |
| **Route B** | Undocumented issue → Jira ticket created (CodeRoute project) |
| **Ask: Missing Info** | One or more critical variables absent → single consolidated clarification request |

---

---

# ROLE 1 — Plant / Production Operator

---

### Scenario 1.1

**User Input:**
> "The optimizer in CoderoadOPS TEST won't let me allocate roll batch RB-9902, it says the batch is locked by another terminal but nobody is logged in."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Production (CoderoadOPS) |
| Identifier | RB-9902 |
| Description | Batch locked by another terminal — no active user session visible |
| Environment | TEST |

**Routing Decision:** Route A — KB-006 (Stuck Roll Stock / Database Row Lock)

**Expected AI Copilot Response:**
> "I can see that batch RB-9902 is displaying a stale database row lock in CoderoadOPS TEST. This is a known issue caused by an interrupted optimization session that did not release its lock properly.
>
> Please follow these steps to clear it immediately:
> 1. Navigate to **CoderoadOPS → Inventory Utilities → Active Session Monitor**.
> 2. In the search field, enter batch code **RB-9902**.
> 3. Locate the entry showing **"Orphaned"** or **"No Active User"** status.
> 4. Highlight the row and click **"Force Clear Stale Row Locks"**.
> 5. Confirm the action in the dialog. The batch will be released immediately.
>
> Return to your optimization screen and attempt the allocation again. Let me know if the issue persists."

---

### Scenario 1.2

**User Input:**
> "I cannot pull up the manufacturing machine queue for Corrugator Line 1 in production this afternoon. The screen is totally blank."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Production (CoderoadOPS) |
| Identifier | Corrugator Line 1 |
| Description | Machine queue screen completely blank |
| Environment | LIVE |
| Missing | Error code, software patch version |

**Routing Decision:** Ask: Missing Info

**Expected AI Copilot Response:**
> "I have registered your issue with Corrugator Line 1 in the LIVE environment. A blank machine queue screen is not a self-service case — it requires engineering review.
>
> To open a priority ticket immediately, please provide the following two details in your next message:
> 1. **Error code** — is there any code or message appearing anywhere on the screen, even briefly? (e.g., ERR-500, "Connection Lost", "Render Failed")
> 2. **Software patch version** — this is usually displayed at the bottom footer of the CoderoadOPS screen (e.g., v4.2.1).
>
> Once I have these, I will create a high-priority engineering ticket right away."

---

### Scenario 1.3

**User Input:**
> "We have a fatal error code ERR-402 when posting raw material consumption on production order PO-7731 in LIVE."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Production (CoderoadOPS) |
| Identifier | PO-7731 |
| Description | Fatal error ERR-402 on raw material consumption posting |
| Environment | LIVE |
| Error Code | ERR-402 |

**Routing Decision:** Route B — Jira ticket (ERR-402 is not in KB, LIVE environment, operational block)

**Expected AI Copilot Response:**
> "Error ERR-402 on a LIVE production order is treated as high priority. I am escalating this to engineering immediately.
>
> **Jira Ticket Created — CR-9401**
> - Module: Production (CoderoadOPS)
> - Order: PO-7731
> - Issue: Fatal error ERR-402 during raw material consumption posting
> - Environment: LIVE
> - Priority: High
>
> Our engineering team will begin tracing the material consumption tables immediately. You should receive an update within 2 hours. If the production line is fully blocked, please also notify your shift supervisor so they can initiate manual logging as a contingency."

---

### Scenario 1.4

**User Input:**
> "The barcode scanner terminal at the plant floor is throwing an invalid sync warning for finished goods pallet FG-5511 in production."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Production / Quality Control (CoderoadOPS) |
| Identifier | FG-5511 |
| Description | Invalid sync warning on barcode scanner for finished goods pallet |
| Environment | Missing — "in production" is ambiguous |

**Routing Decision:** Ask: Missing Info (Environment confirmation required)

**Expected AI Copilot Response:**
> "I have logged the sync warning on pallet **FG-5511**. Before I can route this correctly, I need one confirmation:
>
> 1. **Environment** — you mentioned "in production." Does this mean:
>    - **LIVE** (the active production floor where real goods are moving), or
>    - **TEST** (the staging sandbox environment)?
>
> This distinction determines whether this needs immediate escalation. Please confirm in your next message."

---

### Scenario 1.5

**User Input:**
> "I'm trying to start production order PO-8812 but the active start button is greyed out. We are running in the LIVE database."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Production (CoderoadOPS) |
| Identifier | PO-8812 |
| Description | "Start" button is greyed out and non-clickable |
| Environment | LIVE |

**Routing Decision:** Route A — KB-003 (Greyed-Out / Inactive Button)

**Expected AI Copilot Response:**
> "A greyed-out Start button on production order PO-8812 in LIVE indicates a role permissions limitation. This is a known access control behavior in CoderoadOPS, not a system error.
>
> Please follow these steps:
> 1. Navigate to **My Profile → Permissions & Authorization Levels** (top-right user menu).
> 2. Review your **Action Thresholds** table and locate the "Start Production Order" permission.
> 3. **Option A:** If your role should grant access, click **"Request Temporary Elevation"** and submit a justification note to your supervisor for in-system approval.
> 4. **Option B:** Ask your floor manager to enter their **on-screen override PIN** directly on your workstation to authorize the start action for this specific order.
>
> If neither option works and your permissions appear correct, let me know and I will open a ticket for the IT Administrator to review your profile."

---

---

# ROLE 2 — Billing & Finance Clerk

---

### Scenario 2.1

**User Input:**
> "I am trying to approve a critical shipment invoice in CoderoadERP LIVE but it says the customer account balance exceeds their matrix limit. The invoice is INV-4001."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Billing (CoderoadERP) |
| Identifier | INV-4001 |
| Description | Invoice approval blocked — customer balance exceeds credit matrix limit |
| Environment | LIVE |

**Routing Decision:** Route A — KB-004 (Credit Limit Block on Sales Order)

**Expected AI Copilot Response:**
> "The block on invoice **INV-4001** is a credit matrix control, not a system error. The customer's current outstanding balance has exceeded their approved credit line in CoderoadERP.
>
> Here is how to resolve this:
> 1. Navigate to **Finance Workspace → Customer Accounts → Credit & Aging Status**.
> 2. Search for the customer linked to INV-4001 to view their full credit profile.
> 3. Check the **Unallocated Receipts** tab first — if the customer sent a wire transfer that has not been applied yet, allocating it may clear the block immediately.
> 4. If no unallocated payments exist, click **"Apply Temporary Credit Extension"**, enter the required amount and a justification, and submit for Finance Manager approval.
> 5. Once the credit check passes, return to INV-4001 and proceed with the approval.
>
> Let me know if you need further assistance."

---

### Scenario 2.2

**User Input:**
> "The system throws an unhandled exception timeout whenever I hit 'Post Ledger' for the quarterly report in TEST."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Finance / Billing (CoderoadERP) |
| Identifier | Quarterly Report |
| Description | Unhandled exception timeout on "Post Ledger" action |
| Environment | TEST |

**Routing Decision:** Route B — Jira ticket (unhandled exception, not in KB)

**Expected AI Copilot Response:**
> "A ledger posting timeout in the TEST environment requires database-level investigation. I am creating a ticket now.
>
> **Jira Ticket Created — CR-9402**
> - Module: Finance (CoderoadERP)
> - Record: Quarterly Report Ledger
> - Issue: Unhandled exception timeout on "Post Ledger" action
> - Environment: TEST
> - Priority: Medium
>
> A database administrator will review the staging server execution logs. You can expect a response by the next business day. In the meantime, avoid retrying the post — repeated failed attempts can generate duplicate draft entries that complicate the cleanup."

---

### Scenario 2.3

**User Input:**
> "I am clicking the download button for customer statement invoice INV-8891 in production and nothing opens up."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Billing (CoderoadERP) |
| Identifier | INV-8891 |
| Description | PDF download button does nothing when clicked |
| Environment | LIVE |

**Routing Decision:** Route A — KB-002 (PDF / Report Generation Failure)

**Expected AI Copilot Response:**
> "The download button on invoice **INV-8891** is almost certainly being silently blocked by your browser's pop-up filter. This is a very common issue after browser security updates.
>
> Here is the fix:
> 1. Look at the **top-right corner of your browser address bar** for a small icon showing a blocked pop-up (a window with a red X or warning symbol).
> 2. Click that icon and select **"Always allow pop-ups and redirects from this site"**.
> 3. Click **Done**.
> 4. Return to invoice INV-8891 and click the download button again.
>
> If no pop-up icon is visible, press `Ctrl + Shift + Delete`, clear the cached files for the CoderoadERP domain, and try again from a fresh tab. Let me know if the download still does not open."

---

### Scenario 2.4

**User Input:**
> "The tax calculation engine is pulling zero percent VAT on our local invoice INV-3392. This is happening in the real production environment."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Billing (CoderoadERP) |
| Identifier | INV-3392 |
| Description | Tax calculation returning 0% VAT incorrectly on a local invoice |
| Environment | LIVE |
| Error Code | None — data anomaly |

**Routing Decision:** Route B — Jira ticket (critical data anomaly in LIVE, not in KB)

**Expected AI Copilot Response:**
> "A zero-VAT calculation on a LIVE local invoice is a critical financial data anomaly. Do not post or send this invoice until engineering has confirmed the tax tables are correct.
>
> **Jira Ticket Created — CR-9403**
> - Module: Billing (CoderoadERP)
> - Invoice: INV-3392
> - Issue: Tax engine returning 0% VAT on local invoice — potential tax table disconnection
> - Environment: LIVE
> - Priority: Critical
>
> This has been escalated to Tier-3 support. The team will check for tax table configuration errors and calculation engine disconnects. You will receive a status update within 1 hour. Please flag this to your Finance Manager as well, as regulatory compliance may be affected."

---

### Scenario 2.5

**User Input:**
> "I am getting a duplicate sequence block warning in the billing screen for a document in CoderoadERP."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Billing (CoderoadERP) |
| Identifier | Missing |
| Description | Duplicate sequence block warning — document not specified |
| Environment | Missing |

**Routing Decision:** Ask: Missing Info

**Expected AI Copilot Response:**
> "I have registered a duplicate sequence block warning in the Billing module. To investigate and resolve this immediately, I need two pieces of information:
>
> 1. **Document Number** — the specific Invoice ID or Document Number shown on the screen where the warning appeared (e.g., INV-XXXX).
> 2. **Environment** — is this occurring in **LIVE** (your active business environment) or **TEST** (the staging sandbox)?
>
> Please include both in your next message and I will route this to the correct resolution path right away."

---

---

# ROLE 3 — Logistics & Warehouse Manager

---

### Scenario 3.1

**User Input:**
> "I'm at the loading dock in production and trying to print the bill of lading for guide GD-7782 but the thermal printer is completely unresponsive."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Logistics (CoderoadOPS) |
| Identifier | GD-7782 |
| Description | Thermal printer unresponsive when printing BOL |
| Environment | LIVE |

**Routing Decision:** Route A — KB-005 (Thermal Printer Routing Failure)

**Expected AI Copilot Response:**
> "A completely unresponsive thermal printer for load guide **GD-7782** in LIVE is almost always caused by the workstation reverting to Spooler Pool routing instead of Direct Network IP. This is a fast fix.
>
> 1. On your logistics workstation, navigate to **Logistics Setup → Workstation Print Configuration → Local Print Routing**.
> 2. Check the **Default Printer Destination** field. If it reads **"Spooler Pool"**, that is the cause.
> 3. Change it to **"Direct Network IP"**.
> 4. Confirm the printer's IP address is correctly listed in the **Printer IP Address** field (check the label on the printer if needed).
> 5. Click **Save Configuration**.
> 6. Run a **Line-Feed Test Print** to confirm the connection is live.
> 7. Return to guide GD-7782 and print the BOL.
>
> If the thermal printer still does not respond after confirming the IP is correct, let me know and I will escalate to IT."

---

### Scenario 3.2

**User Input:**
> "The fleet routing engine between CoderoadERP and CoderoadOPS is lagging. Dispatch guides aren't updating vehicle allocations in TEST."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Logistics / Integration Layer |
| Identifier | Dispatch Guides (general) |
| Description | Vehicle allocation updates not syncing between CoderoadERP and CoderoadOPS |
| Environment | TEST |

**Routing Decision:** Route B — Jira ticket (cross-system sync issue, not a standard KB article)

**Expected AI Copilot Response:**
> "Cross-system fleet routing latency between CoderoadERP and CoderoadOPS indicates a message queue issue in the Integration Layer. I am logging this now.
>
> **Jira Ticket Created — CR-9404**
> - Module: Logistics / Integration Layer
> - Issue: Vehicle allocation updates not propagating from CoderoadERP to CoderoadOPS dispatch guides
> - Environment: TEST
> - Priority: Medium
>
> Integration engineers will verify the inter-module message queues and check for stalled payloads. Because this is in TEST, it will be reviewed by the next business day. Operations in your LIVE environment are not affected."

---

### Scenario 3.3

**User Input:**
> "The system is throwing a 'Weight Tolerance Discrepancy' block on load guide GD-1192 in production, and it won't let me release the delivery truck."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Logistics (CoderoadOPS) |
| Identifier | GD-1192 |
| Description | Weight Tolerance Discrepancy block preventing truck release |
| Environment | LIVE |

**Routing Decision:** Route B — Jira ticket (blocking LIVE logistics operation, not in KB)

**Expected AI Copilot Response:**
> "A weight tolerance block on a LIVE load guide is a high-priority operational issue — I am escalating this immediately to prevent further delivery delays.
>
> **Jira Ticket Created — CR-9405**
> - Module: Logistics (CoderoadOPS)
> - Load Guide: GD-1192
> - Issue: Weight Tolerance Discrepancy block — truck release prevented
> - Environment: LIVE
> - Priority: High
>
> The logistics operations support team has been paged. They will verify the physical scale calibration logs and cross-reference them against the system's configured weight tolerance profiles for this load. You should receive an update within 30–60 minutes. In the meantime, do not manually override the block without engineering sign-off."

---

### Scenario 3.4

**User Input:**
> "I am trying to process a warehouse bin transfer for item code paper roll PR-4412 in the staging sandbox environment but the transfer button is dead."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Logistics / Inventory (CoderoadOPS) |
| Identifier | PR-4412 |
| Description | Warehouse bin transfer button is inactive / non-clickable |
| Environment | TEST |

**Routing Decision:** Route A — KB-003 (Greyed-Out / Inactive Button)

**Expected AI Copilot Response:**
> "An inactive bin transfer button for item **PR-4412** in the TEST environment points to a role permission limitation. CoderoadOPS mirrors LIVE permission settings in TEST to ensure accurate testing conditions.
>
> Here is what to check:
> 1. Go to **My Profile → Permissions & Authorization Levels**.
> 2. Look for **"Warehouse Bin Transfer"** in your Action Thresholds list and verify your staging clearance tier.
> 3. **Option A:** Click **"Request Temporary Elevation"** and submit a justification note for your supervisor's approval.
> 4. **Option B:** Ask a supervisor to input a temporary **override PIN** directly on your workstation for this specific transfer.
>
> If your role should already have this permission and the button is still inactive, let me know and I will raise a ticket for the IT Administrator to audit your TEST profile configuration."

---

### Scenario 3.5

**User Input:**
> "The RMA receiving log module is throwing an unexpected connection timeout screen right now."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Logistics (CoderoadOPS) — RMA Receiving |
| Identifier | RMA Log (general) |
| Description | Connection timeout screen on RMA receiving log module |
| Environment | Missing |

**Routing Decision:** Ask: Missing Info + Partial Route A guidance (KB-001 likely applies but environment must be confirmed)

**Expected AI Copilot Response:**
> "A connection timeout on the RMA receiving log is likely caused by a VPN session drop — this is a known issue covered in our Knowledge Base.
>
> Before I confirm the resolution path, I need one quick clarification:
>
> 1. **Environment** — is this happening in **LIVE** (active receiving operations) or **TEST** (staging environment)?
>
> While you check, you can try this first step right now: **verify that your corporate VPN client shows "Connected — Active"**. If it shows disconnected, re-authenticate and refresh CoderoadOPS. This resolves the timeout in most cases.
>
> Let me know the environment so I can either confirm this as a full resolution or escalate if the timeout persists in LIVE."

---

---

# ROLE 4 — IT System Administrator

---

### Scenario 4.1

**User Input:**
> "A warehouse operator just called me — their CoderoadERP account is locked after 3 failed login attempts. Employee ID is EMP-4421. This is on LIVE."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Security / User Management (CoderoadERP Admin) |
| Identifier | EMP-4421 |
| Description | Account locked after 3 failed login attempts |
| Environment | LIVE |

**Routing Decision:** Route A — KB-007 (User Account Lockout)

**Expected AI Copilot Response:**
> "Account lockouts after 3 failed attempts are handled directly in the Administration Console. Here is the unlock procedure for employee **EMP-4421**:
>
> 1. Log in to the **CoderoadERP Administration Console** with your IT Admin credentials.
> 2. Navigate to **Security → User Management → Active Directory Sync**.
> 3. Search for **EMP-4421** by Employee ID or email address.
> 4. The account will show a red **"Locked"** status badge. Click the user record.
> 5. Select **"Unlock Account"** and confirm. The system will log the unlock event with your admin credentials.
> 6. Optionally, select **"Force Password Reset on Next Login"** if the lockout may have been caused by a compromised credential.
> 7. Notify the operator that their account is now active.
>
> The full unlock event is recorded in the Security Audit Trail for compliance purposes."

---

### Scenario 4.2

**User Input:**
> "We are seeing a sync delay between CoderoadERP and CoderoadOPS. Sales orders posted 2 hours ago in CoderoadERP are not showing up as production orders in CoderoadOPS."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Integration Layer (CoderoadERP ↔ CoderoadOPS) |
| Identifier | Sales Orders (general — no specific ID given) |
| Description | 2-hour sync delay — SOs not creating production orders in CoderoadOPS |
| Environment | Missing |

**Routing Decision:** Ask: Missing Info (Environment needed; partial KB-008 guidance can be offered)

**Expected AI Copilot Response:**
> "A 2-hour sync gap between CoderoadERP and CoderoadOPS is a significant message queue issue that needs immediate attention. I need one confirmation before opening the right ticket:
>
> 1. **Environment** — is this occurring in **LIVE** (active business operations) or **TEST** (staging)?
>
> While you confirm, you can begin investigating right now:
> - Open the **IT Operations Dashboard → Integration Health Monitor → Message Queue Status**.
> - Look for any queues marked **"Paused"** or **"Error State"**.
> - If you find stalled queues, check the **Dead Letter Queue (DLQ)** for the specific failed messages.
>
> Once you confirm the environment, I will create the appropriate priority ticket and engage the integration engineering team."

---

### Scenario 4.3

**User Input:**
> "The nightly backup job failed again this morning. The job log shows Exit Code 2 — Partial Execution. This is on the LIVE server."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | IT Operations — Scheduled Job Manager |
| Identifier | Nightly Backup Job |
| Description | Partial execution — Exit Code 2 on LIVE server nightly backup |
| Environment | LIVE |

**Routing Decision:** Route A — KB-009 (Scheduled Job Partial Execution Warning)

**Expected AI Copilot Response:**
> "Exit Code 2 on a nightly backup job means it terminated gracefully before completing — no data is corrupted, but the backup is incomplete. Here is how to diagnose and re-run it:
>
> 1. Log in to the **IT Operations Dashboard → Scheduled Job Manager**.
> 2. Locate the failed backup job in the **Last Run Results** panel (highlighted in yellow).
> 3. Click the entry to view the full **Execution Log** — identify the exact step where the job exited.
> 4. Open the **Server Resource Monitor** panel and check CPU, memory, and disk usage for the time of execution (01:00–04:00 AM window).
> 5. **If disk usage exceeded 85%:** Archive older log files from the `/var/coderoad/archive/` directory to free space, then proceed to step 7.
> 6. **If a timeout occurred:** Review the job's maximum execution timeout in **Job Configuration** and consult with the infrastructure team before modifying it.
> 7. Click **"Manual Re-Run"** on the job entry and monitor execution in the **Live Job Console** view.
>
> If the job fails again with a different exit code, let me know and I will escalate to the infrastructure team."

---

### Scenario 4.4

**User Input:**
> "Multiple users are reporting they cannot access the sales reporting dashboard in CoderoadERP. The panel just shows a blank white screen. Happening in both LIVE and TEST."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Sales / Reporting (CoderoadERP) |
| Identifier | Sales Reporting Dashboard |
| Description | Blank white screen on sales dashboard — multiple users affected simultaneously |
| Environment | LIVE and TEST |

**Routing Decision:** Route B — Jira ticket (multiple users affected simultaneously indicates server-side issue, not individual cache)

**Expected AI Copilot Response:**
> "A simultaneous dashboard failure affecting multiple users in both LIVE and TEST is a server-side rendering issue — this goes beyond individual browser caches. I am escalating immediately.
>
> **Jira Ticket Created — CR-9406**
> - Module: Sales / Reporting (CoderoadERP)
> - Issue: Sales dashboard returning blank white screen for multiple users — LIVE and TEST simultaneously affected
> - Environment: LIVE + TEST
> - Priority: Critical
>
> The platform team will check the dashboard rendering service, CDN health, and recent deployment logs. Because LIVE operations are impacted, this is treated as a Critical priority with a 1-hour response SLA.
>
> As a temporary workaround, ask affected users to access raw report data via **Sales → Reports → Manual Export** while the dashboard is restored."

---

### Scenario 4.5

**User Input:**
> "A new user account was created for a finance clerk but they are not showing up in the CoderoadERP LIVE user list after Active Directory sync. Their email is jsmith@company.com."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Security / User Management (CoderoadERP Admin) |
| Identifier | jsmith@company.com |
| Description | New user not appearing in CoderoadERP LIVE after AD sync |
| Environment | LIVE |

**Routing Decision:** Route B — Jira ticket (AD sync propagation failure is not covered by KB)

**Expected AI Copilot Response:**
> "A new user not appearing after Active Directory sync suggests a propagation failure between the corporate AD and CoderoadERP's user provisioning layer. This requires backend investigation.
>
> **Jira Ticket Created — CR-9407**
> - Module: Security / User Management (CoderoadERP)
> - User: jsmith@company.com
> - Issue: New account not provisioning in CoderoadERP LIVE after AD sync
> - Environment: LIVE
> - Priority: High
>
> The identity management team will check the sync logs, verify the AD group assignment, and manually trigger a re-sync for this user if necessary. In the meantime, if the clerk needs urgent access, you can create a temporary local CoderoadERP account via **Admin Console → User Management → Create Local User** and deactivate it once the AD sync issue is resolved."

---

---

# ROLE 5 — Sales & Account Manager

---

### Scenario 5.1

**User Input:**
> "A sales order I just entered for customer ID CUS-3301 is showing prices that do not match their negotiated contract. The order number is SO-5521 and this is in LIVE."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Sales (CoderoadERP) |
| Identifier | SO-5521 / CUS-3301 |
| Description | Sales order prices not matching customer's negotiated contract rates |
| Environment | LIVE |

**Routing Decision:** Route A — KB-010 (Contract Price Table Mismatch)

**Expected AI Copilot Response:**
> "The pricing discrepancy on order **SO-5521** for customer **CUS-3301** in LIVE is typically caused by a missing or expired contract price schedule. Here is how to fix this without creating a new order:
>
> 1. Navigate to **Sales → Customer Master Data → CUS-3301 → Pricing & Contracts**.
> 2. Check the **Active Contract Schedule** field. If it shows **"None"** or an expired date, the contract link is broken.
> 3. Click **"Assign Contract"** and search for the correct agreement by contract number or negotiated date.
> 4. Select the correct contract and click **Save**.
> 5. Return to sales order **SO-5521** and click **"Recalculate Prices"** — the system will now apply the correct contract rates to all line items.
> 6. Verify the updated totals match the expected negotiated values before submitting.
>
> If the correct contract does not exist in the system, do not submit the order — escalate to the Contracts & Pricing team to load the agreement first."

---

### Scenario 5.2

**User Input:**
> "I am trying to create a new customer account but the system is blocking me with a 'Potential Duplicate Detected' warning. The new company is different from the existing one."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | CRM (CoderoadERP) |
| Identifier | Missing (new customer name not provided) |
| Description | Duplicate detection block on new customer account creation |
| Environment | Missing |

**Routing Decision:** Ask: Missing Info

**Expected AI Copilot Response:**
> "I can help you resolve the duplicate detection block. To investigate whether this is a true duplicate or a false positive, I need a couple of details:
>
> 1. **New customer name or Tax ID** — the name or tax registration number you entered for the new account.
> 2. **Environment** — is this in **LIVE** or **TEST**?
>
> With this information, I can guide you through the Duplicate Management Console to either merge the records (if it is the same company) or confirm them as unique (if they are different companies). Please include both details in your next message."

---

### Scenario 5.3

**User Input:**
> "A new customer account is being blocked because the credit bureau API is timing out. The customer name is Acosta & Partners and this is in LIVE."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | CRM / Finance (CoderoadERP) |
| Identifier | Acosta & Partners (new customer) |
| Description | New account creation blocked due to external credit bureau API timeout |
| Environment | LIVE |

**Routing Decision:** Route B — Jira ticket (external API failure, not in KB)

**Expected AI Copilot Response:**
> "A credit bureau API timeout in LIVE is blocking new customer onboarding — I will escalate this to IT immediately.
>
> **Jira Ticket Created — CR-9408**
> - Module: CRM / Finance (CoderoadERP)
> - Customer: Acosta & Partners
> - Issue: External credit bureau API timing out during new account creation
> - Environment: LIVE
> - Priority: High
>
> The IT team will investigate the API connection status and contact the credit bureau provider if necessary. You should receive a status update within 2 hours.
>
> In the meantime, if this is a time-sensitive account, the Finance Manager can authorize a **manual credit profile override** in **CRM → Customer Accounts → Credit Override Request** to temporarily bypass the API check and complete the account setup."

---

### Scenario 5.4

**User Input:**
> "My sales dashboard is completely blank — none of the monthly KPI panels are loading. I just came back from lunch."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Sales (CoderoadERP) |
| Identifier | Sales Dashboard / Monthly KPI Panels |
| Description | All KPI panels blank — issue appeared after a browser session break |
| Environment | Missing (not critical — likely individual browser issue) |

**Routing Decision:** Route A — KB-012 (Dashboard / KPI Panel Not Loading — Browser Cache Issue)

**Expected AI Copilot Response:**
> "A blank dashboard after returning from a break is almost always a browser cache conflict — especially after a recent system update. This is quick to fix:
>
> 1. Press `Ctrl + Shift + Delete` to open the **Clear Browsing Data** dialog.
> 2. Select **"Cached images and files"** and **"Cookies and other site data"** for the CoderoadERP domain only.
> 3. Set the time range to **"Last 7 days"** and click **Clear Data**.
> 4. Close all CoderoadERP tabs and open a fresh tab.
> 5. Log back in to CoderoadERP and navigate to your Sales Dashboard.
>
> If the panels are still blank, open a **Private / Incognito window** and try accessing the dashboard there. If it loads correctly in Incognito, the issue is confirmed as a browser cache problem and the steps above will fully resolve it.
>
> If the dashboard is also blank in Incognito, let me know immediately — that would indicate a server-side issue requiring escalation."

---

### Scenario 5.5

**User Input:**
> "The commission split on sales order SO-8834 is wrong. It is showing 100% to one account manager but it should be split 60/40 between two reps. This is in LIVE."

**Extracted Entities:**

| Variable | Value |
|----------|-------|
| Module | Sales / Finance (CoderoadERP) |
| Identifier | SO-8834 |
| Description | Commission split calculated incorrectly — 100% to one rep instead of 60/40 split |
| Environment | LIVE |

**Routing Decision:** Route B — Jira ticket (commission calculation error in LIVE, financial impact, not in KB)

**Expected AI Copilot Response:**
> "An incorrect commission split in LIVE has direct payroll and compensation implications — this needs to go to the Finance and Commissions team immediately.
>
> **Jira Ticket Created — CR-9409**
> - Module: Sales / Finance (CoderoadERP)
> - Order: SO-8834
> - Issue: Commission split showing 100% to one account manager — expected 60/40 split
> - Environment: LIVE
> - Priority: High
>
> The Commissions team will audit the order's account manager assignment and the commission rule table applied to this order type. Do not process any commission payments against this order until the ticket is resolved.
>
> Please also confirm the names or Employee IDs of both account managers involved when you have a moment — this will help the team correct the record faster."

---

---

## Testing Summary Table

| # | Role | Scenario | Route | KB Article / Action |
|---|------|----------|-------|---------------------|
| 1.1 | Plant Operator | Batch locked in TEST | A | KB-006 |
| 1.2 | Plant Operator | Blank queue screen LIVE — missing data | Ask | Need error code + patch version |
| 1.3 | Plant Operator | ERR-402 on production order LIVE | B | CR-9401 |
| 1.4 | Plant Operator | Barcode sync warning — missing env | Ask | Need LIVE vs TEST confirmation |
| 1.5 | Plant Operator | Greyed-out Start button LIVE | A | KB-003 |
| 2.1 | Billing Clerk | Credit limit block on invoice LIVE | A | KB-004 |
| 2.2 | Billing Clerk | Ledger posting timeout TEST | B | CR-9402 |
| 2.3 | Billing Clerk | PDF download does nothing LIVE | A | KB-002 |
| 2.4 | Billing Clerk | Zero VAT on invoice LIVE | B | CR-9403 |
| 2.5 | Billing Clerk | Duplicate sequence block — missing data | Ask | Need doc number + environment |
| 3.1 | Logistics Manager | Thermal printer unresponsive LIVE | A | KB-005 |
| 3.2 | Logistics Manager | Fleet routing lag TEST | B | CR-9404 |
| 3.3 | Logistics Manager | Weight tolerance block LIVE | B | CR-9405 |
| 3.4 | Logistics Manager | Bin transfer button inactive TEST | A | KB-003 |
| 3.5 | Logistics Manager | RMA timeout — missing env | Ask | VPN check + need environment |
| 4.1 | IT Administrator | Account locked after 3 attempts LIVE | A | KB-007 |
| 4.2 | IT Administrator | 2-hour sync delay — missing env | Ask | Need env + IMQ investigation |
| 4.3 | IT Administrator | Backup job Exit Code 2 LIVE | A | KB-009 |
| 4.4 | IT Administrator | Dashboard blank for all users LIVE+TEST | B | CR-9406 |
| 4.5 | IT Administrator | New user not in AD sync LIVE | B | CR-9407 |
| 5.1 | Sales Manager | Contract price mismatch LIVE | A | KB-010 |
| 5.2 | Sales Manager | Duplicate block — missing data | Ask | Need customer name + environment |
| 5.3 | Sales Manager | Credit bureau API timeout LIVE | B | CR-9408 |
| 5.4 | Sales Manager | Blank dashboard after lunch break | A | KB-012 |
| 5.5 | Sales Manager | Wrong commission split LIVE | B | CR-9409 |

---

*End of Testing Framework — Version 1.0*

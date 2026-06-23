# CoderoadERP AI Copilot — Frequently Asked Questions (FAQ)

> **Version:** 1.0 | **Classification:** Internal — Demo Use  
> **Audience:** All CoderoadERP and CoderoadOPS users across all roles  
> **Language:** English (B2)

---

## General System Questions

**Q: What is the CoderoadERP AI Copilot?**  
A: The AI Copilot is an intelligent support assistant embedded in the CoderoadERP platform. It accepts questions by text or voice, analyzes the issue, and either resolves it immediately using the Knowledge Base or creates a structured support ticket in Jira automatically — without the need to fill out any forms.

---

**Q: What types of issues can the AI Copilot resolve on its own?**  
A: The Copilot can resolve any issue that matches an article in the Knowledge Base. This includes connection timeouts, PDF generation failures, greyed-out buttons, printer routing issues, credit limit blocks, stuck inventory locks, user account lockouts, and browser cache problems. These are called **Route A** resolutions.

---

**Q: What happens when the AI Copilot cannot resolve my issue directly?**  
A: If your issue does not match a known KB article — or if it involves an undocumented error in the LIVE environment — the Copilot automatically creates a support ticket in Jira (CodeRoute project) with all the relevant technical details pre-filled. This is called a **Route B** escalation. You receive the ticket number immediately in the conversation.

---

**Q: Can I report issues by voice instead of typing?**  
A: Yes. The AI Copilot accepts audio input. Your voice message is transcribed automatically using the Whisper Speech-to-Text engine and processed in exactly the same way as a typed message. You do not need to repeat information — a single voice description is enough.

---

**Q: Does the AI Copilot work in both the LIVE and TEST environments?**  
A: Yes. The Copilot supports both environments. Issues reported in `LIVE` are treated with higher priority. Financial controls and escalation rules are strictly enforced for LIVE issues. In `TEST`, the Copilot is more flexible and may suggest self-service options before escalating.

---

**Q: Will the Copilot ask me multiple questions one by one?**  
A: No. If your initial message is missing critical information (such as the document number or the affected environment), the Copilot will ask for all missing details in a single, clearly formatted message. You only need to respond once with the complete information.

---

## Production & Plant Operations

**Q: I cannot allocate a roll batch and the system says it is locked by another terminal. What should I do?**  
A: This is a known issue caused by an orphaned database row lock. Ask the AI Copilot to help you with the locked batch and provide the batch number. The Copilot will guide you to **CoderoadOPS → Inventory Utilities → Active Session Monitor** to force-clear the stale lock. Full instructions are in **KB-006**.

---

**Q: The start button for a production order is greyed out. Is this a system error?**  
A: Not necessarily. In most cases, a greyed-out button means your user role does not have the required permission level for that specific action or document value. Check **My Profile → Permissions** to review your authorization levels, or ask a floor supervisor to enter an override PIN. See **KB-003** for full details.

---

**Q: The machine queue screen for my corrugator line is completely blank in LIVE. What information does the AI Copilot need?**  
A: The Copilot will need the specific **line or machine identifier** and any **error codes** visible on the screen (even partial codes help). It will also ask for the **software patch version** shown at the screen footer. With this information, it can create an accurate engineering ticket.

---

**Q: I am seeing Error Code ERR-402 on a production order. Is this in the Knowledge Base?**  
A: ERR-402 is not a known self-service issue and will trigger a **Route B** escalation. Provide the Copilot with your production order number and confirm whether you are in LIVE or TEST. A Jira ticket will be created immediately for the engineering team.

---

**Q: The barcode scanner is throwing an invalid sync warning for a finished goods pallet. How do I report this?**  
A: Tell the AI Copilot the **pallet ID** and confirm whether the issue is happening in LIVE or TEST. The environment confirmation is critical for routing. Provide both pieces of information together for the fastest response.

---

## Billing & Finance

**Q: Why is the system blocking me from approving an invoice because of a credit limit?**  
A: CoderoadERP applies a real-time credit check when posting invoices. If the customer's outstanding balance exceeds their approved credit line, the system triggers a soft block. This is a financial control, not a system error. See **KB-004** for the step-by-step process to apply a temporary credit extension or allocate unmatched payments.

---

**Q: The PDF download button for an invoice does nothing when I click it. Is the system down?**  
A: No. This is almost always caused by the browser's pop-up blocker silently canceling the PDF generation script. Look for a blocked pop-up icon in the browser address bar, allow pop-ups from CoderoadERP, and try again. Full instructions are in **KB-002**.

---

**Q: The tax calculation on an invoice is showing 0% VAT incorrectly. What should I do?**  
A: This is a critical data anomaly that requires engineering review. Provide the AI Copilot with the invoice number and confirm you are in LIVE. The Copilot will escalate immediately to Tier-3 support via a Jira ticket.

---

**Q: The "Post Ledger" function is timing out for a quarterly report in TEST. Should I be concerned?**  
A: A posting timeout in TEST requires investigation by a database administrator but is not a critical emergency. The AI Copilot will create a Jira ticket with the relevant details. TEST environment jobs will be reviewed by the next business day.

---

**Q: I received a "duplicate sequence block" warning in the billing screen but I do not know what document is causing it.**  
A: The AI Copilot needs the specific **Invoice or Document Number** and the **environment (LIVE or TEST)** to investigate. Provide both in your next message and the Copilot will guide you to resolution.

---

## Logistics & Warehouse

**Q: The thermal printer at the loading dock is not responding when I try to print a Bill of Lading.**  
A: This is a known printer routing issue. After a network restart, the workstation sometimes reverts to "Spooler Pool" mode, which loses the direct connection to dock thermal printers. See **KB-005** for the step-by-step fix in **Logistics Setup → Local Print Routing**.

---

**Q: The load guide for a truck that is ready to depart will not release because of a weight tolerance error.**  
A: A weight tolerance block in LIVE is treated as high priority because it directly impacts logistics operations. Provide the AI Copilot with the Load Guide number and it will immediately create a Jira ticket and page the logistics operations support team.

---

**Q: Vehicle allocations in the fleet routing system are not updating in TEST. Who should I contact?**  
A: This indicates a cross-system message queue issue between CoderoadERP and CoderoadOPS. The AI Copilot will log a Jira ticket for the integration engineering team. Because this is in TEST, it is non-critical but will be reviewed the same business day.

---

**Q: A warehouse bin transfer button is completely inactive for an item in the staging environment.**  
A: Inactive buttons typically indicate a role permission limitation. In TEST, permission settings mirror LIVE for testing accuracy. Check **My Profile → Permissions** or see **KB-003** for the override procedure.

---

## IT & System Administration

**Q: A user cannot log in because their account has been locked. How do I unlock it quickly?**  
A: Log in to the **CoderoadERP Administration Console → Security → User Management**, find the user by Employee ID or email, and click "Unlock Account." See **KB-007** for the full procedure including the optional forced password reset.

---

**Q: Data from CoderoadERP is not showing up in CoderoadOPS — orders posted an hour ago are still missing.**  
A: This indicates a message queue stall in the Integration Layer. Check the **Integration Health Monitor → Message Queue Status** panel for queues in "Paused" or "Error State." See **KB-008** for the dead letter queue inspection and retry process.

---

**Q: A scheduled nightly job shows "Partial — Exit Code 2" this morning. Is any data at risk?**  
A: No data is at risk. Exit Code 2 means the job terminated gracefully before completion, typically due to a resource constraint. No corruption occurs. Check the **Scheduled Job Manager** for the execution log and follow **KB-009** to identify the cause and re-run the job manually.

---

**Q: Can the AI Copilot help with server-level infrastructure issues?**  
A: The AI Copilot handles application-level support (CoderoadERP and CoderoadOPS module issues). For infrastructure issues — server hardware failures, network outages, SSL certificate renewals — the Copilot will create a Jira ticket and route it to the infrastructure team, but it cannot perform system-level actions directly.

---

## Sales & Account Management

**Q: A sales order is showing prices that do not match the customer's negotiated contract. What happened?**  
A: This usually means the customer's contract price schedule is missing or expired in CoderoadERP. See **KB-010** for the process to reassign the correct contract and recalculate the order prices.

---

**Q: I am trying to create a new customer account but the system is blocking it as a potential duplicate.**  
A: CoderoadERP's duplicate prevention engine checks Tax ID, company name, and primary address. Navigate to **CRM → Customer Accounts → Duplicate Management Console** to review both records side by side. See **KB-011** for the merge or confirm-as-unique procedure.

---

**Q: The sales dashboard is not showing the current month's KPIs — the panel is completely blank.**  
A: This is almost certainly a browser cache issue following a recent system update. Clear your browser cache for the CoderoadERP domain, log out, and log back in. See **KB-012** for the full procedure. If the panel is still blank in an Incognito window, report it as a server-side issue via the AI Copilot.

---

**Q: The commission calculation on a sales order is showing the wrong split between two account managers.**  
A: Commission allocation errors in LIVE are flagged as high priority because they affect payroll. Provide the AI Copilot with the Sales Order number and the names or IDs of the involved account managers. The Copilot will create a Jira ticket for the Finance and Commissions team.

---

**Q: A new customer account creation is being blocked because of a credit bureau API timeout.**  
A: When CoderoadERP cannot reach the external credit bureau API to perform a background credit check, it blocks new account creation as a precaution. The AI Copilot will create a Jira ticket and notify the IT team to check the API connection status. You can retry the account creation once the connection is restored.

---

*End of FAQ — Version 1.0*

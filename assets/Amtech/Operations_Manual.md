# CoderoadERP + CoderoadOPS — Generic ERP Operations Manual

> **Version:** 1.0 | **Classification:** Internal — Demo Use  
> **Purpose:** Reference manual for the AI Copilot system. Describes the core system architecture, data flow mechanics, and module interactions that the agent uses to triage and route support requests accurately.

---

## 1. System Overview

The Coderoad enterprise platform consists of two interconnected systems that together cover the full order-to-cash and plan-to-produce lifecycle:

| System | Primary Domain | Typical Users |
|--------|---------------|---------------|
| **CoderoadERP** | Commercial operations: Sales, Billing, CRM, Finance, Purchasing | Billing Clerks, Sales Managers, Finance Teams |
| **CoderoadOPS** | Shop-floor execution: Production scheduling, inventory optimization, machine queuing | Plant Operators, Logistics Managers, Production Planners |

Both systems share a unified user authentication layer (Single Sign-On) and exchange data in real time through a dedicated **Integration Message Queue (IMQ)**.

---

## 2. Core Data Synchronization Process

Data flows continuously between CoderoadERP and CoderoadOPS through the IMQ. Understanding this pipeline is essential for accurate issue triage.

### 2.1 Order Initiation (CoderoadERP → CoderoadOPS)

When a Sales Order (SO) or Purchase Order (PO) is finalized and approved in CoderoadERP, a structured data payload containing the physical line-item specifications (dimensions, material grades, quantities, delivery dates) is placed into the IMQ. CoderoadOPS picks up this payload within 60–90 seconds and creates the corresponding production order in the manufacturing scheduler.

### 2.2 Production Completion (CoderoadOPS → CoderoadERP)

When CoderoadOPS marks a production order as complete, it broadcasts a completion receipt back to CoderoadERP. This triggers:

- Automatic update of the shipping schedule
- Generation of the Bill of Lading (BOL) and Load Guide documents in the Logistics module
- Initiation of the customer invoicing cycle in the Billing module

### 2.3 Inventory Reconciliation (Bidirectional)

Physical inventory movements recorded in CoderoadOPS (raw material consumption, finished goods output, pallet transfers) are synchronized back to CoderoadERP's finance module for accurate Cost of Goods Sold (COGS) accounting. This reconciliation runs every 15 minutes during production hours.

---

## 3. Module Reference Guide

### 3.1 CoderoadERP Modules

| Module | Function | Common Support Issues |
|--------|----------|-----------------------|
| **Sales** | Sales order entry, contract pricing, customer master data | Pricing mismatches, credit blocks, order approval failures |
| **Billing** | Invoice generation, payment allocation, credit management | PDF failures, ledger posting errors, VAT calculation anomalies |
| **Finance** | General ledger, accounts receivable/payable, credit matrices | Ledger timeout, credit limit blocks, period-end close failures |
| **CRM** | Customer profiles, contact management, duplicate prevention | Duplicate account blocks, contract assignment errors |
| **Purchasing** | Vendor orders, goods receipts, three-way matching | PO approval failures, goods receipt mismatches |

### 3.2 CoderoadOPS Modules

| Module | Function | Common Support Issues |
|--------|----------|-----------------------|
| **Production Scheduler** | Machine queue, production order management | Greyed-out buttons, queue blank screens, approval blocks |
| **Inventory Utilities** | Roll stock allocation, batch tracking, row lock management | Stale row locks, stuck batch allocations |
| **Logistics** | Load guide creation, BOL printing, fleet dispatch | Thermal printer failures, weight tolerance blocks |
| **Quality Control** | Finished goods inspection, pallet validation | Barcode sync errors, pallet ID mismatches |

---

## 4. Database Locking Mechanics

To maintain transaction integrity, CoderoadOPS applies temporary row locks whenever an operator modifies a critical record. This prevents simultaneous edits from corrupting data.

### 4.1 Normal Lock Lifecycle

1. User opens a record (e.g., a Roll Stock batch) for editing — lock is applied.
2. User saves the change — lock is released automatically.
3. The updated record is available to other users immediately.

### 4.2 Orphaned Lock Scenario

If a session is interrupted before saving (network drop, browser crash, forced logout), the lock remains active indefinitely. The system cannot distinguish between an active session and a dead one without administrative intervention.

**Symptoms:**
- "Record is locked by another terminal" error message
- Batch, pallet, or document appears "in use" with no active operator

**Resolution:** Use the **Active Session Monitor** in CoderoadOPS → Inventory Utilities to identify and force-clear orphaned locks. See **KB-006** for the full procedure.

---

## 5. Environment Architecture

CoderoadERP and CoderoadOPS operate in two parallel environments:

| Environment | Label | Purpose | Financial Controls |
|-------------|-------|----------|--------------------|
| **Production** | `LIVE` | Real business operations, actual customer data | Fully enforced |
| **Staging / Sandbox** | `TEST` | Training, QA testing, configuration changes | Disabled |

> **Critical Rule for AI Copilot:** Any issue reported in the `LIVE` environment that cannot be resolved via a known KB article must be escalated immediately via a Jira ticket. Issues in `TEST` may have a higher tolerance for investigation before escalation.

---

## 6. User Role & Permission Model

CoderoadERP uses a five-tier permission model that controls which actions each role can perform on each module:

| Tier | Label | Typical Role | Max Approval Value |
|------|-------|-------------|-------------------|
| 1 | Operator | Plant Operator, Billing Clerk | Read + Limited Write |
| 2 | Senior Operator | Logistics Manager, Senior Billing | Write + Departmental Approval |
| 3 | Supervisor | Department Supervisor | Write + Cross-department Approval |
| 4 | Manager | Sales Manager, IT Administrator | Full Module Access |
| 5 | Administrator | System Administrator, Finance Director | Full System Access |

Permission mismatches are the most common cause of greyed-out buttons and action blocks. See **KB-003** for the resolution workflow.

---

## 7. Jira Integration — CodeRoute Project

When the AI Copilot cannot resolve an issue via a KB article (Route B), it creates a structured ticket in the **Coderoad Jira project: CodeRoute**.

### 7.1 Required Ticket Fields

| Field | Source | Example |
|-------|--------|---------|
| `Module` | Extracted from user input | Production, Billing, Logistics |
| `Document_ID` | Extracted from user input | PO-7731, INV-4001, GD-7782 |
| `Description` | Summarized from full interaction | "Error ERR-402 on material consumption post" |
| `Environment` | Confirmed from user | LIVE / TEST |
| `Error_Code` | Extracted if mentioned | ERR-402, ERR-500, ERR-DB-LOCK |
| `Priority` | Assigned by AI based on environment | LIVE = High, TEST = Medium |
| `Reporter_Role` | Inferred from user context | Plant Operator, Billing Clerk |

### 7.2 Ticket Numbering Convention

Tickets follow the format `CR-XXXX` (e.g., CR-9401). The AI Copilot confirms the ticket number to the user upon successful creation.

---

## 8. AI Copilot Integration Points

The AI Copilot connects to the following systems in the demo environment:

| Integration | Purpose | Protocol |
|-------------|---------|----------|
| **KB Index** | Article matching for Route A | Vector similarity search |
| **Jira API** | Ticket creation for Route B | REST API (CodeRoute project) |
| **Whisper STT** | Audio transcription for voice inputs | OpenAI Whisper v3 |
| **CoderoadERP API** | Optional: live document status lookup | REST API (read-only) |

---

*End of Operations Manual — Version 1.0*

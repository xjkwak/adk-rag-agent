# SOP-402: Component Traceability & MSL Handling
**Effective Date:** 2024-01-15  
**Revision:** 3.2  
**Classification:** CONTROLLED DOCUMENT — Aerospace & Defense Programs  
**Applicable Standards:** IPC/JEDEC J-STD-033D, MIL-STD-130N, AS9100D Section 8.5.2

---

## Section 1: Moisture Sensitive Device (MSD) Controls

### 1.1 Floor Life Tracking (Mandatory)
Every Moisture Sensitive Device (MSD) classified MSL-2 through MSL-6 **must** have its Floor Life tracked in the MES from the moment the sealed dry-pack bag is opened.

**Requirements:**
- The MES shall record the **bag-open timestamp** for every MSD lot.
- Floor Life remaining shall be calculated in real-time as: `FloorLifeRemaining = MSL_Limit_Hours - (CurrentTime - BagOpenTimestamp)`.
- **If a component's Floor Life has expired, the SMT line MUST be blocked from mounting the part.** The operator shall receive an explicit error: "MSL LIMIT EXCEEDED — BAKE OR DISCARD."
- Components that exceed Floor Life may be recovered via a **bake-out cycle** per J-STD-033D Table 4-1. The bake-out must be recorded in the MES before the component is returned to the floor.

### 1.2 MSL Classification Override
If an engineer determines that a component's MSL classification should be overridden (e.g., from MSL-3 to MSL-2a), the override requires:
- A written justification referencing test data.
- Digital signature from a **Level III IPC Specialist** or above.
- The override must be recorded in the component master record and flagged in every subsequent WO that consumes the part.

---

## Section 2: Unique Identification (UID) Policy

### 2.1 Scope
All components classified as **"High Value"** (unit cost > $50 or criticality class A/B in ERP) require Unique Identification per MIL-STD-130N.

### 2.2 UID Format
UIDs shall follow the construct: `[CAGE_CODE]-[PART_NUMBER]-[SERIAL]`. Example: `1ABC2-MCU-7700-00145`.

### 2.3 As-Built Record Integrity (Mandatory)
- A Work Order (WO) **cannot be closed** unless **100% of the BoM items classified as High Value** have valid UIDs recorded in the as-built record.
- The MES shall enforce this at the point of WO closure. If any High-Value line item has a null or empty UID, the system must block closure and display: "AS-BUILT INCOMPLETE — MISSING UIDs FOR [PART_LIST]."
- Manual override of this block requires dual digital signatures: the **Production Supervisor** and a **Quality Engineer**.

### 2.4 UID Verification at Receiving
Upon receiving High-Value components, the warehouse must scan and validate the UID against the supplier's Certificate of Conformance (CoC). Mismatches must trigger a Non-Conformance Report (NCR).

---

## Section 3: As-Built Record Retention

### 3.1 Retention Period
As-built records for Aerospace and Defense programs shall be retained for a **minimum of 15 years** from the date of final delivery.

### 3.2 Immutability
Once a WO is closed and the as-built record is finalized, **no modifications are permitted** without a formal Corrective Action (CA) process. The original record must be preserved, and amendments tracked as separate entries.

### 3.3 Audit Access
Quality Auditors and regulatory inspectors shall have **read-only access** to all as-built records at any time, with full traceability to the operator, timestamp, and station that recorded each data point.

---

## Section 4: Compliance Verification

### 4.1 Periodic Audit
The Quality Department shall conduct quarterly audits of MSL tracking compliance and UID integrity. Findings must be documented in the CAPA system.

### 4.2 System Validation
Any changes to the MES logic governing MSL tracking or UID enforcement must go through a formal **IQ/OQ/PQ validation cycle** per 21 CFR Part 11 (for Medical Device programs) or AS9100D Section 8.5.1.

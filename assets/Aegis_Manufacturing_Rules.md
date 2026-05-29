# Aegis Manufacturing Execution Rules
**Document ID:** MFG-RULES-2024  
**Revision:** 2.1  
**Scope:** All SMT and Through-Hole Assembly Lines  
**Applicable to:** FactoryLogix MES Configuration

---

## Rule MFG-01: Work Order Status Transitions
A Work Order must follow this lifecycle:  
`CREATED → RELEASED → IN_PROGRESS → COMPLETED → CLOSED`

**Constraints:**
- Transition from RELEASED to IN_PROGRESS requires a successful **Line Clearance** check.
- Transition from COMPLETED to CLOSED requires **As-Built Validation** (see SOP-402 Section 2.3).
- No WO may skip a status. Backdating of status transitions is prohibited.

---

## Rule MFG-02: Line Clearance Protocol
Before any WO transitions to IN_PROGRESS, the following must be verified:
1. All feeder positions match the BoM.
2. Solder paste has not exceeded its 4-hour open-life limit.
3. No previous WO residual material remains on the line.
4. The operator has scanned their badge confirming line readiness.

**Enforcement:** The MES shall block the transition if any check fails. Manual override requires a Production Supervisor's digital signature.

---

## Rule MFG-03: First Article Inspection (FAI)
The first unit off any new WO setup must pass a First Article Inspection before full production begins. FAI results must be recorded in the MES with:
- Inspector ID
- Timestamp
- Pass/Fail status
- Photo evidence (if visual inspection)

---

## Rule MFG-04: Operator Certification Check
Operators must hold valid certifications for the processes they perform:
- **IPC-A-610** for visual inspection
- **IPC J-STD-001** for soldering
- **IPC-7711/7721** for rework

The MES shall verify operator certification status at login. Expired certifications must block the operator from performing the associated process.

---

## Rule MFG-05: Traceability Granularity
For Aerospace & Defense programs:
- **Component-level traceability** is required for all Class A and Class B components.
- **Lot-level traceability** is acceptable for Class C components (passives, standard fasteners).
- The MES must record: Component UID or Lot ID, Station ID, Operator ID, Timestamp, and Machine Program Version.

---

## Rule MFG-06: Non-Conformance Handling
When a defect is detected:
1. The defective unit must be **quarantined** in the MES (status = HOLD).
2. A Non-Conformance Report (NCR) must be opened within **4 hours** of detection.
3. Disposition (Use As-Is, Rework, Scrap) requires a **Material Review Board (MRB)** decision.
4. If the defect affects more than 3 units in the same lot, a **containment action** must be triggered automatically.

---

## Rule MFG-07: Engineering Change Order (ECO) Management
- ECOs must be **digitally signed** by the Design Engineer and the Manufacturing Engineer before release.
- If a WO is **currently IN_PROGRESS** when an ECO is released that affects its BoM or process routing:
  - The line must **pause** immediately.
  - A **Re-validation** must be performed (equivalent to a new Line Clearance + FAI).
  - The WO must be annotated with the ECO reference number.
- ECOs that affect Critical components require an additional sign-off from Quality.

---

## Rule TRACE-01: Manual Material Substitution
Any manual material substitution on the factory floor must follow this protocol:
1. The substitute component must be **form-fit-function equivalent** per the approved AVL (Approved Vendor List).
2. If the original component is classified as **"Critical"** in the ERP system:
   - A **Quality Engineer's digital signature** is required before the substitution can proceed.
   - The substitution must be recorded in the as-built record with both the original and substitute part numbers.
3. If the component is not classified as Critical, a Production Supervisor's signature suffices.
4. All substitutions must be auditable and traceable in the MES for a minimum of 10 years.

---

## Rule TRACE-02: Serialization for High-Reliability Programs
For Medical Device (FDA 21 CFR 820) and Defense (DFARS 252.211-7003) programs:
- Every finished assembly must receive a unique serial number at the point of final test.
- The serial number must be linked to the complete as-built record in the MES.
- Serial numbers cannot be reused, even for scrapped units.

---

## Rule TRACE-03: Supplier Lot Traceability
Incoming materials must retain the supplier's lot identification through the entire manufacturing process. If a field failure is traced back to a supplier lot, the MES must be able to identify:
- All WOs that consumed material from that lot.
- All finished assemblies that contain components from that lot.
- All customers who received units containing that lot.

# Agent Test Questions

This file contains sample questions used to test the Knowledge Hub agent (Aegis Manufacturing Oracle). Use it after seeding the `aegis-demo` corpus to validate retrieval, compliance analysis, and role-appropriate responses across detail levels (Low / High).

Role 1: Production Manager

1. Will our current system block the line if an operator tries to use a component that has exceeded its Moisture Sensitivity Level (MSL) limit?
2. What is our exposure if we ship units with incomplete As-Built records?
3. If we discover a defective lot from a supplier, can the system tell me which shipped units contain parts from that lot?
4. How much unplanned downtime could we face from ECO-related disruptions?
5. Can an operator start a production run without proper authorization?

Role 2: Manufacturing Engineer

1. I'm reviewing WorkOrderService.cs. What compliance gaps exist in the ExecuteMaterialPick method?
2. Why is the solder paste open-life check using 8 hours instead of 4?
3. How should we refactor the material consumption flow to include MSL validation?
4. We're getting quality flags on closed WOs with missing data. Where exactly is the vulnerability in the database logic?
5. Is the ECO impact check in LineValidationService.cs reliable?

Role 3: Quality Auditor

1. Show me evidence of non-compliance with our Unique Identification (UID) policy.
2. Are manual Work Order closures being audited correctly?
3. Can you identify all locations where a required digital signature is bypassed?
4. Is the system capable of blocking production when operator certifications expire?
5. What is the state of our First Article Inspection enforcement?

Role 4: IT / Systems Architect

1. What are the critical integration points between the MES code and the ERP system?
2. How would you design the data model to properly support MSL Floor Life tracking?
3. What's the risk of the hardcoded EngineerId > 5 logic in the audit procedure?
4. If we wanted to scale this system to support multiple factory sites, what breaks first?
5. What monitoring and alerting should we build around these compliance gaps?

Role 5: VP of Operations / Executive

1. In plain terms, what's the biggest risk in our current system?
2. What would it cost us if an auditor found these gaps?
3. Why do we need an intelligent agent for this? Can't we just put all our SOPs in Google Drive and search them?
4. How does this scale beyond our current codebase?
5. What's the competitive advantage of having this versus our competitors?

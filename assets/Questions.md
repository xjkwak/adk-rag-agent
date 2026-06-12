Role 1: Production Manager
Will our current system block the line if an operator tries to use a component that has exceeded its Moisture Sensitivity Level (MSL) limit?
What is our exposure if we ship units with incomplete As-Built records?
If we discover a defective lot from a supplier, can the system tell me which shipped units contain parts from that lot?
How much unplanned downtime could we face from ECO-related disruptions?
Can an operator start a production run without proper authorization?

Role 2: Manufacturing Engineer
I'm reviewing WorkOrderService.cs. What compliance gaps exist in the ExecuteMaterialPick method?
Why is the solder paste open-life check using 8 hours instead of 4?
How should we refactor the material consumption flow to include MSL validation?
We're getting quality flags on closed WOs with missing data. Where exactly is the vulnerability in the database logic?
Is the ECO impact check in LineValidationService.cs reliable?

Role 3: Quality Auditor
Show me evidence of non-compliance with our Unique Identification (UID) policy.
Are manual Work Order closures being audited correctly?
Can you identify all locations where a required digital signature is bypassed?
Is the system capable of blocking production when operator certifications expire?
What is the state of our First Article Inspection enforcement?

Role 4: IT / Systems Architect
What are the critical integration points between the MES code and the ERP system?
How would you design the data model to properly support MSL Floor Life tracking?
What's the risk of the hardcoded EngineerId > 5 logic in the audit procedure?
If we wanted to scale this system to support multiple factory sites, what breaks first?
What monitoring and alerting should we build around these compliance gaps?

Role 5: VP of Operations / Executive
In plain terms, what's the biggest risk in our current system?
What would it cost us if an auditor found these gaps?
Why do we need an intelligent agent for this? Can't we just put all our SOPs in Google Drive and search them?
How does this scale beyond our current codebase?
What's the competitive advantage of having this versus our competitors?
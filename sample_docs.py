

DOCUMENTS = [
    {
        "id": "sop-production-001",
        "domain": "production",
        "title": "Production Line Deviation Response SOP",
        "text": (
            "When a production line's defect rate exceeds 8% over a rolling 5-day window, or downtime "
            "exceeds 30 minutes/day for 3+ consecutive days, initiate a Tier-2 investigation. The line "
            "supervisor must document the deviation, pause non-critical changeovers, and escalate to the "
            "Quality team within 4 hours. Root causes typically fall into: tooling wear, operator training "
            "gaps, upstream material defects, or environmental drift (temperature/humidity). Corrective "
            "actions above $10,000 in estimated impact require plant manager approval before execution."
        ),
    },
    {
        "id": "sop-inventory-001",
        "domain": "inventory",
        "title": "Inventory Reorder Policy",
        "text": (
            "Any SKU falling below its defined reorder point triggers an automatic replenishment "
            "recommendation. Standard reorders under $5,000 may be auto-approved. Reorders between "
            "$5,000 and $25,000 require warehouse manager sign-off. Reorders above $25,000, or any "
            "emergency expedited shipment, require procurement director approval due to freight premium "
            "costs. Safety stock should never be allowed to reach zero for SKUs flagged as customer-critical."
        ),
    },
    {
        "id": "sop-quality-001",
        "domain": "quality",
        "title": "Customer Complaint Escalation Playbook",
        "text": (
            "A complaint spike (2x the 30-day average) on any product line is treated as a potential "
            "field-quality issue. Quality Engineering must cross-reference recent production and inspection "
            "records for the same line and date range. If a correlated defect pattern is found, a containment "
            "action (hold shipments from the affected lot) is required before root-cause analysis completes. "
            "Containment decisions are high-risk and always require human approval regardless of dollar impact."
        ),
    },
    {
        "id": "sop-procurement-001",
        "domain": "procurement",
        "title": "Supplier Performance Management Policy",
        "text": (
            "Suppliers whose on-time delivery rate falls below 80% over a trailing 30-day period are flagged "
            "for a performance review. Two consecutive flagged periods trigger a formal corrective action "
            "request (CAR) to the supplier and activation of a backup/dual-sourcing plan for critical items. "
            "Switching primary suppliers requires procurement director approval given contractual and quality "
            "requalification implications."
        ),
    },
    {
        "id": "sop-finance-001",
        "domain": "finance",
        "title": "Departmental Budget Variance Policy",
        "text": (
            "Departments exceeding their monthly budget by more than 15% must submit a variance explanation "
            "within 5 business days. Variances above 25%, or any variance that would cause year-to-date "
            "spend to exceed 90% of annual budget before Q3, require CFO review and are treated as high-risk "
            "financial actions requiring explicit approval before any reallocation or additional spend is approved."
        ),
    },
    {
        "id": "sop-hr-001",
        "domain": "hr",
        "title": "Attrition and Headcount Risk Guidelines",
        "text": (
            "A department with attrition exceeding 10% in a rolling 90-day window, combined with open "
            "positions above 15% of headcount, is flagged as a retention risk. HR Business Partners should "
            "initiate stay interviews and review compensation benchmarking. Any headcount backfill request "
            "tied to a flagged department is prioritized in the hiring pipeline but still requires standard "
            "hiring-manager and finance approval before requisitions open."
        ),
    },
    {
        "id": "sop-sales-001",
        "domain": "sales",
        "title": "Regional Sales Underperformance Playbook",
        "text": (
            "A region trailing more than 15% behind its trailing-90-day average revenue run rate is reviewed "
            "in the weekly sales operations meeting. Recommended interventions include targeted promotions, "
            "pipeline coverage review, and reallocating sales development resources. Discount or promotion "
            "actions affecting margin by more than 5 percentage points require sales director approval."
        ),
    },
    {
        "id": "sop-projects-001",
        "domain": "projects",
        "title": "Project Health and Escalation Standard",
        "text": (
            "A project is 'at risk' when actual spend exceeds the percent-complete-adjusted budget by more "
            "than 10%, or the due date is within 30 days with completion below 70%. At-risk projects require "
            "a recovery plan from the project sponsor. Budget increases or scope changes on at-risk projects "
            "require portfolio steering committee approval."
        ),
    },
    {
        "id": "sop-operations-001",
        "domain": "operations",
        "title": "General Operations Risk Tiering",
        "text": (
            "Operational recommendations are tiered: Low risk (informational, no cost, reversible) can be "
            "auto-executed. Medium risk (moderate cost, or process changes affecting a single team) require "
            "notification but not blocking approval. High and Critical risk (safety, compliance, customer-"
            "facing, or spend above departmental discretionary limits) always require a named human approver "
            "before the Action Agent executes anything."
        ),
    },
    {
        "id": "sop-reporting-001",
        "domain": "reporting",
        "title": "Executive Reporting Standards",
        "text": (
            "Cross-domain reports synthesized for leadership must cite the underlying data window, flag data "
            "quality caveats, and distinguish between LLM-generated interpretation and directly queried facts. "
            "Any recommendation included in an executive report must also appear in the workflow's approval "
            "trail if it was above the auto-approval risk threshold."
        ),
    },
]

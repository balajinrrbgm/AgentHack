# 🎬 Demo Script — ProcureFlow AI
## Track 2: UiPath Maestro BPMN | Time: 5 minutes

---

## Pre-Demo Setup Checklist
- [ ] UiPath Maestro BPMN editor showing the full P2P process
- [ ] Requisition intake portal open
- [ ] Action Center ready (manager approval persona)
- [ ] SAP/mock ERP dashboard visible
- [ ] Invoice processing queue showing 1 pending invoice
- [ ] Analytics dashboard in second tab
- [ ] Backup recording ready

---

## Demo Flow (5 minutes total)

---

### ⏱️ 0:00–0:30 — Opening Hook (30 seconds)

**Say:**
> "Your finance team is drowning. 65% of invoices require manual intervention. Purchase orders sit in email chains. Vendors call every week asking where their payment is. Invoice fraud cost enterprises $1.2 million on average last year. And the ERP? It's SAP. Nobody wants to touch it. This is ProcureFlow AI — end-to-end procurement, automated, on UiPath Maestro BPMN."

**Show:** The BPMN process diagram in Maestro — all lanes visible: Requester, AI Agents, Procurement, Vendor, AP, Finance.

---

### ⏱️ 0:30–1:30 — Requisition to PO (60 seconds)

**Say:**
> "Let's start at the beginning. A team lead sends a purchase request."

**Action:** Type into the requisition portal:
> "I need 15 MacBook Pro 14-inch laptops for the new engineering team starting next Monday. Budget should come from IT-001. Pretty urgent."

**Click Submit.**

**Say:**
> "Natural language. No forms. No codes. Watch our LangChain Requisition Agent process this."

**Show:** BPMN diagram — first task "Parse Requisition" lights up as active.

**Show:** Agent output (appears in 3 seconds):
```
Extracted: 15 × MacBook Pro 14" | Category: IT Hardware
Estimated cost: $29,250 (at $1,950/unit)
Cost Center: IT-001 | Available Budget: $130,000 ✓
Vendor: TechSupply Corp (preferred vendor, score: 92/100, 5-day delivery)
Approval Required: MANAGER (>$10K threshold)
Policy: No violations
```

**Say:**
> "In 3 seconds: parsed, estimated, vendor matched, budget validated, routing determined. Managers need to approve — above the $10K auto-approve threshold."

**Show:** BPMN gateway activates — branches to "Manager Approval" lane.

**Action:** Switch to Action Center. Approve the requisition.

**Show:** BPMN flow continues — PO generation task activates.

**Say:**
> "Approved. Now RPA generates the PO in SAP."

**Show:** SAP screen (or mock) — PO created: PO-2024-4471, $29,250, TechSupply Corp.

---

### ⏱️ 1:30–2:30 — Invoice 3-Way Match (60 seconds)

**Say:**
> "Jump forward — goods arrived, receipt confirmed. Now the invoice comes in."

**Action:** Click "Process Invoice" — shows a PDF invoice from TechSupply Corp.

**Say:**
> "Document Understanding extracts the invoice data. Then our AutoGen 3-Way Match Agent compares PO, goods receipt, and invoice."

**Show:** 3-way match table appearing:
```
Item: MacBook Pro 14"
PO Quantity: 15 | Received: 15 | Invoice: 15 ✓
PO Price: $1,950 | Invoice Price: $1,975 ⚠️ (+$25/unit)
Variance: $375 total (1.3% — within 2% tolerance)
Result: WITHIN TOLERANCE — auto-resolving at PO rate
```

**Say:**
> "The invoice price is slightly higher — $25 per unit. That's 1.3% variance. Within our 2% auto-resolve tolerance. Our agents handle it automatically — pay the PO rate, no human needed."

**Show:** BPMN — bypasses manual AP review, flows directly to Fraud Check.

**Say:**
> "But watch — what if there was a REAL discrepancy?"

**Action:** Click "Demo: Fraud Scenario"

**Show:** CrewAI fraud detection crew activating:
```
Fraud Investigator Agent: NEW BANK ACCOUNT for vendor TechSupply Corp
  → Previous IBAN: DE89370400440532013000
  → New IBAN: DE12345678901234567890
  → ALERT: Bank account changed 3 days ago — HOLD PAYMENT
```

**Say:**
> "The fraud agent caught a bank account change — a classic vendor impersonation attack. Payment automatically held. Action Center task created for finance investigation."

---

### ⏱️ 2:30–3:30 — BPMN Visualization & Process Control (60 seconds)

**Say:**
> "This is the power of BPMN 2.0 in Maestro. Every step is visible, auditable, and controllable."

**Show:** Full BPMN diagram with active processes highlighted.

**Say:**
> "I can see 47 active purchase orders right now. 3 awaiting approval. 2 in fraud investigation. 1 pending invoice reconciliation. No more guessing where things are stuck."

**Show:** Maestro process analytics:
- Average end-to-end time: 2.4 days (vs 14 day industry average)
- Auto-resolved invoices: 87%
- Fraud attempts caught: 3 this month
- Cost savings vs previous process: $180K this quarter

**Say:**
> "87% of invoices are fully automated. Finance now handles only genuine exceptions — not a tsunami of manual work."

---

### ⏱️ 3:30–4:15 — ERP Update & Payment (45 seconds)

**Say:**
> "Back to our standard flow — fraud check cleared. Payment goes through."

**Show:** BPMN final lanes lighting up:
- ✅ SAP ERP updated — invoice cleared
- ✅ EFT payment triggered: $29,250 to TechSupply Corp
- ✅ Vendor notification sent
- ✅ Process instance closed — audit trail complete

**Say:**
> "Full audit trail for SOX compliance. Every agent decision, every human approval, every system interaction — recorded and timestamped."

---

### ⏱️ 4:15–4:45 — Coding Agents BONUS (30 seconds)

**Say:**
> "This was built using UiPath for Coding Agents. Claude Code wrote the AutoGen reconciliation agent while I described it in plain English."

**Show:** Brief terminal flash:
```bash
$ claude "add a contract price escalation clause validator to the 3-way match agent"
# Claude Code analyzes threeway_match_agent.py, generates the new validation function
```

**Say:**
> "From business requirement to production agent code — minutes, not weeks."

---

### ⏱️ 4:45–5:00 — Impact Close (15 seconds)

**Say:**
> "ProcureFlow AI: 87% invoice automation, fraud stopped before payment, full BPMN visibility, SOX-compliant audit trails. The $50 trillion procure-to-pay market, finally automated end to end on UiPath Maestro BPMN. Thank you."

---

## Backup Plans

1. **Agent API down:** Show pre-recorded agent output, click through BPMN manually
2. **SAP demo slow:** Use mock ERP dashboard (prepared screenshots)
3. **Fraud demo glitch:** Walk through architecture slide showing fraud detection logic
4. **General failure:** Switch to architectural walkthrough with 30-second business impact close

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Industry avg invoice processing | 14 days |
| ProcureFlow AI processing | 2.4 days |
| Manual invoice intervention (industry) | 65% |
| ProcureFlow AI auto-resolution | 87% |
| Enterprise invoice fraud (annual avg) | $1.2M |
| Auto-approve threshold | Under $1,000 |
| Manager approval threshold | $1K–$10K |

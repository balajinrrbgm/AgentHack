# 🎬 Demo Script — MediClaim Guardian
## Track 1: UiPath Maestro Case | Time: 5 minutes

---

## Pre-Demo Setup Checklist
- [ ] UiPath Automation Cloud open and logged in
- [ ] Maestro Case view showing empty queue
- [ ] Agent API services running (health check: all green)
- [ ] Sample claim documents prepared (PDF, medical notes)
- [ ] Action Center logged in as "Case Manager" persona
- [ ] Analytics dashboard open in second tab
- [ ] Backup recording ready (local video of full flow)

---

## Demo Flow (5 minutes total)

---

### ⏱️ 0:00–0:30 — Hook: The Problem (30 seconds)

**Say:**
> "Every day, 40 million healthcare claims are submitted in the US. 30% are initially denied. Clinicians spend a third of their time on paperwork instead of patients. And fraud costs the system $100 billion a year. The tools that handle this? Rules engines from the 1990s. Today I'm going to show you what it looks like when that changes."

**Show:** A healthcare claim PDF on screen — messy, multi-page, with codes and numbers.

---

### ⏱️ 0:30–1:30 — Intake & AI Triage (60 seconds)

**Action 1:** Drag a sample claim PDF into the portal intake interface.

**Say:**
> "A provider submits this claim — medical records, an EOB, procedure codes. Watch what happens."

**Action 2:** Click "Submit Claim" — case is created in Maestro.

**Show:** The Maestro Case dashboard refreshes. A new case appears: "CLM-2024-00847 — INTAKE"

**Say:**
> "Maestro Case creates a case automatically. Document Understanding immediately extracts the structured data — diagnosis codes, procedure codes, billed amounts — with confidence scores."

**Show:** Extracted data panel: ICD-10 codes, CPT codes, $47,000 billed, provider NPI.

**Action 3:** Watch the stage advance to "TRIAGE."

**Say:**
> "Now our LangChain clinical reasoning agent — powered by GPT-4o — takes over. It's checking clinical necessity, code alignment, billing patterns. This used to take a human reviewer 45 minutes."

**Show:** Agent reasoning log (briefly): "Checking CPT 27447 against M17.11... checking provider NPI billing patterns... complexity score: 72 — routing to EXPERT_REVIEW"

**Say:**
> "In 8 seconds, it has a complexity score of 72 — high complexity. It's detected a potential billing anomaly. The case moves to investigation."

---

### ⏱️ 1:30–2:45 — Multi-Agent Investigation (75 seconds)

**Show:** Case stage changes to "INVESTIGATION."

**Say:**
> "Here's where it gets interesting. A CrewAI investigation crew launches — three specialized agents working in parallel."

**Show:** Split view or sequential agent logs:
- Fraud Investigator: "Checking provider NPI 1234567... 96th percentile billing for CPT 27447... flagging"
- Clinical Validator: "Procedure-diagnosis alignment: VALID. Documentation supports medical necessity."
- Coverage Checker: "Policy confirmed. Prior auth required for this procedure — checking..."

**Say:**
> "The Fraud Investigator found a billing anomaly. The Clinical Validator confirmed the procedure is medically necessary. The Coverage Checker found a prior authorization requirement. Three agents, three different domains, running simultaneously."

**Action:** Click "View Investigation Report"

**Show:** AutoGen-synthesized investigation report:
```
CLAIM CLM-2024-00847 — INVESTIGATION COMPLETE
Clinical Validity: CONFIRMED (score: 85/100)
Coverage: CONFIRMED with prior auth requirement
Fraud Risk: MEDIUM — billing percentile anomaly flagged
Recommendation: HUMAN REVIEW — prior auth validation + fraud flag review
Payable (if approved): $38,200
```

**Say:**
> "AutoGen synthesized all three agents' findings into one coherent report with a payment recommendation."

---

### ⏱️ 2:45–3:30 — Human-in-Loop (45 seconds)

**Show:** Action Center notification badge appears.

**Say:**
> "Maestro Case created a human task with everything the case manager needs. No digging through systems."

**Action:** Open Action Center task.

**Show:** Task with:
- One-page AI-generated case summary
- Clinical findings
- Fraud flag details
- Recommended decision buttons: APPROVE / DENY / REQUEST INFO / ESCALATE FRAUD

**Say:**
> "The case manager has full context — patient history, what the agents found, the prior auth status. They don't need to log into Epic, call the payer, or look up policy documents. The AI brought everything to them."

**Action:** Click "APPROVE" with a note: "Prior auth confirmed via payer portal."

**Say:**
> "Human approves in 30 seconds with full audit trail. Watch the case close."

---

### ⏱️ 3:30–4:15 — Settlement & Completion (45 seconds)

**Show:** Case advances to SETTLEMENT stage.

**Say:**
> "RPA robots kick in. They update the EHR, trigger the payment, notify the provider."

**Show:** Three parallel activities completing:
- ✅ Epic EHR updated — claim status: APPROVED
- ✅ Payment triggered: $38,200 EFT to provider
- ✅ Provider notification sent via API

**Say:**
> "From document submission to payment trigger — 4 minutes 12 seconds for a complex claim. Industry average? 45 days."

**Show:** Case closed, stage: CLOSED_PAID, full audit trail visible.

---

### ⏱️ 4:15–4:45 — UiPath for Coding Agents BONUS (30 seconds)

**Say:**
> "One more thing — this entire coded agent layer was built using UiPath for Coding Agents with Claude Code. Let me show you."

**Action:** Switch to terminal. Show:
```bash
$ claude "add a drug interaction check tool to the clinical reasoning agent"
```

**Show:** Claude Code analyzing the file, generating the new tool function, adding it to the agent.

**Say:**
> "Natural language to production-ready coded agent. That's UiPath for Coding Agents."

---

### ⏱️ 4:45–5:00 — Closing Impact Statement (15 seconds)

**Say:**
> "MediClaim Guardian turns a 45-day, error-prone, fraud-vulnerable process into a 4-minute, AI-governed, human-accountable workflow. $1.1 trillion in administrative waste — this is how we start recovering it. Thank you."

---

## Backup Plan (If live demo fails)

1. **Primary backup:** Pre-recorded video (same flow) — play without commentary
2. **Secondary backup:** Static screenshots in presentation slides
3. **Specific failure scenarios:**
   - Agent API down → Show pre-cached triage result, explain it's from the live agent
   - Maestro not responding → Show architecture diagram and walk through the flow conceptually
   - Action Center slow → Have two browser tabs open — pre-populated task as backup

---

## Key Numbers to Memorize

| Metric | Value |
|--------|-------|
| Industry avg claim processing | 45 days |
| MediClaim Guardian processing | < 5 minutes |
| Healthcare admin waste (US) | $1.1 trillion/year |
| Claims initially denied | 30% |
| AI triage time | 8 seconds |
| Fraud cost to US healthcare | $100B+/year |
| Human review time (Action Center) | < 2 minutes |

# 🎬 Demo Script — TestGen AI Sentinel
## Track 3: UiPath Test Cloud | Time: 5 minutes

---

## Pre-Demo Setup Checklist
- [ ] UiPath Test Cloud dashboard open showing test suite health
- [ ] TestGen AI Sentinel dashboard open (fragility scores visible)
- [ ] Jira ticket ready to show (DEMO-101: Login with SSO feature)
- [ ] GitHub repo with a recently "broken" test (pre-prepared)
- [ ] Terminal ready for UiPath for Coding Agents demo
- [ ] Backup video recording ready

---

## Demo Flow (5 minutes total)

---

### ⏱️ 0:00–0:30 — Hook (30 seconds)

**Say:**
> "80% of your QA team's time is spent maintaining old tests, not writing new ones. Your CI/CD breaks at 2am — not because your code is bad, but because a button's ID changed. And no one knows which of your 847 tests will break until it's in production. That's the state of enterprise QA in 2025. TestGen AI Sentinel changes it."

**Show:** UiPath Test Cloud dashboard — test suite with 847 tests, red failures highlighted.

---

### ⏱️ 0:30–1:45 — Demo 1: Requirements to Tests in 60 Seconds (75 seconds)

**Say:**
> "Let's start with the most painful part of testing: writing tests for new features."

**Action:** Navigate to Jira. Open ticket DEMO-101.

**Show:** Jira story:
```
DEMO-101: Add SSO login with Microsoft Entra ID
As a user, I want to log in using my Microsoft account
Acceptance Criteria:
- Users can click "Sign in with Microsoft" 
- Authentication redirects to Microsoft login
- After auth, user is returned to app and logged in
- Failed auth shows appropriate error message
- Session persists for 8 hours
```

**Say:**
> "There's a Jira story. Let's have TestGen AI Sentinel generate the test suite."

**Action:** In TestGen dashboard, click "Generate Tests from Requirement" → paste the Jira URL or ID.

**Show:** Progress bar — "Analyzing requirement... Identifying test dimensions... Generating scenarios..."

**After 15 seconds, show results:**
```
Generated 9 test scenarios for DEMO-101:
  ✅ TC-001: Successful SSO login (HAPPY_PATH) — CRITICAL
  ✅ TC-002: SSO button visible and clickable (UI) — HIGH
  ✅ TC-003: Microsoft auth redirect (INTEGRATION) — CRITICAL
  ✅ TC-004: Successful return and session creation (HAPPY_PATH) — HIGH
  ✅ TC-005: Failed auth error handling (NEGATIVE) — HIGH
  ✅ TC-006: Session persistence 8-hour validation (BOUNDARY) — MEDIUM
  ✅ TC-007: Invalid credentials error message (NEGATIVE) — HIGH
  ✅ TC-008: Unauthorized access attempt logging (SECURITY) — CRITICAL
  ✅ TC-009: Concurrent login sessions (EDGE_CASE) — MEDIUM

Estimated coverage: 94%
UiPath test automation code: GENERATED ✓
```

**Say:**
> "9 test scenarios with full BDD Given-When-Then structure. And the UiPath test automation code is already written."

**Action:** Click "View Generated Code" — show the XML test case code.

**Say:**
> "Ready to import into UiPath Test Cloud. From Jira to running test — under 60 seconds. This used to take a QA engineer 3 hours."

---

### ⏱️ 1:45–2:45 — Demo 2: Test Health Monitoring (60 seconds)

**Say:**
> "Great — tests are generated. But the real pain is keeping them alive. Let me show the Test Health Monitor."

**Show:** TestGen AI Sentinel health dashboard — list of tests with fragility scores:

```
Test Health Monitor — 847 Total Tests

🟢 HEALTHY (712)     🟡 AT RISK (98)     🔴 FRAGILE (37)

Top At-Risk Tests (fragility score > 70):
  • Login_Flow_v2.xaml ────────────────── 84/100 ⚠️
    Reason: 4 failures in last 30 days, selector dependency on dynamic ID
  • InvoiceUpload_Attachment.xaml ──────── 79/100 ⚠️
    Reason: Timeout issues correlating with page load performance
  • UserProfile_EditModal.xaml ─────────── 73/100 ⚠️
    Reason: DOM structure changed in last deploy
```

**Say:**
> "The ML model analyzed 30 days of execution history and identified 37 tests that are going to break before they break. We know about Login_Flow_v2 TODAY — before it fails in Friday's production release."

**Action:** Click on Login_Flow_v2 — show the fragility breakdown:
- Failure frequency: 4x in 30 days
- Selector type: dynamic ID (unstable)
- Correlated with: UI deploy on June 15
- Recommendation: Update to text-based selector

---

### ⏱️ 2:45–3:45 — Demo 3: Self-Healing (60 seconds)

**Say:**
> "Now let me show the most impressive part: what happens when a test actually breaks."

**Action:** Click "Simulate Test Failure" on UserProfile_EditModal.xaml.

**Show:** Test fails:
```
ERROR: Selector not found
  <webctrl id="edit-modal-submit-btn-1847" .../>
  Element not found after 30s timeout
```

**Say:**
> "The Submit button's ID changed in the last deploy. Old selector is dead. In the past, a developer would be paged at 2am to fix this manually."

**Show:** Self-healing crew activating:
```
🔧 Self-Healing Activated
  → Failure Diagnostician: Analyzing... ROOT CAUSE: Dynamic ID change in UI deploy
  → Fix Engineer: Generating selector alternatives...
     Option 1: text="Save Changes" (reliability: HIGH)
     Option 2: data-testid="edit-profile-submit" (reliability: VERY HIGH)
  → Quality Gate: Validating fix... confidence: 87% — AUTO-APPLY threshold met
  → Applying fix... ✓
  → Creating GitHub PR #127: "auto-heal: update UserProfile selector" ✓
```

**Say:**
> "3 agents: diagnose, fix, validate. 87% confidence — above the auto-apply threshold. A PR is created. The test heals itself. Developer wakes up to a PR, not a 2am page."

**Action:** Show the auto-created GitHub PR — title, changed line (before/after selector).

---

### ⏱️ 3:45–4:15 — Demo 4: Risk-Based Test Orchestration (30 seconds)

**Say:**
> "Last piece — CI/CD integration. Watch what happens when a PR comes in."

**Show:** GitHub PR notification → TestGen sees it → Risk analysis runs:

```
PR #142 changed: src/auth/SSOProvider.js, src/auth/SessionManager.js

Impact Analysis: 23 tests affected by these changes
Running targeted suite (23 tests) instead of full suite (847 tests)
Estimated time: 4 min vs 28 min for full suite

Results: 22 passed ✅ | 1 failed ❌
  FAIL: Session_Timeout_8hr — assertion needs update for new token format
  → Self-heal agent activated...
```

**Say:**
> "847 tests → 23 tests. 28 minutes → 4 minutes. Same confidence. That's risk-based orchestration."

---

### ⏱️ 4:15–4:45 — Coding Agents BONUS (30 seconds)

**Say:**
> "And the whole test generation engine? Built with UiPath for Coding Agents."

**Show:** Terminal:
```bash
$ uipath run test-generation --jira-ticket DEMO-101
# Internally: Claude Code generated this test generator agent

$ claude "add AI LLM output validation to the test generation pipeline"
# Claude Code extends the test generator to handle non-deterministic AI outputs
```

**Say:**
> "We used Claude Code through UiPath's CLI to build the self-healing agents and extend the platform in real time. That's the future of software development."

---

### ⏱️ 4:45–5:00 — Impact Close (15 seconds)

**Say:**
> "TestGen AI Sentinel: from Jira story to running test in under 60 seconds. 37 fragile tests identified before production. Tests that fix themselves. The 80% of QA time wasted on maintenance — recovered. Thank you."

---

## Backup Plans

1. **Agent API down:** Show pre-generated test output (cached), walk through the code
2. **UiPath Test Cloud slow:** Use local test execution screenshot
3. **Self-heal demo fails:** Show the GitHub PR (pre-prepared) and explain the fix
4. **General failure:** Focus on the architecture slide and the business impact numbers

---

## Key Numbers

| Metric | Value |
|--------|-------|
| Time to write tests manually | 3 hours / feature |
| TestGen AI Sentinel | 60 seconds / feature |
| Test maintenance % of QA time | 80% |
| Tests at-risk caught proactively | 37 in demo scenario |
| Full suite → targeted suite | 847 → 23 tests |
| Execution time saved | 28 min → 4 min (85% faster) |
| Self-heal auto-apply confidence threshold | 75% |

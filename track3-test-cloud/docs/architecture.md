# Architecture — TestGen AI Sentinel
## Track 3: UiPath Test Cloud

---

## High-Level System Architecture

```mermaid
graph TB
    subgraph Sources["📥 Input Sources"]
        J[Jira] --> ING
        G[GitHub PR/Commits] --> ING
        C[Confluence] --> ING
        M[Manual Input] --> ING
        ING[Requirements\nIngestion Service\nAPI Workflow]
    end

    subgraph Core["🧠 TestGen AI Core (UiPath)"]
        subgraph TestGen["Test Generation Pipeline"]
            RPA_GEN[Requirement\nAnalyzer\nLangChain]
            SCEN[BDD Scenario\nGenerator]
            CODE[Test Code\nWriter\nClaude Code + CLI]
            REV[AutoGen\nReview Panel]
        end

        subgraph TestCloud["UiPath Test Cloud"]
            TC_SUITE[Test Suite\nManager]
            TC_RUN[Test\nExecutor]
            TC_REPORT[Results &\nReporting]
            TC_SCHED[Scheduler &\nOrchestrator]
        end

        subgraph Health["Test Health Monitor"]
            ML_MODEL[Fragility ML\nModel\nscikit-learn]
            ALERT[Alert Engine\nAgent Builder]
            DASH[Health\nDashboard]
        end

        subgraph SelfHeal["Self-Healing Engine"]
            DIAG[Diagnosis\nAgent\nLangChain]
            FIXER[Fix Generator\nCrewAI Crew]
            VALID[Fix Validator\nAutoGen]
            GIT[GitHub PR\nCreator\nAPI Workflow]
        end

        subgraph Orchestration["Risk Orchestrator"]
            IMPACT[Impact\nAnalyzer\nLangChain + AST]
            SELECTOR[Test\nSelector\nML Model]
            RUNNER[Targeted\nTest Runner]
        end
    end

    subgraph HumanLoop["👤 Human Loop"]
        AC[Action Center\nReview Tasks]
    end

    subgraph External["🔗 External Systems"]
        GH[(GitHub)] --> ING
        GH --> IMPACT
        CI[CI/CD\nPipeline] --> ORCHESTRATION_WEBHOOK[GitHub Webhook\nAPI Workflow]
        ORCHESTRATION_WEBHOOK --> IMPACT
    end

    ING --> RPA_GEN --> SCEN --> CODE --> REV --> TC_SUITE
    TC_SUITE --> TC_RUN --> TC_REPORT
    TC_REPORT --> ML_MODEL --> DASH
    ML_MODEL --> ALERT
    TC_RUN -->|Failure| DIAG --> FIXER --> VALID
    VALID -->|Confident| GIT
    VALID -->|Uncertain| AC
    IMPACT --> SELECTOR --> RUNNER --> TC_RUN
```

---

## Test Generation Pipeline

```mermaid
flowchart LR
    A[Jira Story] --> B[API Workflow\nFetch Story]
    B --> C[LangChain\nRequirement Parser]
    C --> D[Coverage Analyzer\nGPT-4o]
    D --> E[BDD Scenario\nGenerator]
    E --> F[Claude Code\nTest Writer\nvia UiPath CLI]
    F --> G[AutoGen\nReview Panel\n3 agents]
    G --> H{Quality\nGate}
    H -->|Pass| I[Import to\nTest Cloud]
    H -->|Fail| J[Regenerate\nw/ feedback]
    J --> E
    I --> K[Test Suite\nReady ✓]
```

---

## Self-Healing Flow

```mermaid
stateDiagram-v2
    [*] --> TestRunning

    TestRunning --> TestFailed : Failure detected
    TestRunning --> TestPassed : Test passes
    TestPassed --> [*]

    TestFailed --> ConsecutiveCheck : Record failure

    ConsecutiveCheck --> Alert : First failure
    ConsecutiveCheck --> HealingTriggered : 2+ consecutive failures

    Alert --> TestRunning : Next scheduled run

    HealingTriggered --> Diagnosis : Launch crew

    Diagnosis --> FixGeneration : Root cause identified
    Diagnosis --> HumanEscalation : Cannot diagnose

    FixGeneration --> Validation : Fix generated

    Validation --> AutoApply : Confidence >= 75%
    Validation --> HumanEscalation : Confidence < 75%

    AutoApply --> GitHubPR : Create PR
    GitHubPR --> MergeAndDeploy : PR merged
    MergeAndDeploy --> TestRunning : Test updated

    HumanEscalation --> ActionCenter : Create task
    ActionCenter --> ManualFix : Human repairs
    ManualFix --> TestRunning : Fix applied
```

---

## Risk-Based Test Orchestration

```mermaid
graph LR
    A[Git Push / PR] --> B[Webhook Trigger\nAPI Workflow]
    B --> C[Code Diff\nExtractor]
    C --> D[AST Change\nAnalyzer\nPython]
    D --> E[Module Map\nFiles → Tests]
    E --> F[ML Risk\nScorer]
    F --> G[Ranked Test\nSelection]
    G --> H{Coverage\nGuarantee}
    H -->|Met| I[Targeted Run\nFast Path]
    H -->|Not Met| J[Add Coverage\nTests]
    J --> I
    I --> K[UiPath Test\nCloud Execution]
    K --> L[Results]
    L --> M[PR Comment\nwith Results]
    M --> N[ML Model\nUpdate]
```

---

## AI Workflow Validation (Novel Feature)

```mermaid
graph TB
    subgraph AI_Target["UiPath Automation with AI Agents"]
        AIA[Agent Builder\nAgent] --> UF[UiPath\nWorkflow]
        EXT[External LLM\nService] --> UF
    end

    subgraph Validator["AI Workflow Validator (Novel)"]
        V1[Behavior Capture\nAgent Builder] --> V2[LLM Output\nValidator]
        V2 --> V3[Reasoning Chain\nChecker]
        V3 --> V4[Non-Determinism\nStatistical Sampler]
        V4 --> V5[Contract\nAsserter]
    end

    subgraph Results["Test Results"]
        R1[✅ Output within\nacceptable range]
        R2[⚠️ Degradation\ndetected]
        R3[❌ Contract\nviolation]
    end

    UF --> V1
    V5 --> R1 & R2 & R3
```

This is the unique capability for testing AI-infused UiPath workflows — validating that LLM-based agents produce correct, consistent outputs even when they're non-deterministic.

---

## ML Fragility Model

The test fragility prediction uses a gradient boosting model trained on:

| Feature | Description |
|---------|-------------|
| `failure_rate_30d` | Failures in last 30 days |
| `selector_type` | ID (unstable) vs text vs XPath (stable) |
| `avg_execution_time` | Growing execution time = instability signal |
| `days_since_last_update` | Old tests tend to drift |
| `deploy_correlation` | Tests that fail after deploys |
| `page_load_dependency` | Tests sensitive to dynamic loading |
| `flakiness_score` | Pass/fail inconsistency |
| `dom_depth` | Deep DOM selectors are more brittle |

**Output:** Fragility score 0-100 (>70 = at-risk, >85 = likely to fail within 7 days)

---

## Security Design

- All API calls authenticated with UiPath Cloud OAuth 2.0
- GitHub token scoped to minimum permissions (read PR + write PR comments)
- Auto-applied fixes never touch production — always through PR review
- Test code sandboxed — no access to production data
- Jira/Confluence access read-only via service account

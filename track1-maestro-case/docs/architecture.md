# Architecture — MediClaim Guardian

## System Architecture Overview

MediClaim Guardian uses UiPath Maestro Case as the central orchestration engine, coordinating multiple AI agents, RPA robots, and human reviewers through a dynamic healthcare claims lifecycle.

---

## High-Level Architecture

```mermaid
C4Context
    title MediClaim Guardian — System Context

    Person(claimant, "Claimant / Provider", "Submits healthcare claims")
    Person(caseManager, "Case Manager", "Reviews escalated claims")
    Person(clinician, "Medical Reviewer", "Clinical exception decisions")

    System(mediClaim, "MediClaim Guardian", "AI-powered healthcare claims processing on UiPath")

    System_Ext(ehr, "EHR/EMR Systems", "Epic, Cerner, Allscripts")
    System_Ext(payer, "Payer APIs", "Availity, Change Healthcare")
    System_Ext(payment, "Payment Rails", "ACH/EFT banking")
    System_Ext(clinicalDB, "Clinical Guidelines", "MCG, InterQual, ICD-10")

    Rel(claimant, mediClaim, "Submits claim documents")
    Rel(mediClaim, caseManager, "Escalates complex cases")
    Rel(mediClaim, clinician, "Requests clinical review")
    Rel(mediClaim, ehr, "Reads/writes patient data")
    Rel(mediClaim, payer, "Checks eligibility/authorization")
    Rel(mediClaim, payment, "Triggers settlement")
    Rel(mediClaim, clinicalDB, "Validates clinical necessity")
```

---

## Maestro Case Stage Flow

```mermaid
stateDiagram-v2
    [*] --> Intake : Claim Received

    Intake --> DocumentProcessing : Documents Validated
    Intake --> Rejected : Invalid / Duplicate

    DocumentProcessing --> Triage : Data Extracted
    DocumentProcessing --> PendingDocuments : Missing Documents

    PendingDocuments --> DocumentProcessing : Documents Received
    PendingDocuments --> Closed_Incomplete : Timeout (30 days)

    Triage --> AutoProcessing : Low Complexity (Score 0-30)
    Triage --> StandardReview : Medium Complexity (Score 31-70)
    Triage --> ExpertReview : High Complexity (Score 71-100)
    Triage --> FraudInvestigation : Fraud Signals Detected

    AutoProcessing --> Settlement : Approved
    AutoProcessing --> Denied : Not Covered

    StandardReview --> Investigation : CrewAI Analysis
    Investigation --> HumanDecision : Complex Case
    Investigation --> AutoDecision : Clear Case

    ExpertReview --> HumanDecision : Requires Clinician

    FraudInvestigation --> FraudReferred : Confirmed Fraud
    FraudInvestigation --> StandardReview : False Positive

    HumanDecision --> Settlement : Human Approved
    HumanDecision --> Denied : Human Denied
    HumanDecision --> AdditionalInfo : Info Requested

    AutoDecision --> Settlement : Approved
    AutoDecision --> Denied : Denied

    AdditionalInfo --> StandardReview : Info Received
    AdditionalInfo --> Closed_Timeout : No Response (14 days)

    Settlement --> Appeal : Denied + Appeal Filed
    Settlement --> Closed_Paid : Payment Processed

    Appeal --> ExpertReview : Appeal Review
    Denied --> Closed_Denied : No Appeal
    FraudReferred --> Closed_Fraud : Fraud Case Opened

    Closed_Paid --> [*]
    Closed_Denied --> [*]
    Closed_Incomplete --> [*]
    Closed_Timeout --> [*]
    Closed_Fraud --> [*]
```

---

## Component Architecture

```mermaid
graph TB
    subgraph UiPathCloud["UiPath Automation Cloud"]
        subgraph Maestro["Maestro Case Engine"]
            MC[Case Manager]
            MS[Stage Router]
            MT[SLA Timer]
            MA[Audit Logger]
        end

        subgraph AgentLayer["Agent Layer"]
            AB1[Validation Agent\nAgent Builder]
            AB2[Notification Agent\nAgent Builder]
            AB3[Coverage Checker\nAgent Builder]
        end

        subgraph ActionCenter["Action Center"]
            HT1[Case Manager Tasks]
            HT2[Clinical Review Tasks]
            HT3[Fraud Review Tasks]
        end

        subgraph IDP["Document Understanding"]
            DU1[Document Classifier]
            DU2[Data Extractor]
            DU3[Confidence Scorer]
        end

        subgraph RPA["Automation Robots"]
            R1[EHR Data Bot]
            R2[Payment Bot]
            R3[Portal Bot]
        end

        subgraph APIWorkflows["API Workflows"]
            AW1[Payer Eligibility]
            AW2[Authorization Check]
            AW3[EFT Trigger]
        end
    end

    subgraph ExternalAI["External AI Layer (Python)"]
        LA[LangChain Triage Agent\nGPT-4o + Clinical Tools]
        CA[CrewAI Investigation Crew\n3 Specialized Agents]
        AG[AutoGen Synthesizer\nReport Generation]
    end

    subgraph ExternalSystems["Enterprise Systems"]
        EHR[(EHR/EMR)]
        PAYER[(Payer APIs)]
        PAYMENT[(Payment Rails)]
        CLINICAL[(Clinical DB)]
    end

    MC --> MS --> AgentLayer
    MS --> ExternalAI
    MS --> ActionCenter
    ExternalAI --> IDP
    AgentLayer --> APIWorkflows
    APIWorkflows --> PAYER
    R1 --> EHR
    R2 --> PAYMENT
    LA --> CLINICAL
```

---

## Data Flow

```mermaid
flowchart LR
    A[Claim Submission] --> B{Input Channel}
    B -->|Email| C[Email Trigger\nRPA]
    B -->|Portal| D[Web API\nAPI Workflow]
    B -->|EDI 837| E[EDI Parser\nCoded Agent]

    C & D & E --> F[Document Store\nUiPath Storage]
    F --> G[Document Understanding\nExtract + Classify]
    G --> H[Structured Claim Data\nJSON]

    H --> I[LangChain Triage Agent]
    I --> J[Complexity Score\n+ Risk Flags]
    J --> K[Maestro Case\nCreated + Staged]

    K --> L{Routing}
    L -->|Complex| M[CrewAI Crew\nLaunch]
    L -->|Simple| N[Agent Builder\nAuto-Check]

    M --> O[Investigation Report\nAutoGen]
    N --> O

    O --> P{Decision}
    P -->|Human| Q[Action Center Task\n+ AI Summary]
    P -->|Auto| R[Decision Engine\nRPA]

    Q --> S[Human Decision]
    R --> T[Auto Decision]

    S & T --> U[API Workflow\nSettlement]
    U --> V[EHR Update\nRPA]
    U --> W[Payment\nRPA]
    U --> X[Notification\nAgent Builder]
```

---

## Security Architecture

```mermaid
graph TB
    subgraph Security["Security Controls"]
        AUTH[OAuth 2.0\nUiPath Auth]
        AUDIT[Immutable Audit Log\nAll decisions recorded]
        ENCRYPT[Data Encryption\nAt rest + in transit]
        HIPAA[HIPAA Compliance\nData handling controls]
        RBAC[Role-Based Access\nCase Manager / Clinician / Admin]
        PII[PII Masking\nIn logs and traces]
    end

    subgraph DataFlow["Secure Data Flow"]
        EXT[External Claim Data] -->|TLS 1.3| GATEWAY[API Gateway\nUiPath Cloud]
        GATEWAY -->|Encrypted| PROCESS[Processing Layer]
        PROCESS -->|Masked| LOGS[Audit Logs]
        PROCESS -->|Encrypted| STORAGE[Document Storage]
    end
```

---

## Technology Stack Justification

| Decision | Rationale |
|----------|-----------|
| **Maestro Case over BPMN** | Claims are dynamic — an appeal path can appear at any stage, fraud investigations emerge mid-process. BPMN's fixed flow can't handle this. |
| **LangChain for triage** | Clinical reasoning requires chain-of-thought, tool calling (ICD-10 lookup, guideline query), and structured output. LangChain excels here. |
| **CrewAI for investigation** | Three independent agents (fraud, clinical, coverage) can work in parallel and converge — exactly what CrewAI's crew model enables. |
| **AutoGen for synthesis** | Investigation requires a "discussion" between findings to produce a coherent recommendation — AutoGen's conversational model fits perfectly. |
| **Document Understanding** | Medical documents (EOBs, records, prior auth forms) are non-standard. UiPath IDP provides pre-trained models for healthcare documents. |
| **RPA for EHR** | 90% of hospitals use Epic/Cerner — both have proprietary UIs. RPA is the only reliable integration path without expensive HL7 FHIR implementations. |

---

## Scalability Design

- **Horizontal scaling:** Multiple Maestro Case instances handle thousands of simultaneous claims
- **Queue-based routing:** Cases dispatched to available agents via UiPath Orchestrator queues
- **Stateless AI agents:** FastAPI coded agents are containerized and auto-scale
- **Async processing:** Long-running AI tasks use async patterns — Maestro waits for completion without blocking
- **SLA monitoring:** Built-in escalation prevents queue buildup from aging claims

# Architecture — ProcureFlow AI
## Track 2: UiPath Maestro BPMN

---

## BPMN 2.0 Process Overview

```mermaid
graph LR
    subgraph Pool1["🏢 Enterprise Procurement Process (ProcureFlow AI)"]
        subgraph Lane_Req["Lane: Requester"]
            A([Start]) --> B[Submit Purchase\nRequest]
            E_ACT[Receive\nApproval Notice] --> F_ACT[Confirm\nGoods Receipt]
        end

        subgraph Lane_AI["Lane: AI Agents"]
            C[Requisition\nIntelligence Agent\nLangChain]
            J[Vendor Selection\nAgent - LangChain]
            O_M[3-Way Match\nAgent - AutoGen]
            R_F[Fraud Detection\nCrew - CrewAI]
        end

        subgraph Lane_Proc["Lane: Procurement"]
            D{Budget\nGateway}
            G_RFQ[Generate RFQ\nAgent Builder]
            H_PO[Create PO\nRPA → SAP]
        end

        subgraph Lane_Vendor["Lane: Vendor"]
            I[Send PO to Vendor]
            K[Vendor Response\nAPI Workflow]
            L_SHIP[Goods Shipped\n+ Invoice Sent]
        end

        subgraph Lane_AP["Lane: Accounts Payable"]
            N_INV[Receive Invoice\nDocument Understanding]
            Q_RVW[AP Review Task\nAction Center]
        end

        subgraph Lane_Finance["Lane: Finance"]
            S_PAY[Process Payment\nRPA + EFT]
            T_ERP[Update ERP\nRPA]
            U([End ✓])
        end

        B --> C
        C --> D
        D -->|Auto ≤$1K| G_RFQ
        D -->|Manager $1K-$10K| E_APPR[Manager Approval\nAction Center]
        D -->|VP $10K-$50K| VP_APPR[VP Approval\nAction Center]
        E_APPR & VP_APPR --> G_RFQ
        G_RFQ --> J
        J --> H_PO
        H_PO --> I
        I --> K
        K --> G_RFQ
        H_PO --> L_SHIP
        L_SHIP --> F_ACT
        F_ACT --> N_INV
        N_INV --> O_M
        O_M --> MATCH_GW{Match\nGateway}
        MATCH_GW -->|Perfect Match| R_F
        MATCH_GW -->|Within Tolerance| R_F
        MATCH_GW -->|Discrepancy| Q_RVW
        Q_RVW --> R_F
        R_F --> FRAUD_GW{Fraud\nCheck}
        FRAUD_GW -->|Clean| S_PAY
        FRAUD_GW -->|Suspicious| FRAUD_RVW[Fraud Investigation\nAction Center]
        FRAUD_RVW --> S_PAY
        S_PAY --> T_ERP --> U
    end
```

---

## System Architecture

```mermaid
graph TB
    subgraph Cloud["UiPath Automation Cloud"]
        subgraph BPMN["Maestro BPMN Engine"]
            PE[Process Engine]
            PV[Process Visibility\nDashboard]
            PA[Process Analytics]
            PT[SLA Timer &\nEscalation]
        end

        subgraph Agents["Agent Layer"]
            AB1[Catalog Match Agent\nAgent Builder]
            AB2[Notification Agent\nAgent Builder]
            AB3[Status Update Agent\nAgent Builder]
        end

        subgraph HumanTasks["Action Center"]
            HT1[Manager Approval Tasks]
            HT2[AP Review Tasks]
            HT3[Fraud Investigation Tasks]
            HT4[VP/Exec Approval Tasks]
        end

        subgraph IDP["Document Understanding"]
            DU1[Invoice Extractor]
            DU2[PO Parser]
            DU3[Contract Reader]
        end

        subgraph RPA["Automation Robots"]
            R1[SAP PO Bot]
            R2[SAP GR Confirmation]
            R3[EFT Payment Bot]
            R4[Oracle Integration Bot]
        end

        subgraph APIWorkflows["API Workflows"]
            AW1[Vendor Portal Integration]
            AW2[ERP REST API]
            AW3[Payment Gateway]
            AW4[Coupa Catalog API]
        end
    end

    subgraph ExternalAI["AI Agent Layer (Python FastAPI)"]
        LA[LangChain\nRequisition Agent\nPort 8003]
        TMA[AutoGen\n3-Way Match Agent\nPort 8004]
        FA[CrewAI\nFraud Detection\nPort 8005]
        VKB[Chroma DB\nVendor Knowledge Base]
    end

    subgraph ERP["Enterprise Systems"]
        SAP[(SAP ERP)]
        ORC[(Oracle Financials)]
        CPA[(Coupa Procurement)]
        VND[(Vendor APIs)]
        BNK[(Banking/EFT)]
    end

    PE --> Agents
    PE --> HumanTasks
    PE --> ExternalAI
    IDP --> TMA
    RPA --> SAP
    RPA --> ORC
    RPA --> BNK
    APIWorkflows --> VND
    LA --> VKB
```

---

## Data Flow

```mermaid
sequenceDiagram
    participant Req as Requester
    participant BPMN as Maestro BPMN
    participant ReqAgent as LangChain Agent
    participant AC as Action Center
    participant RPA as RPA Robots
    participant IDP as Doc Understanding
    participant MatchAgent as AutoGen Agent
    participant FraudAgent as CrewAI Crew
    participant ERP as SAP/Oracle

    Req->>BPMN: Submit purchase request (free text)
    BPMN->>ReqAgent: Parse and analyze requisition
    ReqAgent->>BPMN: Items, vendor, budget, approval tier
    BPMN->>AC: Create approval task (if >$1K)
    AC->>BPMN: Manager approves
    BPMN->>RPA: Create PO in SAP
    RPA->>ERP: PO created: PO-2024-4471
    Note over BPMN: Wait for goods receipt + invoice
    BPMN->>IDP: Extract invoice data
    IDP->>MatchAgent: PO + GR + Invoice data
    MatchAgent->>BPMN: Match result + payable amount
    alt Discrepancy found
        BPMN->>AC: Create AP review task
        AC->>BPMN: AP resolves
    end
    BPMN->>FraudAgent: Run fraud checks
    FraudAgent->>BPMN: Fraud score + verdict
    alt Fraud suspected
        BPMN->>AC: Create fraud investigation task
        AC->>BPMN: Finance clears
    end
    BPMN->>RPA: Process EFT payment
    RPA->>ERP: Payment executed
    BPMN->>Req: Process complete notification
```

---

## BPMN 2.0 Patterns Used

| Pattern | Usage | Location in Flow |
|---------|-------|-----------------|
| **Exclusive Gateway (XOR)** | Budget threshold routing | After requisition processing |
| **Exclusive Gateway (XOR)** | Match result routing | After 3-way match |
| **Exclusive Gateway (XOR)** | Fraud check routing | After fraud analysis |
| **Service Task** | All AI agent calls | Throughout |
| **User Task** | All human approvals | Action Center tasks |
| **Parallel Gateway** | (ERP update + notification) | Final payment phase |
| **Timer Event** | SLA escalation (48h approval) | Approval tasks |
| **Error Boundary Event** | Agent failure handling | All agent tasks |
| **Compensation Task** | PO cancellation on fraud | Fraud path |

---

## Security Design

```mermaid
graph TB
    subgraph Security["Security Controls"]
        AUTH[OAuth 2.0\nUiPath + ERP]
        AUDIT[SOX Audit Trail\nImmutable log]
        SEGREGATION[Duty Segregation\nRequester ≠ Approver]
        FRAUD[AI Fraud Detection\nReal-time]
        VENDOR_VERIFY[Vendor Bank\nChange Alerts]
        AMOUNT_CTRL[Amount Controls\nThreshold routing]
    end
```

---

## Scalability

- **Horizontal:** Multiple BPMN process instances — thousands of concurrent POs
- **Async agents:** AI agents called asynchronously — BPMN doesn't block waiting
- **Queue-based:** Approval tasks distributed across available approvers
- **Idempotent:** All RPA actions are idempotent — safe to retry on failure
- **Stateless AI agents:** FastAPI containers auto-scale based on load

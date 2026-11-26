# UiPath AgentHack 2026 — Project Repository

> Three track submissions for the UiPath AgentHack global hackathon ($50,000 in prizes)

---

## 🗂️ Repository Structure

```
.
├── docs/
│   ├── research_report.md          ← Phase 1: Full hackathon research & strategy
│   └── submission_checklist.md     ← Pre-submission verification checklist
│
├── track1-maestro-case/            ← Track 1 submission
│   ├── README.md                   ← MediClaim Guardian — full project description
│   ├── LICENSE                     ← MIT License
│   ├── .gitignore
│   ├── docs/
│   │   ├── architecture.md         ← System architecture with Mermaid diagrams
│   │   ├── presentation.md         ← 8-slide presentation deck content
│   │   └── demo_script.md          ← 5-minute demo walkthrough script
│   ├── src/
│   │   └── agents/
│   │       ├── clinical_reasoning_agent.py    ← LangChain + GPT-4o triage agent
│   │       ├── fraud_investigation_crew.py    ← CrewAI 3-agent investigation crew
│   │       ├── requirements.txt
│   │       └── .env.example
│   └── tests/
│       └── e2e_test_claim_flow.py  ← End-to-end integration tests
│
├── track2-maestro-bpmn/            ← Track 2 submission
│   ├── README.md                   ← ProcureFlow AI — full project description
│   ├── LICENSE
│   ├── .gitignore
│   ├── docs/
│   │   ├── architecture.md         ← BPMN 2.0 diagrams and system design
│   │   ├── presentation.md         ← 8-slide presentation
│   │   └── demo_script.md          ← 5-minute demo script
│   ├── src/
│   │   └── agents/
│   │       ├── requisition_agent.py           ← LangChain requisition intelligence
│   │       ├── threeway_match_agent.py        ← AutoGen 3-way match reconciliation
│   │       ├── requirements.txt
│   │       └── .env.example
│   └── tests/
│       └── test_standard_po_flow.py
│
└── track3-test-cloud/              ← Track 3 submission
    ├── README.md                   ← TestGen AI Sentinel — full project description
    ├── LICENSE
    ├── .gitignore
    ├── docs/
    │   ├── architecture.md         ← Platform architecture diagrams
    │   ├── presentation.md         ← 8-slide presentation
    │   └── demo_script.md          ← 5-minute demo script
    ├── src/
    │   ├── agents/
    │   │   ├── test_generator_agent.py        ← LangChain test generation
    │   │   ├── self_heal_agent.py             ← CrewAI self-healing crew
    │   │   ├── requirements.txt
    │   │   └── .env.example
    │   └── ml/
    │       └── fragility_model.py             ← scikit-learn fragility prediction
    └── tests/
        └── test_agent_flows.py
```

---

## 📊 Track Summary

| | Track 1: MediClaim Guardian | Track 2: ProcureFlow AI | Track 3: TestGen AI Sentinel |
|---|---|---|---|
| **Track** | Maestro Case | Maestro BPMN | Test Cloud |
| **Domain** | Healthcare Claims | Procure-to-Pay | QA Automation |
| **Business Problem** | $1.1T admin waste | 65% manual invoices | 80% QA maintenance |
| **Key Innovation** | Multi-agent clinical crew | AutoGen reconciliation | Self-healing + AI validation |
| **UiPath Components** | Maestro Case, IDP, Action Center, RPA, API Workflows | Maestro BPMN, IDP, Action Center, RPA, API Workflows | Test Cloud, Agent Builder, Action Center, API Workflows |
| **External AI** | LangChain + CrewAI + AutoGen | LangChain + AutoGen + CrewAI | LangChain + CrewAI + AutoGen |
| **Coding Agents** | ✅ Claude Code (BONUS) | ✅ Claude Code (BONUS) | ✅ Claude Code centerpiece |

---

## 🚀 Quick Start (Any Track)

```bash
# 1. Navigate to your chosen track
cd track1-maestro-case  # or track2-maestro-bpmn, track3-test-cloud

# 2. Install UiPath CLI (for Coding Agents integration)
npm install -g @uipath/cli
uipath auth login

# 3. Set up Python environment
cd src/agents
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys

# 4. Run the agents
uvicorn clinical_reasoning_agent:app --port 8001  # Track 1
uvicorn requisition_agent:app --port 8003         # Track 2
uvicorn test_generator_agent:app --port 8005      # Track 3

# 5. Run tests
cd ../../tests
pytest -v
```

---

## 🏆 Grand Prize Strategy

All three solutions are designed to compete for:
1. **Track-specific prize** ($5,000 each for Best of Track)
2. **Grand Prize** ($8,000 — best across all tracks)
3. **Best Cross-Platform Integration** ($1,500)
4. **Most Creative Solution** ($3,000)
5. **Best Demo / Presentation** ($3,000)

**Grand Prize recommendation:** Submit Track 1 (MediClaim Guardian) for the strongest combination of business impact, technical depth, and complete platform usage.

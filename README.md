# 🏭 AI Intime V1 — Conversational Manufacturing Analytics

> Built for [Vegam Solutions](https://vegam.co) | Varaun Gandhi

A fully on-device conversational analytics system that converts plain English questions into structured reports with calculated KPIs and charts — powered by **LangGraph**, **Ollama (DeepSeek Coder V2)**, and **SQLAlchemy**.

Plant managers type questions. The system writes SQL, runs it, computes KPIs with Pandas, generates Plotly charts, and returns a complete report. No SQL knowledge required. No data leaves the device.

---

## Demo

### Yield Trend Analysis
![Yield Trend](screenshots/yield_trend.png)

### Night Shift Report with Step Breakdown
![Shift Report](screenshots/shift_report_summary.png)
![Step Breakdown](screenshots/step_breakdown_chart.png)

---

## Architecture

```
User Question (plain English)
        │
        ▼
┌─────────────────────┐
│  Node 1             │
│  Intent Classifier  │   → LOOKUP | AGGREGATION | COMPARISON | TREND | REPORT
│  (DeepSeek LLM)     │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Node 2             │
│  Schema Retriever   │   → TF-IDF matches query to relevant tables
│  (scikit-learn)     │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Node 3             │
│  SQL Generator      │   → DeepSeek writes SQL → Validator blocks writes
│  + Executor         │   → SQLAlchemy executes → Auto-retry up to 3x
│  (DeepSeek + SQLAlchemy)
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Node 4             │
│  KPI Calculator     │   → Pure Pandas: yield %, variance, trends
│  (Pandas)           │   → No LLM involved — deterministic math
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Node 5             │
│  Report Assembler   │   → Text summary (DeepSeek)
│                     │   → Auto-chart (Plotly, intent-driven)
│                     │   → Final report object
└──────────┬──────────┘
           ▼
    ┌──────┴──────┐
    ▼             ▼
Streamlit UI   MCP Server
```

---

## Tech Stack

| Component | Technology | Role |
|---|---|---|
| Agent Orchestrator | LangGraph | 5-node stateful workflow with conditional retry |
| LLM | Ollama — DeepSeek Coder V2 | Intent classification, SQL generation, summaries |
| SQL Engine | SQLAlchemy | Database-agnostic query execution |
| KPI Calculations | Pandas + NumPy | Deterministic metrics (yield, variance, trends) |
| Schema Search | scikit-learn TF-IDF | Matches queries to relevant tables |
| Charts | Plotly | Auto-generated based on intent type |
| UI | Streamlit | Chat interface with report rendering |
| Database | SQLite (swappable) | Sample manufacturing data |

---

## Key Design Decisions

**Why on-device LLM?** Manufacturing data is sensitive operational IP. Sending it to a cloud API creates compliance and security risks. Ollama runs everything locally — zero data leaves the premises.

**Why Pandas for math, not the LLM?** LLMs hallucinate numbers. Pandas does not. Every KPI is computed deterministically on the actual dataframe. The LLM only writes the English summary around numbers Pandas already calculated.

**Why TF-IDF instead of vector embeddings?** The sample database has 7 tables. At this scale, TF-IDF is faster (<1ms vs ~50ms), requires zero additional dependencies (no PyTorch), and is 100% accurate. The `SchemaStore` interface is abstracted — swap to Milvus + sentence-transformers for production databases with 50-100+ tables with zero code changes.

**Why LangGraph over a simple chain?** SQL generation fails. Chart code fails. The agent needs to retry, route around errors, and make decisions at runtime. LangGraph's conditional edges handle all failure modes gracefully.

**Why SQLAlchemy?** Database-agnostic. Same code works whether the customer runs PostgreSQL, MySQL, SQLite, or MSSQL.

---

## Sample Database

The demo uses a SQLite database simulating a chemical/polymer production facility.

| Metric | Value |
|---|---|
| Time period | Jan 18 – Feb 16, 2026 (30 days) |
| Total records | 949 across 7 tables |
| Production lines | 4 lines across 3 buildings |
| Products | ChemX-500, PolyBlend-A, SurfaceCoat-Pro, AdhesivePrime |
| Staff | 6 (3 Supervisors, 2 Operators, 1 QC Inspector) |
| Shifts | 240 (2 per day per line) |
| Production orders | 117 completed |
| Production steps | 578 step-level logs |
| Average yield | 91.4% (range: 85–98%) |

Full schema documentation: [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md)

---

## Test Results (V1)

```
Total queries:     20
Data returned:     19/20  (95%)
KPIs computed:     19/20  (95%)
Summaries valid:   19/20  (95%)
Charts generated:  8/20   (correct — only generated when relevant)
Avg response time: ~18s   (local Ollama on MacBook Air)
```

Sample queries tested:
- ✅ "How many orders were completed?"
- ✅ "Plot yield trend for the last 10 days"
- ✅ "Compare yield between day and night shift"
- ✅ "How does Building A compare to Building B in total output?"
- ✅ "Give me a full shift report for the night shift on February 10th"
- ✅ "Show me details for order PO-1042"
- ✅ "What percentage of orders were cancelled?"
- ✅ "Which supervisor had the best performance this month?"
- ✅ "What's the average cycle time for ChemX-500?"

---

## Project Structure

```
ai-intime/
├── src/
│   ├── agents/
│   │   └── analytics_agent.py     # LangGraph 5-node workflow
│   ├── schema/
│   │   └── extractor.py           # Reads DB schema + builds JOIN guide
│   ├── retrieval/
│   │   └── schema_store.py        # TF-IDF schema search (Milvus-compatible interface)
│   ├── sql/
│   │   ├── generator.py           # NL → SQL via DeepSeek
│   │   ├── executor.py            # SQLAlchemy execution + PostgreSQL auto-fixer
│   │   └── validator.py           # Read-only safety enforcement
│   ├── calculations/
│   │   └── kpi_agent.py           # Pandas KPI calculations
│   ├── report/
│   │   ├── summarizer.py          # Text summary via DeepSeek
│   │   ├── chart_generator.py     # Deterministic Plotly charts + LLM fallback
│   │   └── assembler.py           # Final report builder
│   ├── llm/
│   │   └── provider.py            # Ollama / Anthropic abstraction
│   ├── mcp/
│   │   └── server.py              # MCP tool exposure (Flask)
│   └── utils/
│       └── error_handler.py       # Retry logic, exceptions
├── ui/
│   └── app.py                     # Streamlit chat + report UI
├── data/
│   └── sample_manufacturing.db    # SQLite sample database
├── tests/
│   └── test_all_queries.py        # 20-query test suite
├── screenshots/                   # Demo screenshots
├── DATABASE_SCHEMA.md             # Full schema documentation
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Setup

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.ai) installed and running
- DeepSeek Coder V2 model pulled

### Installation

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/ai-intime.git
cd ai-intime

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Pull the LLM
ollama pull deepseek-coder-v2

# Configure
cp .env.example .env
# Edit .env if needed

# Run
streamlit run ui/app.py
```

### Configuration

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-coder-v2
DATABASE_URL=sqlite:///data/sample_manufacturing.db
```

---

## Safety

- **Read-only enforcement**: SQL validator blocks INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER before execution
- **No data exfiltration**: Ollama runs fully local — zero API calls to external services
- **Auto-retry with guardrails**: SQL retries up to 3x, chart retries up to 2x, graceful degradation on failure
- **PostgreSQL syntax auto-fix**: Catches `::DATE`, `EXTRACT()`, `NOW()`, `ILIKE` and converts to SQLite equivalents

---

## Roadmap (V2)

- [ ] Connect to production database (PostgreSQL/MySQL/MSSQL)
- [ ] MCP Server integration for Claude Desktop
- [ ] Milvus + sentence-transformers for semantic schema search at scale
- [ ] Multi-turn conversation memory
- [ ] PDF/Excel report export
- [ ] User authentication + role-based access
- [ ] Larger LLM option (Llama 3.1 70B) for complex multi-table joins

---

## Author

**Varaun Gandhi**
- M.S. AI Systems Management, Carnegie Mellon University (Dec 2025)
- varaun.gandhi@gmail.com

Built for Vegam Solutions — AI Intime platform validation.

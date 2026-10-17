# DevAgent Intelligence & AI-Git Suite ✦

An enterprise-grade, evidence-grounded universal Git repository analysis and architectural intelligence suite. DevAgent bridges the gap between static version control and autonomous AI reasoning by anchoring every insight directly in commit-pinned source code, preventing hallucinations and speculative assumptions.

---

## 🏗️ Technical Stack

- **Backend Framework**: `FastAPI` (Asynchronous Python API gateway with high-throughput routing).
- **Database & Persistence**: `SQLite` (Lightweight local storage for semantic memory chunks, evidence provenance stores, and performance caching).
- **AI Core & Engine**: `Google GenAI SDK` powered by **Gemini 2.5 Flash** (Enabling lightning-fast, high-context code comprehension, multi-node architectural mapping, and structured markdown synthesis).
- **Authentication & Security**: GitHub OAuth / Personal Access Tokens with secure `Starlette SessionMiddleware` persistence and token expiration checks.
- **Frontend Presentation**: Modern single-page responsive dashboard built with `Tailwind CSS`, interactive agent report modals, and real-time Mermaid.js graph visualization.

---

## 🧠 The LLM Model: Gemini 2.5 Flash

DevAgent leverages **Gemini 2.5 Flash** as its core cognitive engine. 
- **Massive Context Window**: Allows the ingestion and cross-reference of dozens of repository files simultaneously.
- **Precise Structured Output**: Utilized to translate raw code snippets into rigorous evidence categories (`iteration`, `data_parsing`, `hardware_polling`, `packet_processing`, `entry_point`, `interface_declaration`).
- **Resilient Fallback Design**: Features intelligent quota-monitoring (`429` / `RESOURCE_EXHAUSTED` handling) that seamlessly transitions to deterministic, cache-backed architectural Mermaid diagrams when upstream limits are reached.

---

## ⚡ How DevAgent AI-Git Differs from Existing Git

| Feature / Capability | Traditional Git | DevAgent AI-Git Suite |
| :--- | :--- | :--- |
| **Commit Delta Comparison** | Shows raw line diffs (`+` / `-`) without semantic context. | Computes actual diff stats while generating an **evidence-backed impact analysis graph**. |
| **Code Understanding** | Blind text search (`grep`) or manual file traversal. | **Semantic Code Memory** allowing natural language queries across any repository file type (`.py`, `.cpp`, `.ts`, `.md`, `.json`, etc.). |
| **Risk Assessment** | Manual code review and guesswork. | **Change Risk Radar & Fragility Index** calculating blast radius and coupling reachability. |
| **Verification** | Hope tests pass. | **Self-Verifying Agent** that grounds conclusions in commit-pinned permalinks (`#L12-L28`). |

---

## 🎯 Thoughtful & Principled AI Integration

Most AI coding assistants suffer from hallucination—inventing function names, assuming modules are safe, or generating unverified claims. DevAgent was built on strict **Evidence-Grounded AI Engineering**:

1. **Retrieval Before Generation**: The system never asks the LLM to guess. It first traverses the Git tree, ranks candidates using smart keyword scoring, fetches exact file blobs at the target commit SHA, and feeds structured code chunks into the prompt.
2. **Strict Provenance Tracking**: Every finding is categorized into strict provenance tiers:
   - **`Verified`**: Backed by successfully retrieved code chunks and commit-pinned permalinks.
   - **`Inferred`**: Reasonable architectural hypotheses explicitly marked as inferences.
   - **`Unknown / Insufficient evidence`**: When analysis data is partial or missing, DevAgent refuses to fabricate conclusions, ensuring absolute auditability.
3. **Multi-Node Visual Mapping**: Automatically generates dynamic `Mermaid.js` diagrams representing component hierarchies, call graphs, and dependency trees directly inside interactive modals.

---

## 🚀 Getting Started

1. **Clone & Setup Environment**:
   ```bash
   git clone https://github.com/your-username/devagent-intelligence.git
   cd devagent-intelligence
   pip install -r requirements.txt
   ```
2. **Configure Environment Variables**:
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key"
   export SESSION_SECRET="your-secure-session-secret"
   ```
3. **Run the Backend Server**:
   ```bash
   python backend/server/app.py
   ```
4. **Access the Suite**: Open `http://127.0.0.1:8000` in your browser, authenticate with your GitHub token, and select any repository to start exploring!

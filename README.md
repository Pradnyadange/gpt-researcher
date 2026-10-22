# 🚀 DevAgent: The AI-Git Intelligence & Universal Evidence Suite

> **Bridge the gap between static version control and cognitive code comprehension.** Traditional Git tracks *what* changed and *who* changed it, but leaves developers blind to semantic structure, cross-file architectural dependencies, and automated regression risks. **DevAgent** transforms standard GitHub repositories into active, queryable semantic knowledge graphs with **zero hallucinations** and **commit-pinned evidence grounding**.

---

## ✨ Core Features & Capabilities

- **🧠 Semantic Code Memory ("Digital Librarian"):** Scans live repository file trees recursively, indexes code files (`.py`, `.cpp`, `.js`, `.ts`, etc.), and generates commit-pinned permalinks.
- **🔀 Commit Delta & Regression Risk Scoring:** Compares any two Git references (e.g., `HEAD~1` vs `HEAD`), computes net additions/deletions, and calculates a quantitative regression risk score (0–100 scale).
- **🤖 Evidence-Backed Copilot:** Natural language code queries backed by strict sliding-window relevance matching. Every response links directly to exact line numbers and GitHub permalinks.
- **🏛️ AI-Diagnostics Suite:**
  - **Architecture Visualizer:** Dynamic Mermaid.js system maps across client, core engine, and persistence tiers.
  - **Relationship Graph:** Cross-file symbol call graph mapping entry points to core handlers.
  - **Change Risk Radar:** Evaluates structural coupling indices and code fragility.
  - **Dependency Intelligence:** Parses package manifests (`requirements.txt`, `package.json`) to compute architectural blast radius.
- **⚡ Efficiency Monitor & Health Scoring:** Tracks SQLite cache hits, chunk reuse metrics, file reprocessed counts, and generates an automated Repository Health Score (Code Quality, Security, Architecture, Testing, Documentation).

---

## 🛠️ Technology Stack

- **Backend:** FastAPI (Python 3.10+), Asynchronous HTTPX Client
- **Database & Persistence:** SQLite (`devagent_memory.db`) for caching, file chunks, snapshots, and efficiency metrics
- **Authentication:** GitHub Personal Access Token (PAT) with Starlette `SessionMiddleware`
- **Frontend & UI:** Tailwind CSS, responsive dashboards, Mermaid.js diagrams, and Markdown rendering (`marked.js`)
- **AI Engine:** Google GenAI SDK integration with custom AST/regex grounding algorithms

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- A GitHub Personal Access Token (PAT) with repo scopes

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Pradnyadange/DevAgent.git](https://github.com/Pradnyadange/DevAgent.git)
   cd DevAgent

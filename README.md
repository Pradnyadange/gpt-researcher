# 🤖 DevAgent: AI-Powered GitHub Developer Agent

DevAgent is an intelligent, context-aware developer copilot and repository manager built with FastAPI, Google Gemini AI, and SQLite. It bridges the gap between static code hosting and dynamic, personalized AI development workflows.

---

## ✨ Key Features

* **🧠 Persistent Repository Memory & Chat History:** Remembers past conversation threads and context for each individual repository so you never have to re-explain your architecture.
* **⚙️ Customizable Developer Preferences:** Set your preferred coding standards (e.g., C++20 guidelines, asynchronous patterns, clean architecture rules), and DevAgent automatically applies them to all code reviews and AI answers.
* **🔍 RAG-Powered Semantic Code Search:** Go beyond basic keyword matching. Query your codebase by intent and meaning to find relevant logic instantly.
* **🧹 Automated Code Smell Audits:** Instantly scan core files for long functions, duplicate logic, naming anti-patterns, and error handling bottlenecks.
* **📖 README & Documentation Analyser:** Evaluate existing documentation quality and automatically generate missing sections or complete professional README files.
* **📂 Interactive Code Explorer:** Browse folder trees, view source files directly in a clean dark/light UI, and click **"Ask AI about selected code"** for deep file explanations.

---

## ⚡ How DevAgent is Different from Traditional GitHub

| Feature / Capability | Traditional GitHub | DevAgent (AI Developer Agent) |
| :--- | :--- | :--- |
| **Code Search** | Keyword or regex-based search (`filename:main.py`). | **Semantic RAG Search:** Understands developer intent and natural language queries to retrieve code chunks by logical meaning. |
| **Developer Context & Memory** | Stateless; every issue, PR review, or discussion starts without persistent awareness of your specific coding style. | **Persistent Preferences & Memory:** SQLite-backed memory retains your custom coding standards, tech stack choices, and past repository conversations. |
| **Code Audits & Diagnostics** | Requires third-party CI/CD actions or manual code reviews to catch smells or missing docs. | **Instant AI-Driven Diagnostics:** Built-in automated code smell detection, documentation analyzers, and refactoring recommendations on-demand. |
| **Interactive File Assistance** | Static web file viewer; you must copy-paste code into external LLMs to get explanations. | **Embedded Copilot Workspace:** Select any file in the tree viewer and query it directly with contextually tuned AI prompts. |

---

## 🛠️ Tech Stack

* **Backend:** Python 3.14, FastAPI, Uvicorn, SQLite
* **AI Engine:** Google Gemini SDK (`gemini-2.5-flash`)
* **API Integration:** GitHub REST API v3, HTTPX
* **Frontend:** Jinja2 Templates, HTML5, CSS3, Modern JavaScript (GitHub Dark/Light theme UI)

---

## 🚀 Getting Started & Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Pradnyadange/DevAgent.git](https://github.com/Pradnyadange/DevAgent.git)
   cd DevAgent

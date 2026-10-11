import os
import sys
import base64
import sqlite3
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import httpx
from google import genai

app = FastAPI(title="DevAgent - Ultimate AI GitHub Developer Agent")

app.add_middleware(SessionMiddleware, secret_key="devagent-super-secret-key-change-in-production")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

GITHUB_API_URL = "https://api.github.com"
client_ai = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

DB_PATH = os.path.join(BASE_DIR, "devagent_memory.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS developer_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            preferences TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            repo TEXT,
            role TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user_preferences(username: str) -> str:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT preferences FROM developer_preferences WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else "No specific preferences set."
    except Exception:
        return "No specific preferences set."

def save_chat_memory(username: str, repo: str, role: str, message: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_memory (username, repo, role, message) VALUES (?, ?, ?, ?)", (username, repo, role, message))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_chat_memory(username: str, repo: str, limit: int = 5) -> str:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT role, message FROM chat_memory WHERE username = ? AND repo = ? ORDER BY id DESC LIMIT ?", (username, repo, limit))
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "No previous conversation history for this repository."
        history = reversed(rows)
        return "\n".join([f"{r[0].upper()}: {r[1]}" for r in history])
    except Exception:
        return "No previous conversation history."

@app.get("/api/memory/preferences")
async def get_preferences_api(request: Request):
    user = request.session.get("github_user", "default_user")
    return {"preferences": get_user_preferences(user)}

@app.post("/api/memory/preferences")
async def save_preferences_api(request: Request):
    user = request.session.get("github_user", "default_user")
    body = await request.json()
    prefs = body.get("preferences", "")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO developer_preferences (username, preferences) VALUES (?, ?)
        ON CONFLICT(username) DO UPDATE SET preferences = ?
    ''', (user, prefs, prefs))
    conn.commit()
    conn.close()
    return {"status": "success", "preferences": prefs}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, error: str = None):
    return templates.TemplateResponse(request, "index.html", {"request": request, "error": error})

@app.post("/login")
async def login(request: Request, token: str = Form(...)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_URL}/user",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
        )
    if response.status_code != 200:
        return templates.TemplateResponse(request, "index.html", {"request": request, "error": "Invalid Personal Access Token."})
    
    user_data = response.json()
    request.session["github_token"] = token
    request.session["github_user"] = user_data.get("login")
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not request.session.get("github_token"):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "dashboard.html", {"request": request, "user": request.session.get("github_user")})

@app.get("/api/repos")
async def get_user_repos(request: Request):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_URL}/user/repos",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            params={"sort": "updated", "per_page": 50}
        )
    if response.status_code != 200: return {"repositories": []}
    repos = response.json()
    return {"repositories": [{"name": r.get("name"), "full_name": r.get("full_name"), "description": r.get("description"), "private": r.get("private"), "language": r.get("language") or "Mixed"} for r in repos]}

@app.get("/api/repo/tree")
async def get_repo_tree(request: Request, owner: str, repo: str):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient() as client:
        tree_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/main?recursive=1", headers=headers)
        if tree_res.status_code != 200:
            tree_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/master?recursive=1", headers=headers)
        if tree_res.status_code != 200: return {"files": []}
        files = [{"path": item["path"], "type": item["type"]} for item in tree_res.json().get("tree", []) if item["type"] in ["blob", "tree"]]
    return {"files": files}

@app.get("/api/repo/file")
async def get_repo_file_content(request: Request, owner: str, repo: str, path: str):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient() as client:
        file_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}", headers=headers)
        if file_res.status_code != 200: raise HTTPException(status_code=404, detail="File not found")
        try: content = base64.b64decode(file_res.json().get("content", "")).decode("utf-8", errors='ignore')
        except Exception: content = "Binary file."
    return {"path": path, "content": content}

# --- ADVANCED AGENT FEATURE ENDPOINTS ---

@app.post("/api/repo/issue-mapping")
async def issue_mapping(request: Request):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    owner, repo, issue = body.get("owner"), body.get("repo"), body.get("issue", "")
    prompt = f"[ISSUE -> CODE MAPPING]\nRepo: {owner}/{repo}\nGitHub Issue: '{issue}'\nFind and list the exact files and functions responsible for this issue."
    res = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return {"analysis": res.text}

@app.post("/api/repo/issue-solver")
async def issue_solver(request: Request):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    owner, repo, issue = body.get("owner"), body.get("repo"), body.get("issue", "")
    prompt = f"[ISSUE SOLVER AGENT]\nRepo: {owner}/{repo}\nIssue: '{issue}'\nUnderstand issue, locate relevant code, and build a complete step-by-step implementation plan with code snippets."
    res = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return {"analysis": res.text}

@app.post("/api/repo/pr-review")
async def pr_review(request: Request):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    owner, repo, pr_number = body.get("owner"), body.get("repo"), body.get("pr_number", "latest")
    prompt = f"[PR REVIEW AGENT]\nRepo: {owner}/{repo}\nReview Pull Request #{pr_number}, find bugs, check architecture, and suggest improvements."
    res = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return {"analysis": res.text}

@app.post("/api/repo/commit-analyzer")
async def commit_analyzer(request: Request):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    owner, repo = body.get("owner"), body.get("repo")
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient() as client:
        c_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits?per_page=5", headers=headers)
        commits = c_res.json() if c_res.status_code == 200 else []
    
    prompt = f"[AI COMMIT ANALYZER]\nRecent Commits: {str(commits[:3])}\nExplain what these commits changed and detect potentially dangerous modifications."
    res = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return {"analysis": res.text}

@app.post("/api/repo/commit-risk")
async def commit_risk(request: Request):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    owner, repo = body.get("owner"), body.get("repo")
    prompt = f"[COMMIT RISK PREDICTION]\nAnalyze repository {owner}/{repo} and provide a risk score (Low/Medium/High) based on affected core components."
    res = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return {"analysis": res.text}

@app.post("/api/repo/dependency-analyzer")
async def dependency_analyzer(request: Request):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    owner, repo = body.get("owner"), body.get("repo")
    prompt = f"[DEPENDENCY ANALYZER]\nMap package/library dependencies for {owner}/{repo} and identify outdated or risky dependencies."
    res = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return {"analysis": res.text}

@app.post("/api/repo/architecture-visualizer")
async def architecture_visualizer(request: Request):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    owner, repo = body.get("owner"), body.get("repo")
    prompt = f"""[ARCHITECTURE VISUALIZER]
    Generate an architecture diagram breakdown for {owner}/{repo}. 
    IMPORTANT: Provide valid Mermaid.js code inside a ```mermaid ... ``` code block. Do not use any HTML tags like <br> inside the mermaid block.
    """
    res = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return {"analysis": res.text}

@app.post("/api/repo/relationship-graph")
async def relationship_graph(request: Request):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    owner, repo = body.get("owner"), body.get("repo")
    prompt = f"""[CODEBASE RELATIONSHIP GRAPH]
    Map flow: API -> Service -> Database -> External API for {owner}/{repo}.
    IMPORTANT: Provide valid Mermaid.js code inside a ```mermaid ... ``` code block. Do not use any HTML tags like <br> inside the mermaid block.
    """
    res = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return {"analysis": res.text}

@app.post("/api/repo/performance-investigator")
async def performance_investigator(request: Request):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    owner, repo = body.get("owner"), body.get("repo")
    prompt = f"[PERFORMANCE INVESTIGATOR]\nFind potentially expensive operations, identify bottlenecks, and suggest optimizations for {owner}/{repo}."
    res = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return {"analysis": res.text}

@app.post("/api/repo/refactoring-suggestions")
async def refactoring_suggestions(request: Request):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    owner, repo = body.get("owner"), body.get("repo")
    prompt = f"[AI REFACTORING SUGGESTIONS]\nSuggest how to restructure problematic code in {owner}/{repo} and explain why."
    res = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return {"analysis": res.text}

@app.post("/api/agent/query")
async def agent_query(request: Request):
    token = request.session.get("github_token")
    if not token: raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    query, owner, repo = body.get("query", ""), body.get("owner"), body.get("repo")
    user = request.session.get("github_user", "default_user")
    prefs = get_user_preferences(user)
    
    prompt = f"[MULTI-STEP AGENT]\nPreferences: {prefs}\nQuery: {query}"
    res = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    save_chat_memory(user, f"{owner}/{repo}", "user", query)
    save_chat_memory(user, f"{owner}/{repo}", "assistant", res.text)
    return {"answer": res.text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

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

app = FastAPI(title="DevAgent - AI GitHub Developer Agent")

app.add_middleware(SessionMiddleware, secret_key="devagent-super-secret-key-change-in-production")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

GITHUB_API_URL = "https://api.github.com"
client_ai = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Initialize Local SQLite Memory & Preferences Database
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
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_URL}/user/repos",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            params={"sort": "updated", "per_page": 50, "affiliation": "owner,collaborator,organization_member"}
        )
    
    if response.status_code != 200:
        return {"repositories": []}
    
    repos = response.json()
    formatted_repos = [{
        "name": repo.get("name"),
        "full_name": repo.get("full_name"),
        "description": repo.get("description"),
        "private": repo.get("private"),
        "language": repo.get("language") or "Mixed",
        "updated_at": repo.get("updated_at")
    } for repo in repos]
    
    return {"repositories": formatted_repos}

@app.get("/api/repo/overview")
async def get_repo_overview(request: Request, owner: str, repo: str):
    token = request.session.get("github_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient() as client:
        repo_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}", headers=headers)
        if repo_res.status_code != 200:
            raise HTTPException(status_code=404, detail="Repository not found")
        repo_data = repo_res.json()
        
        lang_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/languages", headers=headers)
        languages = lang_res.json() if lang_res.status_code == 200 else {}
        
        dependencies = []
        for dep_file in ["package.json", "requirements.txt", "Cargo.toml", "pom.xml", "go.mod", "CMakeLists.txt"]:
            file_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{dep_file}", headers=headers)
            if file_res.status_code == 200:
                try:
                    content = base64.b64decode(file_res.json().get("content", "")).decode("utf-8", errors='ignore')
                    dependencies.append({"file": dep_file, "snippet": content[:400]})
                except Exception:
                    pass

    description = repo_data.get("description") or "No description provided."
    dep_text = str(dependencies).lower()
    frameworks = []
    if "fastapi" in dep_text: frameworks.append("FastAPI")
    if "flask" in dep_text: frameworks.append("Flask")
    if "react" in dep_text or "next" in dep_text: frameworks.append("Next.js / React")
    if "express" in dep_text: frameworks.append("Node.js Express")
    if "drogon" in dep_text: frameworks.append("Drogon C++ Web Framework")
    if not frameworks: frameworks.append("Core Modular Architecture")

    return {
        "name": repo_data.get("name"),
        "full_name": repo_data.get("full_name"),
        "private": repo_data.get("private"),
        "what_it_does": description,
        "tech_stack": list(languages.keys())[:5],
        "languages": languages,
        "frameworks": frameworks,
        "dependencies": [d["file"] for d in dependencies] if dependencies else ["None detected"]
    }

@app.get("/api/repo/tree")
async def get_repo_tree(request: Request, owner: str, repo: str):
    token = request.session.get("github_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient() as client:
        tree_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/main?recursive=1", headers=headers)
        if tree_res.status_code != 200:
            tree_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/master?recursive=1", headers=headers)
        if tree_res.status_code != 200:
            return {"files": []}
        tree_data = tree_res.json()
        files = [{"path": item["path"], "type": item["type"]} for item in tree_data.get("tree", []) if item["type"] in ["blob", "tree"]]
    return {"files": files}

@app.get("/api/repo/file")
async def get_repo_file_content(request: Request, owner: str, repo: str, path: str):
    token = request.session.get("github_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient() as client:
        file_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}", headers=headers)
        if file_res.status_code != 200:
            raise HTTPException(status_code=404, detail="File not found")
        try:
            content = base64.b64decode(file_res.json().get("content", "")).decode("utf-8", errors='ignore')
        except Exception:
            content = "Binary or unreadable file content."
    return {"path": path, "content": content}

@app.post("/api/repo/analyze-readme")
async def analyze_readme(request: Request):
    token = request.session.get("github_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    body = await request.json()
    owner, repo = body.get("owner"), body.get("repo")
    user = request.session.get("github_user", "default_user")
    prefs = get_user_preferences(user)
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    
    try:
        async with httpx.AsyncClient() as client:
            repo_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}", headers=headers)
            repo_data = repo_res.json() if repo_res.status_code == 200 else {}
            
            readme_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/readme", headers=headers)
            readme_content = ""
            if readme_res.status_code == 200:
                try:
                    readme_content = base64.b64decode(readme_res.json().get("content", "")).decode("utf-8", errors='ignore')
                except Exception:
                    pass

        prompt = f"Developer Preferences: {prefs}\n\nAnalyze README quality, missing sections, and generate an improved README.md for {owner}/{repo}. Description: {repo_data.get('description')}. Current README: {readme_content}"
        response = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return {"analysis": response.text}
    except Exception as e:
        return {"analysis": f"⚠️ Analysis failed: {str(e)}"}

@app.post("/api/repo/code-smells")
async def analyze_code_smells(request: Request):
    token = request.session.get("github_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    body = await request.json()
    owner, repo = body.get("owner"), body.get("repo")
    user = request.session.get("github_user", "default_user")
    prefs = get_user_preferences(user)
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    
    try:
        async with httpx.AsyncClient() as client:
            tree_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/main?recursive=1", headers=headers)
            if tree_res.status_code != 200:
                tree_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/master?recursive=1", headers=headers)
            tree_data = tree_res.json() if tree_res.status_code == 200 else {}
            files = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]

            code_context = ""
            target_exts = ('.py', '.js', '.ts', '.java', '.cpp', '.cc', '.h', '.hpp')
            for kf in [f for f in files if f.endswith(target_exts)][:5]:
                file_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{kf}", headers=headers)
                if file_res.status_code == 200:
                    try:
                        decoded = base64.b64decode(file_res.json().get('content', '')).decode('utf-8', errors='ignore')
                        code_context += f"\n--- FILE: {kf} ---\n{decoded[:1200]}\n"
                    except Exception:
                        pass

        if not code_context:
            code_context = "No readable source files found."

        prompt = f"Developer Preferences: {prefs}\n\nAnalyze code smells (Long Functions, Duplicate Code, Naming Problems, Error Handling) for {owner}/{repo}:\n{code_context}"
        response = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return {"analysis": response.text}
    except Exception as e:
        return {"analysis": f"⚠️ Code smells analysis failed: {str(e)}"}

@app.post("/api/repo/semantic-search")
async def semantic_search(request: Request):
    token = request.session.get("github_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    body = await request.json()
    owner, repo, query = body.get("owner"), body.get("repo"), body.get("query", "")
    if not query:
        return {"results": "Please provide a search query."}
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    try:
        async with httpx.AsyncClient() as client:
            tree_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/main?recursive=1", headers=headers)
            if tree_res.status_code != 200:
                tree_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/master?recursive=1", headers=headers)
            tree_data = tree_res.json() if tree_res.status_code == 200 else {}
            files = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]

            code_chunks = []
            target_exts = ('.py', '.js', '.ts', '.java', '.cpp', '.cc', '.h', '.hpp', '.md')
            for kf in [f for f in files if f.endswith(target_exts)][:10]:
                file_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{kf}", headers=headers)
                if file_res.status_code == 200:
                    try:
                        content = base64.b64decode(file_res.json().get("content", "")).decode("utf-8", errors='ignore')
                        for i in range(0, len(content), 800):
                            if len(content[i:i+800].strip()) > 50:
                                code_chunks.append({"path": kf, "snippet": content[i:i+800]})
                    except Exception:
                        pass

        prompt = f"Semantic RAG Search. Intent: '{query}'. Chunks: {str(code_chunks[:20])}. Select top matching code chunks by meaning."
        response = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return {"results": response.text}
    except Exception as e:
        return {"results": f"⚠️ Semantic search failed: {str(e)}"}

@app.post("/api/agent/query")
async def multi_step_agent_query(request: Request):
    token = request.session.get("github_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    body = await request.json()
    query, owner, repo = body.get("query", ""), body.get("owner"), body.get("repo")
    user = request.session.get("github_user", "default_user")
    
    prefs = get_user_preferences(user)
    history = get_chat_memory(user, f"{owner}/{repo}", limit=5)
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    
    try:
        async with httpx.AsyncClient() as client:
            tree_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/main?recursive=1", headers=headers)
            if tree_res.status_code != 200:
                tree_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/master?recursive=1", headers=headers)
            tree_data = tree_res.json() if tree_res.status_code == 200 else {}
            file_paths = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]

            relevant_files = [f for f in file_paths if any(kw in f.lower() for kw in ['main', 'server', 'app', 'router', 'controller', 'index', 'config'])]
            if not relevant_files:
                relevant_files = file_paths[:5]

            code_context = ""
            for kf in relevant_files[:6]:
                file_res = await client.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{kf}", headers=headers)
                if file_res.status_code == 200:
                    try:
                        decoded = base64.b64decode(file_res.json().get('content', '')).decode('utf-8', errors='ignore')
                        code_context += f"\n--- FILE: {kf} ---\n{decoded[:1500]}\n"
                    except Exception:
                        pass

        prompt = f"""
        [MULTI-STEP AI AGENT MODE]
        Developer Preferences: {prefs}

        Previous Repository Conversation:
        {history}

        Repository File Structure ({len(file_paths)} files total):
        {str(file_paths[:40])}

        Retrieved Code Context & Dependencies:
        {code_context}

        User Request: "{query}"

        Analyze cross-file relationships, dependencies, and architecture to provide a comprehensive, step-by-step technical response.
        """
        
        response = client_ai.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        answer = response.text
        
        save_chat_memory(user, f"{owner}/{repo}", "user", query)
        save_chat_memory(user, f"{owner}/{repo}", "assistant", answer)

        return {"answer": answer, "indexed_files_count": len(file_paths)}
    except Exception as e:
        return {"answer": f"⚠️ Agent execution failed: {str(e)}", "indexed_files_count": 0}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
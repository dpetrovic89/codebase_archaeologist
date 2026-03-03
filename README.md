# 🏺 Codebase Archaeologist

An MCP server and Gradio UI that digs through GitHub repositories to surface tech debt, security smells, architectural patterns, and dependency risks. 

## ✨ Features
- **📊 Repo Summary**: Instant metadata, line counts, and language breakdown.
- **📉 Tech Debt Scan**: Cyclomatic complexity hotspots, TODOs, and **Long Function Detection (>50 lines)**.
- **🛡️ Security Audit**: Regexp-based secret scanning and integration with **Bandit** (with 60s safety timeout).
- **📦 Dependency Check**: Detects vulnerable packages for **Python (PyPI)** & **Node.js (npm)**.
- **📖 Onboarding Guide**: Instant README-based walkthroughs for new contributors.
- **🔋 Live Progress**: Real-time feedback and state reporting during archaeological digs.
- **🎨 Premium UI**: A high-density **Industrial Utilitarian** dashboard with Space Grotesk & JetBrains Mono typography.
- **🔌 AI Agent Access**: Ready-to-use Model Context Protocol (MCP) server for Claude, Cursor, and Windsurf.

Technical details about the system design can be found in [architecture.md](architecture.md).

## 🚀 Getting Started

### 🖥️ Gradio Web UI
The easiest way to explore repositories visually.
1. Install dependencies: `pip install -r requirements.txt`
2. Run the app: `python app.py`
3. Open `http://127.0.0.1:7860` in your browser.

### 🔌 MCP Server (For AI Agents)
Expose archaeological tools to your favorite AI agent.

**Claude Desktop Setup:**
Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "codebase-archaeologist": {
      "command": "python",
      "args": ["/absolute/path/to/main.py"],
      "env": { "GITHUB_TOKEN": "your_token_here" }
    }
  }
}
```
坐
## 🔐 Environment Variables
To avoid GitHub API rate limits, it is highly recommended to set a token:
- `GITHUB_TOKEN`: Your GitHub Personal Access Token.

## 🛳️ Deployment
This project is designed to be deployed directly to **Hugging Face Spaces** using the provided `Dockerfile`.

1. Create a "Docker" Space on Hugging Face.
2. Push this repository.
3. Set your `GITHUB_TOKEN` in the Space Settings > Variables/Secrets.

---
*Analyzed via the Codebase Archaeologist.*

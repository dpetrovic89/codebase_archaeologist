import os # Build Trigger: Project Migration
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import gradio as gr
import asyncio
from main import (
    mcp, git_service, analysis_service, dep_service, sec_service, onboarding_service,
    RepoSummary, TechDebtReport, DependencyReport, SecurityReport, OnboardingGuide
)

# Custom Theme for Codebase Archaeologist
theme = gr.themes.Soft(
    primary_hue="emerald",
    secondary_hue="slate",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Outfit"), "sans-serif"],
).set(
    body_background_fill="*neutral_950",
    block_background_fill="*neutral_900",
    block_border_width="1px",
    block_title_text_color="*primary_400",
)

css_code = """
    .gradio-container { background: #050505 !important; }
    #header-log { 
        background: #111; 
        border: 1px solid #10b981; 
        padding: 10px; 
        margin-bottom: 20px; 
        font-family: 'JetBrains Mono';
        color: #10b981;
    }
    .technical-card {
        background: #111827 !important;
        border: 1px solid #374151 !important;
        border-radius: 4px !important;
    }
"""

async def full_analyze(github_url, branch=None, progress=gr.Progress()):
    if not github_url:
        return "Please enter a valid GitHub URL.", "", "", "", "", ""
    
    # Sanitize inputs
    github_url = github_url.strip()
    branch = branch.strip() if branch and branch.strip() else None
    
    path = None
    try:
        progress(0, desc="🔍 Validating GitHub URL...")
        await asyncio.sleep(0.5)

        progress(0.2, desc="🏺 Unearthing Repository (Cloning)...")
        # We need the path first to run other services
        path = await git_service.clone_repo(github_url, branch)
        
        progress(0.4, desc="🔬 Scouring for Tech Debt...")
        summary_task = analysis_service.analyze_structure(path)
        tech_debt_task = analysis_service.find_tech_debt(path)
        
        progress(0.5, desc="🔐 Inspecting Security Smells...")
        sec_task = sec_service.detect_security_smells(path)
        
        progress(0.7, desc="📦 Checking Dependencies...")
        dep_task = dep_service.audit_dependencies(path)
        
        progress(0.8, desc="📖 Generating Onboarding Guide...")
        onboarding_task = onboarding_service.generate_onboarding_guide(path)

        # Gather all results
        summary, tech_debt, security, deps, onboarding = await asyncio.gather(
            summary_task, tech_debt_task, sec_task, dep_task, onboarding_task
        )
        
        progress(1.0, desc="💎 Analysis Complete!")
        
        # Format outputs as Markdown/HTML for the cards
        summary_md = f"""
### 📊 {summary['repo_name']} Summary
- **Files**: {summary['total_files']} 
- **Lines**: {summary['total_lines']}
- **Primary**: {next(iter(summary['languages']), 'Unknown')}
- **Size**: {summary['size_kb']} KB
"""

        # Tech Debt Card with Progress bar concept
        score = tech_debt['debt_score']
        grade = tech_debt['debt_grade']
        color = "#10b981" if score < 30 else "#f59e0b" if score < 60 else "#ef4444"
        
        debt_md = f"""
<div style='border-left: 4px solid {color}; padding-left: 15px;'>
    <h2 style='color: {color}; margin-bottom: 5px;'>Grade: {grade}</h2>
    <p style='font-size: 1.1em; font-family: "JetBrains Mono";'>Debt Score: {score}/100</p>
    <hr style='border: 0; border-top: 1px solid #334155; margin: 10px 0;'>
    <details>
        <summary style='cursor: pointer; color: #10b981;'>Show Complex Functions ({len(tech_debt['complex_functions'])})</summary>
        <pre>{chr(10).join([f"- {f['name']} (score: {f['complexity']})" for f in tech_debt['complex_functions'][:5]])}</pre>
    </details>
    <details>
        <summary style='cursor: pointer; color: #10b981;'>Show Long Functions ({len(tech_debt['long_functions'])})</summary>
        <pre>{chr(10).join([f"- {f['name']} ({f['lines']} lines)" for f in tech_debt['long_functions'][:5]])}</pre>
    </details>
</div>
"""

        # Security Smells
        sec_md = "#### 🛡️ Security Findings\n"
        if not security['regex_findings'] and not security['bandit_findings']:
            sec_md += "✅ No high-priority smells detected."
        else:
            for f in security['regex_findings']:
                sec_md += f"- ⚠️ **{f['type']}** in `{f['file']}`\n"
            for b in security['bandit_findings']:
                sec_md += f"- 🚩 **Bandit {b['issue_severity']}**: {b['issue_text']}\n"

        # Dependencies
        dep_md = f"#### 📦 Dependencies ({deps['total_deps']})\n"
        if not deps['vulnerable_deps']:
            dep_md += "✅ No known vulnerabilities found (OSV Scan)."
        else:
            for v in deps['vulnerable_deps']:
                dep_md += f"- ❌ `vulnerable`: **{v['name']}**\n"
        
        # Onboarding Guide
        onboarding_md = f"### 🗺️ Contributor Roadmap\n\n{onboarding['guide']}"

        status_text = "✨ Archaeological dig successful. View findings below."
        
        return summary_md, debt_md, sec_md, dep_md, onboarding_md, status_text

    except Exception as e:
        # Privacy: redact paths in errors
        err_msg = str(e)
        if "tmp_repos" in err_msg or ":" in err_msg:
            err_msg = "An internal analysis error occurred. Local file system paths have been redacted for security."
        return "Analysis Failed.", "", "", "", "", f"❌ Error: {err_msg}"
    finally:
        if path:
            git_service.cleanup(path)

# --- Comparison Tab Logic ---
async def compare_repos(url1, url2):
    if not url1 or not url2:
        return "Please enter two valid URLs."
    
    # Simple parallel run of basic metrics
    try:
        from main import comparison_tool
        result = await comparison_tool(url1, url2)
        
        comparison_md = f"""
## ⚔️ Codebase Battle: {result.repo1_name} vs {result.repo2_name}

| Metric | {result.repo1_name} | {result.repo2_name} |
| :--- | :---: | :---: |
| **Debt Score** | {result.debt_score_1} | {result.debt_score_2} |
| **Risk Score** | {result.risk_score_1} | {result.risk_score_2} |
| **Languages** | {", ".join(list(result.languages_1.keys())[:3])} | {", ".join(list(result.languages_2.keys())[:3])} |
| **Winner** | {"🏆" if result.winner == url1 else ""} | {"🏆" if result.winner == url2 else ""} |

**Verdict**: {result.verdict}
"""
        return comparison_md
    except Exception as e:
        return f"❌ Comparison failed: {str(e)}"

# Define the local port for MCP (used in documentation)
local_port = 8000 # Default FastMCP port

with gr.Blocks() as app:
    
    with gr.Group(elem_id="header-log"):
        gr.HTML("<h1>🏺 CODEBASE ARCHAEOLOGIST - EXCAVATION TERMINAL</h1>")
        gr.Markdown("Surfacing technical debt and architectural artifacts from the digital deep.")

    with gr.Tabs():
        with gr.Tab("⚒️ Repository Dig"):
            with gr.Row():
                with gr.Column(scale=4):
                    repo_url = gr.Textbox(
                        label="Gimme Repository URL", 
                        placeholder="https://github.com/username/repo",
                        elem_id="url-input"
                    )
                with gr.Column(scale=1):
                    branch = gr.Textbox(label="Branch (optional)", placeholder="main")
            
            scan_btn = gr.Button("🚀 START EXCAVATION", variant="primary")
            status_out = gr.Markdown("Status: Idle", elem_id="status-bar")
            
            with gr.Row():
                with gr.Column():
                    summary_view = gr.Markdown(label="Archaeological Summary", elem_classes="technical-card")
                with gr.Column():
                    tech_debt_view = gr.HTML(label="Tech Debt Analysis", elem_classes="technical-card")
            
            with gr.Row():
                with gr.Column():
                    security_view = gr.Markdown(label="Security Smells", elem_classes="technical-card")
                with gr.Column():
                    dependency_view = gr.Markdown(label="Contaminant Audit", elem_classes="technical-card")
            
            with gr.Row():
                onboarding_view = gr.Markdown(label="Onboarding Artifacts", elem_classes="technical-card")

        with gr.Tab("⚔️ Comparison Hall"):
            gr.Markdown("### Battle of the Codebases")
            with gr.Row():
                cmp_url1 = gr.Textbox(label="Repository 1", placeholder="https://github.com/repo1")
                cmp_url2 = gr.Textbox(label="Repository 2", placeholder="https://github.com/repo2")
            compare_btn = gr.Button("⚔️ EVALUATE MATURITY")
            compare_output = gr.Markdown(elem_classes="technical-card")
            
            compare_btn.click(compare_repos, inputs=[cmp_url1, cmp_url2], outputs=[compare_output])

        with gr.Tab("🔌 MCP Server"):
            gr.Markdown("""
            ## 🏺 Connect your AI Agent
            The Codebase Archaeologist uses the **Model Context Protocol (MCP)** to empower AI agents with repository discovery tools.
            
            ### 🖥️ 1. Local Setup (Claude Desktop)
            Add this to your `claude_desktop_config.json` (typically in `%APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/settings/` or similar):
            
            ```json
            {
              "mcpServers": {
                "codebase-archaeologist": {
                  "command": "python",
                  "args": ["/path/to/your/project/main.py"],
                  "env": {
                    "GITHUB_TOKEN": "your_personal_access_token"
                  }
                }
              }
            }
            ```

            ### ☁️ 2. Remote Setup (Hugging Face)
            If you have deployed this to Hugging Face, you can use the **SSE** endpoint:
            - **URL**: `https://executor1389-codebase-archaeologist.hf.space/mcp/sse`
            - **Type**: `Remote MCP`
            - **Health Check**: `https://executor1389-codebase-archaeologist.hf.space/mcp_test`

            ### 🏺 Available Tools
            AI agents will gain access to:
            - `analyze_repo`: Structure & metadata analysis.
            - `find_tech_debt`: Detect complex functions & TODOs.
            - `detect_security_smells`: Scan for leaks & SQLi.
            - `audit_dependencies`: Check for contaminated packages.
            """)

    scan_btn.click(
        full_analyze,
        inputs=[repo_url, branch],
        outputs=[summary_view, tech_debt_view, security_view, dependency_view, onboarding_view, status_out]
    )
    
    gr.Markdown("---")
    gr.Markdown("🛡️ **Privacy**: Analysis is performed on-the-fly. Local clones are cleaned up immediately after report generation.")

# Mount the MCP SSE application
# This exposes /sse and /messages required for Remote MCP
app.app.mount("/mcp", mcp.sse_app())

@app.app.get("/mcp_test")
async def mcp_test():
    return {"status": "alive", "mcp_prefix": "/mcp"}

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860, theme=theme, css=css_code)
坐

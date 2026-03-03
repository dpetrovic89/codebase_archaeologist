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
        
        progress(0.7, desc="📦 Auditing Dependencies...")
        deps_task = dep_service.audit_dependencies(path)
        
        # Run analysis concurrently
        summary_res, debt_res, deps_res, sec_res = await asyncio.gather(
            summary_task, tech_debt_task, deps_task, sec_task
        )
        
        progress(0.9, desc="📖 Generating Onboarding Guide...")
        guide_res = onboarding_service.generate_guide(path, summary_res)
        
        # Casting/Processing
        repo_name = github_url.rstrip("/").split("/")[-1]
        
        # Calculate Tech Debt Scores before instantiation
        debt_score = min(100, (debt_res["todo_count"] * 2) + (len(debt_res["complex_functions"]) * 5) + (len(debt_res["long_files"]) * 5) + (len(debt_res.get("long_functions", [])) * 3))
        debt_grade = "A" if debt_score <= 20 else "B" if debt_score <= 40 else "C" if debt_score <= 60 else "D" if debt_score <= 80 else "F"
        debt_res["debt_score"] = debt_score
        debt_res["debt_grade"] = debt_grade
        
        summary = RepoSummary(
            repo_name=repo_name,
            description="Analyzed via Codebase Archaeologist",
            stars=0,
            languages=summary_res["languages"],
            total_files=summary_res["total_files"],
            total_lines=summary_res["total_lines"],
            estimated_test_coverage_pct=(summary_res["test_files_count"] / max(1, summary_res["total_files"])) * 100,
            entry_points=summary_res["entry_points"],
            top_level_structure=summary_res["top_level"],
            size_kb=0
        )
        debt = TechDebtReport(**debt_res)
        sec = SecurityReport(**sec_res)
        deps = DependencyReport(ecosystem="Mixed/PyPI", **deps_res)
        guide = OnboardingGuide(**guide_res)
        
        # Format Results
        summary_md = f"## 🏺 Repository: <span class='data-readout'>{summary.repo_name}</span>\n"
        summary_md += f"- 📊 **Files**: <span class='data-readout'>{summary.total_files}</span>\n"
        summary_md += f"- 📈 **Lines**: <span class='data-readout'>{summary.total_lines}</span>\n"
        summary_md += f"- 🧪 **Coverage**: <span class='data-readout'>{summary.estimated_test_coverage_pct:.1f}%</span>\n"
        summary_md += f"- 🚀 **Entry**: <span class='data-readout'>{', '.join(summary.entry_points) or 'None'}</span>\n"
        
        debt_md = f"## 📉 Grade: <span class='data-readout'>{debt_grade}</span> (Score: <span class='data-readout'>{debt_score}</span>)\n"
        debt_md += f"- 📝 **TODOs**: {debt.todo_count}\n"
        if debt.todo_examples:
            debt_md += f"\n<details><summary>🔎 View Exploration Log (TODOs: {len(debt.todo_examples)})</summary>\n\n"
            import html
            for item in debt.todo_examples:
                safe_content = html.escape(item['content'])
                debt_md += f"- `{item['file']}:{item['line']}`: {safe_content}\n"
            debt_md += "\n</details>\n"
        
        debt_md += f"- 🏗️ **Complexity**: {len(debt.complex_functions)}\n"
        if debt.complex_functions:
            debt_md += f"\n<details><summary>🔎 View Hotspots</summary>\n\n"
            for item in debt.complex_functions:
                debt_md += f"- `{item['file']}`: `{item['name']}` (Score: {item['complexity']})\n"
            debt_md += "\n</details>\n"

        debt_md += f"- 📏 **Large Components**: {len(debt.long_functions)}\n"
        if debt.long_functions:
            debt_md += f"\n<details><summary>🔎 View Artifacts (>50 lines)</summary>\n\n"
            for item in debt.long_functions:
                debt_md += f"- `{item['file']}`: `{item['name']}` ({item['lines']} lines)\n"
            debt_md += "\n</details>\n"

        sec_md = f"## 🛡️ Risk Assessment: <span class='data-readout'>{sec.overall_risk}</span>\n"
        sec_md += f"- 🚨 **High Alert**: {sec.bandit_high_count}\n"
        sec_md += f"- ⚠️ **Medium Alert**: {sec.bandit_medium_count}\n"
        if sec.findings:
            sec_md += f"\n<details><summary>🔎 View Exposure Logs</summary>\n\n"
            for find in sec.findings:
                sec_md += f"- **[{find['severity']}]** `{find['file']}:{find['line']}`: {find['issue']}\n"
            sec_md += "\n</details>\n"
        
        deps_md = f"## 📦 Inventory (Risk: <span class='data-readout'>{deps.risk_score}</span>)\n"
        deps_md += f"- 🐛 **Vulnerable Packages**: {len(deps.vulnerable_deps)}\n"
        deps_md += f"- ✅ **Safe Artifacts**: {deps.safe_deps_count}\n"
        if deps.vulnerable_deps:
            deps_md += f"\n<details><summary>🔎 View Contaminated Packages</summary>\n\n"
            for item in deps.vulnerable_deps:
                deps_md += f"- **{item['name']}**: {item.get('vulnerabilities', [])[0].get('summary', 'Vulnerability detected')}\n"
            deps_md += "\n</details>\n"

        guide_md = f"## 📖 Onboarding Guide\n"
        guide_md += f"<details open><summary><b>🛠️ Setup Steps</b></summary>\n\n{guide.setup_steps}\n\n</details>\n"
        guide_md += f"<details><summary><b>🧱 Key Modules</b></summary>\n\n{guide.key_modules}\n\n</details>\n"
        guide_md += f"<details><summary><b>🧪 How to Run Tests</b></summary>\n\n{guide.run_tests}\n\n</details>\n"

        progress(1.0, desc="✅ Discovery Complete!")
        return summary_md, debt_md, sec_md, deps_md, guide_md, "Analysis Complete!"
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        error_msg = str(e)
        # Sanitize error: Hide local system paths
        if "tmp_repos" in error_msg:
             error_msg = "An error occurred during cleanup or cloning. The repository could not be processed."
        return f"Error: {error_msg}", "", "", "", "", "Analysis Failed."
    finally:
        if path:
            git_service.cleanup(path)

# --- Custom CSS (Industrial Utilitarian) ---
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;500;700&family=JetBrains+Mono:wght@400;700&family=Plus+Jakarta+Sans:wght@300;400;600&display=swap');

:root {
    --primary-color: #10b981;
    --bg-color: #050505;
    --card-bg: #0d0d0d;
    --border-color: #1f2937;
    --text-main: #e5e7eb;
    --text-muted: #9ca3af;
    --font-display: 'Space Grotesk', sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
    --font-body: 'Plus Jakarta Sans', sans-serif;
}

body, .gradio-container {
    background-color: var(--bg-color) !important;
    font-family: var(--font-body) !important;
    color: var(--text-main) !important;
}

/* Header & Titles */
h1, h2, .discovery-header {
    font-family: var(--font-display) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    color: var(--primary-color) !important;
    text-transform: uppercase;
}

.discovery-log-header {
    border-left: 4px solid var(--primary-color);
    padding-left: 1rem;
    margin-bottom: 2rem;
    background: linear-gradient(90deg, rgba(16, 185, 129, 0.1) 0%, transparent 100%);
}

/* Cards & Containers */
.gradio-container .gr-box, .gradio-container .gr-panel, .gradio-container .gr-button {
    border: 1px solid var(--border-color) !important;
    background-color: var(--card-bg) !important;
    border-radius: 4px !important;
}

.gradio-container .gr-button-primary {
    background-color: var(--primary-color) !important;
    color: var(--bg-color) !important;
    font-family: var(--font-display) !important;
    font-weight: 700 !important;
}

/* Data Readouts */
.data-readout {
    font-family: var(--font-mono);
    color: var(--primary-color);
    background: #000;
    padding: 0.2rem 0.5rem;
    border: 1px solid #10b98144;
    border-radius: 2px;
}

/* Tabs */
.tabs .tab-nav button.selected {
    color: var(--primary-color) !important;
    border-bottom: 2px solid var(--primary-color) !important;
}

/* Progress Bar */
.progress-container .progress-bar-wrap {
    background-color: #111 !important;
    border: 1px solid #333;
}
.progress-container .progress-bar {
    background: linear-gradient(90deg, #10b981, #059669) !important;
}

/* Collapsible Details */
details {
    border: 1px solid var(--border-color);
    margin: 0.5rem 0;
    padding: 0.5rem;
    background: rgba(255, 255, 255, 0.02);
}
summary {
    cursor: pointer;
    font-family: var(--font-display);
    font-weight: 500;
    color: var(--text-main);
}
"""

with gr.Blocks(css=custom_css, title="Codebase Archaeologist") as app:
    gr.HTML("""
        <div class="discovery-log-header">
            <h1 style="margin:0; font-size: 2.5rem;">🏺 Codebase Archaeologist</h1>
            <p style="margin:0; opacity: 0.7; font-family: 'JetBrains Mono';">SYSTEM STATUS: READY // AUTH: TOKEN_LOADED</p>
        </div>
    """)
    
    with gr.Row():
        with gr.Column(scale=4):
            repo_url = gr.Textbox(
                label="Repository URL", 
                placeholder="https://github.com/user/project",
                info="Paste a public GitHub link to begin exploration."
            )
            branch = gr.Textbox(
                label="Branch (Optional)",
                placeholder="main",
                info="Specific branch to analyze. Leave empty for default."
            )
        with gr.Column(scale=1):
            scan_btn = gr.Button("🏺 BEGIN DISCOVERY", variant="primary", scale=1)
            status_out = gr.Textbox(label="Archaeologist Action", interactive=False)
            
    with gr.Tabs():
        with gr.TabItem("📊 Summary"):
            summary_view = gr.Markdown("Enter a repository to start the dig.")
        with gr.TabItem("📉 Tech Debt"):
            tech_debt_view = gr.Markdown()
        with gr.TabItem("🛡️ Security"):
            security_view = gr.Markdown()
        with gr.TabItem("📦 Dependencies"):
            dependency_view = gr.Markdown()
        with gr.TabItem("📖 Onboarding"):
            onboarding_view = gr.Markdown()
        with gr.TabItem("🔌 MCP Server"):
            gr.Markdown("""
            ## 🔌 Using the MCP Server
            This application is also a **Model Context Protocol (MCP)** server. You can connect it to AI agents like **Claude Desktop**, **Cursor**, or **Windsurf** to let them analyze repositories autonomously.

            ### 💻 1. Local Setup (Claude Desktop)
            Add this to your `claude_desktop_config.json`:
            ```json
            {
              "mcpServers": {
                "codebase-archaeologist": {
                  "command": "python",
                  "args": ["/path/to/your/project/main.py"],
                  "env": { "GITHUB_TOKEN": "your_token_here" }
                }
              }
            }
            ```

            ### ☁️ 2. Remote Setup (Hugging Face)
            If you have deployed this to Hugging Face, you can use the **SSE** endpoint:
            - **URL**: `https://your-space-name.hf.space/mcp/sse`
            - **Type**: `Remote MCP`

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

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860)

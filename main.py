import os
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

from services.git_service import GitService
from services.analysis_service import AnalysisService
from services.dependency_service import DependencyService
from services.security_service import SecurityService
from services.effort_service import EffortService
from services.onboarding_service import OnboardingService

# Initialize FastMCP server
mcp = FastMCP("codebase_archaeologist_mcp")

# Services
git_service = GitService()
analysis_service = AnalysisService()
dep_service = DependencyService()
sec_service = SecurityService()
effort_service = EffortService()
onboarding_service = OnboardingService()

# --- Models ---

class RepoSummary(BaseModel):
    repo_name: str
    description: str
    stars: int
    languages: Dict[str, int]
    total_files: int
    total_lines: int
    estimated_test_coverage_pct: float
    entry_points: List[str]
    top_level_structure: List[str]
    size_kb: int

class TechDebtReport(BaseModel):
    todo_count: int
    todo_examples: List[Dict[str, Any]]
    complex_functions: List[Dict[str, Any]]
    long_files: List[Dict[str, Any]]
    long_functions: List[Dict[str, Any]]
    missing_docstrings_count: int
    debt_score: int
    debt_grade: str

class DependencyReport(BaseModel):
    total_deps: int
    ecosystem: str
    vulnerable_deps: List[Dict[str, Any]]
    outdated_deps: List[Dict[str, Any]]
    safe_deps_count: int
    risk_score: int

class SecurityReport(BaseModel):
    findings: List[Dict[str, Any]]
    bandit_high_count: int
    bandit_medium_count: int
    overall_risk: str
    scanned_files_count: int

class EffortEstimate(BaseModel):
    target: str
    effort_days: int
    confidence: str
    affected_file_count: int
    risks: List[str]
    suggested_first_steps: List[str]
    complexity_multiplier: float

class OnboardingGuide(BaseModel):
    setup_steps: str
    key_modules: str
    data_flow: str
    run_tests: str
    gotchas: str

class ComparisonReport(BaseModel):
    repo1_name: str
    repo2_name: str
    debt_score_1: int
    debt_score_2: int
    risk_score_1: int
    risk_score_2: int
    test_coverage_1: float
    test_coverage_2: float
    total_deps_1: int
    total_deps_2: int
    languages_1: Dict[str, int]
    languages_2: Dict[str, int]
    winner: str
    verdict: str

# --- Internal Helper ---

async def _get_full_analysis(github_url: str, branch: Optional[str] = None):
    path = await git_service.clone_repo(github_url, branch)
    try:
        summary_task = analysis_service.analyze_structure(path)
        tech_debt_task = analysis_service.find_tech_debt(path)
        deps_task = dep_service.audit_dependencies(path)
        sec_task = sec_service.detect_security_smells(path)
        
        summary, debt, deps, sec = await asyncio.gather(
            summary_task, tech_debt_task, deps_task, sec_task
        )
        
        # Calculate scores
        # Syncing formula with UI: TODOs(2), Complex(5), LongFiles(5), LongFunctions(3)
        debt_score = min(100, (debt["todo_count"] * 2) + (len(debt["complex_functions"]) * 5) + (len(debt["long_files"]) * 5) + (len(debt.get("long_functions", [])) * 3))
        debt_grade = "A" if debt_score <= 20 else "B" if debt_score <= 40 else "C" if debt_score <= 60 else "D" if debt_score <= 80 else "F"
        debt["debt_score"] = debt_score
        debt["debt_grade"] = debt_grade

        return path, summary, debt, deps, sec
    except Exception as e:
        if path:
            git_service.cleanup(path)
        error_msg = str(e)
        # Sanitize error: Hide local system paths in MCP tool output
        if "tmp_repos" in error_msg or ":" in error_msg:
             error_msg = "An internal analysis error occurred. Local file system paths have been redacted for security."
        raise RuntimeError(error_msg)

# --- Tools ---

@mcp.tool()
async def analyze_repo(github_url: str, branch: Optional[str] = None) -> RepoSummary:
    """Analyze basic repository structure and metadata."""
    path, summary, debt, deps, sec = await _get_full_analysis(github_url, branch)
    git_service.cleanup(path)
    
    parts = github_url.rstrip("/").split("/")
    repo_name = parts[-1]
    
    return RepoSummary(
        repo_name=repo_name,
        description="Analyzed via Codebase Archaeologist",
        stars=0, # Would need deeper API call
        languages=summary["languages"],
        total_files=summary["total_files"],
        total_lines=summary["total_lines"],
        estimated_test_coverage_pct=(summary["test_files_count"] / max(1, summary["total_files"])) * 100,
        entry_points=summary["entry_points"],
        top_level_structure=summary["top_level"],
        size_kb=0 # Placeholder
    )

@mcp.tool()
async def find_tech_debt(github_url: str, branch: Optional[str] = None) -> TechDebtReport:
    """Identify TODOs, complexity hotspots, and code smells."""
    path, summary, debt, deps, sec = await _get_full_analysis(github_url, branch)
    git_service.cleanup(path)
    return TechDebtReport(**debt)

@mcp.tool()
async def audit_dependencies(github_url: str, branch: Optional[str] = None) -> DependencyReport:
    """Check for vulnerable and outdated dependencies using OSV and PyPI."""
    path, summary, debt, deps, sec = await _get_full_analysis(github_url, branch)
    git_service.cleanup(path)
    return DependencyReport(ecosystem="Mixed/PyPI", **deps)

@mcp.tool()
async def detect_security_smells(github_url: str, branch: Optional[str] = None) -> SecurityReport:
    """Scan for hardcoded secrets, SQLi, and dangerous function calls."""
    path, summary, debt, deps, sec = await _get_full_analysis(github_url, branch)
    git_service.cleanup(path)
    return SecurityReport(**sec)

@mcp.tool()
async def estimate_refactor_effort(github_url: str, target: str, branch: Optional[str] = None) -> EffortEstimate:
    """Predict the time and effort required for a specific refactor target."""
    path, summary, debt, deps, sec = await _get_full_analysis(github_url, branch)
    git_service.cleanup(path)
    # Add coverage to summary for service
    summary["estimated_test_coverage_pct"] = (summary["test_files_count"] / max(1, summary["total_files"])) * 100
    res = effort_service.estimate_effort(summary, debt, target)
    return EffortEstimate(**res)

@mcp.tool()
async def generate_onboarding_guide(github_url: str, branch: Optional[str] = None) -> OnboardingGuide:
    """Generate a markdown onboarding guide for new developers."""
    path, summary, debt, deps, sec = await _get_full_analysis(github_url, branch)
    guide = onboarding_service.generate_guide(path, summary)
    git_service.cleanup(path)
    return OnboardingGuide(**guide)

@mcp.tool()
async def compare_repos(repo1_url: str, repo2_url: str) -> ComparisonReport:
    """Side-by-side comparison of two codebases based on quality and risk."""
    t1 = _get_full_analysis(repo1_url)
    t2 = _get_full_analysis(repo2_url)
    (p1, s1, d1, dp1, sc1), (p2, s2, d2, dp2, sc2) = await asyncio.gather(t1, t2)
    
    git_service.cleanup(p1)
    git_service.cleanup(p2)

    winner = repo1_url if d1["debt_score"] < d2["debt_score"] else repo2_url
    
    return ComparisonReport(
        repo1_name=repo1_url.split("/")[-1],
        repo2_name=repo2_url.split("/")[-1],
        debt_score_1=d1["debt_score"],
        debt_score_2=d2["debt_score"],
        risk_score_1=dp1["risk_score"],
        risk_score_2=dp2["risk_score"],
        test_coverage_1=(s1["test_files_count"] / max(1, s1["total_files"])) * 100,
        test_coverage_2=(s2["test_files_count"] / max(1, s2["total_files"])) * 100,
        total_deps_1=dp1["total_deps"],
        total_deps_2=dp2["total_deps"],
        languages_1=s1["languages"],
        languages_2=s2["languages"],
        winner=winner,
        verdict=f"Selected {winner} as the more mature codebase based on lower tech debt score."
    )

if __name__ == "__main__":
    mcp.run()

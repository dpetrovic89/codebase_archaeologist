from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class EffortService:
    def estimate_effort(self, repo_summary: Dict[str, Any], tech_debt: Dict[str, Any], target: str) -> Dict[str, Any]:
        """Calculates deterministic effort estimate based on code metrics."""
        total_files = repo_summary.get("total_files", 0)
        total_lines = repo_summary.get("total_lines", 0)
        debt_score = tech_debt.get("debt_score", 0)
        current_coverage = repo_summary.get("estimated_test_coverage_pct", 0) / 100
        js_file_count = repo_summary.get("languages", {}).get(".js", 0)
        
        # Complexity multiplier (derived from complex functions count)
        complex_count = len(tech_debt.get("complex_functions", []))
        complexity_multiplier = 1.0 + (complex_count / max(1, total_files)) * 2.0
        
        effort_days = 0
        risks = []
        steps = []
        confidence = "MEDIUM"

        target = target.lower()
        if "test coverage 80%" in target:
            effort_days = int((0.8 - current_coverage) * total_files * 0.3 * complexity_multiplier)
            effort_days = max(1, effort_days)
            risks.append("Low existing test base increases discovery time")
            steps = ["Identify critical paths", "Setup jest/pytest", "Mock external APIs", "Write unit tests", "Verify coverage"]
        
        elif "typescript migration" in target:
            effort_days = int(js_file_count * 0.5 * complexity_multiplier)
            effort_days = max(1, effort_days)
            risks.append("Implicit 'any' types in legacy JS")
            steps = ["Initialize tsconfig", "Rename .js to .ts", "Fix compiler errors", "Add type definitions", "Enable strict mode"]
            
        elif "docker" in target:
            effort_days = max(1, int(total_files * 0.05 + 2))
            steps = ["Create Dockerfile", "Setup .dockerignore", "Build image", "Test container", "Optimize layers"]
            
        else:
            # Generic estimate
            effort_days = int((total_lines / 500) * (1 + debt_score/100))
            effort_days = max(1, effort_days)
            steps = ["Research requirements", "Identify dependencies", "Implementation phase", "Testing", "Review"]

        return {
            "target": target,
            "effort_days": effort_days,
            "confidence": "HIGH" if effort_days < 10 else "MEDIUM" if effort_days < 30 else "LOW",
            "affected_file_count": total_files,
            "risks": risks,
            "suggested_first_steps": steps[:5],
            "complexity_multiplier": round(complexity_multiplier, 2)
        }

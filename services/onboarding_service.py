import os
from typing import Dict, Any

class OnboardingService:
    def generate_guide(self, repo_path: str, repo_summary: Dict[str, Any]) -> Dict[str, str]:
        """Generates onboarding guide based on repository files and structure."""
        guide = {
            "setup_steps": "No specific setup found.",
            "key_modules": "Project structure: " + ", ".join(repo_summary.get("top_level", [])[:10]),
            "data_flow": "Entry points detected: " + ", ".join(repo_summary.get("entry_points", [])),
            "run_tests": "No test framework detected.",
            "gotchas": "Ensure all dependencies are installed."
        }

        # Setup steps
        if "README.md" in os.listdir(repo_path):
            with open(os.path.join(repo_path, "README.md"), 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
                if "install" in content or "setup" in content:
                    guide["setup_steps"] = "Instructions found in README.md"

        # Key Modules
        src_dirs = [d for d in os.listdir(repo_path) if os.path.isdir(os.path.join(repo_path, d)) and d in ("src", "app", "lib", "pkg", "cmd")]
        if src_dirs:
            guide["key_modules"] = f"Main code is located in: " + ", ".join(src_dirs)

        # Tests
        ci_dirs = [".github", ".circleci", ".travis.yml"]
        if any(os.path.exists(os.path.join(repo_path, d)) for d in ci_dirs):
             guide["run_tests"] = "CI/CD configuration detected. Check CI workflows for test commands."

        return guide

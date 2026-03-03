import os
import re
import json
import asyncio
from typing import List, Dict, Any

class SecurityService:
    def __init__(self):
        self.secret_pattern = re.compile(r"(?i)(api_key|secret|password|token)\s*=\s*[\"'][^\"']{8,}[\"']")
        self.sqli_pattern = re.compile(r"(SELECT|INSERT|UPDATE|DELETE).*\+")
        self.dangerous_py_pattern = re.compile(r"eval\(|exec\(|pickle\.loads\(|yaml\.load\([^,)]*\)")

    async def detect_security_smells(self, repo_path: str) -> Dict[str, Any]:
        """Runs regex scans and Bandit analysis."""
        findings = []
        scanned_files_count = 0

        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.env', '.yml', '.yaml')):
                    scanned_files_count += 1
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            lines = content.splitlines()
                            
                            for i, line in enumerate(lines):
                                # Secrets
                                if self.secret_pattern.search(line):
                                    findings.append({
                                        "file": rel_path,
                                        "line": i + 1,
                                        "issue": "Potential hardcoded secret",
                                        "severity": "HIGH"
                                    })
                                # SQLi
                                if self.sqli_pattern.search(line):
                                    findings.append({
                                        "file": rel_path,
                                        "line": i + 1,
                                        "issue": "Potential SQL injection pattern",
                                        "severity": "MEDIUM"
                                    })
                                # Dangerous Python
                                if file.endswith('.py') and self.dangerous_py_pattern.search(line):
                                    findings.append({
                                        "file": rel_path,
                                        "line": i + 1,
                                        "issue": "Dangerous function usage (eval/exec/pickle)",
                                        "severity": "HIGH"
                                    })
                    except:
                        pass

        # Bandit Scan
        bandit_res = await self._run_bandit(repo_path)
        findings.extend(bandit_res["findings"])
        
        high_count = sum(1 for f in findings if f["severity"] == "HIGH")
        medium_count = sum(1 for f in findings if f["severity"] == "MEDIUM")

        risk = "LOW"
        if high_count > 0:
            risk = "CRITICAL"
        elif medium_count >= 3:
            risk = "HIGH"
        elif medium_count > 0:
            risk = "MEDIUM"

        return {
            "findings": findings[:50], # Cap findings
            "bandit_high_count": bandit_res["high_count"],
            "bandit_medium_count": bandit_res["medium_count"],
            "overall_risk": risk,
            "scanned_files_count": scanned_files_count
        }

    async def _run_bandit(self, path: str) -> Dict[str, Any]:
        """Runs Bandit via subprocess."""
        res = {"findings": [], "high_count": 0, "medium_count": 0}
        try:
            cmd = ["bandit", "-r", path, "-f", "json", "-q"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Add 60s timeout to prevent hanging on massive repos
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=60.0)
            except asyncio.TimeoutError:
                process.kill()
                return res
                
            if stdout:
                data = json.loads(stdout)
                for issue in data.get("results", []):
                    severity = issue.get("issue_severity")
                    if severity in ("HIGH", "MEDIUM"):
                        if severity == "HIGH": res["high_count"] += 1
                        else: res["medium_count"] += 1
                        
                        res["findings"].append({
                            "file": os.path.relpath(issue.get("filename"), path),
                            "line": issue.get("line_number"),
                            "issue": issue.get("issue_text"),
                            "severity": severity
                        })
        except:
            pass
        return res

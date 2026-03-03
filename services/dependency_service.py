import httpx
import asyncio
from typing import List, Dict, Any, Optional
import os
import json

class DependencyService:
    def __init__(self):
        self.osv_url = "https://api.osv.dev/v1/query"
        self.pypi_url = "https://pypi.org/pypi/{package}/json"

    async def audit_dependencies(self, repo_path: str) -> Dict[str, Any]:
        """Parses dependency files and checks OSV and PyPI."""
        deps = self._parse_deps(repo_path)
        if not deps:
            return {
                "total_deps": 0, 
                "vulnerable_deps": [], 
                "outdated_deps": [], 
                "safe_deps_count": 0,
                "risk_score": 0
            }

        tasks = []
        for pkg_info in deps:
            tasks.append(self._check_package(pkg_info))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        report = {
            "total_deps": len(deps),
            "vulnerable_deps": [],
            "outdated_deps": [],
            "safe_deps_count": 0,
            "risk_score": 0
        }

        for res in results:
            if isinstance(res, dict):
                if res.get("vulnerabilities"):
                    report["vulnerable_deps"].append(res)
                if res.get("is_outdated"):
                    report["outdated_deps"].append(res)
                if not res.get("vulnerabilities") and not res.get("is_outdated"):
                    report["safe_deps_count"] += 1

        # Calculate risk score (simplified)
        risk = (len(report["vulnerable_deps"]) * 40) + (len(report["outdated_deps"]) * 10)
        report["risk_score"] = min(100, risk)
        
        return report

    def _parse_deps(self, repo_path: str) -> List[Dict[str, str]]:
        """Basic parser for requirements.txt and package.json. Returns list of {name, ecosystem, version}"""
        deps = []
        # Requirements.txt
        req_path = os.path.join(repo_path, "requirements.txt")
        if os.path.exists(req_path):
            with open(req_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Basic split for == or >=
                        pkg = re.split(r'[=><~]', line)[0].strip()
                        deps.append({"name": pkg, "ecosystem": "PyPI", "version": "unknown"})

        # package.json
        pkg_json = os.path.join(repo_path, "package.json")
        if os.path.exists(pkg_json):
            try:
                with open(pkg_json, 'r') as f:
                    data = json.load(f)
                    all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    for pkg, ver in all_deps.items():
                        # Clean version (e.g. ^1.2.3 -> 1.2.3)
                        ver = ver.lstrip('^~')
                        deps.append({"name": pkg, "ecosystem": "npm", "version": ver})
            except:
                pass
        
        return deps

    async def _check_package(self, pkg_info: Dict[str, str]) -> Dict[str, Any]:
        """Checks a single package for vulnerabilities and updates."""
        pkg = pkg_info["name"]
        ecosystem = pkg_info["ecosystem"]
        version = pkg_info["version"]
        
        info = {"name": pkg, "version": version, "vulnerabilities": [], "is_outdated": False}
        
        async with httpx.AsyncClient() as client:
            # OSV Check
            try:
                osv_payload = {"package": {"name": pkg, "ecosystem": ecosystem}}
                response = await client.post(self.osv_url, json=osv_payload, timeout=5.0)
                if response.status_code == 200:
                    vulns = response.json().get("vulns", [])
                    for v in vulns:
                        info["vulnerabilities"].append({
                            "id": v.get("id"),
                            "summary": v.get("summary")
                        })
            except:
                pass

            # PyPI Check (only for Python)
            if ecosystem == "PyPI":
                try:
                    pypi_res = await client.get(self.pypi_url.format(package=pkg), timeout=5.0)
                    if pypi_res.status_code == 200:
                        data = pypi_res.json()
                        latest = data["info"]["version"]
                        info["latest_version"] = latest
                        if version != "unknown" and version != latest:
                            info["is_outdated"] = True
                except:
                    pass

        return info

import re

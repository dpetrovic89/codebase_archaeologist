import os
import re
import ast
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from radon.complexity import cc_visit

class TodoItem(BaseModel):
    file: str
    line: int
    content: str

class ComplexFunction(BaseModel):
    file: str
    name: str
    complexity: int

class LongFile(BaseModel):
    file: str
    lines: int

class AnalysisService:
    def __init__(self):
        self.todo_pattern = re.compile(r"TODO|FIXME|HACK|XXX")
        self.secret_pattern = re.compile(r"(?i)(api_key|secret|password|token)\s*=\s*[\"'][^\"']{8,}[\"']")
        self.sqli_pattern = re.compile(r"(SELECT|INSERT|UPDATE|DELETE).*\+")
        self.dangerous_py_pattern = re.compile(r"eval\(|exec\(|pickle\.loads\(|yaml\.load\([^,)]*\)")

    async def analyze_structure(self, repo_path: str) -> Dict[str, Any]:
        """Counts files, lines, and identifies languages/entry points."""
        stats = {
            "total_files": 0,
            "total_lines": 0,
            "languages": {},
            "entry_points": [],
            "test_files_count": 0,
            "top_level": []
        }
        
        entry_point_names = {"main.py", "index.js", "app.py", "manage.py", "server.py"}

        for root, dirs, files in os.walk(repo_path):
            if ".git" in dirs:
                dirs.remove(".git")
            
            # Top level structure
            if root == repo_path:
                stats["top_level"] = files + dirs

            for file in files:
                stats["total_files"] += 1
                ext = os.path.splitext(file)[1].lower()
                if ext:
                    stats["languages"][ext] = stats["languages"].get(ext, 0) + 1
                
                if file in entry_point_names:
                    stats["entry_points"].append(os.path.relpath(os.path.join(root, file), repo_path))

                if "test_" in file or "_test" in file:
                    stats["test_files_count"] += 1

                # Line count (text files)
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        stats["total_lines"] += len(lines)
                except:
                    pass

        return stats

    async def find_tech_debt(self, repo_path: str) -> Dict[str, Any]:
        """Scans for TODOs, complexity, and long files."""
        report = {
            "todo_count": 0,
            "todo_examples": [],
            "complex_functions": [],
            "long_files": [],
            "long_functions": [],
            "missing_docstrings_count": 0
        }

        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.go', '.java', '.cpp', '.c', '.rs')):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            lines = content.splitlines()
                            
                            # TODO scan
                            for i, line in enumerate(lines):
                                if self.todo_pattern.search(line):
                                    report["todo_count"] += 1
                                    if len(report["todo_examples"]) < 20:
                                        report["todo_examples"].append({
                                            "file": rel_path,
                                            "line": i + 1,
                                            "content": line.strip()
                                        })

                            # Long files
                            if len(lines) > 500:
                                report["long_files"].append({"file": rel_path, "lines": len(lines)})

                            # Python specific (AST and Radon)
                            if file.endswith('.py'):
                                self._analyze_python_file(content, rel_path, report)
                    except:
                        pass
        
        return report

    def _analyze_python_file(self, content: str, rel_path: str, report: Dict[str, Any]):
        try:
            # Radon Complexity
            blocks = cc_visit(content)
            for block in blocks:
                if block.complexity > 10:
                    report["complex_functions"].append({
                        "file": rel_path,
                        "name": block.name,
                        "complexity": block.complexity
                    })

            # AST for missing docstrings and long functions
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Missing docstring
                    if not ast.get_docstring(node):
                        report["missing_docstrings_count"] += 1
                    
                    # Long function (estimated)
                    line_count = node.end_lineno - node.lineno
                    if line_count > 50:
                        report["long_functions"].append({
                            "file": rel_path,
                            "name": node.name,
                            "lines": line_count
                        })
        except:
            pass

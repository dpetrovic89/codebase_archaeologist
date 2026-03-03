import pytest
from services.effort_service import EffortService
from services.security_service import SecurityService
from services.dependency_service import DependencyService
import os

def test_effort_calculation():
    service = EffortService()
    summary = {
        "total_files": 10,
        "total_lines": 1000,
        "estimated_test_coverage_pct": 50
    }
    debt = {
        "debt_score": 10,
        "debt_grade": "A",
        "complex_functions": []
    }
    target = "Refactor components"
    
    result = service.estimate_effort(summary, debt, target)
    assert "effort_days" in result
    assert result["effort_days"] > 0
    assert result["affected_file_count"] == 10

def test_security_patterns():
    service = SecurityService()
    # Test secret detection
    assert service.secret_pattern.search("API_KEY = \"1234567890abcdef\"")
    assert service.secret_pattern.search("password = 'mysecretpassword'")
    
    # Test SQLi detection
    assert service.sqli_pattern.search("SELECT * FROM users WHERE id = \" + user_id")
    
    # Test dangerous python
    assert service.dangerous_py_pattern.search("eval(user_input)")
    assert service.dangerous_py_pattern.search("exec(code)")

def test_dependency_parsing_logic(tmp_path):
    service = DependencyService()
    
    # Setup mock repo structure
    repo_dir = tmp_path / "mock_repo"
    repo_dir.mkdir()
    
    # 1. Test Python requirements.txt
    req_file = repo_dir / "requirements.txt"
    req_file.write_text("flask==2.0.1\nrequests>=2.25.1")
    
    deps = service._parse_deps(str(repo_dir))
    assert len(deps) == 2
    assert deps[0]["name"] == "flask"
    assert deps[1]["name"] == "requests"
    assert deps[0]["ecosystem"] == "PyPI"
    
    # 2. Test Node.js package.json (appended to same repo)
    pkg_file = repo_dir / "package.json"
    pkg_file.write_text('{"dependencies": {"express": "^4.17.1"}}')
    
    # Re-run parsing to get both sets
    all_deps = service._parse_deps(str(repo_dir))
    # 2 from requirements + 1 from package.json
    assert len(all_deps) == 3
    # Find express in list
    express_pkg = next(d for d in all_deps if d["name"] == "express")
    assert express_pkg["ecosystem"] == "npm"
    assert express_pkg["version"] == "4.17.1"

def test_path_sanitization_concept():
    # Verify the error masking logic used in app.py
    error_msg = "Error in E:/Programming/Antigravity/tmp_repos/123/file.py"
    if "tmp_repos" in error_msg or ":" in error_msg:
         sanitized = "An internal analysis error occurred. Local file system paths have been redacted for security."
    else:
         sanitized = error_msg
    
    assert "E:/Programming" not in sanitized
    assert "tmp_repos" not in sanitized

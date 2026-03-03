import os
import shutil
import uuid
import httpx
import asyncio
import stat
from typing import Optional
import git

class GitService:
    def __init__(self, base_temp_dir: Optional[str] = None):
        if base_temp_dir:
            self.base_temp_dir = base_temp_dir
        else:
            # Better cross-platform temp directory
            self.base_temp_dir = os.path.join(os.getcwd(), "tmp_repos")
            
        if not os.path.exists(self.base_temp_dir):
            os.makedirs(self.base_temp_dir)

    async def check_repo_size(self, repo_url: str) -> int:
        """Checks the size of the repository via the GitHub API."""
        import httpx
        import os
        
        repo_url = repo_url.strip()
        if not ("github.com" in repo_url.lower()):
            raise ValueError("Unsupported provider. Currently only GitHub repositories are supported.")
            
        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            raise ValueError("Invalid GitHub URL.")
        
        owner, repo = parts[-2], parts[-1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(api_url, headers=headers)
                if response.status_code == 404:
                    raise ValueError(f"Repository not found: {repo_url}")
                elif response.status_code == 403:
                    if "rate limit" in response.text.lower():
                        raise RuntimeError("GitHub API Rate Limit exceeded. Please set GITHUB_TOKEN to increase limits.")
                    raise RuntimeError(f"GitHub API Access Denied (403): {response.text}")
                
                response.raise_for_status()
                data = response.json()
                return data.get("size", 0)
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"GitHub API error: {e.response.status_code}")
            except Exception as e:
                raise RuntimeError(f"Could not verify repository size: {str(e)}")

    async def clone_repo(self, repo_url: str, branch: Optional[str] = None) -> str:
        """Shallow clones a repo to a temporary directory. Returns the path."""
        repo_id = str(uuid.uuid4())
        target_dir = os.path.join(self.base_temp_dir, repo_id)

        # Check size first
        size_kb = await self.check_repo_size(repo_url)
        if size_kb > 51200: # 50MB
            raise ValueError(f"Repository size ({size_kb} KB) exceeds the 50MB limit.")

        try:
            # Clone arguments
            clone_args = {
                "url": repo_url,
                "to_path": target_dir,
                "depth": 1
            }
            if branch:
                clone_args["branch"] = branch

            # Shallow clone - Capture repo object and close it immediately
            repo = await asyncio.to_thread(
                git.Repo.clone_from, 
                **clone_args
            )
            # Explicitly close repo to release file handles on Windows
            repo.close()
            return target_dir
        except Exception as e:
            if os.path.exists(target_dir):
                self.cleanup(target_dir)
            raise RuntimeError(f"Clone failed: {str(e)}")

    def cleanup(self, path: str):
        """Removes the cloned repository directory, handling read-only files and retrying on Windows."""
        import time

        def remove_readonly(func, path, excinfo):
            os.chmod(path, stat.S_IWRITE)
            func(path)

        if os.path.exists(path) and path.startswith(self.base_temp_dir):
            # Try cleanup up to 3 times with a small delay for file handles to release
            for i in range(3):
                try:
                    shutil.rmtree(path, onerror=remove_readonly)
                    break
                except Exception:
                    if i == 2: # Last try
                        # Log or ignore? For now, we've tried our best
                        pass
                    time.sleep(0.5)

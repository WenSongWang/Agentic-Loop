from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class WorktreeInfo:
    path: Path
    branch: str


class WorktreeManager:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.base_dir = self.repo_root / ".agentic-loop" / "worktrees"

    def create(self, *, prefix: str = "agent") -> WorktreeInfo:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        branch = f"{prefix}/{uuid.uuid4().hex[:8]}"
        path = self.base_dir / branch.replace("/", "-")
        subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(path)],
            cwd=str(self.repo_root),
            check=True,
            capture_output=True,
            text=True,
        )
        return WorktreeInfo(path=path, branch=branch)

    def remove(self, info: WorktreeInfo) -> None:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(info.path)],
            cwd=str(self.repo_root),
            check=False,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "branch", "-D", info.branch],
            cwd=str(self.repo_root),
            check=False,
            capture_output=True,
            text=True,
        )

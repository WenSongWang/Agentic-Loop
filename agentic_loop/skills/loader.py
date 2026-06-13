from __future__ import annotations

from pathlib import Path


class SkillLoader:
    def __init__(self, cwd: Path, state_dir: Path) -> None:
        self.cwd = cwd
        self.search_dirs = [
            state_dir / "skills",
            cwd / "skills",
            cwd / ".agentic-loop" / "skills",
        ]

    def _find_skill_file(self, name: str) -> Path | None:
        for base in self.search_dirs:
            direct = base / name / "SKILL.md"
            if direct.is_file():
                return direct
            flat = base / f"{name}.md"
            if flat.is_file():
                return flat
        return None

    def load_skill(self, name: str) -> str:
        path = self._find_skill_file(name)
        if not path:
            raise ValueError(
                f"Skill '{name}' not found. Expected SKILL.md under one of: "
                + ", ".join(str(d / name) for d in self.search_dirs)
            )
        return path.read_text(encoding="utf-8").strip()

    def list_skills(self) -> list[str]:
        names: set[str] = set()
        for base in self.search_dirs:
            if not base.exists():
                continue
            for path in base.rglob("SKILL.md"):
                names.add(path.parent.name)
            for path in base.glob("*.md"):
                names.add(path.stem)
        return sorted(names)

    def default_system_prompt(self) -> str | None:
        parts: list[str] = []
        for name in self.list_skills():
            try:
                parts.append(self.load_skill(name))
            except ValueError:
                continue
        return "\n\n".join(parts) if parts else None

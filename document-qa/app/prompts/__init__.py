"""Prompt loader: reads PROMPTS_DIR, renders templates, computes prompt_version.

Prompts are plain *.md files with `$name` placeholders (string.Template). They ship
inside the image and can be overridden per environment by mounting a ConfigMap and
pointing PROMPTS_DIR at it. Every prompt carries a content hash (`version`) that is
recorded with each answer, in traces and in metrics, so quality changes can be
correlated with prompt changes.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from string import Template


@dataclass(frozen=True)
class Prompt:
    name: str
    text: str
    version: str

    def render(self, **variables: str) -> str:
        """Substitute placeholders; a missing variable raises KeyError (fail loud)."""
        return Template(self.text).substitute(variables)


def _digest(*texts: str) -> str:
    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:12]


class PromptRegistry:
    def __init__(self, directory: Path) -> None:
        if not directory.is_dir():
            raise FileNotFoundError(f"PROMPTS_DIR {directory} does not exist")
        self.directory = directory
        self._prompts: dict[str, Prompt] = {}
        for path in sorted(directory.glob("*.md")):
            text = path.read_text(encoding="utf-8").strip()
            self._prompts[path.stem] = Prompt(name=path.stem, text=text, version=_digest(text))

    def get(self, name: str) -> Prompt:
        try:
            return self._prompts[name]
        except KeyError:
            raise KeyError(f"Prompt {name!r} not found in {self.directory}") from None

    def require(self, *names: str) -> None:
        """Fail fast at startup if an override directory is missing a prompt."""
        for name in names:
            self.get(name)

    def version_of(self, *names: str) -> str:
        """Combined version for a set of prompts used together in one call."""
        return _digest(*(self.get(n).text for n in names))

"""Prompt loading, rendering and prompt_version stability."""

from pathlib import Path

import pytest

from app.config import DEFAULT_PROMPTS_DIR
from app.prompts import PromptRegistry
from tests.conftest import MakeClient


def test_bundled_prompts_load_and_render() -> None:
    reg = PromptRegistry(DEFAULT_PROMPTS_DIR)
    text = reg.get("answer_user").render(context="[1] c", history="(none)", question="q?")
    assert "Question: q?" in text


def test_missing_variable_fails_loudly() -> None:
    reg = PromptRegistry(DEFAULT_PROMPTS_DIR)
    with pytest.raises(KeyError):
        reg.get("answer_user").render(question="q?")


def test_version_is_content_hash(tmp_path: Path) -> None:
    (tmp_path / "p.md").write_text("hello $name")
    v1 = PromptRegistry(tmp_path).get("p").version
    assert v1 == PromptRegistry(tmp_path).get("p").version  # stable
    (tmp_path / "p.md").write_text("hello there $name")
    assert PromptRegistry(tmp_path).get("p").version != v1  # changes with content


def test_override_dir_must_contain_required_prompts(
    tmp_path: Path, make_client: MakeClient
) -> None:
    (tmp_path / "answer_system.md").write_text("Only system.")
    with pytest.raises(KeyError, match="answer_user"):
        make_client(prompts_dir=tmp_path)


def test_override_dir_changes_prompt_version(tmp_path: Path, make_client: MakeClient) -> None:
    for name in ("answer_system", "answer_user"):
        text = (DEFAULT_PROMPTS_DIR / f"{name}.md").read_text()
        (tmp_path / f"{name}.md").write_text(text + "\nBe concise.")
    default = make_client()
    custom = make_client(prompts_dir=tmp_path)
    for c in (default, custom):
        c.post("/documents", json={"text": "A pod runs containers."})
    v_default = default.post("/ask", json={"question": "What runs containers?"}).json()
    v_custom = custom.post("/ask", json={"question": "What runs containers?"}).json()
    assert v_default["prompt_version"] != v_custom["prompt_version"]

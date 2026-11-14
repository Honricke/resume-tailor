import json
import pytest

from resume_tailor import config, pipeline, prompts
from resume_tailor.cli import main
from resume_tailor.refine import parse_rating, refine
from resume_tailor.schema import InvalidResume, extract_json

RESUME = {
    "basics": {"name": "A", "email": "a@a.com", "summary": "s"},
    "work": [{"name": "X", "position": "Dev", "startDate": "2020", "endDate": "Present", "highlights": ["h"]}],
    "education": [], "skills": [], "certificates": [],
}
FENCED = "```json\n" + json.dumps(RESUME) + "\n```"


def test_parse_rating():
    assert parse_rating("blah\nFINAL_RATING: 8,5") == 8.5
    assert parse_rating("FINAL_RATING: 11") is None
    assert parse_rating("no rating") is None


def test_extract_json_and_validation():
    assert extract_json("text " + FENCED)["basics"]["name"] == "A"
    with pytest.raises(InvalidResume):
        extract_json("no json here")
    bad = dict(RESUME, work=[])
    with pytest.raises(InvalidResume):
        extract_json("```json\n" + json.dumps(bad) + "\n```")


def _run_refine(ratings, enabled=True, target=8.5, max_rev=3):
    it, calls = iter(ratings), {"rev": 0}
    state = {"v": 0}
    def evaluate(): return f"FINAL_RATING: {next(it)}"
    def revise(_): calls["rev"] += 1; state["v"] += 1
    res = refine(evaluate, revise, lambda: state["v"], lambda s: state.update(v=s), target, max_rev, enabled)
    return res, calls["rev"], state["v"]


def test_refine_disabled_evaluates_once():
    res, revs, _ = _run_refine([6], enabled=False)
    assert (res.stop_reason, revs) == ("single_evaluation", 0)


def test_refine_target_and_limits():
    assert _run_refine([6, 9])[0].stop_reason == "target_reached"
    res, revs, _ = _run_refine([5, 6, 7, 7.5], max_rev=2)
    assert (res.stop_reason, revs) == ("max_revisions", 2)


def test_refine_no_improvement_restores_best():
    res, _, version = _run_refine([6, 5])
    assert res.stop_reason == "no_improvement" and res.restored and version == 0 and res.best_rating == 6


def test_config_precedence(monkeypatch):
    monkeypatch.setenv("RESUME_TARGET", "9")
    monkeypatch.setenv("RESUME_MAX_REVISIONS", "5")
    monkeypatch.setenv("RESUME_REFINE", "1")
    cfg = config.resolve(None, None, None)
    assert (cfg.refine, cfg.target, cfg.max_revisions) == (True, 9.0, 5)
    cfg = config.resolve(True, 7.0, 1)
    assert (cfg.target, cfg.max_revisions) == (7.0, 1)
    monkeypatch.delenv("RESUME_TARGET"); monkeypatch.delenv("RESUME_MAX_REVISIONS"); monkeypatch.delenv("RESUME_REFINE")
    cfg = config.resolve(None, None, None)
    assert (cfg.refine, cfg.target, cfg.max_revisions) == (False, 8.5, 1)


def _fake_ask(rating_cycle):
    ratings = iter(rating_cycle)
    log = []
    def ask(system, prompt, model):
        if system == prompts.HIRING_MANAGER_SYSTEM:
            log.append("hm"); return f"eval\nFINAL_RATING: {next(ratings)}"
        log.append("strat" if system == prompts.STRATEGIST_SYSTEM else "edit")
        return FENCED + "\n\n## Coverage audit\nX: ok"
    return ask, log


def test_pipeline_default_no_loop(tmp_path):
    ask, log = _fake_ask([6, 7])
    cfg = config.Config(refine=False, target=8.5, max_revisions=3, model=None)
    res = pipeline.run("truth", "job", "en", cfg, tmp_path, ask)
    assert log == ["strat", "hm", "edit"]
    assert (tmp_path / "resume.json").exists()
    assert not (tmp_path / "coverage_review.md").exists()
    assert "draft" in (tmp_path / "rating_report.md").read_text()


def test_pipeline_refine_keeps_audit(tmp_path):
    ask, log = _fake_ask([6, 9])
    cfg = config.Config(refine=True, target=8.5, max_revisions=3, model=None)
    pipeline.run("truth", "job", "en", cfg, tmp_path, ask)
    assert log == ["strat", "hm", "edit", "hm"]
    assert (tmp_path / "coverage_review.md").read_text().startswith("## Coverage audit")
    assert "## Coverage audit" in (tmp_path / "rating_report.md").read_text()


def test_pipeline_retries_invalid_json_once(tmp_path):
    replies = iter(["not json", FENCED])
    def ask(system, prompt, model):
        if system == prompts.STRATEGIST_SYSTEM: return next(replies)
        if system == prompts.HIRING_MANAGER_SYSTEM: return "FINAL_RATING: 9"
        if system == prompts.EDITOR_SYSTEM: return FENCED + "\n## Coverage audit\nok"
        return "report"
    cfg = config.Config(False, 8.5, 3, None)
    pipeline.run("t", "j", "en", cfg, tmp_path, ask)
    assert (tmp_path / "resume.json").exists()


def test_cli_input_errors_before_model(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        main(["--person", "x", "--lang", "fr"])
    assert "Supported: pt-BR, en" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        main(["--person", "x"])
    assert "profile_truth.md" in capsys.readouterr().err


def test_render_pdf(tmp_path):
    from resume_tailor.render import render
    resume = dict(RESUME, basics={**RESUME["basics"], "summary": "R&D <b> à é ç ã"})
    pdf = render(resume, tmp_path)
    assert pdf.exists() and pdf.read_bytes().startswith(b"%PDF")


def test_usage_accumulates():
    from types import SimpleNamespace
    from resume_tailor.agent import Usage
    u = Usage()
    msg = SimpleNamespace(usage={"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 2}, total_cost_usd=0.01)
    u.add(msg)
    u.add(msg)
    assert (u.calls, u.input_tokens, u.output_tokens, u.cache_tokens) == (2, 20, 10, 4)
    assert "$0.0200" in u.summary()


def test_hiring_manager_follow_up_sees_previous_evaluation():
    from resume_tailor import prompts
    first = prompts.hiring_manager_prompt("job", {}, "truth")
    follow = prompts.hiring_manager_prompt("job", {}, "truth", previous="OLD EVAL FINAL_RATING: 8.0")
    assert "OLD EVAL" not in first and "OLD EVAL" in follow
    assert "[FIXABLE]" in first

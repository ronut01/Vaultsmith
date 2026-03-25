from __future__ import annotations

import json
from pathlib import Path

from vaultsmith import cli
from vaultsmith import app as app_module
from vaultsmith.app import build_context


def write_session(vault: Path, session_id: str, **overrides: object) -> None:
    ctx = build_context(vault)
    directory = ctx.sessions_dir / session_id
    directory.mkdir(parents=True, exist_ok=True)
    session = {
        "session_id": session_id,
        "agent": "codex",
        "mode": "chat",
        "status": "detached",
        "tmux_session": f"vsm-{session_id}",
        "approved": False,
        "created_at": "2026-03-25T00:00:00+00:00",
        "updated_at": "2026-03-25T00:00:00+00:00",
    }
    session.update(overrides)
    (directory / "session.json").write_text(json.dumps(session), encoding="utf-8")


def write_changes(vault: Path, session_id: str, operations: list[dict[str, object]], **extra: object) -> None:
    ctx = build_context(vault)
    directory = ctx.sessions_dir / session_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {"operations": operations}
    payload.update(extra)
    (directory / "changes.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_proposal(vault: Path, session_id: str, content: str) -> None:
    ctx = build_context(vault)
    directory = ctx.sessions_dir / session_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "proposal.md").write_text(content, encoding="utf-8")


def write_receipt(vault: Path, session_id: str, content: str) -> None:
    ctx = build_context(vault)
    directory = ctx.sessions_dir / session_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "receipt.md").write_text(content, encoding="utf-8")


def test_setup_creates_expected_layout(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)

    exit_code = cli.main(["setup", "vault"])

    assert exit_code == 0
    vault = tmp_path / "vault"
    assert (vault / ".vaultsmith" / "config.toml").exists()
    assert (vault / ".vaultsmith" / "roles" / "input-agent.md").exists()
    assert (vault / ".vaultsmith" / "memory" / "vault-summary.md").exists()
    assert (vault / "AGENTS.md").exists()
    assert (vault / "CLAUDE.md").exists()
    assert "Vaultsmith initialized" in capsys.readouterr().out


def test_setup_preserves_existing_bootstrap_files(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "AGENTS.md").write_text("keep me\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = cli.main(["setup", str(vault)])

    assert exit_code == 0
    assert (vault / "AGENTS.md").read_text(encoding="utf-8") == "keep me\n"
    output = capsys.readouterr().out
    assert "Preserved existing AGENTS.md" in output
    assert (vault / ".vaultsmith" / "instructions" / "codex.md").exists()


def test_status_uses_active_session_when_id_is_omitted(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    ctx = build_context(vault)
    write_session(vault, "session-123", request="정리해줘")
    write_proposal(vault, "session-123", "# Proposal\n\n- update note\n")
    ctx.active_session_path.write_text("session-123\n", encoding="utf-8")
    monkeypatch.chdir(vault)

    exit_code = cli.main(["status"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Session: session-123" in output
    assert "Runtime: stopped" in output
    assert "Request: 정리해줘" in output
    assert "Proposal: yes" in output


def test_chat_uses_current_vault_and_detaches(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    monkeypatch.chdir(vault)

    calls: list[tuple[Path, str, str | None, bool, str]] = []

    def fake_launch(ctx, *, agent, request, attach, mode):
        calls.append((ctx.root, agent, request, attach, mode))
        session = {
            "session_id": "abc123",
            "agent": agent,
            "mode": mode,
            "status": "detached",
        }
        return session, None

    monkeypatch.setattr(cli, "launch_tmux_session", fake_launch)

    exit_code = cli.main(["chat", "--detach"])

    assert exit_code == 0
    assert calls == [(vault, "codex", None, False, "chat")]
    assert "Started session abc123 with codex" in capsys.readouterr().out


def test_run_requires_request(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    monkeypatch.chdir(vault)

    exit_code = cli.main(["run"])

    assert exit_code == 1
    assert "A request is required" in capsys.readouterr().err


def test_run_accepts_request_without_explicit_path(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    monkeypatch.chdir(vault)

    calls: list[tuple[Path, str, str | None, bool, str]] = []

    def fake_launch(ctx, *, agent, request, attach, mode):
        calls.append((ctx.root, agent, request, attach, mode))
        session = {
            "session_id": "run123",
            "agent": agent,
            "mode": mode,
            "status": "waiting-review",
        }
        return session, "captured output"

    monkeypatch.setattr(cli, "launch_tmux_session", fake_launch)

    exit_code = cli.main(["run", "--", "현재", "정리", "안", "된", "노트", "정리해줘"])

    assert exit_code == 0
    assert calls == [(vault, "codex", "현재 정리 안 된 노트 정리해줘", True, "run")]
    output = capsys.readouterr().out
    assert "Started one-shot session run123 with codex" in output
    assert "Monitor progress with `vsm status` or `vsm tail`." in output


def test_run_accepts_optional_path_prefix(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])

    calls: list[tuple[Path, str, str | None, bool, str]] = []

    def fake_launch(ctx, *, agent, request, attach, mode):
        calls.append((ctx.root, agent, request, attach, mode))
        session = {
            "session_id": "run456",
            "agent": agent,
            "mode": mode,
            "status": "waiting-review",
        }
        return session, None

    monkeypatch.setattr(cli, "launch_tmux_session", fake_launch)

    exit_code = cli.main(["run", str(vault), "현재", "정리", "안", "된", "노트", "정리해줘"])

    assert exit_code == 0
    assert calls == [(vault, "codex", "현재 정리 안 된 노트 정리해줘", True, "run")]


def test_run_detach_keeps_background_behavior(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    monkeypatch.chdir(vault)

    calls: list[tuple[Path, str, str | None, bool, str]] = []

    def fake_launch(ctx, *, agent, request, attach, mode):
        calls.append((ctx.root, agent, request, attach, mode))
        session = {
            "session_id": "run-detach",
            "agent": agent,
            "mode": mode,
            "status": "running",
        }
        return session, "captured output"

    monkeypatch.setattr(cli, "launch_tmux_session", fake_launch)

    exit_code = cli.main(["run", "--detach", "--", "현재", "정리", "안", "된", "노트", "정리해줘"])

    assert exit_code == 0
    assert calls == [(vault, "codex", "현재 정리 안 된 노트 정리해줘", False, "run")]
    output = capsys.readouterr().out
    assert "Latest tmux output:" in output


def test_run_defaults_to_attached_interactive_flow(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    monkeypatch.chdir(vault)

    calls: list[tuple[Path, str, str | None, bool, str]] = []

    def fake_launch(ctx, *, agent, request, attach, mode):
        calls.append((ctx.root, agent, request, attach, mode))
        session = {
            "session_id": "trust123",
            "agent": agent,
            "mode": mode,
            "status": "awaiting-trust",
        }
        return session, "> trust prompt"

    monkeypatch.setattr(cli, "launch_tmux_session", fake_launch)

    exit_code = cli.main(["run", "--", "현재", "정리", "안", "된", "노트", "정리해줘"])

    assert exit_code == 0
    assert calls == [(vault, "codex", "현재 정리 안 된 노트 정리해줘", True, "run")]
    output = capsys.readouterr().out
    assert "Started one-shot session trust123 with codex" in output
    assert "Latest tmux output" not in output


def test_launch_tmux_session_survives_missing_capture(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    ctx = build_context(vault)

    commands: list[list[str]] = []

    def fake_run_subprocess(args, *, cwd=None, capture_output=True, check=True):
        commands.append(args)

        class Result:
            stdout = ""

        return Result()

    monkeypatch.setattr(app_module, "tmux_available", lambda: True)
    monkeypatch.setattr(app_module, "agent_available", lambda agent: True)
    monkeypatch.setattr(app_module, "run_subprocess", fake_run_subprocess)
    monkeypatch.setattr(app_module, "capture_tmux_output", lambda ctx, session_name, scroll="-200": None)
    monkeypatch.setattr(app_module, "runtime_state", lambda ctx, session: "running")

    session, captured = app_module.launch_tmux_session(
        ctx,
        agent="codex",
        request="정리해줘",
        attach=False,
        mode="run",
        wait_seconds=0,
    )

    assert session["status"] == "running"
    assert captured is None
    assert any(args[:3] == ["tmux", "new-session", "-d"] for args in commands)


def test_launch_tmux_session_marks_awaiting_trust_when_prompt_detected(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    ctx = build_context(vault)

    commands: list[list[str]] = []

    def fake_run_subprocess(args, *, cwd=None, capture_output=True, check=True):
        commands.append(args)

        class Result:
            stdout = ""

        return Result()

    monkeypatch.setattr(app_module, "tmux_available", lambda: True)
    monkeypatch.setattr(app_module, "agent_available", lambda agent: True)
    monkeypatch.setattr(app_module, "run_subprocess", fake_run_subprocess)
    monkeypatch.setattr(
        app_module,
        "capture_tmux_output",
        lambda ctx, session_name, scroll="-200": (
            "> You are in /tmp/demo\n\nDo you trust the contents of this directory?"
        ),
    )

    session, captured = app_module.launch_tmux_session(
        ctx,
        agent="codex",
        request="정리해줘",
        attach=False,
        mode="run",
        wait_seconds=0,
    )

    assert session["status"] == "awaiting-trust"
    assert "Do you trust the contents of this directory?" in (captured or "")


def test_agent_command_sanitizes_codex_env_and_embeds_prompt(monkeypatch) -> None:
    monkeypatch.setenv("CODEX_THREAD_ID", "thread-123")
    monkeypatch.setenv("CODEX_CI", "1")
    monkeypatch.setenv("OMX_TEAM_STATE_ROOT", "/tmp/omx")

    command, embedded = app_module.agent_command("codex", "BOOTSTRAP", "정리해줘")

    assert embedded is True
    assert command[:2] == ["env", "-u"]
    assert "CODEX_THREAD_ID" in command
    assert "CODEX_CI" in command
    assert "OMX_TEAM_STATE_ROOT" in command
    assert command[-2] == "codex"
    assert command[-1] == "BOOTSTRAP\n\nUser request:\n정리해줘"


def test_alias_enable_and_disable_use_configurable_bin_dir(tmp_path: Path, monkeypatch, capsys) -> None:
    bin_dir = tmp_path / "bin"
    monkeypatch.setenv("VSM_ALIAS_BIN_DIR", str(bin_dir))

    exit_code = cli.main(["alias", "enable", "vs"])
    assert exit_code == 0
    shim = bin_dir / "vs"
    assert shim.exists()
    assert shim.read_text(encoding="utf-8") == "#!/bin/sh\nexec vsm \"$@\"\n"

    exit_code = cli.main(["alias", "disable", "vs"])
    assert exit_code == 0
    assert not shim.exists()
    output = capsys.readouterr().out
    assert "Enabled alias `vs`" in output
    assert "Disabled alias `vs`" in output


def test_apply_without_approval_fails_for_active_session(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    ctx = build_context(vault)
    write_session(vault, "session-apply")
    write_proposal(vault, "session-apply", "# Proposal\n\nApply me\n")
    ctx.active_session_path.write_text("session-apply\n", encoding="utf-8")
    monkeypatch.chdir(vault)

    exit_code = cli.main(["apply"])

    assert exit_code == 1
    assert "no approved changes yet" in capsys.readouterr().err


def test_sessions_marks_active_session(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    ctx = build_context(vault)
    write_session(vault, "a-session")
    write_session(vault, "b-session", status="waiting-review")
    ctx.active_session_path.write_text("b-session\n", encoding="utf-8")
    monkeypatch.chdir(vault)

    exit_code = cli.main(["sessions"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "* b-session" in output
    assert "a-session" in output


def test_review_shows_proposal_markdown(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    ctx = build_context(vault)
    write_session(vault, "session-review")
    write_proposal(
        vault,
        "session-review",
        "# Proposal\n\nSummary: Update the note title\n\n- Edit `Inbox/note.md`\n- Rename `raw.md` to `Archive/raw.md`\n",
    )
    ctx.active_session_path.write_text("session-review\n", encoding="utf-8")
    monkeypatch.chdir(vault)

    exit_code = cli.main(["review"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Review for session session-review" in output
    assert "Summary: Update the note title" in output
    assert "Rename `raw.md` to `Archive/raw.md`" in output


def test_tail_uses_active_session_when_id_is_omitted(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    ctx = build_context(vault)
    write_session(vault, "session-tail")
    ctx.active_session_path.write_text("session-tail\n", encoding="utf-8")
    monkeypatch.chdir(vault)

    monkeypatch.setattr(cli, "tail_session", lambda context, session_id, lines=120: f"tail for {session_id or 'active'} {lines}")

    exit_code = cli.main(["tail"])

    assert exit_code == 0
    assert "tail for active 120" in capsys.readouterr().out


def test_approve_and_apply_dispatches_agent_with_proposal(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    ctx = build_context(vault)
    write_session(vault, "session-approve")
    write_proposal(
        vault,
        "session-approve",
        "# Proposal\n\n- Create `Inbox/new-note.md`\n- Rename `Old/old-name.md` to `Archive/renamed-note.md`\n",
    )
    ctx.active_session_path.write_text("session-approve\n", encoding="utf-8")
    monkeypatch.chdir(vault)

    calls: list[tuple[Path, str, str]] = []

    def fake_dispatch(context, session, prompt):
        calls.append((context.root, session["session_id"], prompt))

    monkeypatch.setattr(cli, "approve_session", cli.approve_session)
    monkeypatch.setattr("vaultsmith.app.dispatch_agent_instruction", fake_dispatch)

    approve_exit = cli.main(["approve"])
    apply_exit = cli.main(["apply"])

    assert approve_exit == 0
    assert apply_exit == 0
    assert calls
    assert calls[0][0] == vault
    assert calls[0][1] == "session-approve"
    assert "Apply the approved Vaultsmith proposal now." in calls[0][2]
    assert "receipt.md" in calls[0][2]
    approval_note = ctx.sessions_dir / "session-approve" / "approval.md"
    assert approval_note.exists()
    output = capsys.readouterr().out
    assert "Approved the current proposal for session session-approve" in output
    assert "Dispatched apply request for session session-approve" in output


def test_status_reports_change_and_approval_state(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    ctx = build_context(vault)
    write_session(vault, "session-status", approved=True, applied=False)
    write_proposal(vault, "session-status", "# Proposal\n\n- Touch `Inbox/test.md`\n")
    ctx.active_session_path.write_text("session-status\n", encoding="utf-8")
    monkeypatch.chdir(vault)

    exit_code = cli.main(["status"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Runtime: stopped" in output
    assert "Proposal: yes" in output
    assert "Receipt: no" in output
    assert "Approved: yes" in output
    assert "Applied: no" in output


def test_status_marks_applied_when_receipt_exists(tmp_path: Path, monkeypatch, capsys) -> None:
    vault = tmp_path / "vault"
    cli.main(["setup", str(vault)])
    ctx = build_context(vault)
    write_session(vault, "session-receipt", approved=True, applied=False, status="applying")
    write_proposal(vault, "session-receipt", "# Proposal\n\n- apply\n")
    write_receipt(vault, "session-receipt", "# Receipt\n\nApplied.\n")
    ctx.active_session_path.write_text("session-receipt\n", encoding="utf-8")
    monkeypatch.chdir(vault)

    exit_code = cli.main(["status"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Runtime: stopped" in output
    assert "Receipt: yes" in output
    assert "Applied: yes" in output

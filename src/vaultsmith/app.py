from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import textwrap
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROLE_PROMPTS = {
    "input-agent.md": """
    # Input Agent

    You are the primary interface for the user. Receive the request directly,
    decide whether any supporting agent is actually necessary, and keep the
    response grounded in the vault's actual conventions.

    Speed rules:
    - Default to direct work.
    - Spawn no sub-agent for simple vault-only edits.
    - Spawn at most 1 helper for vault-only work, or 2 parallel helpers when a
      vault scan and an external lookup are both required.
    - Keep proposals concise and action-oriented.
    """,
    "vault-analyst.md": """
    # Vault Analyst

    Inspect the vault only as much as needed to infer how the user titles,
    files, structures, and links notes. Report evidence, not guesses.

    Start with `.vaultsmith/memory/vault-summary.md` if it exists.
    Do not scan the whole vault unless local evidence is still insufficient.
    """,
    "research-scout.md": """
    # Research Scout

    Fetch external information when the request depends on links, web pages, or
    other outside material. Summarize only the evidence needed by the Input Agent.

    Keep the report under 8 bullets unless the task is explicitly deep research.
    """,
    "draft-agent.md": """
    # Draft Agent

    Produce the proposed note or vault change using the conventions discovered
    in the vault and the context gathered by other agents.

    Prefer minimal edits over broad rewrites. Keep the proposal short.
    """,
    "consistency-reviewer.md": """
    # Consistency Reviewer

    Review the draft against the user's existing vault habits. Flag mismatches,
    missing links, odd placement, or formatting drift before anything is applied.

    Skip this pass entirely if the change is a trivial move/rename with clear evidence.
    """,
}

INSTRUCTION_DOCS = {
    "codex.md": """
    # Vaultsmith Codex Bootstrap

    When you are inside this vault, use Vaultsmith as the session launcher and
    coordinator.

    Workflow:
    1. Treat the user's raw input as the task source. Do not rewrite it before planning.
    2. Read `.vaultsmith/memory/vault-summary.md` first if it exists.
    3. Default to direct execution. Only delegate if the task clearly benefits.
    4. For vault-only work, use at most 1 helper. For mixed vault + external work, use at most 2 helpers in parallel.
    5. Keep changes review-first unless the user explicitly asks otherwise.

    Speed and token rules:
    - Do not do a full-vault survey for simple requests.
    - Prefer the smallest set of candidate files that can answer the task.
    - Keep `proposal.md` under 8 bullets and `receipt.md` under 6 bullets.
    - Prefer moving, renaming, or lightly editing files over rewriting large notes.

    Obsidian CLI rules:
    - If the `obsidian` CLI is available and usable, prefer it for vault-aware actions.
    - Prefer `obsidian rename` over raw shell rename operations when renaming notes.
    - Prefer `obsidian create`, `obsidian read`, and `obsidian search` over generic shell commands when they fit the task.
    - Consider `obsidian move` for relocation when it behaves correctly in the current vault, but keep direct file operations as the safe fallback.
    - If the `obsidian` CLI is unavailable or a command fails, fall back to direct file operations.
    """,
    "claude.md": """
    # Vaultsmith Claude Bootstrap

    Use Vaultsmith's role split when operating in this vault.

    Roles:
    - Input Agent: user-facing coordinator
    - Vault Analyst: infer vault conventions from existing notes
    - Research Scout: inspect links and external sources
    - Draft Agent: generate the proposed note or update
    - Consistency Reviewer: compare the proposal against vault habits

    Speed rules:
    - Read `.vaultsmith/memory/vault-summary.md` first if it exists.
    - Default to direct work.
    - Use at most 1 helper for vault-only work, or 2 for mixed vault + external work.
    - Keep `proposal.md` and `receipt.md` terse.

    Obsidian CLI rules:
    - If the `obsidian` CLI is available and usable, prefer it for vault-aware actions.
    - Prefer `obsidian rename` over raw shell rename operations when renaming notes.
    - Prefer `obsidian create`, `obsidian read`, and `obsidian search` over generic shell commands when they fit the task.
    - Consider `obsidian move` for relocation when it behaves correctly in the current vault, but keep direct file operations as the safe fallback.
    - If the `obsidian` CLI is unavailable or a command fails, fall back to direct file operations.
    """,
}


@dataclass(slots=True)
class VaultContext:
    root: Path
    state_dir: Path
    sessions_dir: Path
    roles_dir: Path
    memory_dir: Path
    instructions_dir: Path
    config_path: Path
    active_session_path: Path


class VaultsmithError(RuntimeError):
    """Raised when a user-facing command cannot continue."""


AGENT_ENV_PREFIXES = ("CODEX_", "OMX_", "CLAUDE_", "OPENAI_", "ANTHROPIC_")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_context(root: Path) -> VaultContext:
    state_dir = root / ".vaultsmith"
    return VaultContext(
        root=root,
        state_dir=state_dir,
        sessions_dir=state_dir / "sessions",
        roles_dir=state_dir / "roles",
        memory_dir=state_dir / "memory",
        instructions_dir=state_dir / "instructions",
        config_path=state_dir / "config.toml",
        active_session_path=state_dir / "active-session",
    )


def find_vault_root(start: Path) -> Path | None:
    current = start.resolve()
    candidates = [current, *current.parents]
    for candidate in candidates:
        state_dir = candidate / ".vaultsmith"
        if state_dir.is_dir() and (state_dir / "config.toml").exists():
            return candidate
    return None


def resolve_vault(path_arg: str | None, cwd: Path) -> VaultContext:
    if path_arg:
        root = Path(path_arg).expanduser().resolve()
        if not root.exists():
            raise VaultsmithError(f"Vault path does not exist: {root}")
        return build_context(root)

    discovered = find_vault_root(cwd)
    if discovered is None:
        raise VaultsmithError(
            "Could not find a configured vault from the current directory. "
            "Run `vsm setup <path>` first or pass an explicit path."
        )
    return build_context(discovered)


def ensure_state_dirs(ctx: VaultContext) -> None:
    for directory in (
        ctx.state_dir,
        ctx.sessions_dir,
        ctx.roles_dir,
        ctx.memory_dir,
        ctx.instructions_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def write_role_prompts(ctx: VaultContext) -> None:
    for name, content in ROLE_PROMPTS.items():
        write_if_missing(ctx.roles_dir / name, content)


def write_instruction_docs(ctx: VaultContext) -> None:
    for name, content in INSTRUCTION_DOCS.items():
        write_if_missing(ctx.instructions_dir / name, content)


def write_memory_files(ctx: VaultContext) -> None:
    write_if_missing(
        ctx.memory_dir / "vault-summary.md",
        """
        # Vault Summary

        Keep this file short and update it only when you discover a durable vault rule.

        Suggested sections:
        - dominant note families
        - folder placement rules
        - naming patterns
        - formatting habits
        - links/tags/frontmatter conventions
        - recent exceptions worth remembering
        """,
    )


def write_config(ctx: VaultContext, default_agent: str = "codex") -> None:
    if ctx.config_path.exists():
        return
    content = textwrap.dedent(
        f"""
        vault_root = "{ctx.root}"
        default_agent = "{default_agent}"
        write_policy = "review-first"
        created_at = "{now_iso()}"
        """
    ).strip() + "\n"
    ctx.config_path.write_text(content, encoding="utf-8")


def setup_vault(path_arg: str, cwd: Path) -> str:
    root = Path(path_arg).expanduser()
    if not root.is_absolute():
        root = (cwd / root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    ctx = build_context(root)
    ensure_state_dirs(ctx)
    write_role_prompts(ctx)
    write_instruction_docs(ctx)
    write_memory_files(ctx)
    write_config(ctx)
    return "\n".join(
        [
            f"Vaultsmith initialized at {ctx.root}",
            "Use `vsm chat` from inside the vault to start an agent session.",
        ]
    )


def read_default_agent(ctx: VaultContext) -> str:
    if not ctx.config_path.exists():
        return "codex"
    for line in ctx.config_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("default_agent"):
            _, _, raw = line.partition("=")
            return raw.strip().strip('"')
    return "codex"


def generate_session_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def session_path(ctx: VaultContext, session_id: str) -> Path:
    return ctx.sessions_dir / session_id / "session.json"


def session_dir(ctx: VaultContext, session_id: str) -> Path:
    return ctx.sessions_dir / session_id


def changes_path(ctx: VaultContext, session_id: str) -> Path:
    return session_dir(ctx, session_id) / "changes.json"


def proposal_path(ctx: VaultContext, session_id: str) -> Path:
    return session_dir(ctx, session_id) / "proposal.md"


def approval_path(ctx: VaultContext, session_id: str) -> Path:
    return session_dir(ctx, session_id) / "approval.md"


def receipt_path(ctx: VaultContext, session_id: str) -> Path:
    return session_dir(ctx, session_id) / "receipt.md"


def save_session(ctx: VaultContext, session: dict[str, Any]) -> None:
    directory = session_dir(ctx, session["session_id"])
    directory.mkdir(parents=True, exist_ok=True)
    session["updated_at"] = now_iso()
    session_path(ctx, session["session_id"]).write_text(
        json.dumps(session, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_session(ctx: VaultContext, session_id: str) -> dict[str, Any]:
    path = session_path(ctx, session_id)
    if not path.exists():
        raise VaultsmithError(f"Unknown session: {session_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_changes(ctx: VaultContext, session_id: str) -> dict[str, Any]:
    path = changes_path(ctx, session_id)
    if not path.exists():
        raise VaultsmithError(
            f"Session {session_id} has no proposed changes yet. "
            "Store them in `.vaultsmith/sessions/<session-id>/changes.json` first."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    operations = payload.get("operations")
    if not isinstance(operations, list) or not operations:
        raise VaultsmithError(f"Session {session_id} has no operations in changes.json")
    return payload


def load_proposal(ctx: VaultContext, session_id: str) -> str:
    path = proposal_path(ctx, session_id)
    if not path.exists():
        raise VaultsmithError(
            f"Session {session_id} has no proposal yet. "
            "The agent should write `.vaultsmith/sessions/<session-id>/proposal.md` first."
        )
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise VaultsmithError(f"Session {session_id} has an empty proposal.md")
    return content


def list_sessions(ctx: VaultContext) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    if not ctx.sessions_dir.exists():
        return sessions
    for path in sorted(ctx.sessions_dir.glob("*/session.json"), reverse=True):
        sessions.append(json.loads(path.read_text(encoding="utf-8")))
    return sessions


def get_active_session_id(ctx: VaultContext) -> str | None:
    if not ctx.active_session_path.exists():
        return None
    value = ctx.active_session_path.read_text(encoding="utf-8").strip()
    return value or None


def set_active_session(ctx: VaultContext, session_id: str) -> None:
    ctx.active_session_path.write_text(f"{session_id}\n", encoding="utf-8")


def resolve_session_id(ctx: VaultContext, session_id: str | None) -> str:
    if session_id:
        return session_id
    active = get_active_session_id(ctx)
    if active:
        return active
    sessions = list_sessions(ctx)
    if not sessions:
        raise VaultsmithError("No active session and no previous sessions found.")
    raise VaultsmithError(
        "No active session is set. Run `vsm sessions` and retry with a session id."
    )


def run_subprocess(
    args: list[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=check,
        text=True,
        capture_output=capture_output,
    )


def tmux_available() -> bool:
    return shutil.which("tmux") is not None


def agent_available(agent: str) -> bool:
    return shutil.which(agent) is not None


def obsidian_cli_available() -> bool:
    return shutil.which("obsidian") is not None


def obsidian_cli_guidance() -> str:
    if obsidian_cli_available():
        availability = (
            "- The `obsidian` CLI is available on PATH in this environment. Check whether it is "
            "usable for the current action before falling back."
        )
    else:
        availability = (
            "- The `obsidian` CLI was not detected on PATH in this environment. Use shell/file "
            "operations unless you explicitly confirm it is available another way."
        )
    return textwrap.dedent(
        f"""
        Obsidian CLI rules:
        {availability}
        - Prefer `obsidian rename` over raw shell rename operations when renaming notes, because
          Obsidian can keep internal links consistent.
        - Prefer `obsidian create`, `obsidian read`, and `obsidian search` for note creation,
          retrieval, and search when those commands fit the task.
        - Consider `obsidian move` for relocation when it behaves correctly in the current vault,
          but keep direct file operations as the safe fallback.
        - If an `obsidian` command is unavailable, unsupported, or fails, fall back to direct file
          edits and shell commands.
        """
    ).strip()


def agent_command(agent: str, bootstrap_prompt: str, request: str | None) -> tuple[list[str], bool]:
    unset_vars: list[str] = []
    for key in os.environ:
        if key.startswith(AGENT_ENV_PREFIXES):
            unset_vars.extend(["-u", key])

    env_prefix = ["env", *unset_vars]

    if agent == "codex":
        prompt = bootstrap_prompt
        if request:
            prompt = f"{bootstrap_prompt}\n\nUser request:\n{request}"
        return [*env_prefix, "codex", prompt], True

    return [*env_prefix, agent], False


def tmux_session_exists(session_name: str, ctx: VaultContext) -> bool:
    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        cwd=str(ctx.root),
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def capture_tmux_output(ctx: VaultContext, session_name: str, *, scroll: str = "-200") -> str | None:
    result = subprocess.run(
        ["tmux", "capture-pane", "-p", "-t", session_name, "-S", scroll],
        cwd=str(ctx.root),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    return text or None


def runtime_state(ctx: VaultContext, session: dict[str, Any]) -> str:
    if tmux_session_exists(session["tmux_session"], ctx):
        return "running"
    return "stopped"


def launch_tmux_session(
    ctx: VaultContext,
    *,
    agent: str,
    request: str | None,
    attach: bool,
    mode: str,
    wait_seconds: float = 2.0,
) -> tuple[dict[str, Any], str | None]:
    if not tmux_available():
        raise VaultsmithError("tmux is required but not installed.")
    if not agent_available(agent):
        raise VaultsmithError(f"Agent binary not found on PATH: {agent}")

    session_id = generate_session_id()
    tmux_session = f"vsm-{session_id}"
    bootstrap_prompt = textwrap.dedent(
        f"""
        Vaultsmith session {session_id}
        Session workspace: .vaultsmith/sessions/{session_id}/
        Role split:
        - Input Agent
        - Vault Analyst
        - Research Scout
        - Draft Agent
        - Consistency Reviewer
        Rules:
        - Read `.vaultsmith/memory/vault-summary.md` first if it exists.
        - Default to direct work.
        - Use no helper for simple vault-only tasks, at most 1 helper for vault-only tasks,
          or 2 parallel helpers when both vault analysis and external lookup are required.
        - Do not survey the entire vault unless local evidence is insufficient.
        - Use review-first changes and inspect the vault before making style claims.
        - Before any user approval, do not modify vault files.
        - Write the proposed plan, target files, intended edits, and draft content to
          `.vaultsmith/sessions/{session_id}/proposal.md` in under 8 bullets.
        - After apply approval arrives, implement the approved proposal in the vault and
          write a concise execution receipt to `.vaultsmith/sessions/{session_id}/receipt.md`
          in under 6 bullets.

        {obsidian_cli_guidance()}
        """
    ).strip()
    launch_command, prompt_is_embedded = agent_command(agent, bootstrap_prompt, request)

    run_subprocess(
        ["tmux", "new-session", "-d", "-s", tmux_session, "-c", str(ctx.root), *launch_command],
        cwd=ctx.root,
    )
    run_subprocess(["tmux", "set-option", "-t", tmux_session, "remain-on-exit", "on"], cwd=ctx.root)
    if not prompt_is_embedded:
        run_subprocess(["tmux", "send-keys", "-t", tmux_session, bootstrap_prompt, "C-m"], cwd=ctx.root)
        if request:
            run_subprocess(["tmux", "send-keys", "-t", tmux_session, request, "C-m"], cwd=ctx.root)

    session = {
        "session_id": session_id,
        "agent": agent,
        "mode": mode,
        "request": request,
        "tmux_session": tmux_session,
        "status": "running" if attach else "detached",
        "approved": False,
        "applied": False,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    save_session(ctx, session)
    set_active_session(ctx, session_id)

    captured: str | None = None
    if mode == "run":
        time.sleep(wait_seconds)
        captured = capture_tmux_output(ctx, tmux_session)
        if captured and is_workspace_trust_prompt(captured):
            session["status"] = "awaiting-trust"
        else:
            session["status"] = "running" if runtime_state(ctx, session) == "running" else "exited"
        save_session(ctx, session)
        if attach:
            run_subprocess(["tmux", "attach-session", "-t", tmux_session], cwd=ctx.root, capture_output=False)
            session["status"] = "running" if runtime_state(ctx, session) == "running" else "exited"
            save_session(ctx, session)
    elif attach:
        run_subprocess(["tmux", "attach-session", "-t", tmux_session], cwd=ctx.root, capture_output=False)
        session["status"] = "attached"
        save_session(ctx, session)
    return session, captured


def is_workspace_trust_prompt(output: str) -> bool:
    return "Do you trust the contents of this directory?" in output


def attach_session(ctx: VaultContext, session_id: str) -> str:
    session = load_session(ctx, session_id)
    run_subprocess(["tmux", "attach-session", "-t", session["tmux_session"]], cwd=ctx.root, capture_output=False)
    session["status"] = "running" if runtime_state(ctx, session) == "running" else "exited"
    save_session(ctx, session)
    set_active_session(ctx, session_id)
    return f"Attached to session {session_id}"


def format_session(session: dict[str, Any], *, active_id: str | None) -> str:
    active_marker = "*" if session["session_id"] == active_id else " "
    request = session.get("request") or "-"
    proposal_marker = "proposal" if session.get("has_proposal") else "no-proposal"
    receipt_marker = "receipt" if session.get("has_receipt") else "no-receipt"
    return (
        f"{active_marker} {session['session_id']} "
        f"[{session['agent']}] [{session['status']}] "
        f"mode={session['mode']} {proposal_marker} {receipt_marker} request={request}"
    )


def status_text(ctx: VaultContext, session_id: str | None) -> str:
    resolved = resolve_session_id(ctx, session_id)
    session = load_session(ctx, resolved)
    has_proposal = proposal_path(ctx, resolved).exists()
    has_receipt = receipt_path(ctx, resolved).exists()
    runtime = runtime_state(ctx, session)
    session["has_proposal"] = has_proposal
    session["has_receipt"] = has_receipt
    session["runtime"] = runtime
    if has_receipt:
        session["applied"] = True
        session["status"] = "applied"
    save_session(ctx, session)
    lines = [
        f"Session: {session['session_id']}",
        f"Agent: {session['agent']}",
        f"Mode: {session['mode']}",
        f"Status: {session['status']}",
        f"Runtime: {runtime}",
        f"tmux: {session['tmux_session']}",
        f"Created: {session['created_at']}",
        f"Proposal: {'yes' if has_proposal else 'no'}",
        f"Receipt: {'yes' if has_receipt else 'no'}",
        f"Approved: {'yes' if session.get('approved') else 'no'}",
        f"Applied: {'yes' if session.get('applied') else 'no'}",
    ]
    if session.get("request"):
        lines.append(f"Request: {session['request']}")
    if not session.get("approved", False):
        lines.append("Apply status: waiting for approval")
    return "\n".join(lines)


def sessions_text(ctx: VaultContext) -> str:
    sessions = list_sessions(ctx)
    if not sessions:
        return "No sessions found."
    active = get_active_session_id(ctx)
    for session in sessions:
        session["has_proposal"] = proposal_path(ctx, session["session_id"]).exists()
        session["has_receipt"] = receipt_path(ctx, session["session_id"]).exists()
        if session["has_receipt"]:
            session["applied"] = True
            session["status"] = "applied"
    return "\n".join(format_session(session, active_id=active) for session in sessions)


def apply_session(ctx: VaultContext, session_id: str | None) -> str:
    resolved = resolve_session_id(ctx, session_id)
    session = load_session(ctx, resolved)
    if not session.get("approved"):
        raise VaultsmithError(
            f"Session {resolved} has no approved changes yet. Review the proposal before applying."
        )
    proposal = load_proposal(ctx, resolved)
    approval_note = approval_path(ctx, resolved)
    approval_note.write_text(
        textwrap.dedent(
            f"""
            # Approval

            Session: {resolved}
            Approved at: {now_iso()}

            The user approved the current proposal. Apply it directly to the vault now.
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    prompt = build_apply_prompt(ctx, session, proposal)
    dispatch_agent_instruction(ctx, session, prompt)
    session["status"] = "applying"
    session["applied"] = False
    session["apply_requested_at"] = now_iso()
    save_session(ctx, session)
    return (
        f"Dispatched apply request for session {resolved} to {session['agent']}.\n"
        f"Expected receipt: {receipt_path(ctx, resolved)}"
    )


def approve_session(ctx: VaultContext, session_id: str | None) -> str:
    resolved = resolve_session_id(ctx, session_id)
    session = load_session(ctx, resolved)
    load_proposal(ctx, resolved)
    session["approved"] = True
    session["approved_at"] = now_iso()
    if session.get("status") != "applied":
        session["status"] = "approved"
    save_session(ctx, session)
    approval_note = approval_path(ctx, resolved)
    approval_note.write_text(
        textwrap.dedent(
            f"""
            # Approval

            Session: {resolved}
            Approved at: {session['approved_at']}

            The current proposal has been approved and is ready for apply.
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return f"Approved the current proposal for session {resolved}"


def review_session(ctx: VaultContext, session_id: str | None) -> str:
    resolved = resolve_session_id(ctx, session_id)
    proposal = load_proposal(ctx, resolved)
    lines = [f"Review for session {resolved}", "", proposal]
    receipt = receipt_path(ctx, resolved)
    if receipt.exists():
        lines.extend(["", "---", "", "Existing receipt:", "", receipt.read_text(encoding="utf-8").strip()])
    return "\n".join(lines)


def build_apply_prompt(ctx: VaultContext, session: dict[str, Any], proposal: str) -> str:
    proposal_file = proposal_path(ctx, session["session_id"])
    receipt_file = receipt_path(ctx, session["session_id"])
    return textwrap.dedent(
        f"""
        Apply the approved Vaultsmith proposal now.

        Session: {session['session_id']}
        Read the approved proposal from `{proposal_file.relative_to(ctx.root)}`.

        Requirements:
        - Apply the proposal directly to the vault files now.
        - You may create, edit, move, rename, or delete files if the approved proposal calls for it.
        - Do not produce a new proposal instead of applying.
        - If you must deviate from the proposal, keep the deviation minimal and explain it.
        - When the `obsidian` CLI is available and the operation fits, prefer it for create, read,
          search, and rename actions.
        - Treat `obsidian move` as optional and use it only when it behaves correctly in the
          current vault.
        - If an `obsidian` command is unavailable, unsupported, or fails, fall back to direct file
          operations.
        - After applying, write `{receipt_file.relative_to(ctx.root)}` with:
          1. files touched
          2. actions performed
          3. deviations from the proposal, if any
          4. any follow-up risks

        Proposal snapshot:

        {proposal}
        """
    ).strip()


def dispatch_agent_instruction(ctx: VaultContext, session: dict[str, Any], prompt: str) -> None:
    if not tmux_available():
        raise VaultsmithError("tmux is required but not installed.")
    if not agent_available(session["agent"]):
        raise VaultsmithError(f"Agent binary not found on PATH: {session['agent']}")

    tmux_session = session["tmux_session"]
    if not tmux_session_exists(tmux_session, ctx):
        run_subprocess(
            ["tmux", "new-session", "-d", "-s", tmux_session, "-c", str(ctx.root), session["agent"]],
            cwd=ctx.root,
        )
        run_subprocess(["tmux", "set-option", "-t", tmux_session, "remain-on-exit", "on"], cwd=ctx.root)
    run_subprocess(["tmux", "send-keys", "-t", tmux_session, prompt, "C-m"], cwd=ctx.root)


def tail_session(ctx: VaultContext, session_id: str | None, *, lines: int = 120) -> str:
    resolved = resolve_session_id(ctx, session_id)
    session = load_session(ctx, resolved)
    output = capture_tmux_output(ctx, session["tmux_session"], scroll=f"-{lines}")
    state = runtime_state(ctx, session)
    if output is None:
        return (
            f"Session {resolved} runtime: {state}\n"
            "No tmux pane output is available."
        )
    return "\n".join(
        [
            f"Session {resolved} runtime: {state}",
            "",
            output,
        ]
    )


def alias_bin_dir() -> Path:
    override = os.environ.get("VSM_ALIAS_BIN_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".local" / "bin"


def alias_target(name: str) -> Path:
    return alias_bin_dir() / name


def enable_alias(name: str) -> str:
    destination = alias_target(name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("#!/bin/sh\nexec vsm \"$@\"\n", encoding="utf-8")
    destination.chmod(0o755)
    return f"Enabled alias `{name}` at {destination}"


def disable_alias(name: str) -> str:
    destination = alias_target(name)
    if destination.exists():
        destination.unlink()
        return f"Disabled alias `{name}`"
    return f"Alias `{name}` is not enabled"


def alias_status(name: str) -> str:
    destination = alias_target(name)
    if destination.exists():
        return f"Alias `{name}` -> {destination}"
    return f"Alias `{name}` is not enabled"


def suggest_agent(requested: str | None, ctx: VaultContext) -> str:
    return requested or read_default_agent(ctx)


def shell_join(args: list[str]) -> str:
    return " ".join(shlex.quote(arg) for arg in args)

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from vaultsmith.app import (
    VaultsmithError,
    alias_status,
    apply_session,
    approve_session,
    attach_session,
    enable_alias,
    launch_tmux_session,
    review_session,
    resolve_vault,
    sessions_text,
    setup_vault,
    status_text,
    suggest_agent,
    tail_session,
    disable_alias,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vsm",
        description="Vaultsmith agent launcher for Obsidian vault workflows.",
        epilog=(
            "Examples:\n"
            "  vsm setup ~/obsidian/MyVault\n"
            "  vsm chat\n"
            "  vsm run -- \"현재 정리 안 된 노트 정리해줘\"\n"
            "  vsm tail\n"
            "  vsm review\n"
            "  vsm approve\n"
            "  vsm status\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser("setup", help="Initialize Vaultsmith in a vault")
    setup_parser.add_argument("path", help="Path to the Obsidian vault")

    chat_parser = subparsers.add_parser("chat", help="Start an interactive agent session")
    chat_parser.add_argument("path", nargs="?", help="Vault path. Defaults to the current vault.")
    chat_parser.add_argument("--agent", choices=("codex", "claude"), help="Agent to launch")
    chat_parser.add_argument(
        "--detach",
        action="store_true",
        help="Leave the tmux session detached instead of attaching immediately.",
    )

    run_parser = subparsers.add_parser("run", help="Start a one-shot agent request")
    run_parser.add_argument("--agent", choices=("codex", "claude"), help="Agent to launch")
    run_parser.add_argument("--path", help="Vault path. Defaults to the current vault.")
    run_parser.add_argument(
        "--detach",
        action="store_true",
        help="Leave the one-shot run in the background instead of attaching immediately.",
    )
    run_parser.add_argument(
        "parts",
        nargs=argparse.REMAINDER,
        help="Request text, optionally prefixed with a vault path.",
    )

    resume_parser = subparsers.add_parser("resume", help="Attach to an existing session")
    resume_parser.add_argument("session_id", help="Vaultsmith session id")
    resume_parser.add_argument("path", nargs="?", help="Vault path. Defaults to the current vault.")

    status_parser = subparsers.add_parser("status", help="Show current or selected session status")
    status_parser.add_argument("session_id", nargs="?", help="Optional session id")
    status_parser.add_argument("--path", help="Vault path. Defaults to the current vault.")

    review_parser = subparsers.add_parser("review", help="Show the proposed changes for a session")
    review_parser.add_argument("session_id", nargs="?", help="Optional session id")
    review_parser.add_argument("--path", help="Vault path. Defaults to the current vault.")

    tail_parser = subparsers.add_parser("tail", help="Show recent tmux output for a session")
    tail_parser.add_argument("session_id", nargs="?", help="Optional session id")
    tail_parser.add_argument("--path", help="Vault path. Defaults to the current vault.")
    tail_parser.add_argument("--lines", type=int, default=120, help="How many lines to capture")

    approve_parser = subparsers.add_parser("approve", help="Approve a session's proposed changes")
    approve_parser.add_argument("session_id", nargs="?", help="Optional session id")
    approve_parser.add_argument("--path", help="Vault path. Defaults to the current vault.")

    sessions_parser = subparsers.add_parser("sessions", help="List recent sessions")
    sessions_parser.add_argument("path", nargs="?", help="Vault path. Defaults to the current vault.")

    apply_parser = subparsers.add_parser("apply", help="Apply approved changes for a session")
    apply_parser.add_argument("session_id", nargs="?", help="Optional session id")
    apply_parser.add_argument("--path", help="Vault path. Defaults to the current vault.")

    alias_parser = subparsers.add_parser("alias", help="Manage shorthand shell aliases")
    alias_subparsers = alias_parser.add_subparsers(dest="alias_command", required=True)

    alias_enable = alias_subparsers.add_parser("enable", help="Enable an alias such as `vs`")
    alias_enable.add_argument("name", nargs="?", default="vs")

    alias_disable = alias_subparsers.add_parser("disable", help="Disable an alias")
    alias_disable.add_argument("name", nargs="?", default="vs")

    alias_show = alias_subparsers.add_parser("status", help="Show alias status")
    alias_show.add_argument("name", nargs="?", default="vs")

    return parser


def normalize_request(parts: list[str]) -> str:
    pieces = list(parts)
    if pieces and pieces[0] == "--":
        pieces = pieces[1:]
    text = " ".join(pieces).strip()
    if not text:
        raise VaultsmithError("A request is required. Example: `vsm run -- \"정리해줘\"`")
    return text


def split_run_parts(parts: list[str], cwd: Path) -> tuple[str | None, str]:
    pieces = list(parts)
    if pieces and pieces[0] == "--":
        pieces = pieces[1:]
    if not pieces:
        raise VaultsmithError("A request is required. Example: `vsm run -- \"정리해줘\"`")

    if len(pieces) >= 2 and not pieces[0].startswith("-"):
        candidate = Path(pieces[0]).expanduser()
        if not candidate.is_absolute():
            candidate = (cwd / candidate).resolve()
        if candidate.exists():
            return str(candidate), " ".join(pieces[1:]).strip()

    request = " ".join(pieces).strip()
    if not request:
        raise VaultsmithError("A request is required. Example: `vsm run -- \"정리해줘\"`")
    return None, request


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cwd = Path.cwd()

    try:
        if args.command == "setup":
            print(setup_vault(args.path, cwd))
            return 0

        if args.command == "chat":
            ctx = resolve_vault(args.path, cwd)
            agent = suggest_agent(args.agent, ctx)
            session, _ = launch_tmux_session(
                ctx,
                agent=agent,
                request=None,
                attach=not args.detach,
                mode="chat",
            )
            print(f"Started session {session['session_id']} with {agent}")
            return 0

        if args.command == "run":
            inferred_path, request = split_run_parts(args.parts, cwd)
            ctx = resolve_vault(args.path or inferred_path, cwd)
            agent = suggest_agent(args.agent, ctx)
            session, captured = launch_tmux_session(
                ctx,
                agent=agent,
                request=request,
                attach=not args.detach,
                mode="run",
            )
            print(f"Started one-shot session {session['session_id']} with {agent}")
            print("Monitor progress with `vsm status` or `vsm tail`.")
            if args.detach and session["status"] == "awaiting-trust":
                print("Codex is waiting for workspace trust confirmation. Attaching now so you can choose.")
                print(attach_session(ctx, session["session_id"]))
                return 0
            if args.detach and captured:
                print("\nLatest tmux output:\n")
                print(captured)
            return 0

        if args.command == "resume":
            ctx = resolve_vault(args.path, cwd)
            print(attach_session(ctx, args.session_id))
            return 0

        if args.command == "status":
            ctx = resolve_vault(args.path, cwd)
            print(status_text(ctx, args.session_id))
            return 0

        if args.command == "review":
            ctx = resolve_vault(args.path, cwd)
            print(review_session(ctx, args.session_id))
            return 0

        if args.command == "tail":
            ctx = resolve_vault(args.path, cwd)
            print(tail_session(ctx, args.session_id, lines=args.lines))
            return 0

        if args.command == "approve":
            ctx = resolve_vault(args.path, cwd)
            print(approve_session(ctx, args.session_id))
            return 0

        if args.command == "sessions":
            ctx = resolve_vault(args.path, cwd)
            print(sessions_text(ctx))
            return 0

        if args.command == "apply":
            ctx = resolve_vault(args.path, cwd)
            print(apply_session(ctx, args.session_id))
            return 0

        if args.command == "alias":
            if args.alias_command == "enable":
                print(enable_alias(args.name))
                return 0
            if args.alias_command == "disable":
                print(disable_alias(args.name))
                return 0
            if args.alias_command == "status":
                print(alias_status(args.name))
                return 0

        parser.error(f"Unhandled command: {args.command}")
        return 2
    except VaultsmithError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

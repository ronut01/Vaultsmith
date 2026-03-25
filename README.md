# Vaultsmith

Vaultsmith is a local agent launcher for Obsidian vault workflows. It starts `codex` or `claude` inside `tmux`, seeds the vault with role prompts and bootstrap instructions, and keeps session state in `.vaultsmith/`.

## Quick start

```bash
python -m pip install -e .
vsm setup ~/obsidian/MyVault
cd ~/obsidian/MyVault
vsm chat
```

Useful commands:

```bash
vsm run -- "현재 정리 안 된 노트 정리해줘"
vsm review
vsm approve
vsm apply
vsm status
vsm tail
vsm sessions
vsm alias enable vs
```

## Review-first flow

Vaultsmith stores each session under `.vaultsmith/sessions/<session-id>/`.

- `session.json`: session metadata and approval state
- `proposal.md`: agent-authored review proposal
- `approval.md`: approval checkpoint written by `vsm approve`
- `receipt.md`: execution receipt written after apply

Recommended flow:

```bash
vsm run -- "강의 영상 링크 정리해줘"
vsm review
vsm approve
vsm apply
```

`vsm run` now attaches to the agent session by default so you can answer trust prompts and other interactive questions directly. For Codex, Vaultsmith starts a fresh session with the initial bootstrap and user request passed as the startup prompt, instead of typing into an already-running TUI. Use `vsm run --detach -- "..."` if you want background behavior.

`vsm apply` does not apply a structured patch itself. It re-dispatches the approved session to the underlying agent, which performs the vault edits and writes a `receipt.md` summary afterward.

To see whether a background session is still alive and what it is currently doing:

- `vsm status`
- `vsm tail`

If Codex asks whether it should trust the current directory, Vaultsmith now leaves that choice to you.
In that case `vsm run` will attach you to the tmux-backed Codex session automatically so you can choose directly.
You can also re-attach manually with:

```bash
vsm resume <session-id>
```

Choose in the attached Codex session, then continue monitoring with `vsm status` and `vsm tail`.

Example `proposal.md`:

```md
# Proposal

Summary: summarize the lecture and file it in the existing course folder.

Planned work:
- create `Courses/ML/Lecture 07.md`
- move `Inbox/ml-rough-notes.md` to `Archive/ml-rough-notes-2026-03-25.md`

Draft:
## Key Ideas
- ...
```

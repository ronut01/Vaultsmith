# Vaultsmith

[![CI](https://github.com/ronut01/Vaultsmith/actions/workflows/ci.yml/badge.svg)](https://github.com/ronut01/Vaultsmith/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/vaultsmith)](https://pypi.org/project/vaultsmith/)
[![License](https://img.shields.io/github/license/ronut01/Vaultsmith)](https://github.com/ronut01/Vaultsmith/blob/main/LICENSE)

**AI for Obsidian that works like the vault owner, not like a generic note bot.**

Vaultsmith is a local agent launcher and review-first workflow for Obsidian vaults. It sets up vault-local instructions, starts `codex` or `claude` inside `tmux`, and gives the agent a constrained operating surface so note creation and organization can stay consistent with how the vault already works.

## Why Vaultsmith exists

Most AI note tooling can generate text.

What it usually does badly:

- titles notes in a way that does not match the vault
- picks the wrong folder
- ignores linking habits and structure conventions
- rewrites too much when a small edit would do
- makes users manually clean up the result afterward

Vaultsmith exists to push the agent in the opposite direction:

- inspect the vault before making style claims
- prefer minimal edits over broad rewrites
- keep proposals short and reviewable
- treat vault conventions as a first-class constraint
- make approval explicit before applying edits

## What it does today

Vaultsmith currently ships a practical local workflow:

- initializes a vault-local `.vaultsmith/` workspace
- writes role prompts and bootstrap instructions for Codex and Claude
- launches agent sessions in `tmux`
- defaults to a review-first flow with proposal and receipt files
- lets you inspect status, tail output, approve, and apply
- keeps a small vault memory file for durable conventions

It is intentionally narrow right now. The current product is a launcher and guardrail layer for agent-driven vault work, not a full autonomous vault intelligence system yet.

## Core idea

Vaultsmith should help an agent behave more like the person who owns the vault.

That means the agent should learn and respect signals such as:

- naming patterns
- folder placement habits
- heading structure
- bullet and checklist style
- link and tag behavior
- frontmatter usage
- note family conventions

The long-term direction is simple: when Vaultsmith creates or reorganizes a note, it should feel native to the vault immediately.

## Quick start

Requirements:

- Python 3.11+
- `pipx`
- `tmux`
- at least one supported agent CLI on `PATH`: `codex` or `claude`

### One-line install path

The default install path is:

```bash
pipx install vaultsmith
vsm setup ~/Obsidian/MyVault
cd ~/Obsidian/MyVault
vsm run -- "Organize my inbox notes"
```

### Why `pipx` is the default

Vaultsmith is a CLI tool, not a library. `pipx` is the cleanest default because it installs the command into an isolated environment without making users create a project virtualenv just to try the tool.

If you prefer `pip`, install Vaultsmith into a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install vaultsmith
```

### Install for local development

If you are working on Vaultsmith itself:

```bash
git clone https://github.com/ronut01/Vaultsmith.git
cd Vaultsmith
python -m venv .venv
source .venv/bin/activate
python -m pip install -e . pytest
```

### First commands

Interactive session:

```bash
vsm chat
```

One-shot request:

```bash
vsm run -- "Clean up my unfinished notes"
```

## Review-first workflow

Vaultsmith is designed so the agent proposes work before it applies work.

Typical flow:

```bash
vsm run -- "Organize my lecture video links"
vsm review
vsm approve
vsm apply
```

Useful follow-up commands:

```bash
vsm status
vsm tail
vsm sessions
vsm resume <session-id>
```

Behavior notes:

- `vsm run` attaches by default so you can respond to trust prompts and other interactive agent questions
- `vsm run --detach -- "..."` keeps the run in the background and prints recent tmux output
- `vsm apply` does not patch files itself; it re-dispatches the approved session to the underlying agent and then expects a `receipt.md`

## What gets written into a vault

Running `vsm setup <vault>` creates a small control plane inside the target vault:

```text
.vaultsmith/
  config.toml
  instructions/
    codex.md
    claude.md
  memory/
    vault-summary.md
  roles/
    input-agent.md
    vault-analyst.md
    research-scout.md
    draft-agent.md
    consistency-reviewer.md
  sessions/
    <session-id>/
      session.json
      proposal.md
      approval.md
      receipt.md
      changes.json
```

Session files matter:

- `session.json`: metadata, mode, runtime state, approval state
- `proposal.md`: short proposed plan and draft output before edits are applied
- `approval.md`: approval checkpoint
- `receipt.md`: short execution summary after apply
- `changes.json`: proposed operations payload when the session provides one

## Command overview

```bash
vsm setup <path>          # initialize Vaultsmith in a vault
vsm chat [path]           # start an interactive agent session
vsm run [path] -- "..."   # start a one-shot request
vsm status [session-id]   # inspect current or selected session
vsm tail [session-id]     # show recent tmux output
vsm review [session-id]   # print proposal.md
vsm approve [session-id]  # mark session approved
vsm apply [session-id]    # dispatch approved work
vsm sessions              # list recent sessions
vsm resume <session-id>   # re-attach to tmux session
vsm alias enable vs       # install a shorthand shell alias
```

## Philosophy

Vaultsmith is opinionated in a few ways.

### 1. Inspect before generating

The vault is the source of truth. The agent should look at local evidence before inventing a structure or style.

### 2. Small context beats full-vault scans

For most requests, a few relevant notes are better than a noisy global survey.

### 3. Review before apply

Users should be able to inspect, reject, or refine proposed changes before the agent edits the vault.

### 4. Minimal edits over dramatic rewrites

Most vault work is maintenance, not greenfield writing. The safe default is a narrow change.

## Current scope vs. direction

Current scope:

- local CLI
- tmux-backed agent launch
- vault bootstrap files
- review-first session workflow
- basic session state and approval handling

Planned direction:

- stronger vault-style profiling
- better note placement and naming inference
- more explicit explanation for why a note was titled or placed a certain way
- better support for recurring note families like meetings, research notes, and project updates

## Development

Run tests:

```bash
cd Vaultsmith
source .venv/bin/activate  # or the virtualenv you use for local development
pytest -q
```

Smoke test against a temporary vault:

```bash
mkdir -p /tmp/vsm-smoke-vault
vsm setup /tmp/vsm-smoke-vault
cd /tmp/vsm-smoke-vault
vsm run -- "Create a test note and explain the current vault state"
```

## Contributing

If you want to contribute, start here:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- [docs/roadmap.md](docs/roadmap.md)

Good first contributions are usually:

- docs clarity
- install and onboarding improvements
- safer session UX
- better tests
- small CLI quality-of-life fixes

## Status

Vaultsmith is early, but the direction is deliberate.

The goal is not to bolt AI onto Obsidian. The goal is to make an agent operate inside a vault with enough structure, memory, and review pressure that the output starts to feel like it belongs there.

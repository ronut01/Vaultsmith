# Vaultsmith

**AI for Obsidian that writes and organizes notes like you do.**

Vaultsmith is an AI agent for Obsidian that learns how you write, structure, title, link, and organize notes — then helps create and manage your vault in a way that feels like *you* made the changes.

---

## 1. What Vaultsmith is

Vaultsmith is not just another Obsidian automation tool.

Most Obsidian AI tools can generate notes, summarize content, or move files around.
Vaultsmith focuses on something more personal:

> making an AI agent behave like the user inside an Obsidian vault.

That means the agent should not only be able to write notes, but also:

- write in the user’s usual note structure
- use the user’s common heading and bullet patterns
- name notes the way the user normally names them
- place notes in folders where the user would likely put them
- create links and tags in ways that fit the existing vault
- make changes that feel native rather than generic

The goal is simple:

**When Vaultsmith creates or organizes a note, it should feel like it belongs in the vault immediately.**

---

## 2. Why this project exists

AI note tools are becoming more capable, but they still often feel generic.
They can produce useful text, yet they usually fail at an important detail:

**they do not work the way the user works.**

For Obsidian users, this matters a lot.
A vault is not just a folder of markdown files. It reflects personal habits:

- how ideas are captured
- how notes are structured
- how notes are grouped
- how folders are used
- how links are created
- how much detail is written
- whether the user prefers clean summaries, rough bullets, daily logs, or structured outlines

Generic outputs create friction.
Even if the content is correct, users still have to rewrite, reformat, retitle, relink, and relocate notes.

Vaultsmith exists to reduce that friction.

Instead of asking users to adapt to the AI, Vaultsmith helps the AI adapt to the user.

---

## 3. Core idea

Vaultsmith learns a **working style profile** from the user’s vault.

This profile is not limited to writing tone. It includes practical behaviors such as:

- note title patterns
- folder placement preferences
- heading depth
- bullet and checklist habits
- tag usage
- frontmatter usage
- linking behavior
- template preferences
- note type patterns (meeting note, daily note, idea note, project note, reading note, etc.)

Vaultsmith then uses that profile to guide agent behavior.

So the system is not just answering:

- “What note should I write?”

It is also answering:

- “How would this user write it?”
- “What would they name it?”
- “Where would they put it?”
- “How would they structure it?”
- “What should it link to?”

---

## 4. Product vision

Vaultsmith should make AI-generated changes inside Obsidian feel:

- personal
- native to the vault
- consistent over time
- inspectable
- editable
- trustworthy

The long-term vision is:

**an agent that can operate in your vault in a way that matches your note-taking identity.**

Not just “AI for notes.”
Not just “Obsidian automation.”

But:

**an Obsidian agent that works like you do.**

---

## 5. What makes Vaultsmith different

### Existing tools usually focus on:

- connecting AI to Obsidian
- search and retrieval
- note generation
- task execution
- general PKM workflows

### Vaultsmith focuses on:

- personal writing style
- personal note structure
- personal organizational habits
- personal vault conventions
- behavior consistency across note creation and organization

In short:

**Others help agents work in Obsidian.**
**Vaultsmith helps agents work in Obsidian like the user would.**

---

## 6. Design principles

### 6.1 Personal over generic
The output should fit the user’s vault, not just look polished in isolation.

### 6.2 Structure matters as much as text
A note is not only its content. Its title, location, headings, bullets, metadata, links, and surrounding context matter too.

### 6.3 Explainable behavior
Vaultsmith should be able to explain why it formatted, titled, linked, or placed a note in a certain way.

### 6.4 Human override first
Users should always be able to inspect, edit, reject, or refine the system’s decisions.

### 6.5 Work with existing agents
Vaultsmith should be usable with tools and environments users already like, such as Claude Code, Codex, OpenClaw, and other agent workflows.

---

## 7. Initial scope

Vaultsmith should begin with a narrow and strong MVP.

### MVP focus

Vaultsmith analyzes an existing vault and helps an agent:

1. create new notes in the user’s usual style
2. choose a likely title format
3. choose a likely folder or location
4. apply the user’s usual structure
5. recommend related links or tags
6. explain why those choices were made

### Example user experience

A user asks an agent:

> “Create a meeting note for today’s research sync.”

A generic tool might create a plain markdown file.

Vaultsmith should instead help the agent produce something closer to:

- the user’s usual meeting-note title pattern
- the correct project folder
- the preferred section order
- the user’s usual bullet style
- the user’s linking habits
- the relevant project or daily note connections

The result should feel like it is written by the user.

---

## 8. Core concepts

### 8.1 Vault Profile
A structured representation of how a specific user tends to organize and write inside their Obsidian vault.

Possible signals include:

- common note categories
- title patterns
- folder conventions
- heading patterns
- bullet density
- tag conventions
- frontmatter conventions
- link density and style
- recurring templates

### 8.2 Note Intent
A description of what kind of note the user is trying to create.
Examples:

- meeting note
- reading note
- project update
- idea capture
- daily reflection
- research summary

### 8.3 Placement Decision
A prediction of where a note belongs in the vault.

### 8.4 Structure Plan
A predicted outline based on the user’s habits for this type of note.

### 8.5 Style Guidance
Rules or preferences for tone, formatting, bullets, checklists, and metadata.

### 8.6 Explanation Layer
A human-readable explanation for why Vaultsmith made its recommendation.

---

## 9. Success criteria

Vaultsmith is successful if users feel that the agent’s output is:

- less generic
- less annoying to clean up
- easier to trust
- better aligned with their existing vault
- immediately more usable than standard AI-generated notes

A strong success signal is this reaction:

> “This feels like something I would have written and filed myself.”

---

## 10. Target users

Vaultsmith is especially useful for:

- heavy Obsidian users
- PKM enthusiasts
- researchers and students
- people using Obsidian and AI agents(Claude Code, Codex, OpenClaw, etc.)
- users combining Obsidian with coding agents
- people who care about consistency in their vault

The ideal early adopter is someone who:

- already has an established vault
- already has repeatable note habits
- wants AI help without sacrificing personal style

---

## 11. Positioning

### One-sentence positioning
Vaultsmith is an AI agent layer for Obsidian that writes and organizes notes like you do.

### Main version
Vaultsmith using AI agents(also using sub-agents) create and manage Obsidian notes in the user’s own style, structure, and organization patterns.

### What Vaultsmith is not

- not just another note generator
- not just a file mover
- not just a plugin wrapper around LLM calls
- not a generic “second brain” assistant with no sense of user identity

---

## 12. Early feature directions

Potential first features:

### 12.1 Style-aware note generation
Generate notes using the user’s preferred structure and formatting habits.

### 12.2 Folder and filename recommendations
Suggest where the note should go and how it should be named.

### 12.3 Related note linking
Suggest likely backlinks, hub pages, MOCs, or related references.

### 12.4 Template inference
Infer user-specific templates from recurring note patterns.

### 12.5 Review mode
Show the generated note with explanations before writing to the vault.

### 12.6 Agent integration layer
Support workflows where Claude Code, Codex, OpenClaw, or other agents call Vaultsmith as a personalization layer.

---

## 13. Tone of the project

Vaultsmith should feel:

- practical, not academic
- personal, not creepy
- helpful, not over-automated
- inspectable, not mysterious
- polished, but not over-engineered

The project should communicate a clear promise:

**Your Obsidian agent should not feel generic. It should feel like it knows how you work.**

---

## 14. First guiding question for development

Whenever designing a feature, ask:

> Does this help the agent behave more like the user inside the vault?

If the answer is no, it is probably not core to Vaultsmith.

> Does this fully using AI agents(also using sub-agents)?

If the answer is no, it is probably not core to Vaultsmith.

---

## 15. Working draft mission statement

**Vaultsmith helps AI agents work inside Obsidian in a way that matches the user’s own note-taking habits — including how they write, structure, name, link, and organize notes.**

---

## 16. Working draft tagline candidates

- AI for Obsidian that writes and organizes notes like you do.
- An AI agent for Obsidian that works like you do.
- Teach your Obsidian agent your writing and organization style.
- Make AI-generated notes feel native to your vault.
- Your vault, your habits, your agent.

---

## 17. Current product thesis

The most compelling version of Vaultsmith is not “AI that can write notes.”

It is:

**AI agent that can enter an existing Obsidian vault and make changes that feel consistent with the human who built that vault.**

That is the core identity of the project.
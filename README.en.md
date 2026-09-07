# EOS App

[中文](./README.md) | [English](./README.en.md)

EOS App is a desktop AI coding workspace designed for real project conversations, task execution, command verification, and engineering management.

EOS App is the official desktop distribution repository, providing installers, release notes, screenshots, and basic product information.

This repository does not include the EOS App desktop source code. Core capabilities of EOS App are built on top of the open-source [EOS CLI](https://github.com/eosaios/eos).

The current release is `v1.0.0-beta.4`. Every package ships the signed Rust Core (sha256-verified, Ed25519-signed) across three platforms: Windows (setup installer + portable zip), macOS (dmg installer + portable tar.gz, Intel and Apple Silicon), and Linux (amd64 + arm64).

- Distribution Repository: https://github.com/eosaios/eos-app
- Issues: https://github.com/eosaios/eos-app/issues
- Releases: https://github.com/eosaios/eos-app/releases

## Why EOS App?

| Need | EOS App |
|---|---|
| A desktop interface for AI-assisted coding workflows | Brings conversations, tasks, commands, and project entry points into one workspace |
| Fewer context switches across tools | Centralizes sessions, tasks, Bash, Worktree, and diagnostics |
| Better visibility into context and runtime state | Provides dedicated pages for models, rules, context, cost, and diagnostics |
| A workspace built for regular use | Keeps command palette, notifications, connection management, and system settings in one place |

## Core Capabilities

- Conversation workspace for project-focused requests, attachments, and context-aware collaboration
- Task center for background jobs, execution progress, and stoppable work
- Bash workspace for verification commands, recent output, and failure review
- Worktree entry for branch-aware and worktree-aware project operations
- Models and connections management for provider status and related configuration
- Rules, context, and cost views for instruction management and execution visibility
- Engineering support pages including LSP, Diagnostics, Settings, and Notifications

## Who It Is For

- Individual developers who want a desktop-first AI coding workspace
- Power users who need sessions, tasks, command output, and system state in one place
- EOS users who prefer a graphical interface over a terminal-only workflow

## Downloads

This repository is intended for desktop app distribution. Public materials focus on the README, release notes, and installable packages.

Each release provides:

- Windows x64 setup installer (`eos-app-setup-<version>.exe`) and portable archive
- macOS dmg installer (Intel and Apple Silicon, drag-and-drop install) and portable tar.gz
- Linux tar.gz (amd64 and arm64)
- Checksum file `SHA256SUMS.txt`

Exact asset names, versions, and checksums are published on each Release page.

## Screenshots

Main workspace overview (macOS with native traffic-light window controls; Windows and Linux use matching platform-style buttons):

![EOS App workspace overview](https://github.com/eosaios/eos-app/releases/download/v1.0.0-beta.4/workspace-overview.png)

- The left sidebar provides entry points for new chats, skills and apps, automations, and sessions
- The center area hosts the main conversation workspace and quick-start suggestions
- The input area at the bottom is used to start the next task directly, with the Bash terminal docked below

## License

This repository is released under the EOS App Installer and Documentation Non-Commercial License v1.0. See [LICENSE](./LICENSE) for details:

- Free to download, install, and use the official installers for personal and non-commercial purposes
- Unmodified redistribution of official installers and bundled documentation is allowed for non-commercial use
- This repository does not include the EOS App desktop source code
- Any commercial use is prohibited, including internal production use, paid services, SaaS, and commercial redistribution
- Commercial use requires separate written authorization from the copyright holder

## Contact

- Issues: https://github.com/eosaios/eos-app/issues
- Commercial licensing: legal@eosaios.com

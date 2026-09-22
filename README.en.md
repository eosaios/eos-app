# EOS App

[中文](./README.md) | [English](./README.en.md)

**A desktop AI coding workspace.** Conversations, task execution, command verification, and project management in one window—built for real projects, not just code chat.

- Download: [Releases](https://github.com/eosaios/eos-app/releases) (always use the latest release)
- Issues: [Issues](https://github.com/eosaios/eos-app/issues)
- Terminal edition: [EOS CLI](https://github.com/eosaios/eos)

This repository is the **official distribution repo** for EOS App: installers, release notes, and product information — **not** the desktop source code. Core capabilities are built on the Rust core of the open-source [EOS CLI](https://github.com/eosaios/eos). Each package ships a signed Core (SHA-256 checksum + Ed25519 signature).

## Why EOS App

Coding work often stalls on tool switching: chat in one window, terminal in another, a third for the browser, and you still watch Git status yourself.

EOS App pulls that into one workspace:

- **State the goal, keep moving** — chat, planning, tasks, and approvals on one thread
- **AI can drive the web** — embedded live browser; hand control back to you for sign-in / verification
- **See the changes** — Git status, command output, and artifact previews side by side
- **Built for the long run** — theme skins, personalized replies, in-app updates, system tray

## Capabilities

**Conversation & collaboration**  
Conversation workspace · Plan / auto modes · Approvals & sandbox levels · AI refine input · Capture board (save great replies as knowledge cards)

**Tasks & engineering**  
Task center with plan todos · Bash workspace · Git commit/push with reminders · Worktree / remote repos · Change summary & artifact previews

**Browser collaboration**  
Embedded live browser (tabs, shared viewport) · AI navigate / pick / fill · Human takeover · Pick page elements into the chat

**Models & context**  
Multi-provider model access · Model wizard with connectivity test · Linked reasoning levels · Live context usage · Rules / memory · Usage & cost

**Extensions & appearance**  
Skills and apps · Plugin marketplace · Automation · Built-in theme skins + local / GitHub import · MCP / LSP / network / notifications

**Desktop experience**  
In-app updates · System tray & single instance · Desktop notifications · Native windows on Windows / macOS / Linux

## Platforms & install

| Platform | Arch | How to install |
|---|---|---|
| Windows | x64 | setup installer, or portable zip |
| macOS | Intel / Apple Silicon | dmg drag-and-drop, or portable tar.gz |
| Linux | amd64 / arm64 | tar.gz |

1. Open [Releases](https://github.com/eosaios/eos-app/releases) and download the latest package for your platform
2. Verify with `SHA256SUMS.txt` on the same page if needed
3. After install, check for updates in-app — download and install are automatic

> Asset names follow each Release page. Version numbers move with releases and are not repeated in this document.

## Screenshots

### Demo video (90 seconds)

[![EOS App demo: from one request to a working file](https://eosaios.com/assets/eos-promo-preview.gif)](https://eosaios.com/assets/eos-promo.mp4)

Click the preview for the full walkthrough — conversation, task execution, and file generation.

Main workspace (macOS uses native traffic-light window controls; Windows / Linux use matching platform-style buttons):

![EOS App main workspace](https://github.com/eosaios/eos-app/releases/download/v1.0.0-beta.4/workspace-overview.png)

- Left: new chat, skills and apps, automation, plus tasks / worktree, usage / network / memory / help
- Center: conversation and the main workflow
- Bottom: input for new tasks (switch model and reasoning level); Bash terminal docked below

## License

Installers and documentation are released under the EOS App Non-Commercial License (see [LICENSE](./LICENSE)):

- Free to download, install, and use for personal / non-commercial purposes; unmodified redistribution of official packages and docs is allowed
- Commercial use is prohibited (including internal production use, paid services, SaaS, and commercial redistribution)
- Commercial use requires separate written authorization from the copyright holder
- This repository does not include the desktop source code

## Contact

- Issues: https://github.com/eosaios/eos-app/issues
- Commercial licensing: legal@eosaios.com

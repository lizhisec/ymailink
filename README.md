# ymailink

**CLI email management tool for the terminal.** List, read, search, compose, reply, forward, move, copy, delete, and flag emails — all from the command line. Supports IMAP/SMTP, Outlook (Microsoft Graph API), Gmail (Google API), and Exchange backends.

## Features

- **List, read, search** emails in any folder with pagination and search queries
- **Compose, reply, forward** messages using `$EDITOR`
- **Move, copy, delete, flag** messages (flags: seen, answered, flagged, deleted, draft)
- **Manage folders** — list, create, delete, expunge, purge
- **Download attachments**
- **Template-based** message composition pipeline (great for scripting/automation)
- **Multiple accounts** with per-account configuration
- **OAuth2** auto-refresh for Outlook (Microsoft Graph) and Gmail
- **Multiple auth methods**: plain password, command-based (`pass`, `security`), system keyring
- **Structured output**: plain text or JSON (`--output json`)
- **Multiple backends**: IMAP, SMTP, Outlook, Gmail, Exchange

## Supported Email Services

ymailink works with any provider that exposes a supported protocol or API:

| Service | Backend | Notes |
|---------|---------|-------|
| Gmail / Google Workspace | IMAP+SMTP or Gmail (OAuth2) | App password required for IMAP with 2FA |
| Outlook.com / Hotmail / Live | IMAP+SMTP or Outlook (OAuth2) | OAuth2 via Microsoft Graph recommended |
| Microsoft 365 / Office 365 | Outlook (OAuth2) or Exchange | Graph API for cloud; Exchange for on-prem |
| QQ Mail | IMAP+SMTP | Use authorization code, not account password |
| 163 Mail / 126 Mail | IMAP+SMTP | Use authorization code, not account password |
| Sina Mail | IMAP+SMTP | Use authorization code |
| Foxmail | IMAP+SMTP | Same config as QQ Mail |
| Yahoo Mail | IMAP+SMTP | App password required with 2FA |
| iCloud Mail | IMAP+SMTP | App-specific password required |
| Self-hosted (Dovecot, Postfix, etc.) | IMAP+SMTP | Standard IMAP/SMTP |
| Exchange Server (on-prem) | Exchange | Requires exchangelib |

## Installation

```bash
pip install ymailink
```

Optional extras:

```bash
pip install ymailink[outlook]     # Microsoft Graph API support
pip install ymailink[gmail]       # Google Gmail API support
pip install ymailink[keyring]     # System keyring password storage
pip install ymailink[exchange]    # Microsoft Exchange support
pip install ymailink[all]         # All optional backends
```

Requires Python 3.11+.

## Quick Start

### 1. Configuration

Create `~/.config/ymailink/config.toml`:

```toml
[accounts.default]
email = "user@example.com"
display-name = "Your Name"
default = true

backend.type = "imap"
backend.host = "imap.example.com"
backend.port = 993
backend.encryption = "tls"
backend.login = "user@example.com"
backend.auth.type = "password"
backend.auth.cmd = "pass show email/imap"

message.send.backend.type = "smtp"
message.send.backend.host = "smtp.example.com"
message.send.backend.port = 587
message.send.backend.encryption = "start-tls"
message.send.backend.login = "user@example.com"
message.send.backend.auth.type = "password"
message.send.backend.auth.cmd = "pass show email/smtp"
```

Or use the interactive wizard (prints config to stdout — copy-paste to the config file):

```bash
ymailink account configure
```

### 2. Test the connection

```bash
ymailink account doctor
```

### 3. List emails

```bash
ymailink mail list
```

## Usage

### Global Options

| Flag | Description |
|------|-------------|
| `-c`, `--config` | Config file path (repeatable for deep merge) |
| `-o`, `--output` | Output format: `plain` (default) or `json` |
| `-a`, `--account` | Account name (defaults to configured default) |
| `-q`, `--quiet` | Suppress non-error log output |
| `--debug` | Enable debug logging |
| `-V`, `--version` | Show version |

### Commands

| Command | Description |
|---------|-------------|
| `account list` | List configured accounts |
| `account doctor` | Diagnose account connection |
| `account configure` | Interactive account setup wizard |
| `folder list` | List all folders |
| `folder add <name>` | Create folder |
| `folder delete <name>` | Delete folder |
| `folder expunge <name>` | Expunge deleted messages |
| `folder purge <name>` | Delete all messages in folder |
| `mail list [-f FOLDER] [-p PAGE] [-s SIZE] [-q QUERY]` | List messages (default INBOX) |
| `mail thread <id> [-f FOLDER]` | View a message thread |
| `mail read <id> [-f FOLDER]` | Read a message (marks as SEEN) |
| `mail write [--headers K:V ...]` | Compose interactively via `$EDITOR` |
| `mail send [raw]` | Send raw message from file or stdin |
| `mail reply <id> [-f FOLDER] [--all]` | Reply to a message |
| `mail forward <id> [-f FOLDER]` | Forward a message |
| `mail copy <ids...> -t TARGET [-f FOLDER]` | Copy messages to folder |
| `mail move <ids...> -t TARGET [-f FOLDER]` | Move messages to folder |
| `mail delete <ids...> [-f FOLDER]` | Delete messages |
| `flag add <ids...> -g FLAGS... [-f FOLDER]` | Add flags |
| `flag set <ids...> -g FLAGS... [-f FOLDER]` | Replace all flags |
| `flag remove <ids...> -g FLAGS... [-f FOLDER]` | Remove flags |
| `attachment download <id> [-f FOLDER] [-d DIR]` | Download attachments |
| `template write` | Generate blank compose template → stdout |
| `template reply <id> [-f FOLDER] [--all]` | Generate reply template → stdout |
| `template forward <id> [-f FOLDER]` | Generate forward template → stdout |
| `template save [raw]` | Save template as draft |
| `template send [raw]` | Send template from file or stdin |

Running `ymailink` with no arguments is equivalent to: `ymailink mail list --folder INBOX --page 1 --page-size 20`

### Examples

```bash
# List emails in a specific folder
ymailink mail list --folder "Sent"

# Search emails
ymailink mail list --query "from:john@example.com subject:meeting"

# Paginate results
ymailink mail list --page 2 --page-size 10

# Read a message
ymailink mail read 42

# Send a message from a file
ymailink mail send message.txt

# Pipe a message to send
cat message.txt | ymailink mail send

# Reply to a message with reply-all
ymailink mail reply 42 --all

# Move multiple messages to Archive
ymailink mail move 42 43 44 --target "Archive"

# Copy messages
ymailink mail copy 55 56 --target "Important"

# Manage flags
ymailink flag add 42 --flags seen --flags flagged

# Download attachments
ymailink attachment download 42 --dir ~/Downloads

# Template pipeline (compose offline, then send)
ymailink template write > msg.txt
vim msg.txt
ymailink template send msg.txt

# JSON output for scripting
ymailink --output json mail list

# Switch account
ymailink --account work mail list
```

### Available Flags

`seen`, `answered`, `flagged`, `deleted`, `draft`

## Configuration Reference

See full details in [`skill/references/configuration.md`](skill/references/configuration.md).

### Backend Types

| Backend | Read | Send | Auth |
|---------|------|------|------|
| IMAP | imapclient | — | password (raw/cmd/keyring) |
| SMTP | — | aiosmtplib | password (raw/cmd/keyring) |
| Outlook | Microsoft Graph API | Microsoft Graph API | OAuth2 |
| Gmail | Google Gmail API | Google Gmail API | OAuth2 |
| Exchange | exchangelib | exchangelib | password (auto/NTLM/basic) |

## Message Composition

ymailink uses standard RFC 822 format. See [`skill/references/message-composition.md`](skill/references/message-composition.md) for the full reference.

A minimal message:

```
From: You <you@example.com>
To: recipient@example.com
Subject: Hello

Message body here.
```

## Project Structure

```
ymailink/
  src/ymailink/
    cli.py              — Argparse CLI dispatcher (lazy imports)
    backend/            — Backend implementations (IMAP, SMTP, Outlook, Gmail, Exchange)
    commands/           — Command handlers (account, folder, mail, flag, attachment, template)
    config/             — Configuration loading and Pydantic models
    domain/             — Domain models (Summary, Message, Flag, Folder, Attachment, Account)
    output/             — Output formatting (plain, JSON, Rich tables)
    utils/              — Utilities (editor, password resolution, logging, paths)
  tests/                — Unit and integration tests
  skill/                — Claude Code skill with documentation references
```

## Development

```bash
git clone https://github.com/lizhisec/ymailink
cd ymailink
pip install -e ".[dev,all]"
pytest tests/
```

## Backend Notes

- **IMAP delete** is hard (sets `\Deleted` + EXPUNGE) — messages are permanently removed.
- **Gmail delete** moves to trash (not a hard delete).
- **Attachment downloads** from non-IMAP backends (Outlook/Gmail/Exchange) return metadata only — binary data download is not yet supported for those backends.
- **Proxy support**: Set `HTTPS_PROXY` / `https_proxy` env var for Outlook and Gmail backends.

## Supported Email Services

ymailink works with any provider that exposes one of the supported protocols/APIs. Below are the most commonly used services:

| Service | Protocol/API | Recommended Backend | Notes |
|---------|-------------|-------------------|-------|
| Gmail / Google Workspace | IMAP + SMTP or Google API | IMAP+SMTP (basic) or Gmail (OAuth2) | App password required for IMAP with 2FA; OAuth2 via Google API recommended |
| Outlook.com / Hotmail / Live | IMAP + SMTP or Microsoft Graph | IMAP+SMTP (basic) or Outlook (OAuth2) | OAuth2 via Microsoft Graph recommended |
| Microsoft 365 / Office 365 | Microsoft Graph or Exchange | Outlook (OAuth2) or Exchange | Exchange backend for on-prem; Graph API for cloud |
| QQ邮箱 | IMAP + SMTP | IMAP+SMTP | Use authorization code (not email password) |
| 163邮箱 / 126邮箱 | IMAP + SMTP | IMAP+SMTP | Use authorization code (not email password) |
| 新浪邮箱 | IMAP + SMTP | IMAP+SMTP | Use authorization code |
| Foxmail | IMAP + SMTP | IMAP+SMTP | Same as QQ mail backend |
| Yahoo Mail | IMAP + SMTP | IMAP+SMTP | App password required with 2FA |
| iCloud Mail | IMAP + SMTP | IMAP+SMTP | App-specific password required |
| Zoho Mail | IMAP + SMTP | IMAP+SMTP | Standard IMAP/SMTP settings |
| ProtonMail | — | Not supported | No IMAP/SMTP access on free plan |
| Custom / Self-hosted | IMAP + SMTP | IMAP+SMTP | Works with Dovecot, Postfix, etc. |
| Exchange Server (on-prem) | Exchange Web Services | Exchange | Requires exchangelib |

---

> [中文文档](README_zh.md)

## License

MIT

---
name: ymailink
description: "Terminal email client for managing emails from the command line. Supports IMAP/SMTP, Outlook (Graph API), Gmail (Google API), and Exchange backends, plus AI-powered email summarization and quick reply. Use this skill ANYTIME the user mentions email from the terminal — whether they say 'ymailink' by name, ask about sending/reading/searching emails via CLI, need help configuring an email account (IMAP, SMTP, Outlook, Gmail, Exchange), want to automate email notifications in shell scripts, or need to compose/reply/forward/move/copy/delete/flag emails. Also trigger when the user brings up email authentication (OAuth2, app passwords, IMAP credentials), mentions RFC 822 message format, wants to manage email folders, download attachments, or troubleshoot email delivery issues. Also trigger when the user wants AI-powered email summaries, one-line digests, or quick reply suggestions — this skill covers the `ymailink ai` commands. This is the go-to skill for anything email-related in the terminal. Before using ymailink commands, verify it is installed (see Installation section in the skill body)."
metadata: {"homepage":"https://github.com/lizhisec/ymailink","clawdbot":{"emoji":"📧","requires":{"bins":["ymailink"]},"install":[{"id":"pip","kind":"pip","package":"ymailink","bins":["ymailink"],"label":"Install ymailink (pip)"}]}}
---

# ymailink Email CLI

ymailink is a Python CLI email client (v0.1.0) for managing emails from the terminal. It supports four backends:

| Backend | Read | Send | Auth |
|---------|------|------|------|
| **IMAP** | imapclient | — | password (raw/cmd/keyring) |
| **SMTP** | — | aiosmtplib | password (raw/cmd/keyring) |
| **Outlook** (Graph API) | httpx + msal | httpx + msal | OAuth2 (device flow) |
| **Gmail** (Google API) | google-api-python-client | google-api-python-client | OAuth2 (local server) |
| **Exchange** | exchangelib | exchangelib | password (auto/NTLM/basic) |

## Installation

**Before using any ymailink commands, always verify ymailink is installed first.** Run `which ymailink` or `ymailink --version`. If not installed, guide the user to run:

```bash
pip install git+https://github.com/lizhisec/ymailink.git
```

To install with optional dependencies (for specific backends or AI features):

```bash
# Install with all optional dependencies
pip install "git+https://github.com/lizhisec/ymailink.git#egg=ymailink[all]"

# Or install specific extras
pip install "git+https://github.com/lizhisec/ymailink.git#egg=ymailink[outlook,gmail,keyring,exchange,ai]"
```

If GitHub is inaccessible, use Gitee mirror as the git source:
```bash
pip install git+https://gitee.com/w3hsec/ymailink.git
```

```bash
# With optional dependencies
pip install "git+https://gitee.com/w3hsec/ymailink.git#egg=ymailink[all]"
```


## Prerequisites

1. Python 3.11+ installed.
2. `ymailink` installed (see Installation section above).
3. A configuration file at `~/.config/ymailink/config.toml` (or custom path via `-c`).
4. IMAP/SMTP credentials, OAuth2 app registration, or Exchange server details.
5. For AI features (`ymailink ai ...`): an API key configured under `[ai]` in config (see `references/configuration.md`).

## Quick Reference — All Commands

Seven command groups, 27 subcommands:

### `account` — Manage accounts
| Subcommand | Action |
|------------|--------|
| `account list` | List configured accounts |
| `account doctor` | Diagnose account connection |
| `account configure` | Run interactive wizard (prints config to stdout — copy-paste to `~/.config/ymailink/config.toml`) |

### `folder` — Manage folders
| Subcommand | Action |
|------------|--------|
| `folder list` | List all folders (shows count + unread — IMAP omits these) |
| `folder add <name>` | Create folder |
| `folder delete <name>` | Delete folder |
| `folder expunge <name>` | Permanently remove deleted messages (IMAP only; Outlook/Gmail/Exchange are no-ops) |
| `folder purge <name>` | Delete ALL messages in folder (batched 500 at a time) |

### `mail` — Manage messages
| Subcommand | Action |
|------------|--------|
| `mail list [-f FOLDER] [-p PAGE] [-s SIZE] [-q QUERY]` | List messages (default INBOX, page 1, size 20). Search syntax depends on backend. |
| `mail thread <id> [-f FOLDER]` | View a single message by ID (fetches one message, not a full thread) |
| `mail read <id> [-f FOLDER]` | Read message body (marks as SEEN) |
| `mail write [--headers K:V ...]` | Interactive compose via `$EDITOR` (or `vi` if unset) |
| `mail send [raw]` | Send raw message from file or stdin |
| `mail reply <id> [-f FOLDER] [--all]` | Reply to message (reply-all with `--all`) |
| `mail forward <id> [-f FOLDER]` | Forward message |
| `mail copy <ids...> -t TARGET [-f FOLDER]` | Copy messages to target folder |
| `mail move <ids...> -t TARGET [-f FOLDER]` | Move messages to target folder |
| `mail delete <ids...> [-f FOLDER]` | Delete messages (IMAP: hard delete via EXPUNGE; Gmail: moves to trash) |

### `flag` — Manage message flags
| Subcommand | Action |
|------------|--------|
| `flag add <ids...> -g FLAGS... [-f FOLDER]` | Add flags |
| `flag set <ids...> -g FLAGS... [-f FOLDER]` | Replace all flags |
| `flag remove <ids...> -g FLAGS... [-f FOLDER]` | Remove flags |

**Valid flags:** `seen`, `answered`, `flagged`, `deleted`, `draft` (case-insensitive)

### `attachment` — Download attachments
| Subcommand | Action |
|------------|--------|
| `attachment download <id> [-f FOLDER] [-d DIR]` | Download attachments. Directory: `--dir` → account config → global config → `~/Downloads` |

**Note:** Only IMAP backends provide attachment binary data. Outlook/Gmail/Exchange backends report metadata (name, size) but cannot download the actual file bytes yet.

### `template` — Programmatic message composition
| Subcommand | Action |
|------------|--------|
| `template write` | Generate blank compose template → stdout |
| `template reply <id> [-f FOLDER] [--all]` | Generate reply template → stdout |
| `template forward <id> [-f FOLDER]` | Generate forward template → stdout |
| `template save [raw]` | Save template as draft (reads from file or stdin) |
| `template send [raw]` | Send template from file or stdin |

### `ai` — AI-powered email operations
| Subcommand | Action |
|------------|--------|
| `ai short-summary <id> [-f FOLDER]` | One-line email summary |
| `ai summary <id> [-f FOLDER]` | Detailed email summary |
| `ai rapid-reply <id> [-f FOLDER]` | Quick reply suggestions (3) |

**Note:** AI features require `[ai]` section in config (see `references/configuration.md`) and the `ai` extra: `pip install ymailink[ai]`. All three commands fetch the target email, send it to the AI API (`https://ai.ymailink.com`), and print the result.

## Global Flags

| Flag | Description |
|------|-------------|
| `-c`, `--config` | Config file path (repeatable for deep merge) |
| `-o`, `--output` | Output format: `plain` (default) or `json` |
| `-a`, `--account` | Account name (defaults to configured default account) |
| `-q`, `--quiet` | Suppress non-error log output (does not suppress command output) |
| `--debug` | Enable debug logging |
| `-V`, `--version` | Show version (`ymailink 0.1.0`) |

## Configuration Setup

> **CRITICAL — Two most common config mistakes to avoid:**
> 1. Section header MUST be `[accounts.<name>]` (plural **accounts**), never `[account.<name>]` (singular). Wrong: `[account.qq]`. Right: `[accounts.qq]`.
> 2. Backend fields MUST use TOML dotted-key syntax under the account section. Wrong: creating a separate `[backend]` section. Right: `backend.type = "imap"` indented under `[accounts.xxx]`.
> 3. After writing config, verify immediately: `ymailink account list`. If nothing shows, the section header or dotted keys are wrong.

### Interactive wizard

```bash
ymailink account configure
```

This prompts for account details and prints the resulting TOML config to stdout. **It does not write the file** — you need to copy-paste the output to `~/.config/ymailink/config.toml`.

### Quick template: IMAP + SMTP (most common)

This is the most common setup. Copy-paste and fill in your credentials:

```toml
[accounts.YOUR_ACCOUNT_NAME]
email = "you@example.com"
display-name = "Your Name"
default = true

# IMAP backend for reading emails
backend.type = "imap"
backend.host = "imap.example.com"
backend.port = 993
backend.encryption = "tls"
backend.login = "you@example.com"
backend.auth.type = "password"
backend.auth.raw = "your-app-password"

# SMTP backend for sending emails
send.backend.type = "smtp"
send.backend.host = "smtp.example.com"
send.backend.port = 465
send.backend.encryption = "tls"
send.backend.login = "you@example.com"
send.backend.auth.type = "password"
send.backend.auth.raw = "your-app-password"
```

**How to adapt this template:**
1. Replace `YOUR_ACCOUNT_NAME` with a short name (e.g. `qq`, `personal`, `work`).
2. Replace all `you@example.com` with your email address.
3. Replace `imap.example.com` / `smtp.example.com` with your provider's servers (see table below).
4. Set `message.send.backend.port` to 465 for TLS or 587 for STARTTLS.
5. Replace `your-app-password` with your password or app-specific password.
6. Set `default = true` on exactly ONE account. Remove from others or set to `false`.

**Common email provider servers:**

| Provider | IMAP host | IMAP port | SMTP host | SMTP port | Notes |
|----------|-----------|-----------|-----------|-----------|-------|
| QQ Mail | `imap.qq.com` | 993 | `smtp.qq.com` | 465 | Enable IMAP in QQ settings first |
| Gmail | `imap.gmail.com` | 993 | `smtp.gmail.com` | 587 | Requires App Password if 2FA on |
| Outlook.com | `outlook.office365.com` | 993 | `smtp.office365.com` | 587 | |
| 163 Mail | `imap.163.com` | 993 | `smtp.163.com` | 465 | Enable IMAP in 163 settings |
| 126 Mail | `imap.126.com` | 993 | `smtp.126.com` | 465 | |

**Verify your config before use:**
```bash
ymailink account list          # Should show your account names
ymailink account doctor        # Should say OK for both IMAP and SMTP
ymailink mail list             # Should list inbox emails
```

For other backends (Outlook API, Gmail API, Exchange), password options (cmd/keyring), folder aliases, signatures, OAuth2, proxy, and AI features, see `references/configuration.md`.

## Common Workflows

### List and read emails

```bash
# List INBOX
ymailink mail list

# Search
ymailink mail list --query "from:john@example.com subject:meeting"

# Paginate
ymailink mail list --page 2 --page-size 10

# Switch folder
ymailink mail list --folder "Sent"

# Read a message
ymailink mail read 42

# JSON output for scripting
ymailink --output json mail list
```

### Compose and send

```bash
# Interactive compose (opens $EDITOR)
ymailink mail write
ymailink mail write --headers "To:user@example.com" --headers "Subject:Hello"

# Send raw message from file
ymailink mail send message.txt

# Pipe to send
cat message.txt | ymailink mail send
```

### Programmatic template workflow

```bash
# Generate a blank template, edit, send
ymailink template write > msg.txt
vim msg.txt
ymailink template send msg.txt

# Or pipe directly
ymailink template write | cat - msg_body.txt | ymailink template send
```

### Reply and forward

```bash
# Reply (opens editor)
ymailink mail reply 42

# Reply to all
ymailink mail reply 42 --all

# Forward
ymailink mail forward 42
```

### Organize messages

```bash
# Move message(s) to folder
ymailink mail move 42 --target "Archive"
ymailink mail move 42 43 44 --target "Archive" --folder INBOX

# Copy message(s)
ymailink mail copy 55 56 --target "Important"

# Delete message(s)
ymailink mail delete 42
ymailink mail delete 42 43 44 --folder INBOX

# Flag messages
ymailink flag add 42 --flags seen --flags flagged
ymailink flag set 42 --flags answered
ymailink flag remove 42 --flags flagged
```

### Manage folders

```bash
ymailink folder list
ymailink folder add "Archive"
ymailink folder delete "Old Folder"
ymailink folder expunge "Trash"
ymailink folder purge "Junk"
```

### AI-powered email operations

```bash
# One-line summary of an email
ymailink ai short-summary 42

# Detailed summary
ymailink ai summary 42

# Quick reply suggestions (3 options)
ymailink ai rapid-reply 42

# Specify a different folder
ymailink ai short-summary 42 --folder INBOX
ymailink ai summary 42 --folder "Sent"
ymailink ai rapid-reply 42 --folder "Archive"
```

### Download attachments

```bash
ymailink attachment download 42
ymailink attachment download 42 --folder INBOX --dir ~/Downloads
```

## Multiple Accounts

```bash
# List configured accounts
ymailink account list

# Switch accounts
ymailink --account work mail list
ymailink --account personal mail list
```

## Message Composition

ymailink uses standard RFC 822 format. See `references/message-composition.md` for the full reference covering: headers, address formats, plain text bodies, reply/forward quoting, interactive compose, file/stdin send, and template workflows.

A minimal message looks like:
```
From: You <you@example.com>
To: recipient@example.com
Subject: Hello

Message body here.
```

## Default Behavior

Running `ymailink` with no arguments is equivalent to:
```bash
ymailink mail list --folder INBOX --page 1 --page-size 20
```

## Tips & Nuances

- **Message IDs are folder-scoped** (IMAP UIDs). Re-list after changing folders.
- **Plural aliases** work for all command groups: `accounts`, `folders`, `flags`, `attachments`, `templates`. (Not `mail`.)
- **`mail write`** uses `$EDITOR` or `$VISUAL`, falling back to `vi`. The temp file uses the `.eml` suffix. If no changes are detected, the message is not sent.
- **`mail reply` / `mail forward`** also detect unchanged content and abort sending.
- **`mail read --html`** flag exists in the CLI but currently has no effect — the text body is always shown.
- **Gmail delete** moves to trash (not a hard delete). Use the Gmail web interface or API to permanently delete.
- **IMAP delete** is hard: sets `\Deleted` + EXPUNGE, permanently removing messages.
- **Folder counts** (count, unread) are only populated by Outlook, Gmail, and Exchange backends — IMAP does not fetch them.
- **Store passwords securely** using `pass`, system keyring (`pip install ymailink[keyring]`), or a command that outputs the password. Plaintext passwords in config are for testing only.
- **AI features** require `pip install ymailink[ai]` and an `[ai]` section in config with an `api-key`. The default AI endpoint is `https://ai.ymailink.com`.
- **OAuth2 tokens** are cached in `~/.config/ymailink/tokens/{provider}_{account}.json` (chmod 0600). Delete the file to force re-authorization.
- **Proxy support** for Outlook and Gmail backends: set `HTTPS_PROXY` or `https_proxy` environment variable.
- **Account not found** errors produce unhandled exceptions. Verify account names with `ymailink account list`.
- **Config file not found** returns an empty config (no error). Commands will fail with "No accounts configured" rather than a file-not-found error.
- **`--quiet`** only suppresses `log()` output (dimmed stderr). It does not suppress command output (table/JSON on stdout) or error messages.

## References

- `references/configuration.md` — Full config setup: IMAP/SMTP/Outlook/Gmail/Exchange auth, AI config, password methods, OAuth2, folder aliases, signatures, proxy
- `references/message-composition.md` — RFC 822 format, headers, address formats, reply/forward quoting, compose workflows

## Debugging

```bash
# Enable debug logging
ymailink --debug mail list

# Diagnose connection issues
ymailink account doctor

# Suppress non-error output
ymailink --quiet mail list

# Check version
ymailink --version
```

## Help

```bash
ymailink --help
ymailink mail list --help
ymailink flag add --help
```

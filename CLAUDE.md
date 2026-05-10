# ymailink — CLAUDE.md

## Project Overview

ymailink is a Python CLI email management tool (v0.1.0) supporting IMAP/SMTP, Outlook (Microsoft Graph API), and Gmail (Google API) backends. It provides full email lifecycle management from the terminal: list, read, search, compose, reply, forward, move, copy, delete, flag, and attachment download.

## Build & Run

```bash
# Install in development mode
pip install -e ".[dev,all]"

# Run tests
pytest tests/ -v

# Run the CLI
ymailink --help
ymailink mail list

# Run as module
python -m ymailink
```

## Project Structure

```
ymailink/
  src/ymailink/
    cli.py          — Argparse CLI dispatcher (single main() entry point)
    __main__.py     — Enables `python -m ymailink`
    backend/        — Backend implementations
      base.py       — ReadBackend / SendBackend ABCs (async context managers)
      builder.py    — BackendBuilder factory (config → concrete backend)
      imap.py       — IMAP backend (imapclient, ThreadPoolExecutor)
      smtp.py       — SMTP send backend (aiosmtplib)
      outlook.py    — Outlook Graph API backend (httpx + msal)
      gmail.py      — Gmail API backend (google-api-python-client)
      oauth.py      — OAuth2 token management (device flow, refresh)
    commands/       — Command handlers (sync functions, async internals)
      account.py    — account list/doctor/configure
      folder.py     — folder list/add/delete/expunge/purge
      mail.py       — mail list/thread/read/write/send/reply/forward/copy/move/delete
      flag.py       — flag add/set/remove
      attachment.py — attachment download
      template.py   — template write/reply/forward/save/send
    config/         — Configuration
      models.py     — Pydantic models (YmailConfig, AccountConfig, BackendConfig, etc.)
      loader.py     — TOML file loading with deep merge
      defaults.py   — Default paths
    domain/         — Pydantic domain models
      summary.py    — Summary (lightweight listing), Address
      message.py    — Message (full with body, attachments), MessageBody
      flag.py       — Flag enum
      folder.py     — Folder model
      attachment.py — Attachment model
      account.py    — Account model
    output/         — Output formatting
      printer.py    — Printer ABC + StdoutPrinter (plain/JSON), get_printer()
      table.py      — Rich table renderers (summary_table, folder_table, account_table)
    utils/          — Utilities
      editor.py     — $EDITOR invocation
      password.py   — Password resolution (cmd/keyring/raw)
      logging.py    — Logging configuration
      paths.py      — Path resolution
  tests/
    unit/           — Unit tests (domain models)
    integration/    — Integration tests (CLI smoke tests)
    conftest.py     — Shared fixtures (sample_imap_config, sample_config, etc.)
```

## Key Architecture Decisions

### Backend Abstraction (backend/base.py)

All backends implement async context managers:

```python
class ReadBackend(ABC):   # connect() / disconnect() via __aenter__ / __aexit__
class SendBackend(ABC):   # same pattern
```

Usage: `async with backend: ...` — automatically connects and disconnects.

### Lazy Imports Pattern

CLI dispatchers in `cli.py` use deferred imports to avoid slow startup:

```python
def cmd_mail_list(args: argparse.Namespace) -> None:
    from ymailink.commands.mail import mail_list  # lazy import
    mail_list(args)
```

### Synchronous → Async Bridge

All public command functions are synchronous, using `asyncio.run()`:

```python
def mail_list(args):
    asyncio.run(_mail_list(args))

async def _mail_list(args):
    # ... async implementation
```

### BackendBuilder Factory (backend/builder.py)

```python
builder = BackendBuilder(config, account_name)
backend = await builder.build_read_backend()   # → ImapBackend / OutlookBackend / GmailBackend
send_backend = await builder.build_send_backend()  # → SmtpBackend / OutlookBackend / GmailBackend
```

Dispatches based on `config.type` discriminator field. Checks optional dependencies before constructing.

### Config System (config/)

TOML-based, Pydantic-validated, supports deep merge of multiple files:

```python
config = load_config(["/path/to/config.toml"])
```

Config files merge left-to-right (later overrides). Default path: `~/.config/ymailink/config.toml`.

**Config model hierarchy:**
- `YmailConfig` → `AccountConfig` (dict) → `BackendConfig` (discriminated union: IMAP/Outlook/Gmail), `MessageConfig` → `SendBackendConfig`

**Backend discriminator types:** `"imap"`, `"outlook"`, `"gmail"`, `"smtp"`

### Output System (output/)

```python
printer = get_printer(args)    # reads args.output and args.quiet
printer.out(data)              # dispatches by type → table or JSON
printer.log("message")         # dimmed stderr, suppressed by --quiet
printer.error("message")       # red stderr + sys.exit(1)
```

`StdoutPrinter` uses Rich for terminal formatting. Supports `"plain"` and `"json"` output modes.

## Domain Models

All domain models are Pydantic `BaseModel` subclasses with serialization support:

- **`Summary`** — Lightweight listing: `id`, `subject`, `from_`, `to`, `date`, `flags`, `has_attachment`, `thread_id`
- **`Address`** — `name` (optional), `email`
- **`Message`** — Full message: `id`, `folder`, `subject`, `from_`, `to`, `cc`, `bcc`, `reply_to`, `date`, `flags`, `message_id`, `in_reply_to`, `references`, `body` (MessageBody with text/html), `attachments`, `raw`
- **`Flag`** — Enum: SEEN, ANSWERED, FLAGGED, DELETED, DRAFT. Methods: `from_imap()` (→ Flag from "\\Seen"), `to_imap()` (→ "\\Seen"), `parse()` (→ Flag from "seen")
- **`Folder`** — `name`, `delimiter`, `count`, `unread`

## CLI Commands

Six top-level command groups, 24 subcommands:

| Command | Action |
|---------|--------|
| `account list` | List configured accounts |
| `account doctor` | Diagnose connection |
| `account configure` | Interactive wizard |
| `folder list` | List all folders |
| `folder add <name>` | Create folder |
| `folder delete <name>` | Delete folder |
| `folder expunge <name>` | Expunge deleted messages |
| `folder purge <name>` | Delete all messages |
| `mail list` | List messages (paginatable, searchable) |
| `mail thread <id>` | View thread |
| `mail read <id>` | Read message (marks as SEEN) |
| `mail write` | Interactive compose via $EDITOR |
| `mail send [raw]` | Send raw message |
| `mail reply <id>` | Reply (supports --all) |
| `mail forward <id>` | Forward |
| `mail copy <ids> -t <target>` | Copy to folder |
| `mail move <ids> -t <target>` | Move to folder |
| `mail delete <ids>` | Delete messages |
| `flag add <ids> --flags <f>` | Add flags (accepted: seen/answered/flagged/deleted/draft) |
| `flag set <ids> --flags <f>` | Replace flags |
| `flag remove <ids> --flags <f>` | Remove flags |
| `attachment download <id>` | Download attachments |
| `template write/reply/forward` | Generate templates (for pipeline) |
| `template save/send [raw]` | Save draft or send template |

**Global flags:** `-c/--config` (repeatable merge), `-o/--output` (plain/json), `-a/--account`, `-q/--quiet`, `--debug`, `-V/--version`

**Default behavior:** `ymailink` with no args = `ymailink mail list` with folder=INBOX, page=1, page_size=20.

## IMAP Backend Details (backend/imap.py)

### Thread Pool
Uses `ThreadPoolExecutor(max_workers=1)` + `loop.run_in_executor()` to wrap blocking imapclient calls.

```python
async def _run(self, func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(self._executor, partial(func, *args, **kwargs))
```

### Encoding Fix for Non-ASCII Headers

Two code paths for message data:
1. **IMAP ENVELOPE** → `list_summaries()` path, uses `_decode_rfc2047()` for RFC 2047 encoded-words
2. **RFC822 parsing** → `get_messages()` path, uses `email.message_from_bytes(raw_bytes)` → Python's `email.header.Header`

**Problem:** Some SMTP servers send raw UTF-8 bytes in Subject without RFC 2047 encoding. Python's `email.header.Header` stores these with `charset='unknown-8bit'`, encoding individual bytes as surrogate-escaped codepoints in `\udc80`-`\udcff` range.

**Fix in `_get_decoded_header()`:** To handle headers with raw UTF-8 bytes stored as surrogates:

```python
# Header._chunks contains (data, charset) tuples
for chunk, charset in raw_val._chunks:
    if isinstance(chunk, bytes):
        parts.append(chunk.decode(charset or "utf-8", errors="replace"))
    elif isinstance(chunk, str) and charset == "unknown-8bit":
        # Extract bytes from surrogate-escaped chars (U+DC80-U+DCFF range)
        raw_bytes = bytes(ord(c) & 0xFF for c in chunk if 0xDC80 <= ord(c) <= 0xDCFF)
        prefix = "".join(c for c in chunk if not (0xDC80 <= ord(c) <= 0xDCFF))
        parts.append(prefix + raw_bytes.decode("utf-8", errors="replace"))
    else:
        parts.append(chunk)
```

Key insight: `\udc80`-`\udcff` surrogates map directly to byte values 0x80-0xFF. `ord(c) & 0xFF` extracts the original byte.

## OAuth2 Token Management (backend/oauth.py)

`OAuthManager` handles token lifecycle for Outlook and Gmail:

- **Outlook:** MSAL device code flow (`initiate_device_flow` → `acquire_token_by_device_flow`)
- **Gmail:** Google InstalledAppFlow (`run_local_server`)
- **Refresh:** Silently refreshes expired tokens using stored refresh tokens
- **Storage:** JSON files at `~/.config/ymailink/tokens/{provider}_{account}.json`, chmod 0600

## Testing

```bash
pytest tests/ -v
pytest tests/unit/ -v        # Unit tests only
pytest tests/integration/ -v # Integration tests only
```

- Unit tests cover domain model construction and behavior (`TestAddress`, `TestFlag`, `TestSummary`, `TestMessage`, `TestFolder`, `TestAccount`)
- Integration tests are basic smoke tests for CLI importability
- Shared fixtures in `tests/conftest.py` provide sample config objects

## Key Patterns & Conventions

1. **Type hints:** `from __future__ import annotations` in all files
2. **Error handling:** `printer.error(msg)` → red output to stderr + `sys.exit(1)`
3. **Dead code removal:** Remove unused imports, functions, and variables completely. No backwards-compatibility hacks.
4. **Config validation:** Pydantic discriminated unions (`Field(discriminator="type")`)
5. **Email representation:** Standard RFC 822 format (headers + blank line + body). Address format: `Name <email>` or just `email`.

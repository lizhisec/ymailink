[English](./README.md) | [中文](./README_zh.md)

# ymailink

**终端邮件管理工具。** 在命令行中完成邮件的列出、阅读、搜索、编写、回复、转发、移动、复制、删除和标记等所有操作。支持 IMAP/SMTP、Outlook（Microsoft Graph API）、Gmail（Google API）和 Exchange 后端。

## 功能特性

- **邮件列表、阅读、搜索** — 支持分页和搜索查询，可在任意文件夹中操作
- **编写、回复、转发** — 使用 `$EDITOR` 编辑器撰写邮件
- **移动、复制、删除、标记** — 支持 seen/answered/flagged/deleted/draft 五种标记
- **文件夹管理** — 列出、创建、删除、清除已删邮件、清空文件夹
- **附件下载**
- **下载 .eml 格式邮件** — 保存完整邮件到本地，可用于离线归档或导入其他客户端
- **模板管道** — 基于模板的邮件撰写流水线，适合脚本化和自动化
- **AI 邮件助手** — 一键精简总结、详细总结、快速回复建议
- **多账户支持** — 每个账户独立配置
- **OAuth2 自动刷新** — Outlook（Microsoft Graph）和 Gmail 自动刷新 Token
- **多种认证方式** — 明文密码、命令式（`pass`、`security`）、系统密钥环
- **结构化输出** — 纯文本或 JSON 格式（`--output json`）
- **多后端支持** — IMAP、SMTP、Outlook、Gmail、Exchange

## 支持的邮箱服务

ymailink 兼容所有支持标准协议/API 的邮件服务商：

| 服务商 | 推荐后端 | 说明 |
|--------|----------|------|
| Gmail / Google Workspace | IMAP+SMTP 或 Gmail（OAuth2） | 两步验证需使用应用专用密码；推荐 Gmail API OAuth2 |
| Outlook.com / Hotmail / Live | IMAP+SMTP 或 Outlook（OAuth2） | 推荐 Microsoft Graph OAuth2 |
| Microsoft 365 / Office 365 | Outlook（OAuth2）或 Exchange | 云端用 Graph API，本地部署用 Exchange |
| QQ邮箱 | IMAP+SMTP | 使用授权码登录，非QQ密码 |
| 163邮箱 / 126邮箱 | IMAP+SMTP | 使用授权码登录，非邮箱密码 |
| 新浪邮箱 | IMAP+SMTP | 使用授权码 |
| Foxmail | IMAP+SMTP | 同 QQ 邮箱配置 |
| Yahoo Mail | IMAP+SMTP | 两步验证需使用应用专用密码 |
| iCloud Mail | IMAP+SMTP | 需生成 App-Specific Password |
| Zoho Mail | IMAP+SMTP | 标准 IMAP/SMTP 配置 |
| Exchange Server（本地部署） | Exchange | 需安装 exchangelib |

## 安装

```bash
pip install ymailink
```

可选组件：

```bash
pip install ymailink[outlook]     # Microsoft Graph API 支持
pip install ymailink[gmail]       # Google Gmail API 支持
pip install ymailink[keyring]     # 系统密钥环密码存储
pip install ymailink[exchange]    # Microsoft Exchange 支持
pip install ymailink[ai]          # AI 邮件助手功能
pip install ymailink[all]         # 安装所有可选功能
```

需要 Python 3.11+。

## 快速开始

### 1. 创建配置文件

创建 `~/.config/ymailink/config.toml`：

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

send.backend.type = "smtp"
send.backend.host = "smtp.example.com"
send.backend.port = 587
send.backend.encryption = "start-tls"
send.backend.login = "user@example.com"
send.backend.auth.type = "password"
send.backend.auth.cmd = "pass show email/smtp"

[ai]
api-key = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

也可以使用交互式配置向导（配置会输出到终端，手动复制到配置文件中）：

```bash
ymailink account configure
```

### 2. 测试连接

```bash
ymailink account doctor
```

### 3. 查看邮件

```bash
ymailink mail list
```

## 使用说明

### 全局选项

| 参数 | 说明 |
|------|------|
| `-c`、`--config` | 配置文件路径（可重复使用以实现深度合并） |
| `-o`、`--output` | 输出格式：`plain`（默认）或 `json` |
| `-a`、`--account` | 账户名称（默认使用配置中设定的默认账户） |
| `-q`、`--quiet` | 隐藏非错误日志输出 |
| `--debug` | 启用调试日志 |
| `-V`、`--version` | 显示版本号 |

### 命令列表

| 命令 | 说明 |
|------|------|
| `account list` | 列出已配置的账户 |
| `account doctor` | 诊断账户连接 |
| `account configure` | 交互式配置向导 |
| `folder list` | 列出所有文件夹 |
| `folder add <name>` | 创建文件夹 |
| `folder delete <name>` | 删除文件夹 |
| `folder expunge <name>` | 清除已删除邮件 |
| `folder purge <name>` | 清空文件夹中所有邮件 |
| `mail list [-f FOLDER] [-p PAGE] [-s SIZE] [-q QUERY]` | 列出邮件（默认收件箱） |
| `mail thread <id> [-f FOLDER]` | 查看邮件会话 |
| `mail read <id> [-f FOLDER]` | 阅读邮件（标记为已读） |
| `mail write [--headers K:V ...]` | 通过 `$EDITOR` 交互式撰写 |
| `mail send [raw]` | 从文件或标准输入发送原始邮件 |
| `mail reply <id> [-f FOLDER] [--all]` | 回复邮件 |
| `mail forward <id> [-f FOLDER]` | 转发邮件 |
| `mail copy <ids...> -t TARGET [-f FOLDER]` | 复制邮件到文件夹 |
| `mail move <ids...> -t TARGET [-f FOLDER]` | 移动邮件到文件夹 |
| `mail delete <ids...> [-f FOLDER]` | 删除邮件 |
| `mail download <ids...> [-f FOLDER] [-d DIR]` | 下载邮件为 .eml 文件 |
| `flag add <ids...> -g FLAGS... [-f FOLDER]` | 添加标记 |
| `flag set <ids...> -g FLAGS... [-f FOLDER]` | 替换所有标记 |
| `flag remove <ids...> -g FLAGS... [-f FOLDER]` | 移除标记 |
| `attachment download <id> [-f FOLDER] [-d DIR]` | 下载附件 |
| `template write` | 生成空白撰写模板 → 标准输出 |
| `template reply <id> [-f FOLDER] [--all]` | 生成回复模板 → 标准输出 |
| `template forward <id> [-f FOLDER]` | 生成转发模板 → 标准输出 |
| `template save [raw]` | 将模板保存为草稿 |
| `template send [raw]` | 从文件或标准输入发送模板 |
| `ai short-summary <id> [-f FOLDER]` | 精简总结（一行） |
| `ai summary <id> [-f FOLDER]` | 详细总结 |
| `ai rapid-reply <id> [-f FOLDER]` | 快速回复建议（3条） |

不传任何参数直接运行 `ymailink` 等同于：`ymailink mail list --folder INBOX --page 1 --page-size 20`

### 使用示例

```bash
# 查看特定文件夹中的邮件
ymailink mail list --folder "Sent"

# 搜索邮件
ymailink mail list --query "from:john@example.com subject:meeting"

# 分页显示
ymailink mail list --page 2 --page-size 10

# 阅读邮件
ymailink mail read 42

# 从文件发送邮件
ymailink mail send message.txt

# 管道发送邮件
cat message.txt | ymailink mail send

# 回复邮件（回复所有人）
ymailink mail reply 42 --all

# 移动多封邮件到归档
ymailink mail move 42 43 44 --target "Archive"

# 复制邮件
ymailink mail copy 55 56 --target "Important"

# 管理标记
ymailink flag add 42 --flags seen --flags flagged

# 下载附件
ymailink attachment download 42 --dir ~/Downloads

# 下载邮件为 .eml 格式
ymailink mail download 42 43 --dir ~/MailArchive

# 模板管道（离线撰写，稍后发送）
ymailink template write > msg.txt
vim msg.txt
ymailink template send msg.txt

# JSON 输出，便于脚本处理
ymailink --output json mail list

# 切换账户
ymailink --account work mail list

# AI 邮件助手
ymailink ai short-summary 42
ymailink ai summary 42
ymailink ai rapid-reply 42
```

### 可用标记

`seen`（已读）、`answered`（已回复）、`flagged`（星标）、`deleted`（已删除）、`draft`（草稿）

## 配置参考

详细配置文档请参阅 [`skill/references/configuration.md`](skill/references/configuration.md)。

### 后端类型

| 后端 | 读邮件 | 发邮件 | 认证方式 |
|------|--------|--------|----------|
| IMAP | imapclient | — | 密码（明文/命令/密钥环） |
| SMTP | — | aiosmtplib | 密码（明文/命令/密钥环） |
| Outlook | Microsoft Graph API | Microsoft Graph API | OAuth2 |
| Gmail | Google Gmail API | Google Gmail API | OAuth2 |
| Exchange | exchangelib | exchangelib | 密码（自动/NTLM/基本） |

## 邮件撰写

ymailink 使用标准的 RFC 822 格式。完整参考请参阅 [`skill/references/message-composition.md`](skill/references/message-composition.md)。

最小邮件示例：

```
From: You <you@example.com>
To: recipient@example.com
Subject: Hello

Message body here.
```

## 项目结构

```
ymailink/
  src/ymailink/
    cli.py              — Argparse CLI 调度器（延迟导入）
    backend/            — 后端实现（IMAP、SMTP、Outlook、Gmail、Exchange）
    commands/           — 命令处理（account、folder、mail、flag、attachment、template、ai）
    config/             — 配置加载和 Pydantic 模型
    ai/                 — AI API 客户端和请求数据组装
    domain/             — 领域模型（Summary、Message、Flag、Folder、Attachment、Account）
    output/             — 输出格式（plain、JSON、Rich 表格）
    utils/              — 工具（编辑器、密码解析、日志、路径）
  tests/                — 单元测试和集成测试
  skill/                — Claude Code skill 和文档参考
```

## 开发

```bash
git clone https://github.com/lizhisec/ymailink
cd ymailink
pip install -e ".[dev,all]"
pytest tests/
```

## 后端注意事项

- **IMAP 删除是硬删除**（设置 `\Deleted` 标记 + EXPUNGE）— 邮件会被永久移除。
- **Gmail 删除**会移至垃圾箱（不是硬删除）。
- **非 IMAP 后端的附件下载**（Outlook/Gmail/Exchange）仅返回元数据 — 这些后端的二进制数据下载暂不支持。
- **代理支持**：为 Outlook 和 Gmail 后端设置 `HTTPS_PROXY` / `https_proxy` 环境变量。

---

## 许可证

MIT

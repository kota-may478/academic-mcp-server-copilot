# Japanese follows English

## Academic MCP Server

Single local stdio MCP server for academic paper search across Semantic Scholar, arXiv, and Crossref.

This repository provides one MCP server process, not three separate servers. The MCP entrypoint is intentionally thin, while API-specific behavior is split into dedicated connector modules and shared normalization helpers.

## What It Does

- Exposes paper-search tools to GitHub Copilot in VS Code through MCP.
- Searches Semantic Scholar, arXiv, and Crossref from one server.
- Normalizes paper metadata into a shared schema where practical.
- Uses VS Code MCP input variables so secrets are not committed to the repository.
- Sends logging to stderr only, which is safe for stdio MCP transport.

## Prerequisites

- Python 3.11 or newer
- A local virtual environment at `.venv`
- VS Code with GitHub Copilot and MCP support enabled

Semantic Scholar API access works without an API key at lower public limits, but an API key is strongly recommended because the public tier can return HTTP 429 quickly. Crossref requires a contact email for responsible API identification.

## Installation

From the workspace root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Configuration

The workspace includes `.vscode/mcp.json`, which launches the server with the workspace-local Python interpreter:

- Semantic Scholar API key: prompted through a VS Code MCP input variable, optional
- Contact email: prompted through a VS Code MCP input variable, required for Crossref and server identification

Environment variables consumed by the server:

- `ACADEMIC_MCP_SEMANTIC_SCHOLAR_API_KEY`
- `ACADEMIC_MCP_CONTACT_EMAIL`
- `ACADEMIC_MCP_REQUEST_TIMEOUT_SECONDS` (optional, default `20`)
- `ACADEMIC_MCP_CACHE_TTL_SECONDS` (optional, default `300`)
- `ACADEMIC_MCP_DEFAULT_LIMIT` (optional, default `10`)

## Available Tools

- `semantic_scholar_search`: search Semantic Scholar by keyword
- `semantic_scholar_paper`: fetch a single Semantic Scholar paper by identifier
- `arxiv_search`: search arXiv via the Atom API
- `crossref_search_works`: search Crossref works metadata
- `crossref_work_by_doi`: fetch a Crossref work by DOI
- `search_papers`: run a normalized cross-source search from one tool call

The normalized paper response includes fields such as source, source ID, title, authors, abstract, publication date, DOI, venue, URL, PDF URL, citation count, and subjects when the upstream source provides them.

## Run In VS Code

1. Open this workspace in VS Code.
2. Install the package into the workspace `.venv` with `python -m pip install -e .`.
3. Open `.vscode/mcp.json` and verify the server entry points at `${workspaceFolder}/.venv/Scripts/python.exe`.
4. Start the server from the MCP UI or run `MCP: List Servers` and start `academicPaperSearch`.
5. Enter the requested MCP input values when VS Code prompts for them.

If tool metadata does not refresh after edits, run `MCP: Reset Cached Tools` and restart the server.

## Security Notes

- Real secrets are not stored in tracked files.
- `.vscode/mcp.json` uses VS Code MCP input variables rather than hardcoded credentials.
- Local secret files such as `.env` are ignored by `.gitignore`.
- This server writes logs to stderr only so MCP protocol traffic on stdout remains clean.

## Notes On API Behavior

- Semantic Scholar sends `x-api-key` only when a key is configured.
- arXiv uses the legacy query API and enforces single-request behavior with at least a 3-second interval between requests.
- Crossref always sends both `mailto` and `User-Agent` using the configured contact email.
- Unified search returns partial results with per-source errors when one upstream service fails.

---

## Academic MCP Server 日本語

Semantic Scholar、arXiv、Crossref を 1 つのローカル stdio MCP サーバーから検索できるリポジトリです。

この実装は 3 つの別サーバーではなく、1 つの MCP サーバープロセスとして動作します。一方で内部実装は API ごとにコネクタを分離し、正規化や設定は共通モジュールにまとめています。

## できること

- VS Code の GitHub Copilot から MCP ツールとして論文検索を利用できます。
- Semantic Scholar、arXiv、Crossref を単一サーバーで扱えます。
- 可能な範囲で論文メタデータを共通スキーマへ正規化します。
- VS Code MCP の入力変数を使うため、秘密情報をリポジトリへコミットしません。
- stdio MCP で問題にならないよう、ログは stdout ではなく stderr にのみ出力します。

## 前提条件

- Python 3.11 以上
- `.venv` という名前のローカル仮想環境
- GitHub Copilot と MCP が利用できる VS Code

Semantic Scholar は API キーなしでも使えますが、公開レート制限により HTTP 429 が出やすいため API キーの利用を強く推奨します。Crossref では責任ある識別のため連絡先メールアドレスが必要です。

## セットアップ

ワークスペース直下で実行してください。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

macOS / Linux の場合:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## 設定

ワークスペースには `.vscode/mcp.json` が含まれており、ワークスペース内の Python 実行環境からサーバーを起動します。

- Semantic Scholar API キー: VS Code MCP の入力変数で入力、任意
- 連絡先メールアドレス: VS Code MCP の入力変数で入力、Crossref とサーバー識別のため必須

サーバーが利用する環境変数:

- `ACADEMIC_MCP_SEMANTIC_SCHOLAR_API_KEY`
- `ACADEMIC_MCP_CONTACT_EMAIL`
- `ACADEMIC_MCP_REQUEST_TIMEOUT_SECONDS`（任意、既定値 `20`）
- `ACADEMIC_MCP_CACHE_TTL_SECONDS`（任意、既定値 `300`）
- `ACADEMIC_MCP_DEFAULT_LIMIT`（任意、既定値 `10`）

## 利用できるツール

- `semantic_scholar_search`: Semantic Scholar のキーワード検索
- `semantic_scholar_paper`: Semantic Scholar の単一論文取得
- `arxiv_search`: arXiv Atom API による検索
- `crossref_search_works`: Crossref works 検索
- `crossref_work_by_doi`: DOI から Crossref の単一 work を取得
- `search_papers`: 複数ソースを横断した正規化済み検索

返却データには、source、source ID、title、authors、abstract、publication date、DOI、venue、URL、PDF URL、citation count、subjects など、各 API が提供する範囲の共通項目が含まれます。

## VS Code での使い方

1. このワークスペースを VS Code で開きます。
2. `.venv` に対して `python -m pip install -e .` を実行します。
3. `.vscode/mcp.json` の `command` が `${workspaceFolder}/.venv/Scripts/python.exe` を指していることを確認します。
4. MCP UI から起動するか、`MCP: List Servers` で `academicPaperSearch` を起動します。
5. VS Code に求められた入力値を登録します。

ツール一覧が更新されない場合は、`MCP: Reset Cached Tools` を実行してからサーバーを再起動してください。

## セキュリティに関する注意

- 実際の秘密情報は追跡対象ファイルに保存しません。
- `.vscode/mcp.json` はハードコードではなく VS Code MCP 入力変数を使います。
- `.env` などのローカル秘密情報ファイルは `.gitignore` で除外しています。
- stdout は MCP プロトコル用に空け、ログは stderr のみに出力します。

## API ごとの挙動

- Semantic Scholar は API キーが設定されている場合のみ `x-api-key` を送信します。
- arXiv は legacy query API を使い、単一接続かつ 3 秒以上の間隔を強制します。
- Crossref には設定した連絡先メールアドレスを使って `mailto` と `User-Agent` を常に付与します。
- 横断検索では一部ソースが失敗しても、成功したソースの結果を返しつつエラー内容を含めます。

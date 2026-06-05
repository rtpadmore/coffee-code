# Guam GSA Procurement MCP Server

This project is a small MCP server for searching public procurement document
links from the Guam General Services Agency (GSA).

The official source is the Guam GSA Invitation for Bid page:

https://gsa.doa.guam.gov/invitation-for-bid/

Guam GSA publishes IFBs, RFPs, amendments, bid status notices, intent-of-award
notices, cancellations, and signed contract links on that page.

## Install

From this directory:

```bash
python -m pip install -r requirements.txt
```

To install it as a reusable command:

```bash
python -m pip install .
```

That installs this console command:

```bash
guam-procurement-mcp
```

To install from GitHub after this folder is pushed:

```bash
python -m pip install "git+https://github.com/CCF-AI-Officers-Summit-2026/coffee-code.git@main#subdirectory=guam-procurement"
```

## Run

```bash
python server.py
```

Or, after package install:

```bash
python -m guam_procurement_mcp
```

Both commands start a stdio MCP server. The package also installs a
`guam-procurement-mcp` console command when your Python scripts directory is on
`PATH`. MCP clients such as Codex, Claude Code, or the MCP Inspector can start
the server and call its tools.

## Connect To An MCP Client

### Codex

After installing the package, add this to `~/.codex/config.toml` or to a
trusted project's `.codex/config.toml`:

```toml
[mcp_servers.guam-procurement]
command = "python"
args = ["-m", "guam_procurement_mcp"]
startup_timeout_sec = 20
tool_timeout_sec = 60

[mcp_servers.guam-procurement.tools.search_procurement_documents]
approval_mode = "approve"
```

The same config is available at
`mcp-configs/codex.config.example.toml`.

### Claude Code

After installing the package, add this to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "guam-procurement": {
      "command": "python",
      "args": ["-m", "guam_procurement_mcp"]
    }
  }
}
```

The same config is available at
`mcp-configs/claude-code.settings.example.json`.

This workspace also includes `.claude/settings.json` configured to run the
server directly from `/workspaces/coffee-code/guam-procurement`.

## Tools

### `search_procurement_documents`

Searches official Guam GSA procurement document links by keyword.

Parameters:

- `query`: Keyword or phrase, such as `office space`, `award`, `signed contract`,
  `copier`, or `GSA-010-23`.
- `year`: Optional four-digit year, such as `2026` or `2023`.
- `max_results`: Number of results to return, from 1 to 50.

Each result includes:

- `title`
- `url`
- `kind`
- `year`
- `solicitation_number`
- `source`
- `source_url`

Example user questions:

- Find 2026 Guam GSA procurement documents about office space.
- Search Guam GSA procurement records for signed contracts.
- Find bid status or award notices related to copier leases.

## Example Direct Test

```bash
python - <<'PY'
import asyncio
import server

async def main():
    result = await server.search_procurement_documents(
        "amendment",
        year=2026,
        max_results=3,
    )
    print(result)

asyncio.run(main())
PY
```

## Test

From this directory:

```bash
python -m unittest discover -s tests
```

## Build A Wheel

From this directory:

```bash
python -m pip wheel . --no-deps --no-build-isolation -w dist
```

The generated wheel in `dist/` can be shared with another Python environment
and installed with:

```bash
python -m pip install dist/guam_procurement_mcp-0.1.0-py3-none-any.whl
```

## Limitations

- This first version searches document link titles and URLs on the official GSA
  page.
- PDF body text is not searched yet.
- The live tool depends on the Guam GSA website being reachable from the
  environment where the MCP server is running.

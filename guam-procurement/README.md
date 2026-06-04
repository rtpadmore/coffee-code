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

## Run

```bash
python server.py
```

This starts a stdio MCP server. MCP clients such as Codex, Claude Code, or the
MCP Inspector can start this command and call its tools.

## Tools

### `search_procurement_documents`

Searches official Guam GSA procurement document links by keyword.

Parameters:

- `query`: Keyword or phrase, such as `office space`, `award`, `signed contract`,
  `copier`, or `GSA-010-23`.
- `year`: Optional four-digit year, such as `2026` or `2023`.
- `max_results`: Number of results to return, from 1 to 50.

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
        "office space",
        year=2026,
        max_results=3,
    )
    print(result)

asyncio.run(main())
PY
```

## Limitations

- This first version searches document link titles and URLs on the official GSA
  page.
- It does not read the full text inside linked PDFs yet.
- The live tool depends on the Guam GSA website being reachable from the
  environment where the MCP server is running.

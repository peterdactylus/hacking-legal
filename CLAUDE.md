# EQS Legal Investigation MCP Server

## Challenge

Munich Hacking Legal 2026 — EQS Group. Build an AI agent embedded in EQS Integrity Line supporting compliance investigators in two modes:

1. **Legal Q&A**: Answer jurisdiction-specific legal questions during an investigation (interview recording rules, works council involvement, GDPR email review, suspension requirements)
2. **Draft Review**: Scan case record text and flag legally risky phrasing (allegations as established facts, intent speculation, premature liability conclusions), suggest safer alternatives

## EQS Integrity Line API

### Auth

- **OAuth endpoint**: `https://api.integrityline.com/oauth/token`
- **Grant type**: `client_credentials` (form-encoded POST)
- **Credentials**: stored in `credentials.json` (client_id, client_secret)
- **Token TTL**: access token 15 min, refresh token 45 min, session 24 hr
- **Token refresh**: re-POST to oauth endpoint; on 401, retry once with fresh token

### API Base URL

`https://api-compliance.eqscockpit.com/integrations` (EU environment)

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/integrityline/cases` | List cases (paginated, filterable) |
| GET | `/api/v1/integrityline/cases/{id}` | Full case details |

### Case List Query Params

- `pageSize`, `currentPage` (0-based)
- `fromCreatedDate`, `toCreatedDate` (ISO 8601)
- `hasExternalCaseId` (bool), `externalCaseId` (string)

### Case Detail Query Params

- `languageIso` — translate `mainFormData` content (e.g. `"en"`, `"de"`)
- `accept-language` header — sets response structure language

### Key Case Fields

| Field | Notes |
|-------|-------|
| `country.iso` | ISO country code — drives jurisdiction selection |
| `mainFormData` | Dynamic dict of intake form fields (the narrative) |
| `classification` | Case category (fraud, harassment, safety, etc.) |
| `status` | open, in_progress, completed, etc. |
| `severity` | Risk level |
| `assignee` | Investigator assigned |

## MCP Server Tools

| Tool | Purpose |
|------|---------|
| `list_cases` | Paginated case list from EQS |
| `get_case` | Full case details by ID |
| `get_jurisdiction_rules` | Statute lookup by country + topic |
| `get_investigation_checklist` | Required procedural steps for country + case type |
| `flag_risky_phrases` | Regex scan for legally dangerous phrasing in draft text |

## Legal Knowledge Base

Statutes covered per country JSON file in `mcp_server/knowledge/`:

- **EU.json** — GDPR (Art. 5, 6, 9, 88), EU Whistleblowing Directive 2019/1937
- **DE.json** — StGB §201 (recording), BDSG §26 (employee data), BetrVG §87 (works council), HinSchG (whistleblower protection)
- **FR.json** — Loi Sapin II, Code du travail, CNIL employee data guidelines
- **GB.json** — PIDA 1998, UK GDPR / DPA 2018, Employment Rights Act 1996

EU rules are always merged with country-specific rules when `get_jurisdiction_rules` is called.

## Risk Phrase Categories

| Category | Examples |
|----------|---------|
| `established_fact` | "clearly committed", "obviously violated", "is guilty", "is liable" |
| `intent_speculation` | "intended to", "deliberately", "knowingly", "planned to" |
| `premature_conclusion` | "is responsible for", "defrauded", "stole", "is the perpetrator" |

## Project Structure

```
Hackathon/
├── CLAUDE.md
├── Dockerfile
├── Justfile
├── .env                          # EQS_CLIENT_ID, EQS_CLIENT_SECRET (not committed)
├── sources/                      # Original challenge docs (PDF, DOCX)
└── mcp_server/
    ├── server.py                 # FastMCP server, tool definitions
    ├── eqs_client.py             # OAuth auth manager + EQS HTTP client
    ├── legal_kb.py               # Knowledge base loader
    ├── requirements.txt
    ├── knowledge/
    │   ├── EU.json
    │   ├── DE.json
    │   ├── FR.json
    │   └── GB.json
    └── tests/
        ├── test_eqs_client.py
        ├── test_legal_kb.py
        └── test_flag_phrases.py
```

## Running

```bash
just build          # Build Docker image
just start          # Run container (reads .env for credentials)
just stop           # Stop and remove container
just logs           # Tail container logs
just test           # Run pytest inside container
```

Create `.env` from credentials file:
```
EQS_CLIENT_ID=1424c483-57f4-4c5b-ad65-afb39f4529ec
EQS_CLIENT_SECRET=32703be645a7dab244a414714168b8da0b0ba3bd71ed2e8da642ba4aa89d81b5
EQS_OAUTH_ENDPOINT=https://api.integrityline.com/oauth/token
EQS_API_BASE=https://api-compliance.eqscockpit.com/integrations
```

MCP server runs on `http://localhost:8000/sse` (SSE transport).

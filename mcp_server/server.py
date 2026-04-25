"""EQS Legal Investigation MCP Server.

Exposes 5 tools for an LLM to support compliance investigators:
  - list_cases / get_case       : fetch EQS Integrity Line case data
  - get_jurisdiction_rules      : applicable statutes for a country + topic
  - get_investigation_checklist : required procedural steps
  - flag_risky_phrases          : detect legally dangerous phrasing in draft text
"""

import os
import re
from typing import Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from eqs_client import EQSClient
from legal_kb import get_jurisdiction_rules as _get_rules
from legal_kb import get_investigation_checklist as _get_checklist

load_dotenv()

mcp = FastMCP(
    "eqs-legal-investigation",
    instructions=(
        "You are a legal investigation assistant for EQS Integrity Line. "
        "Use the provided tools to fetch case data, look up jurisdiction-specific legal rules, "
        "and flag risky phrasing in draft case records. Always cite statutes when answering "
        "legal questions. Flag your uncertainty when legal advice is genuinely unclear."
    ),
)

_eqs_client: Optional[EQSClient] = None


def _client() -> EQSClient:
    global _eqs_client
    if _eqs_client is None:
        _eqs_client = EQSClient()
    return _eqs_client


# ---------------------------------------------------------------------------
# Tool 1: list_cases
# ---------------------------------------------------------------------------

@mcp.tool()
def list_cases(
    page_size: int = 20,
    current_page: int = 0,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    has_external_id: Optional[bool] = None,
    external_case_id: Optional[str] = None,
) -> dict:
    """List cases from EQS Integrity Line.

    Returns a paginated list of case summaries including id, issue number, status,
    short description, and country. Use the returned `id` with get_case to fetch
    full details.

    Args:
        page_size: Number of cases per page (default 20).
        current_page: Zero-based page index (default 0).
        from_date: ISO 8601 datetime — only return cases created on or after this date.
        to_date: ISO 8601 datetime — only return cases created on or before this date.
        has_external_id: Filter by whether an external case ID exists.
        external_case_id: Return the specific case matching this external ID.
    """
    return _client().list_cases(
        page_size=page_size,
        current_page=current_page,
        from_date=from_date,
        to_date=to_date,
        has_external_id=has_external_id,
        external_case_id=external_case_id,
    )


# ---------------------------------------------------------------------------
# Tool 2: get_case
# ---------------------------------------------------------------------------

@mcp.tool()
def get_case(case_id: int, translate_to: str = "en") -> dict:
    """Fetch full details of a single EQS Integrity Line case.

    Returns all case metadata and the full intake form data (mainFormData), which
    contains the investigator's narrative and reporter submission. The `country.iso`
    field identifies the jurisdiction for legal rule lookups.

    Args:
        case_id: Numeric case ID from EQS (use list_cases to find IDs).
        translate_to: ISO language code for translating mainFormData (default "en").
    """
    return _client().get_case(case_id, language_iso=translate_to)


# ---------------------------------------------------------------------------
# Tool 3: get_jurisdiction_rules
# ---------------------------------------------------------------------------

@mcp.tool()
def get_jurisdiction_rules(country_iso: str, topic: str) -> dict:
    """Return applicable legal rules for a given country and investigation topic.

    Always merges EU-level rules (GDPR, EU Whistleblowing Directive) with
    country-specific statutes. Use the `country.iso` field from get_case to
    determine the correct country code.

    Args:
        country_iso: ISO 3166-1 alpha-2 country code (e.g. "DE", "FR", "GB").
        topic: One of:
            - interview_recording    : rules on recording interviews
            - works_council          : employee representative consultation requirements
            - email_review           : lawfulness of accessing employee email
            - suspension             : rules on suspending an employee during investigation
            - gdpr_data_access       : lawful basis for accessing employee personal data
            - whistleblower_protection : reporter protection and confidentiality rules
            - data_retention         : case record retention requirements

    Returns:
        dict with keys:
            statute  : name and citation of the primary applicable statute
            rule     : plain-language summary of the rule
            caveats  : list of important nuances and practical warnings
    """
    try:
        return _get_rules(country_iso, topic)
    except KeyError as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Tool 4: get_investigation_checklist
# ---------------------------------------------------------------------------

@mcp.tool()
def get_investigation_checklist(country_iso: str, case_classification: str = "") -> list:
    """Return an ordered checklist of required procedural steps for this investigation.

    Steps are jurisdiction-specific and cover notification obligations, consent
    requirements, data protection steps, and documentation requirements.

    Args:
        country_iso: ISO 3166-1 alpha-2 country code (e.g. "DE", "FR", "GB").
        case_classification: Case type from EQS (e.g. "fraud", "harassment", "safety").
                             Used to add classification-specific steps.

    Returns:
        Ordered list of step strings, each referencing the applicable statute.
    """
    return _get_checklist(country_iso, case_classification)


# ---------------------------------------------------------------------------
# Tool 5: flag_risky_phrases
# ---------------------------------------------------------------------------

# Patterns: (regex, risk_type, suggestion_template)
_RISK_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # Established fact — asserting conclusions not yet proven
    (
        re.compile(
            r"\b(clearly|obviously|evidently|undoubtedly|certainly|unquestionably)\b",
            re.IGNORECASE,
        ),
        "established_fact",
        "Replace '{span}' with qualified language such as 'the evidence suggests' or 'it appears that'.",
    ),
    (
        re.compile(
            r"\b(is guilty|are guilty|is liable|are liable|is at fault|are at fault)\b",
            re.IGNORECASE,
        ),
        "established_fact",
        "Replace '{span}' with 'may be responsible for' or 'is alleged to have' — liability has not been established.",
    ),
    (
        re.compile(
            r"\b(committed (fraud|misconduct|bribery|theft|harassment|a crime|the offence|an offence))\b",
            re.IGNORECASE,
        ),
        "established_fact",
        "Replace '{span}' with 'is alleged to have committed' — the investigation has not yet established this as fact.",
    ),
    # Intent speculation — asserting mental state without evidence
    (
        re.compile(
            r"\b(intended to|deliberately|intentionally|knowingly|wilfully|on purpose|planned to|meant to)\b",
            re.IGNORECASE,
        ),
        "intent_speculation",
        "Replace '{span}' with 'the available evidence may indicate' or remove the intent characterisation — intent has not been established.",
    ),
    (
        re.compile(
            r"\b(concealed|hid|covered up|falsified|fabricated)\b",
            re.IGNORECASE,
        ),
        "intent_speculation",
        "Replace '{span}' with 'the records indicate a discrepancy' or 'documents were not produced' — avoid asserting purposeful concealment.",
    ),
    # Premature conclusion — prejudging the outcome
    (
        re.compile(
            r"\b(is (the )?(perpetrator|offender|wrongdoer))\b",
            re.IGNORECASE,
        ),
        "premature_conclusion",
        "Replace '{span}' with 'is the subject of the investigation' — no conclusion has been reached.",
    ),
    (
        re.compile(
            r"\b(defrauded|embezzled|stole|bribed|extorted)\b",
            re.IGNORECASE,
        ),
        "premature_conclusion",
        "Replace '{span}' with 'is alleged to have [defrauded/embezzled/stolen/etc.]' — the allegation has not been proven.",
    ),
    (
        re.compile(
            r"\b(is responsible for|bears responsibility for)\b",
            re.IGNORECASE,
        ),
        "premature_conclusion",
        "Replace '{span}' with 'may bear responsibility for' — responsibility has not been established.",
    ),
]


@mcp.tool()
def flag_risky_phrases(text: str) -> list:
    """Scan a draft case record for legally risky phrasing.

    Detects language that:
    - Treats unproven allegations as established facts
    - Speculates about intent or mental state
    - Draws premature conclusions about liability or guilt

    Use this before finalising any case record to reduce litigation risk.

    Args:
        text: The draft case record text to analyse.

    Returns:
        List of dicts, each with:
            span       : the matched text
            start      : character offset of match start
            end        : character offset of match end
            risk_type  : "established_fact" | "intent_speculation" | "premature_conclusion"
            suggestion : plain-language rewrite suggestion
        Returns an empty list if no risky phrases are detected.
    """
    flags: list[dict] = []
    seen_spans: set[tuple[int, int]] = set()

    for pattern, risk_type, suggestion_template in _RISK_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.start(), match.end()
            # Deduplicate overlapping matches
            if any(s <= start < e or s < end <= e for s, e in seen_spans):
                continue
            seen_spans.add((start, end))
            span = match.group()
            flags.append(
                {
                    "span": span,
                    "start": start,
                    "end": end,
                    "risk_type": risk_type,
                    "suggestion": suggestion_template.replace("{span}", span),
                }
            )

    # Sort by position in document
    flags.sort(key=lambda f: f["start"])
    return flags


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    mcp.run(transport="sse")

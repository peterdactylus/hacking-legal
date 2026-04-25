"""Legal knowledge base loader.

Loads per-country and EU-level statute data from JSON files in the knowledge/ directory.
Country-specific rules are always merged with EU baseline rules when looking up a topic.
"""

import json
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

_cache: dict[str, dict] = {}


def _load(country_iso: str) -> dict:
    if country_iso in _cache:
        return _cache[country_iso]
    path = KNOWLEDGE_DIR / f"{country_iso}.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    _cache[country_iso] = data
    return data


def _eu_rules() -> dict:
    return _load("EU")


def get_jurisdiction_rules(country_iso: str, topic: str) -> dict:
    """Return applicable rules for a given country and investigation topic.

    EU rules are always merged with country-specific rules. Country rules take
    precedence on the same topic key.

    Args:
        country_iso: ISO 3166-1 alpha-2 country code (e.g. "DE", "FR", "GB").
        topic: One of: interview_recording, works_council, email_review,
               suspension, gdpr_data_access, whistleblower_protection, data_retention.

    Returns:
        dict with keys: statute, rule, caveats

    Raises:
        KeyError: if the topic is not found in either the country or EU knowledge base.
    """
    eu = _eu_rules()
    country = _load(country_iso.upper())

    # Merge: country-specific overrides EU for the same topic
    merged: dict = {}
    if topic in eu:
        merged = dict(eu[topic])
    if topic in country:
        merged = dict(country[topic])

    if not merged:
        available = sorted(set(list(eu.keys()) + list(country.keys())))
        raise KeyError(
            f"Topic '{topic}' not found for country '{country_iso}'. "
            f"Available topics: {available}"
        )

    return merged


def get_investigation_checklist(country_iso: str, case_classification: str) -> list[str]:
    """Return required procedural steps for a case in a given jurisdiction.

    Args:
        country_iso: ISO 3166-1 alpha-2 country code.
        case_classification: Case type string from EQS (e.g. "fraud", "harassment").

    Returns:
        Ordered list of procedural step strings.
    """
    country = country_iso.upper()

    # Base steps applicable everywhere (EU Directive + GDPR)
    steps = [
        "Acknowledge receipt of report within 7 days (EU Whistleblowing Directive 2019/1937)",
        "Assign a designated investigator and document the assignment",
        "Assess whether the report falls within scope of the applicable whistleblower protection law",
        "Determine the lawful basis for processing personal data (GDPR Art. 6) and document it",
        "Conduct a proportionality assessment before accessing any employee personal data",
        "Preserve confidentiality of the reporter's identity throughout the investigation",
    ]

    # Country-specific additions
    if country == "DE":
        steps += [
            "Check whether works council (Betriebsrat) notification is required before accessing employee data (BetrVG §87)",
            "Verify all-party consent before recording any interview (StGB §201) — use written notes instead",
            "Determine whether private email use is permitted by policy before reviewing mailbox (BDSG §26 / TKG §88)",
            "If suspension is planned, ensure it is with pay and document the factual basis (BGB §626)",
            "Notify works council before any dismissal and allow 1-week hearing period (BetrVG §102)",
            "Provide feedback to the reporter within 3 months (HinSchG)",
        ]
    elif country == "FR":
        steps += [
            "Consult CSE (Comité Social et Économique) before implementing any monitoring measures",
            "Verify all-party consent before recording any interview (Code pénal Art. 226-1)",
            "Check CNIL guidelines before accessing employee email — especially if private use is permitted",
            "Follow Code du travail disciplinary procedure (convocation at least 5 working days before meeting)",
            "Provide feedback to the reporter within 3 months (Loi 2022-401)",
        ]
    elif country == "GB":
        steps += [
            "Inform the employee of the right to be accompanied at any disciplinary or investigatory meeting (ERA 1999 s.10)",
            "Follow ACAS Code of Practice on Disciplinary and Grievance Procedures",
            "Conduct a Data Protection Impact Assessment (DPIA) if systematic email monitoring is planned",
            "Review DPA 2018 Sch. 2 Para. 29 if withholding information from a subject access request during active investigation",
            "Ensure any suspension is on full pay unless contract expressly provides otherwise",
            "Provide feedback to the reporter within 3 months (PIDA 1998 / ERA 1996 s.43A)",
        ]

    # Classification-specific additions
    classification_lower = (case_classification or "").lower()
    if any(k in classification_lower for k in ("fraud", "financial", "bribery", "corruption")):
        steps.append(
            "Consider whether mandatory reporting obligations to financial regulators apply "
            "(e.g. BaFin in DE, AMF in FR, FCA in GB)"
        )
    if any(k in classification_lower for k in ("harassment", "discrimination", "bullying")):
        steps.append(
            "Ensure the subject of the report and any witnesses are interviewed separately "
            "and that anti-retaliation measures are in place for all parties"
        )
    if any(k in classification_lower for k in ("safety", "health", "environment")):
        steps.append(
            "Assess whether the matter requires immediate notification to a health & safety "
            "or environmental regulator"
        )

    steps.append(
        "Document all investigation steps contemporaneously with dates, persons involved, and findings"
    )
    steps.append(
        "Set a defined retention period for case records before closing the case (GDPR Art. 5(1)(e))"
    )

    return steps

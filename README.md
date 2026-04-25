# EQS Legal Investigation Assistant

An AI agent embedded in EQS Integrity Line that supports compliance investigators. It answers jurisdiction-specific legal questions and reviews draft case documents for legally risky language.

Built for the **Munich Hacking Legal 2026 — EQS Group** hackathon.

---

## What It Does

The assistant operates in two modes:

**Legal Q&A** — Answer questions that arise during an investigation: Can I record this interview? Do I need to involve the works council? Am I allowed to review the employee's inbox? Answers are scoped to the country the case was filed in and cite the applicable statute.

**Draft Review** — Scan investigator notes or case summaries for phrasing that could create legal exposure if the document were used in litigation or a regulatory review. Flags problematic language and suggests safer rewrites.

---

## Tools

### 1. List Cases

Retrieves a list of cases from EQS Integrity Line, filterable by date and status. Returns case number, status, short description, and country for each result.

### 2. Get Case Details

Fetches the full record for a single case: country, severity, status, assigned investigator, category, and the complete intake narrative. Supports automatic translation if the report was filed in another language.

The country the case was filed in determines which laws apply — Germany triggers works council rules and the German Whistleblower Protection Act, France triggers Code du travail equivalents, and so on.

### 3. Update Case

Links an external reference ID to a case in EQS — useful for connecting a case to a record in another system (e.g. an HR platform or ticketing tool).

### 4. List Languages

Returns the languages the EQS platform supports, including which ones have machine translation available for automatic report translation.

### 5. Get Jurisdiction Rules

Looks up the applicable legal rules for a country and topic. EU-level rules (GDPR, EU Whistleblowing Directive) are always included regardless of country.

| Topic | What it covers |
|-------|----------------|
| Interview recording | Whether recording is lawful and what consent is required |
| Works council / employee representatives | When and how employee representatives must be involved |
| Email and device review | Lawfulness of accessing an employee's communications |
| Suspension | Rules for suspending an employee during an investigation |
| Personal data access | GDPR and national rules on processing employee data |
| Whistleblower protection | Confidentiality obligations and anti-retaliation rules |
| Data retention | How long case records may be kept |

Countries currently in the knowledge base: **Germany**, **France**, **United Kingdom**.

Returns the statute name, a plain-language rule summary, and practical caveats.

> The quality of answers depends directly on the accuracy and completeness of what's stored in the knowledge base. Adding more countries, updating statutes, or refining the caveats immediately improves what the assistant tells investigators.

### 6. Get Investigation Checklist

Generates an ordered list of procedural steps for a case, tailored to the country and type of allegation. Each step references the statute that requires it. Steps adjust automatically by country and case category — for example, fraud cases include a prompt to consider regulator notification, harassment cases add a step on interviewing witnesses separately.

### 7. Flag Risky Phrases

Scans draft text and highlights language that could create legal risk. Three risk categories:

| Risk type | What it looks for | Example | Suggested fix |
|-----------|-------------------|---------|---------------|
| **Established fact** | Unproven allegation stated as confirmed | *"The employee clearly committed fraud"* | *"The evidence reviewed suggests the employee may have been involved in..."* |
| **Intent speculation** | Asserted state of mind without evidence | *"She deliberately concealed the records"* | *"The records were not produced during the review period"* |
| **Premature conclusion** | Guilt or liability assigned before the investigation is complete | *"He is responsible for the data breach"* | *"He is the subject of the investigation into the data breach"* |

Returns each flagged phrase with the category of risk and a concrete rewrite suggestion.

---

## Otto Schmidt Legal Database Tools

The assistant also has access to the Otto Schmidt Legal Data Hub — a comprehensive database of German and European legal sources including commentaries, court decisions, and statutory texts across multiple practice areas.

### 8. List Legal Data Assets

Returns all legal databases the account has access to. Each database covers a specific practice area (e.g. labour law, tenancy law, corporate law). The name returned is what gets passed to the other Otto Schmidt tools to scope the search.

### 9. Legal Semantic Search

Searches for relevant sections across a legal database using natural language. Returns ranked document excerpts from commentaries, court decisions, and legal articles. Useful for finding source material on a specific legal question without needing to know the exact statute.

### 10. Legal Q&A

Asks a natural language question against a specific legal database and returns an AI-generated answer with citations to the source documents used. Best for getting a direct answer to a concrete legal question with references attached.

### 11. Legal Clause Check

Analyzes a contract clause for legal validity and appropriateness. Checks the clause against applicable regulations and case law in the selected database, and returns an assessment with references to relevant statutes and precedents.

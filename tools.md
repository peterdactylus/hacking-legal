# Available Tools — EQS Legal Investigation Assistant

This document describes the five capabilities the AI assistant has access to when helping a compliance investigator. Each capability is a discrete action the assistant can take on its own when it needs information to answer a question or complete a task.

---

## 1. List Cases

**What it does:** Retrieves a list of cases currently stored in EQS Integrity Line.

**When the assistant uses it:** When an investigator asks to see open cases, find a specific case, or get an overview of recent reports. The assistant can filter by date or other criteria to narrow down the list.

**What it returns:** For each case: a case number, current status, a short description of the report, and the country it was filed in.

---

## 2. Get Case Details

**What it does:** Fetches the full record for a single case, including everything the reporter submitted and all metadata the investigator has filled in.

**When the assistant uses it:** When the investigator is working on a specific case and the assistant needs the actual content — the reported facts, the country, the category of the allegation — to give a relevant answer or review draft text.

**What it returns:** The complete case record: country, severity, status, assigned investigator, category, and the full narrative text from the intake form. If the case was filed in another language, the assistant can request an English translation automatically.

**Why the country field matters:** The country determines which laws apply. A case filed in Germany triggers German labour law, works council rules, and the German Whistleblower Protection Act. A case filed in France triggers French equivalents. The assistant uses the country to scope every legal answer it gives.

---

## 3. Get Jurisdiction Rules

**What it does:** Looks up the applicable legal rules for a specific country and topic, drawing from a built-in library of statutes and regulations.

**When the assistant uses it:** Whenever an investigator asks a legal question — "Can I record this interview?", "Do I need to involve the works council?", "Am I allowed to review the employee's inbox?" The assistant looks up the answer in the knowledge base and cites the relevant law.

**Topics covered:**

| Topic | What it covers |
|-------|---------------|
| Interview recording | Whether recording is lawful and what consent is required |
| Works council / employee representatives | When and how employee representatives must be involved |
| Email and device review | Lawfulness of accessing an employee's communications |
| Suspension | Rules for suspending an employee during an investigation |
| Personal data access | GDPR and national rules on processing employee data |
| Whistleblower protection | Confidentiality obligations and anti-retaliation rules |
| Data retention | How long case records may be kept |

**Countries currently in the knowledge base:** Germany, France, United Kingdom. EU-level rules (GDPR, EU Whistleblowing Directive 2019/1937) are always included regardless of country.

**What it returns:** The name of the applicable statute, a plain-language summary of the rule, and a list of important caveats and practical warnings.

> **Knowledge base note:** This is where the team's input has the most impact. The quality of the answers depends directly on the accuracy and completeness of the rules stored here. Adding more countries, updating statutes, or refining the caveats will immediately improve what the assistant tells investigators.

---

## 4. Get Investigation Checklist

**What it does:** Generates an ordered list of procedural steps the investigator should follow for a given case, tailored to the country and type of allegation.

**When the assistant uses it:** When an investigator opens a case and wants to know what they need to do, or when they ask "what am I missing?" The assistant builds a checklist from the applicable rules so nothing gets overlooked.

**What it returns:** A numbered list of steps, each referencing the statute that requires it. For example:
- *Acknowledge receipt of the report within 7 days (EU Whistleblowing Directive 2019/1937)*
- *Verify all-party consent before recording any interview (StGB §201)*
- *Notify the works council before any dismissal and allow a one-week hearing period (BetrVG §102)*

Steps are automatically adjusted based on:
- **Country** — German cases get BetrVG and HinSchG steps; French cases get Code du travail steps; UK cases get ACAS Code steps
- **Case category** — fraud cases add a prompt to consider regulator notification; harassment cases add a step on interviewing witnesses separately; safety cases flag potential regulatory reporting obligations

---

## 5. Flag Risky Phrases

**What it does:** Scans a piece of draft text — typically an investigator's case notes or summary — and highlights language that could create legal risk for the company if the document were used as evidence in litigation or a regulatory review.

**When the assistant uses it:** During the write-up phase, when an investigator asks the assistant to review their draft. The assistant scans the text, identifies problematic phrases, explains why each one is risky, and suggests a safer alternative.

**Three categories of risk it detects:**

| Risk type | What it looks for | Example | Suggested fix |
|-----------|------------------|---------|---------------|
| **Established fact** | Language that states an unproven allegation as though it were confirmed | *"The employee clearly committed fraud"* | *"The evidence reviewed suggests the employee may have been involved in..."* |
| **Intent speculation** | Language that asserts the subject's state of mind without evidence | *"She deliberately concealed the records"* | *"The records were not produced during the review period"* |
| **Premature conclusion** | Language that assigns guilt, liability, or responsibility before the investigation is complete | *"He is responsible for the data breach"* | *"He is the subject of the investigation into the data breach"* |

**What it returns:** A list of flagged phrases, each with its position in the text, the category of risk, and a concrete rewrite suggestion. The assistant then elaborates on the reasoning and offers to rewrite the full passage if needed.

**What it does not do:** This tool performs an initial rule-based scan. The AI assistant then reasons over the results to provide context and nuance. It is not a substitute for legal review — it is a first filter to catch the most common and avoidable mistakes before a document leaves the investigation team.

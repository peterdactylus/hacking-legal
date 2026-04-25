"""Tests for the flag_risky_phrases tool."""

from server import flag_risky_phrases


class TestFlagRiskyPhrasesEstablishedFact:
    def test_flags_clearly(self):
        flags = flag_risky_phrases("The employee clearly committed fraud.")
        risk_types = [f["risk_type"] for f in flags]
        assert "established_fact" in risk_types

    def test_flags_obviously(self):
        flags = flag_risky_phrases("He obviously violated company policy.")
        assert any(f["risk_type"] == "established_fact" for f in flags)

    def test_flags_is_guilty(self):
        flags = flag_risky_phrases("The subject is guilty of misconduct.")
        assert any(f["risk_type"] == "established_fact" for f in flags)

    def test_flags_committed_fraud(self):
        flags = flag_risky_phrases("She committed fraud against the company.")
        assert any(f["risk_type"] == "established_fact" for f in flags)

    def test_flags_is_liable(self):
        flags = flag_risky_phrases("The manager is liable for the losses.")
        assert any(f["risk_type"] == "established_fact" for f in flags)


class TestFlagRiskyPhrasesIntentSpeculation:
    def test_flags_intended_to(self):
        flags = flag_risky_phrases("She intended to deceive the auditors.")
        assert any(f["risk_type"] == "intent_speculation" for f in flags)

    def test_flags_deliberately(self):
        flags = flag_risky_phrases("He deliberately withheld the information.")
        assert any(f["risk_type"] == "intent_speculation" for f in flags)

    def test_flags_knowingly(self):
        flags = flag_risky_phrases("The employee knowingly submitted false data.")
        assert any(f["risk_type"] == "intent_speculation" for f in flags)

    def test_flags_concealed(self):
        flags = flag_risky_phrases("The manager concealed the financial records.")
        assert any(f["risk_type"] == "intent_speculation" for f in flags)

    def test_flags_planned_to(self):
        flags = flag_risky_phrases("They planned to manipulate the accounts.")
        assert any(f["risk_type"] == "intent_speculation" for f in flags)


class TestFlagRiskyPhrasesPrematureConclusion:
    def test_flags_is_the_perpetrator(self):
        flags = flag_risky_phrases("The subject is the perpetrator of the scheme.")
        assert any(f["risk_type"] == "premature_conclusion" for f in flags)

    def test_flags_defrauded(self):
        flags = flag_risky_phrases("Mr Smith defrauded the organisation.")
        assert any(f["risk_type"] == "premature_conclusion" for f in flags)

    def test_flags_embezzled(self):
        flags = flag_risky_phrases("She embezzled funds over a period of two years.")
        assert any(f["risk_type"] == "premature_conclusion" for f in flags)

    def test_flags_is_responsible_for(self):
        flags = flag_risky_phrases("The director is responsible for the data breach.")
        assert any(f["risk_type"] == "premature_conclusion" for f in flags)


class TestFlagRiskyPhrasesNeutralText:
    def test_no_flags_on_neutral_text(self):
        flags = flag_risky_phrases(
            "The witness stated they observed the document being signed. "
            "A copy of the email was retrieved from the server. "
            "The investigation is ongoing."
        )
        assert flags == []

    def test_no_flags_on_factual_findings(self):
        flags = flag_risky_phrases(
            "According to the complainant, the transaction occurred on 14 March 2025. "
            "The subject denied involvement when interviewed on 20 March 2025. "
            "Financial records reviewed show a discrepancy of €12,000."
        )
        assert flags == []

    def test_no_flags_on_qualified_language(self):
        flags = flag_risky_phrases(
            "The evidence suggests the employee may have been involved. "
            "It appears that the records were altered, though this has not been confirmed. "
            "The subject is alleged to have submitted inaccurate reports."
        )
        assert flags == []


class TestFlagRiskyPhrasesFlagStructure:
    def test_flag_has_required_keys(self):
        flags = flag_risky_phrases("The employee clearly intended to defraud the company.")
        assert len(flags) > 0
        for flag in flags:
            assert "span" in flag
            assert "start" in flag
            assert "end" in flag
            assert "risk_type" in flag
            assert "suggestion" in flag

    def test_span_matches_text_slice(self):
        text = "The employee clearly committed fraud."
        flags = flag_risky_phrases(text)
        for flag in flags:
            assert text[flag["start"]:flag["end"]] == flag["span"]

    def test_flags_sorted_by_position(self):
        text = "She clearly intended to commit fraud and is liable."
        flags = flag_risky_phrases(text)
        positions = [f["start"] for f in flags]
        assert positions == sorted(positions)

    def test_suggestion_is_non_empty_string(self):
        flags = flag_risky_phrases("He deliberately concealed the evidence.")
        for flag in flags:
            assert isinstance(flag["suggestion"], str)
            assert len(flag["suggestion"]) > 0

    def test_risk_type_is_valid_value(self):
        valid_types = {"established_fact", "intent_speculation", "premature_conclusion"}
        flags = flag_risky_phrases(
            "She clearly intended to defraud the company and is the perpetrator."
        )
        for flag in flags:
            assert flag["risk_type"] in valid_types

    def test_case_insensitive_matching(self):
        flags_lower = flag_risky_phrases("he clearly committed fraud.")
        flags_upper = flag_risky_phrases("HE CLEARLY COMMITTED FRAUD.")
        assert len(flags_lower) == len(flags_upper)

    def test_empty_string_returns_empty_list(self):
        assert flag_risky_phrases("") == []

    def test_no_duplicate_spans_for_overlapping_patterns(self):
        text = "The subject clearly committed fraud."
        flags = flag_risky_phrases(text)
        spans = [(f["start"], f["end"]) for f in flags]
        assert len(spans) == len(set(spans))

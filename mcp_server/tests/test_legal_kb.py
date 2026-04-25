"""Tests for the legal knowledge base loader."""

import pytest

from legal_kb import get_jurisdiction_rules, get_investigation_checklist


class TestGetJurisdictionRules:
    def test_de_interview_recording_returns_expected_keys(self):
        result = get_jurisdiction_rules("DE", "interview_recording")

        assert "statute" in result
        assert "rule" in result
        assert "caveats" in result
        assert isinstance(result["caveats"], list)

    def test_de_interview_recording_cites_stgb(self):
        result = get_jurisdiction_rules("DE", "interview_recording")
        assert "StGB" in result["statute"]

    def test_de_whistleblower_protection_cites_hinschg(self):
        result = get_jurisdiction_rules("DE", "whistleblower_protection")
        assert "HinSchG" in result["statute"] or "HinSchG" in result["rule"]

    def test_eu_gdpr_rule_returned_for_all_countries(self):
        """gdpr_data_access is an EU-level rule — should work for any supported country."""
        for country in ("DE", "FR", "GB"):
            result = get_jurisdiction_rules(country, "gdpr_data_access")
            assert "statute" in result
            assert "GDPR" in result["statute"] or "GDPR" in result["rule"] or "UK GDPR" in result["statute"]

    def test_eu_rules_merged_with_country_rules(self):
        """DE gdpr_data_access should come from DE.json (overrides EU baseline)."""
        result = get_jurisdiction_rules("DE", "gdpr_data_access")
        # DE.json has BDSG §26 as the primary statute
        assert "BDSG" in result["statute"]

    def test_country_fallback_to_eu_for_data_retention(self):
        """data_retention is only in EU.json — should still be returned for DE."""
        result = get_jurisdiction_rules("DE", "data_retention")
        assert "GDPR" in result["statute"]

    def test_fr_works_council_cites_code_du_travail(self):
        result = get_jurisdiction_rules("FR", "works_council")
        assert "Code du travail" in result["statute"] or "Code du travail" in result["rule"]

    def test_gb_whistleblower_cites_pida(self):
        result = get_jurisdiction_rules("GB", "whistleblower_protection")
        assert "PIDA" in result["statute"] or "PIDA" in result["rule"]

    def test_unknown_topic_raises_key_error(self):
        with pytest.raises(KeyError, match="not found"):
            get_jurisdiction_rules("DE", "nonexistent_topic_xyz")

    def test_unknown_country_falls_back_to_eu_or_raises(self):
        """Unknown country with an EU-level topic should return EU rules."""
        result = get_jurisdiction_rules("XX", "gdpr_data_access")
        assert "statute" in result

    def test_unknown_country_unknown_topic_raises_key_error(self):
        with pytest.raises(KeyError):
            get_jurisdiction_rules("XX", "nonexistent_topic_xyz")

    def test_lowercase_country_iso_normalised(self):
        """Country ISO should be case-insensitive."""
        result_upper = get_jurisdiction_rules("DE", "works_council")
        result_lower = get_jurisdiction_rules("de", "works_council")
        assert result_upper == result_lower


class TestGetInvestigationChecklist:
    def test_returns_list_of_strings(self):
        result = get_investigation_checklist("DE", "fraud")
        assert isinstance(result, list)
        assert all(isinstance(step, str) for step in result)
        assert len(result) > 0

    def test_de_checklist_includes_works_council_step(self):
        result = get_investigation_checklist("DE", "harassment")
        combined = " ".join(result)
        assert "BetrVG" in combined or "works council" in combined.lower()

    def test_de_checklist_includes_recording_rule(self):
        result = get_investigation_checklist("DE", "fraud")
        combined = " ".join(result)
        assert "StGB" in combined

    def test_fr_checklist_includes_cse(self):
        result = get_investigation_checklist("FR", "fraud")
        combined = " ".join(result)
        assert "CSE" in combined

    def test_gb_checklist_includes_acas(self):
        result = get_investigation_checklist("GB", "misconduct")
        combined = " ".join(result)
        assert "ACAS" in combined

    def test_fraud_classification_adds_regulator_step(self):
        result = get_investigation_checklist("DE", "financial fraud")
        combined = " ".join(result)
        assert "BaFin" in combined or "regulat" in combined.lower()

    def test_harassment_classification_adds_interview_step(self):
        result = get_investigation_checklist("DE", "harassment")
        combined = " ".join(result)
        assert "witness" in combined.lower() or "separately" in combined.lower()

    def test_empty_classification_returns_base_steps(self):
        result = get_investigation_checklist("DE", "")
        assert len(result) > 0
        combined = " ".join(result)
        assert "GDPR" in combined

    def test_all_steps_end_without_trailing_whitespace(self):
        result = get_investigation_checklist("GB", "fraud")
        for step in result:
            assert step == step.strip()

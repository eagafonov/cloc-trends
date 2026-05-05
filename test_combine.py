#!/usr/bin/env python3
"""Unit tests for parsing SccReport from JSON data."""

import json
from datetime import datetime, timezone, timedelta
import pytest
from combine import SccReport, CommitDates, LanguageStats


SAMPLE_SCC_JSON = {
    "languages": [
        {"Name": "JSON", "Bytes": 500, "CodeBytes": 0, "Lines": 90768, "Code": 90768, "Comment": 0, "Blank": 0, "Complexity": 0, "Count": 27, "WeightedComplexity": 0, "Files": [], "LineLength": None, "ULOC": 0},
        {"Name": "TypeScript", "Bytes": 2000, "CodeBytes": 0, "Lines": 60989, "Code": 49441, "Comment": 4781, "Blank": 6767, "Complexity": 100, "Count": 368, "WeightedComplexity": 0, "Files": [], "LineLength": None, "ULOC": 0},
        {"Name": "Markdown", "Bytes": 800, "CodeBytes": 0, "Lines": 926, "Code": 705, "Comment": 0, "Blank": 221, "Complexity": 0, "Count": 7, "WeightedComplexity": 0, "Files": [], "LineLength": None, "ULOC": 0},
        {"Name": "JavaScript", "Bytes": 300, "CodeBytes": 0, "Lines": 364, "Code": 229, "Comment": 79, "Blank": 56, "Complexity": 5, "Count": 5, "WeightedComplexity": 0, "Files": [], "LineLength": None, "ULOC": 0},
        {"Name": "YAML", "Bytes": 200, "CodeBytes": 0, "Lines": 282, "Code": 210, "Comment": 56, "Blank": 16, "Complexity": 0, "Count": 2, "WeightedComplexity": 0, "Files": [], "LineLength": None, "ULOC": 0},
        {"Name": "CSS", "Bytes": 100, "CodeBytes": 0, "Lines": 72, "Code": 59, "Comment": 0, "Blank": 13, "Complexity": 0, "Count": 2, "WeightedComplexity": 0, "Files": [], "LineLength": None, "ULOC": 0},
        {"Name": "Bourne Shell", "Bytes": 50, "CodeBytes": 0, "Lines": 48, "Code": 30, "Comment": 8, "Blank": 10, "Complexity": 2, "Count": 2, "WeightedComplexity": 0, "Files": [], "LineLength": None, "ULOC": 0},
        {"Name": "Dockerfile", "Bytes": 40, "CodeBytes": 0, "Lines": 51, "Code": 24, "Comment": 13, "Blank": 14, "Complexity": 0, "Count": 1, "WeightedComplexity": 0, "Files": [], "LineLength": None, "ULOC": 0},
    ],
    "commit": {
        "sha": "abc123def456",
        "author_date": "2026-03-05T12:02:13-08:00",
        "commit_date": "2026-03-12T15:33:20-07:00",
    },
}


class TestSccReportFromDict:
    """Tests for SccReport.from_dict() class method."""

    def test_parses_full_report(self):
        report = SccReport.from_dict(SAMPLE_SCC_JSON)

        assert isinstance(report, SccReport)
        assert isinstance(report.commit, CommitDates)
        assert report.summary is not None

    def test_commit_dates(self):
        report = SccReport.from_dict(SAMPLE_SCC_JSON)

        assert isinstance(report.commit.author_date, datetime)
        assert isinstance(report.commit.commit_date, datetime)

        expected_author = datetime(
            2026, 3, 5, 12, 2, 13, tzinfo=timezone(timedelta(hours=-8))
        )
        expected_commit = datetime(
            2026, 3, 12, 15, 33, 20, tzinfo=timezone(timedelta(hours=-7))
        )
        assert report.commit.author_date == expected_author
        assert report.commit.commit_date == expected_commit

    def test_languages_parsed(self):
        report = SccReport.from_dict(SAMPLE_SCC_JSON)

        expected_languages = {
            "JSON",
            "TypeScript",
            "Markdown",
            "JavaScript",
            "YAML",
            "CSS",
            "Bourne Shell",
            "Dockerfile",
        }
        assert set(report.languages.keys()) == expected_languages

    def test_language_stats_values(self):
        report = SccReport.from_dict(SAMPLE_SCC_JSON)

        ts = report.languages["TypeScript"]
        assert ts.nFiles == 368
        assert ts.blank == 6767
        assert ts.comment == 4781
        assert ts.code == 49441

    def test_language_with_spaces_in_name(self):
        report = SccReport.from_dict(SAMPLE_SCC_JSON)

        shell = report.languages["Bourne Shell"]
        assert shell.nFiles == 2
        assert shell.blank == 10
        assert shell.comment == 8
        assert shell.code == 30

    def test_summary_computed(self):
        report = SccReport.from_dict(SAMPLE_SCC_JSON)

        assert report.summary is not None
        assert report.summary.nFiles == 414
        assert report.summary.blank == 7097
        assert report.summary.comment == 4937
        assert report.summary.code == 141466

    def test_single_language(self):
        data = {
            "languages": [
                {"Name": "Go", "Bytes": 1000, "CodeBytes": 0, "Lines": 5150, "Code": 5000, "Comment": 50, "Blank": 100, "Complexity": 10, "Count": 42, "WeightedComplexity": 0, "Files": [], "LineLength": None, "ULOC": 0},
            ],
            "commit": SAMPLE_SCC_JSON["commit"],
        }
        report = SccReport.from_dict(data)

        assert len(report.languages) == 1
        assert "Go" in report.languages
        assert report.languages["Go"].code == 5000

    def test_no_languages(self):
        data = {
            "languages": [],
            "commit": SAMPLE_SCC_JSON["commit"],
        }
        report = SccReport.from_dict(data)

        assert len(report.languages) == 0
        assert report.summary is not None
        assert report.summary.code == 0

    def test_language_stats_are_correct_type(self):
        report = SccReport.from_dict(SAMPLE_SCC_JSON)

        for name, stats in report.languages.items():
            assert isinstance(
                stats, LanguageStats
            ), f"Language '{name}' is not LanguageStats"

    def test_all_language_codes_sum_to_summary(self):
        report = SccReport.from_dict(SAMPLE_SCC_JSON)

        total_code = sum(lang.code for lang in report.languages.values())
        total_blank = sum(lang.blank for lang in report.languages.values())
        total_comment = sum(lang.comment for lang in report.languages.values())
        total_files = sum(lang.nFiles for lang in report.languages.values())

        assert total_code == report.summary.code
        assert total_blank == report.summary.blank
        assert total_comment == report.summary.comment
        assert total_files == report.summary.nFiles


class TestSccReportFromJson:
    """Tests for parsing SccReport from a JSON string (roundtrip)."""

    def test_parse_from_json_string(self):
        json_str = json.dumps(SAMPLE_SCC_JSON)
        data = json.loads(json_str)
        report = SccReport.from_dict(data)

        assert len(report.languages) == 8
        assert report.summary is not None

    def test_json_roundtrip_preserves_data(self):
        report = SccReport.from_dict(SAMPLE_SCC_JSON)
        dumped = report.model_dump()
        restored = SccReport(**dumped)

        assert restored.commit.author_date == report.commit.author_date
        assert set(restored.languages.keys()) == set(report.languages.keys())
        for lang_name in report.languages:
            assert (
                restored.languages[lang_name].code == report.languages[lang_name].code
            )


class TestSccReportValidationErrors:
    """Tests for invalid or incomplete input data."""

    def test_missing_commit_raises(self):
        data = {
            "languages": [
                {"Name": "Python", "Bytes": 100, "CodeBytes": 0, "Lines": 11, "Code": 10, "Comment": 0, "Blank": 1, "Complexity": 0, "Count": 1, "WeightedComplexity": 0, "Files": [], "LineLength": None, "ULOC": 0},
            ],
        }
        with pytest.raises(KeyError):
            SccReport.from_dict(data)

    def test_incomplete_language_entry_raises(self):
        data = {
            "languages": [
                {"Name": "Python", "Count": 10},  # missing Code, Comment, Blank
            ],
            "commit": SAMPLE_SCC_JSON["commit"],
        }
        with pytest.raises(Exception):
            SccReport.from_dict(data)

    def test_incomplete_commit_dates_raises(self):
        data = {
            "languages": [],
            "commit": {"author_date": "2026-01-01T00:00:00Z"},  # missing commit_date
        }
        with pytest.raises(Exception):
            SccReport.from_dict(data)

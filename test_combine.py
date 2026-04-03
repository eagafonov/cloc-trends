#!/usr/bin/env python3
"""Unit tests for parsing ClocReport from JSON data."""

import json
from datetime import datetime, timezone, timedelta
import pytest
from combine import ClocReport, ClocHeader, CommitDates, LanguageStats


SAMPLE_CLOC_JSON = {
    "header": {
        "cloc_url": "github.com/AlDanial/cloc",
        "cloc_version": "1.90",
        "elapsed_seconds": 0.664939880371094,
        "n_files": 414,
        "n_lines": 153500,
        "files_per_second": 622.612678561184,
        "lines_per_second": 230847.937582468,
        "report_file": "/tmp/reports/abc123/cloc.json",
    },
    "JSON": {"nFiles": 27, "blank": 0, "comment": 0, "code": 90768},
    "TypeScript": {"nFiles": 368, "blank": 6767, "comment": 4781, "code": 49441},
    "Markdown": {"nFiles": 7, "blank": 221, "comment": 0, "code": 705},
    "JavaScript": {"nFiles": 5, "blank": 56, "comment": 79, "code": 229},
    "YAML": {"nFiles": 2, "blank": 16, "comment": 56, "code": 210},
    "CSS": {"nFiles": 2, "blank": 13, "comment": 0, "code": 59},
    "Bourne Shell": {"nFiles": 2, "blank": 10, "comment": 8, "code": 30},
    "Dockerfile": {"nFiles": 1, "blank": 14, "comment": 13, "code": 24},
    "SUM": {"blank": 7097, "comment": 4937, "code": 141466, "nFiles": 414},
    "commit": {
        "author_date": "2026-03-05T12:02:13-08:00",
        "commit_date": "2026-03-12T15:33:20-07:00",
    },
}


class TestClocReportFromDict:
    """Tests for ClocReport.from_dict() class method."""

    def test_parses_full_report(self):
        report = ClocReport.from_dict(SAMPLE_CLOC_JSON)

        assert isinstance(report, ClocReport)
        assert isinstance(report.header, ClocHeader)
        assert isinstance(report.commit, CommitDates)
        assert report.summary is not None

    def test_header_fields(self):
        report = ClocReport.from_dict(SAMPLE_CLOC_JSON)

        assert report.header.cloc_url == "github.com/AlDanial/cloc"
        assert report.header.cloc_version == "1.90"
        assert report.header.elapsed_seconds == pytest.approx(0.664939880371094)
        assert report.header.n_files == 414
        assert report.header.n_lines == 153500
        assert report.header.files_per_second == pytest.approx(622.612678561184)
        assert report.header.lines_per_second == pytest.approx(230847.937582468)
        assert report.header.report_file == "/tmp/reports/abc123/cloc.json"

    def test_commit_dates(self):
        report = ClocReport.from_dict(SAMPLE_CLOC_JSON)

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
        report = ClocReport.from_dict(SAMPLE_CLOC_JSON)

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

    def test_languages_exclude_reserved_keys(self):
        report = ClocReport.from_dict(SAMPLE_CLOC_JSON)

        assert "header" not in report.languages
        assert "commit" not in report.languages
        assert "SUM" not in report.languages

    def test_language_stats_values(self):
        report = ClocReport.from_dict(SAMPLE_CLOC_JSON)

        ts = report.languages["TypeScript"]
        assert ts.nFiles == 368
        assert ts.blank == 6767
        assert ts.comment == 4781
        assert ts.code == 49441

    def test_language_with_spaces_in_name(self):
        report = ClocReport.from_dict(SAMPLE_CLOC_JSON)

        shell = report.languages["Bourne Shell"]
        assert shell.nFiles == 2
        assert shell.blank == 10
        assert shell.comment == 8
        assert shell.code == 30

    def test_summary_parsed(self):
        report = ClocReport.from_dict(SAMPLE_CLOC_JSON)

        assert report.summary is not None
        assert report.summary.nFiles == 414
        assert report.summary.blank == 7097
        assert report.summary.comment == 4937
        assert report.summary.code == 141466

    def test_summary_absent_when_no_sum(self):
        data = {
            "header": SAMPLE_CLOC_JSON["header"],
            "commit": SAMPLE_CLOC_JSON["commit"],
            "Python": {"nFiles": 10, "blank": 20, "comment": 5, "code": 300},
        }
        report = ClocReport.from_dict(data)

        assert report.summary is None

    def test_single_language(self):
        data = {
            "header": SAMPLE_CLOC_JSON["header"],
            "commit": SAMPLE_CLOC_JSON["commit"],
            "Go": {"nFiles": 42, "blank": 100, "comment": 50, "code": 5000},
            "SUM": {"nFiles": 42, "blank": 100, "comment": 50, "code": 5000},
        }
        report = ClocReport.from_dict(data)

        assert len(report.languages) == 1
        assert "Go" in report.languages
        assert report.languages["Go"].code == 5000

    def test_no_languages(self):
        data = {
            "header": SAMPLE_CLOC_JSON["header"],
            "commit": SAMPLE_CLOC_JSON["commit"],
        }
        report = ClocReport.from_dict(data)

        assert len(report.languages) == 0
        assert report.summary is None

    def test_language_stats_are_correct_type(self):
        report = ClocReport.from_dict(SAMPLE_CLOC_JSON)

        for name, stats in report.languages.items():
            assert isinstance(
                stats, LanguageStats
            ), f"Language '{name}' is not LanguageStats"

    def test_all_language_codes_sum_to_summary(self):
        report = ClocReport.from_dict(SAMPLE_CLOC_JSON)

        total_code = sum(lang.code for lang in report.languages.values())
        total_blank = sum(lang.blank for lang in report.languages.values())
        total_comment = sum(lang.comment for lang in report.languages.values())
        total_files = sum(lang.nFiles for lang in report.languages.values())

        assert total_code == report.summary.code
        assert total_blank == report.summary.blank
        assert total_comment == report.summary.comment
        assert total_files == report.summary.nFiles


class TestClocReportFromJson:
    """Tests for parsing ClocReport from a JSON string (roundtrip)."""

    def test_parse_from_json_string(self):
        json_str = json.dumps(SAMPLE_CLOC_JSON)
        data = json.loads(json_str)
        report = ClocReport.from_dict(data)

        assert report.header.cloc_version == "1.90"
        assert len(report.languages) == 8
        assert report.summary is not None

    def test_json_roundtrip_preserves_data(self):
        report = ClocReport.from_dict(SAMPLE_CLOC_JSON)
        dumped = report.model_dump()
        restored = ClocReport(**dumped)

        assert restored.header.cloc_version == report.header.cloc_version
        assert restored.commit.author_date == report.commit.author_date
        assert set(restored.languages.keys()) == set(report.languages.keys())
        for lang_name in report.languages:
            assert (
                restored.languages[lang_name].code == report.languages[lang_name].code
            )


class TestClocReportValidationErrors:
    """Tests for invalid or incomplete input data."""

    def test_missing_header_raises(self):
        data = {
            "commit": SAMPLE_CLOC_JSON["commit"],
            "Python": {"nFiles": 1, "blank": 0, "comment": 0, "code": 10},
        }
        with pytest.raises(KeyError):
            ClocReport.from_dict(data)

    def test_missing_commit_raises(self):
        data = {
            "header": SAMPLE_CLOC_JSON["header"],
            "Python": {"nFiles": 1, "blank": 0, "comment": 0, "code": 10},
        }
        with pytest.raises(KeyError):
            ClocReport.from_dict(data)

    def test_incomplete_header_raises(self):
        data = {
            "header": {"cloc_url": "github.com/AlDanial/cloc"},
            "commit": SAMPLE_CLOC_JSON["commit"],
        }
        with pytest.raises(Exception):
            ClocReport.from_dict(data)

    def test_incomplete_language_stats_raises(self):
        data = {
            "header": SAMPLE_CLOC_JSON["header"],
            "commit": SAMPLE_CLOC_JSON["commit"],
            "Python": {"nFiles": 10},  # missing blank, comment, code
        }
        with pytest.raises(Exception):
            ClocReport.from_dict(data)

    def test_incomplete_commit_dates_raises(self):
        data = {
            "header": SAMPLE_CLOC_JSON["header"],
            "commit": {"author_date": "2026-01-01T00:00:00Z"},  # missing commit_date
        }
        with pytest.raises(Exception):
            ClocReport.from_dict(data)

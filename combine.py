#!/usr/bin/env python3
import argparse
import sys
from datetime import datetime
from pathlib import Path
import json
from pydantic import BaseModel
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict

import logging

logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

CHATTY_MODULES = ["matplotlib.font_manager", "PIL.PngImagePlugin"]


class ClocHeader(BaseModel):
    cloc_url: str
    cloc_version: str
    elapsed_seconds: float
    n_files: int
    n_lines: int
    files_per_second: float
    lines_per_second: float
    report_file: str


class LanguageStats(BaseModel):
    nFiles: int
    blank: int
    comment: int
    code: int


class CommitDates(BaseModel):
    author_date: datetime
    commit_date: datetime


class ClocReport(BaseModel):
    header: ClocHeader
    commit: CommitDates
    languages: dict[str, LanguageStats] = {}
    summary: LanguageStats | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "ClocReport":
        header = data["header"]
        commit = data["commit"]
        reserved_keys = {"header", "commit", "SUM"}
        languages = {
            k: LanguageStats(**v) for k, v in data.items() if k not in reserved_keys
        }
        summary = data.get("SUM")
        return cls(
            header=ClocHeader(**header),
            commit=CommitDates(**commit),
            languages=languages,
            summary=LanguageStats(**summary) if summary else None,
        )


def parser():
    p = argparse.ArgumentParser(description="")
    p.add_argument(
        "--repo-dir",
        type=str,
        required=True,
        help="Path to the repo directory under .repos/<repo-name>/ (cloc data is in <repo-dir>/cloc/)",
    )
    p.add_argument(
        "--repo-name",
        type=str,
        default=None,
        help="Repository name to include in chart titles (defaults to repo-dir folder name)",
    )

    args = p.parse_args()
    if args.repo_name is None:
        args.repo_name = Path(args.repo_dir).name
    return args


def commits(cloc_dir: Path):
    # Walk cloc dir, read <SHA>.json files, parse and yield them
    # cloc_dir/
    # ├── 00168394b123a4ef8c0ae993619f3c5ecce03437.json
    # ├── 00c0e93a4cfd0f2c5b4fbdd8d74114c998de382c.json
    # ├── 00c3b3ade67634eea0fdecd8e16b65c03f6d3804.json

    for cloc_file in sorted(cloc_dir.glob("*.json")):
        if not cloc_file.is_file():
            continue
        commit_sha = cloc_file.stem
        with open(cloc_file, "r") as f:
            data = json.load(f)

        yield commit_sha, ClocReport.from_dict(data)


def suppress_chatty_modules():
    for m in CHATTY_MODULES:
        logging.getLogger(m).setLevel(logging.INFO)


def main(args):
    logger.debug(f"Args: {args}")

    repo_dir = Path(args.repo_dir)
    cloc_dir = repo_dir / "cloc"

    all_commits = sorted(
        commits(cloc_dir),
        key=lambda item: item[1].commit.commit_date,
    )

    languages = set()

    for commit, commit_info in all_commits:
        languages.update(commit_info.languages.keys())

    logger.info(f"Languages: {languages}")

    rows = []
    sorted_languages = sorted(languages)

    # Group commits by date (using commit_date's date part)

    commits_by_date: dict[datetime, list[tuple[str, ClocReport]]] = defaultdict(list)

    for commit, commit_info in all_commits:
        date_key = commit_info.commit.commit_date.date()
        commits_by_date[date_key].append((commit, commit_info))

    # Build one row per day, using the last commit of each day as the snapshot
    total_commits = 0

    for date_key in sorted(commits_by_date.keys()):
        day_commits = commits_by_date[date_key]
        total_commits += len(day_commits)
        # Use the last commit of the day as the representative snapshot
        last_commit, last_commit_info = day_commits[-1]

        row = {
            "date": date_key,
            "commit": last_commit,
            "author_date": last_commit_info.commit.author_date,
            "commit_date": last_commit_info.commit.commit_date,
            "num_commits": len(day_commits),
            "total_commits": total_commits,
        }

        for lang in sorted_languages:
            stats = last_commit_info.languages.get(lang)
            row[f"{lang}_files"] = stats.nFiles if stats else 0
            row[f"{lang}_blank"] = stats.blank if stats else 0
            row[f"{lang}_comment"] = stats.comment if stats else 0
            row[f"{lang}_code"] = stats.code if stats else 0

        if last_commit_info.summary:
            row["total_files"] = last_commit_info.summary.nFiles
            row["total_blank"] = last_commit_info.summary.blank
            row["total_comment"] = last_commit_info.summary.comment
            row["total_code"] = last_commit_info.summary.code

        rows.append(row)

    df = pd.DataFrame(rows)

    csv_path = repo_dir / "cloc_summary.csv"
    df.to_csv(csv_path, index=False)
    logger.info(f"Saved CSV to {csv_path}")

    charts_dir = repo_dir
    charts_dir.mkdir(parents=True, exist_ok=True)

    plot_commits_over_time(df, charts_dir, repo_name=args.repo_name)
    plot_total_lines_over_time(df, charts_dir, repo_name=args.repo_name)
    plot_lines_by_language(df, charts_dir, sorted_languages, repo_name=args.repo_name)


def plot_commits_over_time(df: pd.DataFrame, charts_dir: Path, repo_name: str = ""):
    """Bar chart of daily commits + line of cumulative total commits."""
    fig, ax1 = plt.subplots(figsize=(14, 6))

    dates = pd.to_datetime(df["date"])

    # Bar: daily commit count
    ax1.bar(
        dates,
        df["num_commits"],
        color="steelblue",
        alpha=0.7,
        label="Daily commits",
        width=2,
    )
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Commits per day", color="steelblue")
    ax1.tick_params(axis="y", labelcolor="steelblue")

    # Line: cumulative commits (secondary y-axis)
    ax2 = ax1.twinx()
    ax2.plot(
        dates,
        df["total_commits"],
        color="darkorange",
        linewidth=2,
        label="Total commits",
    )
    ax2.set_ylabel("Total commits", color="darkorange")
    ax2.tick_params(axis="y", labelcolor="darkorange")

    # Format x-axis dates
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=45)

    # Combined legend
    bars, bar_labels = ax1.get_legend_handles_labels()
    lines, line_labels = ax2.get_legend_handles_labels()
    ax1.legend(bars + lines, bar_labels + line_labels, loc="upper left")

    fig.suptitle(f"Commits Over Time — {repo_name}")
    fig.tight_layout()

    out_path = charts_dir / "commits_over_time.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved chart to {out_path}")


def plot_total_lines_over_time(df: pd.DataFrame, charts_dir: Path, repo_name: str = ""):
    """Stacked area chart of total code, comment, and blank lines over time."""
    fig, ax = plt.subplots(figsize=(14, 6))

    dates = pd.to_datetime(df["date"])

    ax.stackplot(
        dates,
        df["total_code"],
        df["total_comment"],
        df["total_blank"],
        labels=["Code", "Comment", "Blank"],
        colors=["steelblue", "mediumseagreen", "lightcoral"],
        alpha=0.8,
    )

    ax.set_xlabel("Date")
    ax.set_ylabel("Lines")
    ax.legend(loc="upper left")

    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=45)

    fig.suptitle(f"Total Lines Over Time — {repo_name}")
    fig.tight_layout()

    out_path = charts_dir / "total_lines_over_time.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved chart to {out_path}")


def plot_lines_by_language(
    df: pd.DataFrame, charts_dir: Path, languages: list[str], repo_name: str = ""
):
    """Stacked area chart of code lines over time, broken down by language."""
    fig, ax = plt.subplots(figsize=(14, 6))

    dates = pd.to_datetime(df["date"])

    # Collect per-language code columns, drop languages that are all zeros
    lang_series = []
    lang_labels = []
    for lang in languages:
        col = f"{lang}_code"
        if col in df.columns and df[col].sum() > 0:
            lang_series.append(df[col])
            lang_labels.append(lang)

    ax.stackplot(dates, *lang_series, labels=lang_labels, alpha=0.8)

    ax.set_xlabel("Date")
    ax.set_ylabel("Lines of code")
    ax.legend(loc="upper left", fontsize="small", ncol=2)

    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=45)

    fig.suptitle(f"Lines of Code by Language — {repo_name}")
    fig.tight_layout()

    out_path = charts_dir / "lines_by_language.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved chart to {out_path}")


if __name__ == "__main__":
    suppress_chatty_modules()
    args = parser()

    sys.exit(main(args))

import pytest

from open_paxel.decisions.catalog import catalog_by_key, load_decision_catalog
from open_paxel.discover.scanner import discover_repo_for_cwd, filter_repos_by_cwd
from open_paxel.discover.scanner import RepoInfo
from pathlib import Path


def test_decision_catalog_loads():
    patterns = load_decision_catalog()
    assert len(patterns) >= 40
    assert "model-the-data-owner" in catalog_by_key()


def test_filter_repos_by_cwd_exact():
    repos = [
        RepoInfo(
            name="open_paxel",
            path=r"Z:\June 26\open_paxel",
            encoded_dir="x",
            session_count=1,
            session_paths=[],
        ),
        RepoInfo(
            name="other",
            path=r"Z:\Other\project",
            encoded_dir="y",
            session_count=1,
            session_paths=[],
        ),
    ]
    matched = filter_repos_by_cwd(repos, Path(r"Z:\June 26\open_paxel"))
    assert len(matched) == 1
    assert matched[0].name == "open_paxel"


def test_filter_repos_ignores_user_home_false_positive():
    repos = [
        RepoInfo(
            name="91745",
            path=r"C:\Users\91745",
            encoded_dir="home",
            session_count=1,
            session_paths=[],
        ),
        RepoInfo(
            name="io",
            path=r"C:\Users\91745\OneDrive\Desktop\staru09\github\io",
            encoded_dir="io",
            session_count=1,
            session_paths=[],
        ),
    ]
    matched = filter_repos_by_cwd(repos, Path(r"C:\Users\91745\OneDrive\Desktop\staru09\github\io"))
    assert len(matched) == 1
    assert matched[0].name == "io"


def test_discover_repo_prefers_longest_match():
    repos = [
        RepoInfo(
            name="91745",
            path=r"C:\Users\91745",
            encoded_dir="home",
            session_count=1,
            session_paths=[],
        ),
        RepoInfo(
            name="visuals",
            path=r"C:\Users\91745\OneDrive\Desktop\gpu\visuals",
            encoded_dir="gpu",
            session_count=2,
            session_paths=[],
        ),
    ]
    matched = filter_repos_by_cwd(repos, Path(r"C:\Users\91745\OneDrive\Desktop\gpu\visuals"))
    assert len(matched) == 1
    assert matched[0].name == "visuals"


def test_filter_repos_matches_gpu_visuals_alias():
    repos = [
        RepoInfo(
            name="visuals",
            path=r"C:\Users\91745\OneDrive\Desktop\gpu\visuals",
            encoded_dir="gpu",
            session_count=2,
            session_paths=[],
        ),
    ]
    matched = filter_repos_by_cwd(repos, Path(r"C:\Users\91745\OneDrive\Desktop\gpu_visuals"))
    assert len(matched) == 1
    assert matched[0].name == "visuals"


def test_malformed_io_path_does_not_match_unrelated_cwd():
    repos = [
        RepoInfo(
            name="io",
            path="c//Users/91745/OneDrive/Desktop/staru09/github/io",
            encoded_dir="bad",
            session_count=1,
            session_paths=[],
        ),
    ]
    matched = filter_repos_by_cwd(repos, Path(r"Z:\June 26\open_paxel"))
    assert matched == []


def test_filter_repos_matches_audiobook_generator_encoded_key():
    repos = [
        RepoInfo(
            name="generator",
            path=r"Z:\June\26\audiobook\generator",
            encoded_dir="Z--June-26-audiobook-generator",
            session_count=1,
            session_paths=[],
        ),
    ]
    matched = filter_repos_by_cwd(repos, Path(r"Z:\June 26\audiobook_generator"))
    assert len(matched) == 1
    assert matched[0].encoded_dir == "Z--June-26-audiobook-generator"


def test_discover_repo_corrects_path_for_audiobook_generator():
    repos = [
        RepoInfo(
            name="generator",
            path=r"Z:\June\26\audiobook\generator",
            encoded_dir="Z--June-26-audiobook-generator",
            session_count=1,
            session_paths=[],
        ),
    ]
    cwd = Path(r"Z:\June 26\audiobook_generator")
    matched = filter_repos_by_cwd(repos, cwd)
    assert len(matched) == 1
    # discover_repo_for_cwd uses live discover_repos(); test correction helper via filter + manual check
    from open_paxel.discover.scanner import _correct_repo_path

    corrected = _correct_repo_path(matched[0], cwd.resolve())
    assert corrected.path == str(cwd.resolve())
    assert corrected.name == "audiobook_generator"


def test_work_streams_single_project():
    from datetime import datetime, timedelta

    from open_paxel.models.domain import SessionReport
    from open_paxel.pipeline.steps.work_streams import build_work_streams

    base = datetime(2026, 6, 1, 10, 0)
    reports = [
        SessionReport(
            session_id="a",
            transcript_path="a.jsonl",
            project_path="/p",
            started_at=base,
            ended_at=base + timedelta(hours=1),
        ),
        SessionReport(
            session_id="b",
            transcript_path="b.jsonl",
            project_path="/p",
            started_at=base + timedelta(days=3),
            ended_at=base + timedelta(days=3, hours=2),
        ),
    ]
    streams = build_work_streams(reports, gap_hours=48)
    assert len(streams) == 2

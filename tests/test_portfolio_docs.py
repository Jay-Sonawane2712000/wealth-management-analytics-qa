from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
README = PROJECT_ROOT / "README.md"
DOCS = PROJECT_ROOT / "docs"


def test_readme_contains_one_sentence_summary():
    readme = README.read_text(encoding="utf-8")

    assert "## One-Sentence Summary" in readme


def test_readme_contains_key_results():
    readme = README.read_text(encoding="utf-8")

    assert "## Key Results" in readme
    assert "Injected errors" in readme


def test_readme_contains_interview_talking_points():
    readme = README.read_text(encoding="utf-8")

    assert "## Interview Talking Points" in readme


def test_readme_mentions_precision_and_recall():
    readme = README.read_text(encoding="utf-8").lower()

    assert "precision" in readme
    assert "recall" in readme


def test_readme_does_not_claim_pbix_exists():
    readme = README.read_text(encoding="utf-8").lower()

    assert "no finished `.pbix` file is included or claimed" in readme
    assert "finished .pbix exists" not in readme


def test_portfolio_docs_exist():
    assert (DOCS / "interview_story.md").exists()
    assert (DOCS / "architecture.md").exists()
    assert (DOCS / "snowflake_runbook.md").exists()


def test_interview_story_contains_resume_bullet_options():
    interview_story = (DOCS / "interview_story.md").read_text(encoding="utf-8")

    assert "## Resume Bullet Options" in interview_story
    assert "Data Analyst Version" in interview_story
    assert "Data Engineer Version" in interview_story
    assert "Quant / Analytics Version" in interview_story

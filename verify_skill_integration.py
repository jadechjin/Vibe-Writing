"""Quick verification script for skill output parser + context assembly."""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))


def test_parser():
    """Test 1: Verify skill_output_parser correctly extracts structured blocks."""
    from app.modules.drafts.skill_output_parser import parse_skill_output

    sample = """这是一段正常的草稿文本，讨论了聚合物降解的机理 [Claim:S1-F1-1]。

根据文献研究，热降解是主要机制 [Claim:S1-F1-2]。

<!-- ASSET_INGEST: type=literature_reference -->
{"title":"Thermal degradation of polymers","authors":"Smith et al.","year":2023,"doi":"10.1234/test","relevance":"直接支持热降解机理的核心论据"}
<!-- /ASSET_INGEST -->

进一步的分析表明... [Claim:S1-F2-1]

<!-- REVIEW_SCORE -->
{"dimensions":{"originality":72,"methodology":85,"evidence_sufficiency":68,"argument_coherence":80,"writing_quality":78},"verdict":"minor_revision","key_issues":["证据覆盖不足","缺少对比实验数据"]}
<!-- /REVIEW_SCORE -->

<!-- REVISION_ITEM -->
{"severity":"major","section":"3.2","issue":"缺少 TGA 数据支撑","suggestion":"补充热重分析实验数据，与 DSC 结果交叉验证"}
<!-- /REVISION_ITEM -->

<!-- REVISION_ITEM -->
{"severity":"minor","section":"3.1","issue":"引言过于简短","suggestion":"扩展文献综述部分，增加 2-3 篇近期相关工作"}
<!-- /REVISION_ITEM -->

总结部分的文本也应该保留。"""

    result = parse_skill_output(sample)

    print("=" * 60)
    print("TEST 1: Skill Output Parser")
    print("=" * 60)

    # Check clean text
    assert "正常的草稿文本" in result.clean_text, "Clean text should preserve draft content"
    assert "ASSET_INGEST" not in result.clean_text, "Clean text should not contain block markers"
    assert "REVIEW_SCORE" not in result.clean_text, "Clean text should not contain block markers"
    assert "[Claim:S1-F1-1]" in result.clean_text, "Claim tags should be preserved"
    assert "总结部分" in result.clean_text, "Text after blocks should be preserved"
    print(f"  [OK] Clean text preserved ({len(result.clean_text)} chars)")

    # Check assets
    assert len(result.assets) == 1, f"Expected 1 asset, got {len(result.assets)}"
    assert result.assets[0].asset_type == "literature_reference"
    assert result.assets[0].payload["title"] == "Thermal degradation of polymers"
    assert result.assets[0].payload["doi"] == "10.1234/test"
    print(f"  [OK] Assets extracted: {len(result.assets)} (type={result.assets[0].asset_type})")

    # Check review scores
    assert len(result.review_scores) == 1, f"Expected 1 review, got {len(result.review_scores)}"
    assert result.review_scores[0].payload["verdict"] == "minor_revision"
    assert result.review_scores[0].payload["dimensions"]["methodology"] == 85
    print(f"  [OK] Review scores extracted: verdict={result.review_scores[0].payload['verdict']}")

    # Check revision items
    assert len(result.revision_items) == 2, f"Expected 2 revisions, got {len(result.revision_items)}"
    assert result.revision_items[0].payload["severity"] == "major"
    assert result.revision_items[1].payload["severity"] == "minor"
    print(f"  [OK] Revision items extracted: {len(result.revision_items)}")

    # Check has_structured_blocks
    assert result.has_structured_blocks is True
    print(f"  [OK] has_structured_blocks = True")

    # Test with plain text (no blocks)
    plain = "这是普通文本，没有任何结构化标记。"
    plain_result = parse_skill_output(plain)
    assert plain_result.clean_text == plain
    assert plain_result.has_structured_blocks is False
    print(f"  [OK] Plain text passthrough works")

    # Test with malformed JSON (should not crash)
    bad = '<!-- ASSET_INGEST: type=test -->\n{bad json}\n<!-- /ASSET_INGEST -->\nOK text'
    bad_result = parse_skill_output(bad)
    assert "OK text" in bad_result.clean_text
    assert len(bad_result.assets) == 0  # malformed JSON skipped
    print(f"  [OK] Malformed JSON handled gracefully")

    print("\nAll parser tests passed!\n")


def test_skill_installed():
    """Test 2: Verify skills are installed in .claude/skills/."""
    print("=" * 60)
    print("TEST 2: Skill Installation")
    print("=" * 60)

    base = os.path.join(os.path.dirname(__file__), ".claude", "skills")
    expected = [
        "deep-research/SKILL.md",
        "academic-paper/SKILL.md",
        "academic-paper-reviewer/SKILL.md",
        "academic-pipeline/SKILL.md",
    ]

    for skill_path in expected:
        full = os.path.join(base, skill_path)
        exists = os.path.isfile(full)
        status = "[OK]" if exists else "[FAIL]"
        print(f"  {status} {skill_path}")
        if not exists:
            print(f"        Missing: {full}")

    print()


def test_prompt_protocol():
    """Test 3: Verify _DRAFT_SYSTEM_PROMPT contains asset ingest protocol."""
    print("=" * 60)
    print("TEST 3: Prompt Protocol")
    print("=" * 60)

    # Read the service file and check for protocol markers
    service_path = os.path.join(
        os.path.dirname(__file__), "backend", "app", "modules", "drafts", "service.py"
    )
    with open(service_path, encoding="utf-8") as f:
        content = f.read()

    checks = [
        ("ASSET_INGEST protocol", "ASSET_INGEST: type="),
        ("REVIEW_SCORE protocol", "REVIEW_SCORE"),
        ("REVISION_ITEM protocol", "REVISION_ITEM"),
        ("G0 context block", "[G0 研究框架]"),
        ("G1 context block", "[G1 图表计划]"),
        ("G4 context block", "[G4 证据缺口]"),
        ("Claim tag requirement", "[Claim:claim_id]"),
    ]

    for label, marker in checks:
        found = marker in content
        status = "[OK]" if found else "[FAIL]"
        print(f"  {status} {label}")

    print()


if __name__ == "__main__":
    test_skill_installed()
    test_prompt_protocol()
    test_parser()
    print("All verification tests completed.")

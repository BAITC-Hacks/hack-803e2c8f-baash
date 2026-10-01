from pathlib import Path

from scripts.check_docs_localization import switcher, validate, variant


def triplet(root: Path) -> list[Path]:
    source = root / "GUIDE.md"
    paths = [variant(source, language) for language in ("ru", "en", "kk")]
    for path, title in zip(paths, ("Обзор", "Overview", "Шолу"), strict=True):
        path.write_text(
            f"{switcher(source)}\n\n# {title}\n\n```bash\ntrue\n```\n", encoding="utf-8"
        )
    return paths


def test_complete_triplet(tmp_path: Path) -> None:
    assert validate(tmp_path, triplet(tmp_path)) == []


def test_missing_translation_is_named(tmp_path: Path) -> None:
    paths = triplet(tmp_path)
    paths.pop().unlink()
    assert any("GUIDE.kk.md: missing kk" in error for error in validate(tmp_path, paths))


def test_wrong_language_and_broken_anchor_are_detected(tmp_path: Path) -> None:
    paths = triplet(tmp_path)
    with paths[1].open("a", encoding="utf-8") as output:
        output.write("\n[wrong](GUIDE.md#missing)\n")
    errors = validate(tmp_path, paths)
    assert any("wrong-language" in error for error in errors)
    assert any("missing anchor" in error for error in errors)


def test_instruction_and_heading_drift_are_detected(tmp_path: Path) -> None:
    paths = triplet(tmp_path)
    paths[2].write_text(
        paths[2].read_text(encoding="utf-8").replace("true", "false") + "\n## Extra\n",
        encoding="utf-8",
    )
    errors = validate(tmp_path, paths)
    assert any("code blocks differ" in error for error in errors)
    assert any("heading levels/order differ" in error for error in errors)


def test_translation_placeholder_and_missing_link_are_detected(tmp_path: Path) -> None:
    paths = triplet(tmp_path)
    with paths[1].open("a", encoding="utf-8") as output:
        output.write("\nTranslation pending\n[missing](NO.md)\n")
    errors = validate(tmp_path, paths)
    assert any("untranslated placeholder" in error for error in errors)
    assert any("broken local link" in error for error in errors)

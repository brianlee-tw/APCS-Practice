import tempfile
import unittest
from pathlib import Path

from tools.catalog_store import CatalogStore, ProblemMeta
from tools.tag_taxonomy import (
    CANONICAL_SET,
    TAG_GROUPS,
    normalize_tags,
    serialize_selection,
    split_tags,
)


class TagTaxonomyTest(unittest.TestCase):
    def test_groups_have_unique_canonical_tags(self):
        flattened = [
            tag
            for _, tags in TAG_GROUPS
            for tag in tags
        ]
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(set(flattened), CANONICAL_SET)

    def test_io_aliases_normalize(self):
        self.assertEqual(
            normalize_tags(
                "IO Optimization, I/O Optimization, IO, I/O"
            ),
            "I/O",
        )

    def test_normalization_preserves_unknown_tags(self):
        self.assertEqual(
            normalize_tags(
                "Math Theory, Loops, Math Theory"
            ),
            "Math Theory, Loops",
        )

    def test_split_tags_separates_legacy_unknown(self):
        canonical, unknown = split_tags(
            "Array, Math Theory, IO Optimization"
        )
        self.assertEqual(canonical, ["Array", "I/O"])
        self.assertEqual(unknown, ["Math Theory"])

    def test_serialize_selection_uses_taxonomy_order(self):
        self.assertEqual(
            serialize_selection(
                {"Loops", "Basic Syntax", "Array"}
            ),
            "Basic Syntax, Loops, Array",
        )

    def test_serialize_selection_preserves_legacy_unknown(self):
        self.assertEqual(
            serialize_selection(
                {"Array"},
                ["Math Theory"],
            ),
            "Array, Math Theory",
        )

    def test_catalog_store_normalizes_safe_aliases_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / "problems.csv").write_text(
                "problem_id,title,source,difficulty,tags\n"
                'a001,Hello,,1,"IO Optimization, Math Theory"\n',
                encoding="utf-8",
            )
            (data / "solutions.csv").write_text(
                "problem_id,path,language,complexity\n"
                "a001,solutions/a001.cpp,cpp,O(1)\n",
                encoding="utf-8",
            )

            store = CatalogStore(data)
            current = store.load_problems()["a001"]

            store.update_problem(
                ProblemMeta(
                    problem_id=current.problem_id,
                    title=current.title,
                    source=current.source,
                    difficulty=current.difficulty,
                    tags=current.tags,
                )
            )

            updated = store.load_problems()["a001"]
            self.assertEqual(
                updated.tags,
                "I/O, Math Theory",
            )


if __name__ == "__main__":
    unittest.main()

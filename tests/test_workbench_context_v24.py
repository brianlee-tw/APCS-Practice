import tempfile
import unittest
from pathlib import Path

from tools.catalog_store import (
    CatalogStore,
    ProblemMeta,
    SolutionMeta,
)
from tools.workbench_context import (
    resolve_problem_context,
)


class FakeCurriculum:
    def placement_by_uid(self, uid):
        raise ValueError(uid)


class WorkbenchContextV24Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        data = self.root / "data"
        data.mkdir()
        (data / "problems.csv").write_text(
            "problem_id,title,source,difficulty,tags\n"
            "a001,Hello,ZeroJudge,1,I/O\n",
            encoding="utf-8",
        )
        (data / "solutions.csv").write_text(
            "problem_id,path,language,complexity\n"
            "a001,solutions/hello.cpp,cpp,O(1)\n",
            encoding="utf-8",
        )
        self.store = CatalogStore(data)
        source = self.root / "solutions" / "hello.cpp"
        source.parent.mkdir()
        source.write_text(
            "int main(){}\n",
            encoding="utf-8",
        )
        self.source = source
        self.intelligence = (
            data
            / "problem_intelligence"
        )
        self.intelligence.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_registered_solution_path_beats_filename_inference(self):
        context = resolve_problem_context(
            self.source,
            root=self.root,
            store=self.store,
            curriculum=FakeCurriculum(),
            intelligence_dir=self.intelligence,
        )

        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(
            context.problem_id,
            "a001",
        )
        self.assertEqual(
            context.title,
            "Hello",
        )
        self.assertEqual(
            context.source,
            "zerojudge",
        )
        self.assertEqual(
            context.identity_origin,
            "catalog_solution",
        )

    def test_problem_intelligence_respects_catalog_source_authority(self):
        wrong = (
            self.intelligence
            / "codeforces"
            / "a001.json"
        )
        wrong.parent.mkdir(
            parents=True
        )
        wrong.write_text(
            """{
  "identity": {
    "source": "codeforces",
    "external_id": "a001",
    "canonical_url": "https://codeforces.com/problemset/problem/1/A"
  },
  "source_metadata": {
    "title": "Wrong platform"
  }
}""",
            encoding="utf-8",
        )
        right = (
            self.intelligence
            / "zerojudge"
            / "a001.json"
        )
        right.parent.mkdir(
            parents=True
        )
        right.write_text(
            """{
  "identity": {
    "source": "zerojudge",
    "external_id": "a001",
    "canonical_url": "https://zerojudge.tw/ShowProblem?problemid=a001"
  },
  "source_metadata": {
    "title": "Canonical ZeroJudge title"
  }
}""",
            encoding="utf-8",
        )

        context = resolve_problem_context(
            self.source,
            root=self.root,
            store=self.store,
            curriculum=FakeCurriculum(),
            intelligence_dir=self.intelligence,
        )

        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(
            context.source,
            "zerojudge",
        )
        self.assertEqual(
            context.canonical_url,
            "https://zerojudge.tw/ShowProblem?problemid=a001",
        )
        self.assertEqual(
            context.title,
            "Canonical ZeroJudge title",
        )

    def test_ambiguous_intelligence_without_source_fails_closed(self):
        source = self.root / "b130_scratch.cpp"
        source.write_text(
            "int main(){}\n",
            encoding="utf-8",
        )

        for judge in (
            "zerojudge",
            "codeforces",
        ):
            path = (
                self.intelligence
                / judge
                / "b130.json"
            )
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            path.write_text(
                """{
  "identity": {
    "source": "%s",
    "external_id": "b130",
    "canonical_url": "https://example.invalid/%s/b130"
  },
  "source_metadata": {
    "title": "Ambiguous"
  }
}""" % (judge, judge),
                encoding="utf-8",
            )

        context = resolve_problem_context(
            source,
            root=self.root,
            store=self.store,
            curriculum=FakeCurriculum(),
            intelligence_dir=self.intelligence,
        )

        self.assertIsNotNone(context)
        assert context is not None
        self.assertIsNone(
            context.source
        )
        self.assertIsNone(
            context.canonical_url
        )
        self.assertEqual(
            context.title,
            "b130",
        )

    def test_unregistered_filename_fallback_is_last_resort(self):
        source = self.root / "b130_scratch.cpp"
        source.write_text(
            "int main(){}\n",
            encoding="utf-8",
        )

        context = resolve_problem_context(
            source,
            root=self.root,
            store=self.store,
            curriculum=FakeCurriculum(),
            intelligence_dir=self.intelligence,
        )

        self.assertIsNotNone(context)
        assert context is not None
        self.assertEqual(
            context.problem_id,
            "b130",
        )
        self.assertEqual(
            context.identity_origin,
            "filename_fallback",
        )


if __name__ == "__main__":
    unittest.main()

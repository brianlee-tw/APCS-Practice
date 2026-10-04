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

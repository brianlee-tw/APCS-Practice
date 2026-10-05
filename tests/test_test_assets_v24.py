import json
import tempfile
import unittest
from pathlib import Path

from tools.test_assets import (
    PROVENANCE_AI,
    PROVENANCE_OFFICIAL,
    SUITE_FAST,
    SUITE_FULL,
    TRUST_CANDIDATE,
    TRUST_DIFFERENTIAL_VERIFIED,
    TRUST_OFFICIAL,
    TestAssetStore,
)


class TestAssetStoreV24Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.runtime = self.root / "runtime"
        self.store = TestAssetStore(
            self.data,
            self.runtime,
        )

    def tearDown(self):
        self.temp.cleanup()

    def write_bundle(self):
        path = (
            self.data
            / "zerojudge"
            / "d050"
            / "tests.json"
        )
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": "apcs-test-bundle-v1",
                    "identity": {
                        "source": "zerojudge",
                        "external_id": "d050",
                        "canonical_url": "https://zerojudge.tw/ShowProblem?problemid=d050",
                    },
                    "cases": [
                        {
                            "id": "S1",
                            "name": "官方範例 1",
                            "input": "1 2\n",
                            "expected_output": "3\n",
                            "provenance": "OFFICIAL",
                            "trust": "OFFICIAL",
                            "suite": "fast",
                            "visibility": "official",
                        },
                        {
                            "id": "E1",
                            "name": "邊界測資",
                            "input": "0 0\n",
                            "expected_output": "0\n",
                            "provenance": "AI_GENERATED",
                            "trust": "DIFFERENTIAL_VERIFIED",
                            "suite": "full",
                            "visibility": "practice",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def test_dedicated_bundle_loads_trust_and_inventory(self):
        self.write_bundle()
        bundle = self.store.load(
            "zerojudge",
            "d050",
        )
        self.assertIsNotNone(bundle)
        assert bundle is not None
        self.assertEqual(
            bundle.official_count,
            1,
        )
        self.assertEqual(
            bundle.verified_count,
            2,
        )
        self.assertEqual(
            bundle.candidate_count,
            0,
        )
        self.assertEqual(
            bundle.cases[0].trust,
            TRUST_OFFICIAL,
        )
        self.assertEqual(
            bundle.cases[1].trust,
            TRUST_DIFFERENTIAL_VERIFIED,
        )

    def test_dedicated_bundle_identity_must_match_storage_path(self):
        self.write_bundle()
        path = (
            self.data
            / "zerojudge"
            / "d050"
            / "tests.json"
        )
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
        payload["identity"]["source"] = (
            "codeforces"
        )
        path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            ValueError,
            "identity.source",
        ):
            self.store.load(
                "zerojudge",
                "d050",
            )

    def test_source_discovery_fails_closed_when_external_id_is_ambiguous(self):
        self.write_bundle()
        other = (
            self.data
            / "codeforces"
            / "d050"
            / "tests.json"
        )
        other.parent.mkdir(
            parents=True
        )
        other.write_text(
            json.dumps(
                {
                    "schema_version": "apcs-test-bundle-v1",
                    "identity": {
                        "source": "codeforces",
                        "external_id": "d050",
                        "canonical_url": "https://example.invalid/codeforces/d050",
                    },
                    "cases": [],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        self.assertIsNone(
            self.store.load(
                None,
                "d050",
            )
        )

    def test_fast_suite_is_small_and_full_suite_includes_verified_edges(self):
        self.write_bundle()
        bundle = self.store.load(
            "zerojudge",
            "d050",
        )
        assert bundle is not None

        fast = self.store.visible_cases(
            bundle,
            mode="practice",
            activity="Guided Drill",
            post_attempt=False,
            suite=SUITE_FAST,
        )
        full = self.store.visible_cases(
            bundle,
            mode="practice",
            activity="Guided Drill",
            post_attempt=False,
            suite=SUITE_FULL,
        )

        self.assertEqual(
            [case.case_id for case in fast],
            ["S1"],
        )
        self.assertEqual(
            [case.case_id for case in full],
            ["S1", "E1"],
        )

    def test_exam_and_transfer_pre_attempt_only_expose_official_samples(self):
        self.write_bundle()
        bundle = self.store.load(
            "zerojudge",
            "d050",
        )
        assert bundle is not None

        exam = self.store.visible_cases(
            bundle,
            mode="exam",
            activity="Core Independent",
            post_attempt=False,
            suite=SUITE_FULL,
        )
        transfer = self.store.visible_cases(
            bundle,
            mode="practice",
            activity="Transfer Challenge",
            post_attempt=False,
            suite=SUITE_FULL,
        )

        self.assertEqual(
            [case.case_id for case in exam],
            ["S1"],
        )
        self.assertEqual(
            [case.case_id for case in transfer],
            ["S1"],
        )

    def test_post_attempt_unlocks_verified_edge_cases(self):
        self.write_bundle()
        bundle = self.store.load(
            "zerojudge",
            "d050",
        )
        assert bundle is not None

        cases = self.store.visible_cases(
            bundle,
            mode="exam",
            activity="Mock",
            post_attempt=True,
            suite=SUITE_FULL,
        )

        self.assertEqual(
            [case.case_id for case in cases],
            ["S1", "E1"],
        )

    def test_runtime_ai_candidates_never_become_verified_by_presence(self):
        self.write_bundle()
        path = (
            self.runtime
            / "test_candidates"
            / "zerojudge"
            / "d050"
            / "tests.json"
        )
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "cases": [
                        {
                            "id": "G1",
                            "name": "AI 候選",
                            "input": "7 -3\n",
                            "expected_output": "4\n",
                            "provenance": "AI_GENERATED",
                            "trust": "DIFFERENTIAL_VERIFIED",
                            "suite": "fast",
                            "visibility": "official",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        bundle = self.store.load(
            "zerojudge",
            "d050",
            include_candidates=True,
        )
        assert bundle is not None
        candidate = next(
            case
            for case in bundle.cases
            if case.case_id == "G1"
        )

        self.assertEqual(
            candidate.provenance,
            PROVENANCE_AI,
        )
        self.assertEqual(
            candidate.trust,
            TRUST_CANDIDATE,
        )
        self.assertEqual(
            candidate.suite,
            SUITE_FULL,
        )

    def test_legacy_package_official_samples_remain_usable_without_l2_migration(self):
        path = (
            self.data
            / "zerojudge"
            / "d050"
            / "package.json"
        )
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "identity": {
                        "source": "zerojudge",
                        "external_id": "d050",
                        "canonical_url": "https://zerojudge.tw/ShowProblem?problemid=d050",
                    },
                    "tests": {
                        "official_samples": [
                            {
                                "input": "1 2\n",
                                "output": "3\n",
                            }
                        ],
                        "generated_cases": [
                            {
                                "input": "0 0\n",
                            }
                        ],
                    },
                    "verification": {
                        "differential": "NOT_RUN",
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        bundle = self.store.load(
            "zerojudge",
            "d050",
        )
        assert bundle is not None

        self.assertEqual(
            bundle.cases[0].provenance,
            PROVENANCE_OFFICIAL,
        )
        self.assertEqual(
            bundle.cases[0].trust,
            TRUST_OFFICIAL,
        )
        self.assertEqual(
            bundle.cases[1].trust,
            TRUST_CANDIDATE,
        )


if __name__ == "__main__":
    unittest.main()

import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error

from tools.evidence_outbox import (
    EvidenceOutbox,
    build_envelope,
)
from tools.remote_transport import (
    PRODUCTION_ENDPOINT,
    WRITE_KEY_ENV,
    WritebackTransportError,
    post_bundle,
    sync_bundle,
)
from tools.remote_writeback import (
    build_remote_writeback_bundle,
)


TZ = dt.timezone(dt.timedelta(hours=8))
END = dt.datetime(
    2026,
    10,
    2,
    18,
    0,
    tzinfo=TZ,
)


def sample_envelope():
    return build_envelope(
        problem_id="ZJ-d050",
        pb_uid="PB-143",
        started_at=(
            END
            - dt.timedelta(minutes=4)
        ),
        finished_at=END,
        language="cpp",
        judge_result="AC",
        assistance=1,
        independent=True,
        attempt_count=1,
        active_minutes=4,
        timed=False,
        novelty="new",
        activity="Guided Drill",
        evidence=[
            (
                "S01_IO",
                "Implementation",
                "PASS",
                "transport test",
            )
        ],
        attempt_id="att_transport_001",
        writeback_id="wb_transport_001",
        created_at=END,
    )


def receipt_for(
    bundle,
    *,
    complete=True,
):
    return {
        "schema_version": (
            "v2.3-remote-receipt-1"
        ),
        "writeback_id": (
            bundle.writeback_id
        ),
        "complete": complete,
        "rec": {
            "page_id": "rec-page",
            "duplicate": False,
        },
        "evidence": [
            {
                "event_id": (
                    bundle.evidence[0].event_id
                ),
                "page_id": "ev-page",
                "duplicate": False,
            }
        ],
    }


class FakeResponse:
    def __init__(
        self,
        payload,
        status=201,
    ):
        self.status = status
        self._body = json.dumps(
            payload
        ).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        return False

    def read(self):
        return self._body

    def getcode(self):
        return self.status


class RemoteTransportV23Test(
    unittest.TestCase
):
    def test_posts_only_to_fixed_production_endpoint(self):
        bundle = (
            build_remote_writeback_bundle(
                sample_envelope()
            )
        )
        seen = {}

        def opener(
            request,
            *,
            timeout,
        ):
            seen["url"] = request.full_url
            seen["method"] = (
                request.get_method()
            )
            seen["timeout"] = timeout
            seen["key"] = request.get_header(
                "X-apcs-write-key"
            )
            return FakeResponse(
                receipt_for(
                    bundle
                )
            )

        with mock.patch.dict(
            os.environ,
            {
                WRITE_KEY_ENV: (
                    "unit-test-key"
                )
            },
            clear=False,
        ):
            receipt = post_bundle(
                bundle,
                opener=opener,
            )

        self.assertEqual(
            seen["url"],
            PRODUCTION_ENDPOINT,
        )
        self.assertEqual(
            seen["method"],
            "POST",
        )
        self.assertEqual(
            seen["key"],
            "unit-test-key",
        )
        self.assertTrue(
            receipt["complete"]
        )

    def test_missing_credential_fails_before_network(self):
        bundle = (
            build_remote_writeback_bundle(
                sample_envelope()
            )
        )
        called = False

        def opener(*args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError(
                "network should not be called"
            )

        with mock.patch.dict(
            os.environ,
            {},
            clear=True,
        ), mock.patch(
            "tools.remote_transport.KEY_FILE",
            Path(
                "/definitely/missing/key"
            ),
        ):
            with self.assertRaisesRegex(
                WritebackTransportError,
                "missing APCS_WRITEBACK_KEY",
            ):
                post_bundle(
                    bundle,
                    opener=opener,
                )

        self.assertFalse(
            called
        )

    def test_partial_receipt_is_never_acknowledged(self):
        envelope = sample_envelope()
        bundle = (
            build_remote_writeback_bundle(
                envelope
            )
        )

        def opener(
            request,
            *,
            timeout,
        ):
            return FakeResponse(
                receipt_for(
                    bundle,
                    complete=False,
                )
            )

        with tempfile.TemporaryDirectory() as temp:
            outbox = EvidenceOutbox(
                Path(temp)
            )
            outbox.enqueue(
                envelope
            )

            with mock.patch.dict(
                os.environ,
                {
                    WRITE_KEY_ENV: (
                        "unit-test-key"
                    )
                },
                clear=False,
            ):
                with self.assertRaisesRegex(
                    WritebackTransportError,
                    "receipt rejected",
                ):
                    sync_bundle(
                        outbox,
                        bundle,
                        opener=opener,
                    )

            self.assertFalse(
                outbox.has_receipt(
                    bundle.writeback_id
                )
            )
            self.assertEqual(
                len(
                    outbox.pending()
                ),
                1,
            )

    def test_valid_receipt_is_persisted_atomically(self):
        envelope = sample_envelope()
        bundle = (
            build_remote_writeback_bundle(
                envelope
            )
        )

        def opener(
            request,
            *,
            timeout,
        ):
            return FakeResponse(
                receipt_for(
                    bundle
                )
            )

        with tempfile.TemporaryDirectory() as temp:
            outbox = EvidenceOutbox(
                Path(temp)
            )
            outbox.enqueue(
                envelope
            )

            with mock.patch.dict(
                os.environ,
                {
                    WRITE_KEY_ENV: (
                        "unit-test-key"
                    )
                },
                clear=False,
            ):
                receipt, created = (
                    sync_bundle(
                        outbox,
                        bundle,
                        opener=opener,
                    )
                )

            self.assertTrue(
                created
            )
            self.assertTrue(
                receipt["complete"]
            )
            self.assertTrue(
                outbox.has_receipt(
                    bundle.writeback_id
                )
            )
            self.assertEqual(
                outbox.pending(),
                (),
            )

    def test_http_401_leaves_attempt_pending(self):
        envelope = sample_envelope()
        bundle = (
            build_remote_writeback_bundle(
                envelope
            )
        )

        def opener(
            request,
            *,
            timeout,
        ):
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                hdrs=None,
                fp=None,
            )

        with tempfile.TemporaryDirectory() as temp:
            outbox = EvidenceOutbox(
                Path(temp)
            )
            outbox.enqueue(
                envelope
            )

            with mock.patch.dict(
                os.environ,
                {
                    WRITE_KEY_ENV: (
                        "wrong-key"
                    )
                },
                clear=False,
            ):
                with self.assertRaisesRegex(
                    WritebackTransportError,
                    "HTTP 401",
                ):
                    sync_bundle(
                        outbox,
                        bundle,
                        opener=opener,
                    )

            self.assertFalse(
                outbox.has_receipt(
                    bundle.writeback_id
                )
            )
            self.assertEqual(
                len(
                    outbox.pending()
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()

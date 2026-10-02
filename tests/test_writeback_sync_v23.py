import contextlib
import datetime as dt
import io
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
    WRITEBACK_URL_ENV,
    WRITE_KEY_ENV,
    WritebackTransportError,
    post_bundle,
    sync_bundle,
)
from tools.remote_writeback import (
    build_remote_writeback_bundle,
)
from tools import writeback_sync


TZ = dt.timezone(dt.timedelta(hours=8))


def transport_env(
    *,
    key="unit-test-key",
    url=PRODUCTION_ENDPOINT,
):
    return {
        WRITEBACK_URL_ENV: url,
        WRITE_KEY_ENV: key,
    }
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
            headers = {
                key.lower(): value
                for key, value
                in request.header_items()
            }
            seen["key"] = headers.get(
                "x-apcs-write-key"
            )
            seen["content_type"] = headers.get(
                "content-type"
            )
            seen["body"] = json.loads(
                request.data.decode("utf-8")
            )
            return FakeResponse(
                receipt_for(
                    bundle
                )
            )

        with mock.patch.dict(
            os.environ,
            {
                WRITEBACK_URL_ENV: (
                    PRODUCTION_ENDPOINT
                ),
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
        self.assertEqual(
            seen["content_type"],
            "application/json",
        )
        self.assertEqual(
            seen["body"],
            bundle.to_dict(),
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
            {
                WRITEBACK_URL_ENV: (
                    PRODUCTION_ENDPOINT
                )
            },
            clear=True,
        ), mock.patch(
            "tools.remote_transport.KEY_FILE",
            Path(
                "/definitely/missing/key"
            ),
        ):
            with self.assertRaisesRegex(
                WritebackTransportError,
                "missing APCS_WRITE_KEY",
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
                    WRITEBACK_URL_ENV: (
                        PRODUCTION_ENDPOINT
                    ),
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
                    WRITEBACK_URL_ENV: (
                        PRODUCTION_ENDPOINT
                    ),
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
                    WRITEBACK_URL_ENV: (
                        PRODUCTION_ENDPOINT
                    ),
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


    def test_missing_endpoint_fails_before_network(self):
        bundle = build_remote_writeback_bundle(
            sample_envelope()
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
            {
                WRITE_KEY_ENV: "unit-test-key",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(
                WritebackTransportError,
                "missing APCS_WRITEBACK_URL",
            ):
                post_bundle(
                    bundle,
                    opener=opener,
                )

        self.assertFalse(called)

    def test_unapproved_endpoint_fails_before_network(self):
        bundle = build_remote_writeback_bundle(
            sample_envelope()
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
            transport_env(
                url="https://example.invalid/api/record"
            ),
            clear=True,
        ):
            with self.assertRaisesRegex(
                WritebackTransportError,
                "approved production endpoint",
            ):
                post_bundle(
                    bundle,
                    opener=opener,
                )

        self.assertFalse(called)

    def test_http_409_and_500_leave_attempt_pending(self):
        for code in (409, 500):
            with self.subTest(code=code):
                envelope = sample_envelope()
                bundle = build_remote_writeback_bundle(
                    envelope
                )

                def opener(request, *, timeout):
                    raise urllib.error.HTTPError(
                        request.full_url,
                        code,
                        "HTTP failure",
                        hdrs=None,
                        fp=None,
                    )

                with tempfile.TemporaryDirectory() as temp:
                    outbox = EvidenceOutbox(
                        Path(temp)
                    )
                    outbox.enqueue(envelope)

                    with mock.patch.dict(
                        os.environ,
                        transport_env(),
                        clear=True,
                    ):
                        with self.assertRaisesRegex(
                            WritebackTransportError,
                            f"HTTP {code}",
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
                        len(outbox.pending()),
                        1,
                    )

    def test_timeout_and_network_error_leave_attempt_pending(self):
        failures = (
            TimeoutError("timeout"),
            urllib.error.URLError("offline"),
        )

        for failure in failures:
            with self.subTest(
                failure=type(failure).__name__
            ):
                envelope = sample_envelope()
                bundle = build_remote_writeback_bundle(
                    envelope
                )

                def opener(request, *, timeout):
                    raise failure

                with tempfile.TemporaryDirectory() as temp:
                    outbox = EvidenceOutbox(
                        Path(temp)
                    )
                    outbox.enqueue(envelope)

                    with mock.patch.dict(
                        os.environ,
                        transport_env(),
                        clear=True,
                    ):
                        with self.assertRaises(
                            WritebackTransportError
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
                        len(outbox.pending()),
                        1,
                    )

    def test_malformed_json_leaves_attempt_pending(self):
        envelope = sample_envelope()
        bundle = build_remote_writeback_bundle(
            envelope
        )

        class InvalidJsonResponse:
            status = 200

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
                return b"{not-json"

            def getcode(self):
                return self.status

        def opener(request, *, timeout):
            return InvalidJsonResponse()

        with tempfile.TemporaryDirectory() as temp:
            outbox = EvidenceOutbox(
                Path(temp)
            )
            outbox.enqueue(envelope)

            with mock.patch.dict(
                os.environ,
                transport_env(),
                clear=True,
            ):
                with self.assertRaisesRegex(
                    WritebackTransportError,
                    "invalid JSON",
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
                len(outbox.pending()),
                1,
            )

    def test_wrong_writeback_and_missing_evidence_receipts_stay_pending(self):
        for case in (
            "wrong-writeback",
            "missing-evidence",
        ):
            with self.subTest(case=case):
                envelope = sample_envelope()
                bundle = build_remote_writeback_bundle(
                    envelope
                )
                receipt = receipt_for(bundle)

                if case == "wrong-writeback":
                    receipt["writeback_id"] = (
                        "wrong-writeback"
                    )
                else:
                    receipt["evidence"] = []

                def opener(request, *, timeout):
                    return FakeResponse(receipt)

                with tempfile.TemporaryDirectory() as temp:
                    outbox = EvidenceOutbox(
                        Path(temp)
                    )
                    outbox.enqueue(envelope)

                    with mock.patch.dict(
                        os.environ,
                        transport_env(),
                        clear=True,
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
                        len(outbox.pending()),
                        1,
                    )

    def test_success_marks_sent_exactly_once(self):
        envelope = sample_envelope()
        bundle = build_remote_writeback_bundle(
            envelope
        )

        def opener(request, *, timeout):
            return FakeResponse(
                receipt_for(bundle)
            )

        with tempfile.TemporaryDirectory() as temp:
            outbox = EvidenceOutbox(
                Path(temp)
            )
            outbox.enqueue(envelope)

            with mock.patch.object(
                outbox,
                "mark_sent",
                wraps=outbox.mark_sent,
            ) as mark_sent, mock.patch.dict(
                os.environ,
                transport_env(),
                clear=True,
            ):
                sync_bundle(
                    outbox,
                    bundle,
                    opener=opener,
                )

            mark_sent.assert_called_once()

    def test_retry_after_network_failure_reuses_same_ids(self):
        envelope = sample_envelope()
        bundle = build_remote_writeback_bundle(
            envelope
        )
        calls = 0

        def opener(request, *, timeout):
            nonlocal calls
            calls += 1

            if calls == 1:
                raise urllib.error.URLError(
                    "offline"
                )

            body = json.loads(
                request.data.decode("utf-8")
            )
            self.assertEqual(
                body["writeback_id"],
                bundle.writeback_id,
            )
            self.assertEqual(
                [
                    item["event_id"]
                    for item in body["evidence"]
                ],
                [
                    item.event_id
                    for item in bundle.evidence
                ],
            )
            return FakeResponse(
                receipt_for(bundle)
            )

        with tempfile.TemporaryDirectory() as temp:
            outbox = EvidenceOutbox(
                Path(temp)
            )
            outbox.enqueue(envelope)

            with mock.patch.dict(
                os.environ,
                transport_env(),
                clear=True,
            ):
                with self.assertRaises(
                    WritebackTransportError
                ):
                    sync_bundle(
                        outbox,
                        bundle,
                        opener=opener,
                    )

                self.assertEqual(
                    len(outbox.pending()),
                    1,
                )

                sync_bundle(
                    outbox,
                    bundle,
                    opener=opener,
                )

            self.assertEqual(calls, 2)
            self.assertEqual(
                outbox.pending(),
                (),
            )

    def test_idempotent_duplicate_receipt_is_acknowledged(self):
        envelope = sample_envelope()
        bundle = build_remote_writeback_bundle(
            envelope
        )
        receipt = receipt_for(bundle)
        receipt["rec"]["duplicate"] = True

        for item in receipt["evidence"]:
            item["duplicate"] = True

        def opener(request, *, timeout):
            return FakeResponse(receipt)

        with tempfile.TemporaryDirectory() as temp:
            outbox = EvidenceOutbox(
                Path(temp)
            )
            outbox.enqueue(envelope)

            with mock.patch.dict(
                os.environ,
                transport_env(),
                clear=True,
            ):
                returned, created = sync_bundle(
                    outbox,
                    bundle,
                    opener=opener,
                )

            self.assertTrue(created)
            self.assertTrue(
                returned["rec"]["duplicate"]
            )
            self.assertEqual(
                outbox.pending(),
                (),
            )

    def test_secret_is_never_in_transport_error(self):
        secret = "unit-test-secret-do-not-log"
        bundle = build_remote_writeback_bundle(
            sample_envelope()
        )

        def opener(request, *, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                hdrs=None,
                fp=None,
            )

        with mock.patch.dict(
            os.environ,
            transport_env(
                key=secret
            ),
            clear=True,
        ):
            with self.assertRaises(
                WritebackTransportError
            ) as caught:
                post_bundle(
                    bundle,
                    opener=opener,
                )

        self.assertNotIn(
            secret,
            str(caught.exception),
        )

    def test_status_bundle_and_projection_remain_compatible(self):
        envelope = sample_envelope()

        with tempfile.TemporaryDirectory() as temp:
            outbox = EvidenceOutbox(
                Path(temp)
            )
            outbox.enqueue(envelope)

            with mock.patch.object(
                writeback_sync,
                "store",
                return_value=outbox,
            ), mock.patch.dict(
                os.environ,
                transport_env(),
                clear=True,
            ):
                output = io.StringIO()

                with contextlib.redirect_stdout(
                    output
                ):
                    self.assertEqual(
                        writeback_sync.status_cmd(),
                        0,
                    )

                self.assertIn(
                    "eligible=1",
                    output.getvalue(),
                )

                output = io.StringIO()

                with contextlib.redirect_stdout(
                    output
                ):
                    self.assertEqual(
                        writeback_sync.bundle_cmd(
                            envelope.writeback_id,
                            projection=False,
                        ),
                        0,
                    )

                bundle_value = json.loads(
                    output.getvalue()
                )
                self.assertEqual(
                    bundle_value["writeback_id"],
                    envelope.writeback_id,
                )

                output = io.StringIO()

                with contextlib.redirect_stdout(
                    output
                ):
                    self.assertEqual(
                        writeback_sync.bundle_cmd(
                            envelope.writeback_id,
                            projection=True,
                        ),
                        0,
                    )

                projection_value = json.loads(
                    output.getvalue()
                )
                self.assertIn(
                    "rec",
                    projection_value,
                )
                self.assertIn(
                    "evidence",
                    projection_value,
                )


if __name__ == "__main__":
    unittest.main()

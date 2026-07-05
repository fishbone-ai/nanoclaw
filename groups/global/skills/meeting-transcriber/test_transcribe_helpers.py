import unittest
from unittest import mock
import sys

# Stub out heavy third-party imports so transcribe.py can be imported on the host.
for name in ("requests", "google", "google.genai", "google.oauth2",
             "google.oauth2.service_account", "googleapiclient",
             "googleapiclient.discovery", "googleapiclient.http"):
    sys.modules.setdefault(name, mock.MagicMock())

import transcribe  # noqa: E402


class TestHelpers(unittest.TestCase):
    def test_meeting_id_for_uses_created_date_and_slug(self):
        f = {"name": "bxw-faqy-yqf (2026-07-05 15:47 GMT+3).mp4",
             "id": "abc", "createdTime": "2026-07-05T12:47:00.000Z"}
        self.assertEqual(
            transcribe.meeting_id_for(f),
            "2026-07-05-bxw-faqy-yqf-2026-07-05-15-47-gmt-3",
        )

    def test_meeting_id_falls_back_to_today_without_created_time(self):
        f = {"name": "call.mp4", "id": "abc"}
        self.assertRegex(transcribe.meeting_id_for(f), r"^\d{4}-\d{2}-\d{2}-call$")

    def test_infer_source(self):
        self.assertEqual(transcribe.infer_source("phone_20260702-090335_0545881339.m4a"), "phone")
        self.assertEqual(transcribe.infer_source("whatsapp_20260629-222345_ohav.ogg"), "whatsapp")
        self.assertEqual(transcribe.infer_source("voice-020_w_20260629.m4a"), "voice")
        self.assertEqual(transcribe.infer_source("bxw-faqy-yqf (2026-07-05).mp4"), "meet")


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from unittest import mock

import supabase_store as ss


def fake_response(status=200, body=b"[]"):
    resp = mock.MagicMock()
    resp.status = status
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = mock.Mock(return_value=False)
    return resp


@mock.patch.dict("os.environ", {"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SERVICE_KEY": "sk"})
class TestSupabaseStore(unittest.TestCase):
    @mock.patch("supabase_store.urlopen")
    def test_upsert_meeting_posts_merge_duplicates(self, urlopen):
        urlopen.return_value = fake_response(201)
        ss.upsert_meeting({"id": "m1", "date": "2026-07-05", "transcript_md": "hi"})
        req = urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertIn("/rest/v1/meetings", req.full_url)
        self.assertEqual(req.get_header("Prefer"), "resolution=merge-duplicates")
        self.assertEqual(req.get_header("Authorization"), "Bearer sk")
        self.assertEqual(json.loads(req.data), {"id": "m1", "date": "2026-07-05", "transcript_md": "hi"})

    @mock.patch("supabase_store.urlopen")
    def test_get_meeting_returns_row(self, urlopen):
        urlopen.return_value = fake_response(200, json.dumps([{"id": "m1"}]).encode())
        row = ss.get_meeting("m1", columns="id,summary_md")
        self.assertEqual(row, {"id": "m1"})
        self.assertIn("id=eq.m1", urlopen.call_args[0][0].full_url)
        self.assertIn("select=id%2Csummary_md", urlopen.call_args[0][0].full_url)

    @mock.patch("supabase_store.urlopen")
    def test_get_meeting_missing_returns_none(self, urlopen):
        urlopen.return_value = fake_response(200, b"[]")
        self.assertIsNone(ss.get_meeting("nope"))

    @mock.patch("supabase_store.urlopen")
    def test_pending_meetings_filters_null_summary(self, urlopen):
        urlopen.return_value = fake_response(200, json.dumps([{"id": "m1", "owner": "ohav"}]).encode())
        rows = ss.pending_meetings()
        self.assertEqual(rows, [{"id": "m1", "owner": "ohav"}])
        self.assertIn("summary_md=is.null", urlopen.call_args[0][0].full_url)

    @mock.patch("supabase_store.urlopen")
    def test_pending_meetings_respects_limit(self, urlopen):
        urlopen.return_value = fake_response(200, b"[]")
        ss.pending_meetings(limit=5)
        self.assertIn("limit=5", urlopen.call_args[0][0].full_url)
        urlopen.return_value = fake_response(200, b"[]")
        ss.pending_meetings()
        self.assertNotIn("limit=", urlopen.call_args[0][0].full_url)

    @mock.patch("supabase_store.urlopen")
    def test_save_summary_patches_then_replaces_children(self, urlopen):
        urlopen.return_value = fake_response(204, b"")
        ss.save_summary(
            "m1", "## Summary\n- x", "Title", "discovery-call", "123.456",
            participants=[{"name": "Dana", "category": "practitioner"}],
            themes=["ai-security"],
        )
        methods = [(c[0][0].get_method(), c[0][0].full_url) for c in urlopen.call_args_list]
        self.assertEqual(methods[0][0], "PATCH")               # meetings row
        self.assertIn("meetings?id=eq.m1", methods[0][1])
        self.assertEqual(methods[1][0], "DELETE")              # old participants
        self.assertIn("participants?meeting_id=eq.m1", methods[1][1])
        self.assertEqual(methods[2][0], "POST")                # new participants
        self.assertEqual(methods[3][0], "DELETE")              # old themes
        self.assertIn("themes?meeting_id=eq.m1", methods[3][1])
        self.assertEqual(methods[4][0], "POST")                # new themes
        posted = json.loads(urlopen.call_args_list[4][0][0].data)
        self.assertEqual(posted, [{"meeting_id": "m1", "theme": "ai-security"}])

    @mock.patch("supabase_store.urlopen")
    def test_save_summary_skips_empty_children_posts(self, urlopen):
        urlopen.return_value = fake_response(204, b"")
        ss.save_summary("m1", "s", "t", None, None, participants=[], themes=[])
        methods = [c[0][0].get_method() for c in urlopen.call_args_list]
        self.assertEqual(methods, ["PATCH", "DELETE", "DELETE"])  # no empty POSTs

    @mock.patch("supabase_store.urlopen")
    def test_non_2xx_raises_supabase_error(self, urlopen):
        import urllib.error
        urlopen.side_effect = urllib.error.HTTPError(
            "https://x.supabase.co/rest/v1/meetings", 401, "unauthorized", {}, None
        )
        with self.assertRaises(ss.SupabaseError):
            ss.upsert_meeting({"id": "m1", "date": "2026-07-05"})

    @mock.patch("supabase_store.urlopen")
    def test_insert_insights_posts_rows_with_meeting_id(self, urlopen):
        urlopen.return_value = fake_response(201)
        ss.insert_insights("m1", [
            {"content": "AI budgets rising", "category": "signal", "source": "extracted", "status": "candidate"},
            {"content": "note", "category": "note", "quote": "q", "source": "manual", "status": "accepted"},
        ])
        req = urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertIn("/rest/v1/insights", req.full_url)
        body = json.loads(req.data)
        self.assertEqual(body[0]["meeting_id"], "m1")
        self.assertEqual(body[0]["category"], "signal")
        self.assertEqual(body[1]["quote"], "q")

    @mock.patch("supabase_store.urlopen")
    def test_insert_insights_normalizes_keys_across_items(self, urlopen):
        urlopen.return_value = fake_response(201)
        ss.insert_insights("m1", [
            {"content": "no quote here", "category": "signal", "source": "extracted", "status": "candidate"},
            {"content": "note", "category": "note", "quote": "q", "source": "manual", "status": "accepted"},
        ])
        req = urlopen.call_args[0][0]
        body = json.loads(req.data)
        self.assertEqual(set(body[0].keys()), set(body[1].keys()))
        self.assertIsNone(body[0]["quote"])

    @mock.patch("supabase_store.urlopen")
    def test_insert_insights_empty_is_noop(self, urlopen):
        ss.insert_insights("m1", [])
        urlopen.assert_not_called()

    @mock.patch("supabase_store.urlopen")
    def test_meeting_has_extracted_insights(self, urlopen):
        urlopen.return_value = fake_response(200, json.dumps([{"id": "i1"}]).encode())
        self.assertTrue(ss.meeting_has_extracted_insights("m1"))
        url = urlopen.call_args[0][0].full_url
        self.assertIn("insights?", url)
        self.assertIn("meeting_id=eq.m1", url)
        self.assertIn("source=eq.extracted", url)

    @mock.patch("supabase_store.urlopen")
    def test_meeting_has_extracted_insights_false_when_empty(self, urlopen):
        urlopen.return_value = fake_response(200, b"[]")
        self.assertFalse(ss.meeting_has_extracted_insights("m1"))


if __name__ == "__main__":
    unittest.main()

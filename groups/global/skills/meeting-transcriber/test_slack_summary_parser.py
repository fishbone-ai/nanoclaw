import unittest
from slack_summary_parser import parse_slack_summary

CANONICAL = """*Meeting: Sean × Todd prep* | 2026-06-29
_2026-06-29-sean-todd_ | <https://github.com/fishbone-ai/nanoclaw/blob/main/groups/global/calls/meetings/2026-06-29-sean-todd.md|Transcription>

*Participants*
• Avishay, Sean Murphy (⚠️ Speaker 3 identity unclear — who is this?)

*Summary*
• Discussed partnership scope
• Agreed on next steps

*Decisions*
• Go with option B

*Suggested Linear issues* (reply ✅ to approve all, or list which ones to create)
1. [high] Draft proposal — Send by Friday
"""


class TestParser(unittest.TestCase):
    def test_parses_canonical_format(self):
        r = parse_slack_summary(CANONICAL)
        self.assertEqual(r["stem"], "2026-06-29-sean-todd")
        self.assertEqual(r["title"], "Sean × Todd prep")
        self.assertEqual(r["date"], "2026-06-29")
        self.assertEqual(r["participants"], ["Avishay", "Sean Murphy"])
        self.assertIn("## Summary", r["summary_md"])
        self.assertIn("- Discussed partnership scope", r["summary_md"])
        self.assertIn("## Decisions", r["summary_md"])
        self.assertNotIn("Linear", r["summary_md"])  # suggestions section excluded

    def test_rejects_non_canonical_messages(self):
        self.assertIsNone(parse_slack_summary("📋 *Summary: Or Git × Avishay — May 10, 2026*\nIntro..."))
        self.assertIsNone(parse_slack_summary("random chatter"))
        self.assertIsNone(parse_slack_summary(""))

    def test_missing_participants_section_is_ok(self):
        text = "*Meeting: Quick sync* | 2026-06-01\n_2026-06-01-quick-sync_ | <http://x|T>\n\n*Summary*\n• a\n"
        r = parse_slack_summary(text)
        self.assertEqual(r["participants"], [])
        self.assertIn("- a", r["summary_md"])


if __name__ == "__main__":
    unittest.main()

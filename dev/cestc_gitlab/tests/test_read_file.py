import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import read_file  # noqa: E402


class ParseFileUrlTests(unittest.TestCase):
    def test_parses_modern_url_and_decodes_components(self):
        project, target = read_file.parse_file_url(
            "https://code.cestc.cn/group%20one/team/repo/-/blob/main/docs/a%20b.txt#L3"
        )
        self.assertEqual(project, "group one/team/repo")
        self.assertEqual(target, "main/docs/a b.txt")

    def test_supports_legacy_raw_url(self):
        project, target = read_file.parse_file_url(
            "http://code.cestc.cn/team/repo/raw/v1.0/README.md"
        )
        self.assertEqual(project, "team/repo")
        self.assertEqual(target, "v1.0/README.md")

    def test_rejects_other_hosts_and_credentials(self):
        for url in (
            "https://gitlab.com/team/repo/-/blob/main/a.txt",
            "https://user:secret@code.cestc.cn/team/repo/-/blob/main/a.txt",
            "https://code.cestc.cn/team/repo/-/tree/main",
        ):
            with self.subTest(url=url), self.assertRaises(read_file.ReadFileError):
                read_file.parse_file_url(url)


class FetchFileTests(unittest.TestCase):
    @patch("read_file.api")
    def test_infers_ref_containing_slashes(self, mock_api):
        calls = []

        def fake_api(glab, endpoint):
            calls.append(endpoint)
            if len(calls) == 1:
                raise read_file.ApiError("glab: HTTP 404")
            return b"hello\n"

        mock_api.side_effect = fake_api
        project, ref, path, content = read_file.fetch_file(
            "https://code.cestc.cn/team/repo/-/blob/feature/demo/src/a.txt"
        )

        self.assertEqual((project, ref, path, content), ("team/repo", "feature/demo", "src/a.txt", b"hello\n"))
        self.assertIn("ref=feature%2Fdemo%2Fsrc", calls[0])
        self.assertIn("repository/files/src%2Fa.txt/raw?ref=feature%2Fdemo", calls[1])

    @patch("read_file.api")
    def test_does_not_hide_authentication_or_server_errors(self, mock_api):
        mock_api.side_effect = read_file.ApiError("glab: HTTP 401")
        with self.assertRaisesRegex(read_file.ReadFileError, "401"):
            read_file.fetch_file("https://code.cestc.cn/team/repo/-/blob/main/a.txt")
        mock_api.assert_called_once()

    @patch("read_file.subprocess.run")
    def test_every_api_call_pins_the_host_and_uses_no_shell(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], 0, stdout=b"{}", stderr=b"")
        read_file.api("custom-glab", "version")
        command = mock_run.call_args.args[0]
        self.assertEqual(command, ["custom-glab", "api", "--hostname", "code.cestc.cn", "version"])
        self.assertNotIn("shell", mock_run.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()

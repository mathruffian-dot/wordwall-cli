import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import wordwall


class WordwallLoginFlowTest(unittest.TestCase):
    def test_grab_session_uses_managed_chrome_metadata_by_default(self):
        with tempfile.TemporaryDirectory() as folder:
            metadata = Path(folder) / "chrome-login.json"
            profile = Path(folder) / "profile"
            profile.mkdir()
            (profile / "DevToolsActivePort").write_text(
                "9444\n/devtools/browser/wordwall-test\n", encoding="utf-8")
            metadata.write_text(json.dumps({
                "port": 9444,
                "profile_dir": str(profile),
            }), encoding="utf-8")
            with patch.object(wordwall, "CHROME_LOGIN_FILE", metadata):
                self.assertEqual(
                    wordwall._resolve_grab_session_cdp_url(None),
                    "http://127.0.0.1:9444")

    def test_grab_session_requires_metadata_unless_url_is_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "missing.json"
            with patch.object(wordwall, "CHROME_LOGIN_FILE", missing):
                with self.assertRaises(SystemExit) as caught:
                    wordwall._resolve_grab_session_cdp_url(None)
                self.assertEqual(caught.exception.code, 4)
                self.assertEqual(
                    wordwall._resolve_grab_session_cdp_url(
                        "http://127.0.0.1:9555/"),
                    "http://127.0.0.1:9555")

    def test_grab_session_rejects_stale_profile_port(self):
        with tempfile.TemporaryDirectory() as folder:
            profile = Path(folder) / "profile"
            profile.mkdir()
            (profile / "DevToolsActivePort").write_text(
                "9555\n/devtools/browser/not-wordwall\n", encoding="utf-8")
            metadata = Path(folder) / "chrome-login.json"
            metadata.write_text(json.dumps({
                "port": 9444,
                "profile_dir": str(profile),
            }), encoding="utf-8")
            with patch.object(wordwall, "CHROME_LOGIN_FILE", metadata):
                with self.assertRaises(SystemExit) as caught:
                    wordwall._resolve_grab_session_cdp_url(None)
        self.assertEqual(caught.exception.code, 4)

    def test_login_rejects_noninteractive_stdin_before_playwright(self):
        stdin = Mock()
        stdin.isatty.return_value = False
        with patch.object(wordwall.sys, "stdin", stdin), \
                patch.object(wordwall, "_need_playwright") as need_playwright:
            with self.assertRaises(SystemExit) as caught:
                wordwall.cmd_login(argparse.Namespace())
        self.assertEqual(caught.exception.code, 2)
        need_playwright.assert_not_called()

    def test_login_rejects_noninteractive_stdout_before_playwright(self):
        stdin = Mock()
        stdout = Mock()
        stdin.isatty.return_value = True
        stdout.isatty.return_value = False
        with patch.object(wordwall.sys, "stdin", stdin), \
                patch.object(wordwall.sys, "stdout", stdout), \
                patch.object(wordwall, "_need_playwright") as need_playwright:
            with self.assertRaises(SystemExit) as caught:
                wordwall.cmd_login(argparse.Namespace())
        self.assertEqual(caught.exception.code, 2)
        need_playwright.assert_not_called()

    def test_chrome_login_refuses_occupied_port_before_launch(self):
        args = argparse.Namespace(
            port=9333, profile_dir="unused", chrome_path=None)
        with patch.object(wordwall, "_port_is_available", return_value=False), \
                patch.object(wordwall, "_find_chrome") as find_chrome, \
                patch.object(wordwall.subprocess, "Popen") as popen:
            with self.assertRaises(SystemExit) as caught:
                wordwall.cmd_chrome_login(args)
        self.assertEqual(caught.exception.code, 4)
        find_chrome.assert_not_called()
        popen.assert_not_called()

    def test_parser_uses_dedicated_chrome_login_defaults(self):
        parser = wordwall.build_parser()
        chrome_args = parser.parse_args(["chrome-login"])
        grab_args = parser.parse_args(["grab-session"])
        self.assertEqual(chrome_args.port, 9333)
        self.assertIsNone(grab_args.cdp_url)


if __name__ == "__main__":
    unittest.main()

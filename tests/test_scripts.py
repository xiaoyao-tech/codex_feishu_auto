from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "codex-feishu-auto"
SCRIPTS = SKILL / "scripts"


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, env=env, check=False)


class SkillScriptsTest(unittest.TestCase):
    def test_skill_frontmatter_and_evals(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: codex-feishu-auto", text)
        self.assertIn("description:", text)
        evals = json.loads((SKILL / "evals" / "evals.json").read_text(encoding="utf-8"))
        self.assertEqual(evals["skill_name"], "codex-feishu-auto")
        self.assertEqual(len(evals["evals"]), 3)

    def test_init_render_and_state_transitions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            watch = Path(temp) / "launch"
            init = run(
                sys.executable,
                str(SCRIPTS / "init_watch.py"),
                "--name",
                "Test launch",
                "--mode",
                "live-event",
                "--output-dir",
                str(watch),
                "--feishu-doc",
                "https://example.feishu.cn/wiki/TEST",
                "--source",
                "Official|https://example.com/live",
                "--capture",
                "--capture-keyword",
                "Test launch",
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            self.assertTrue((watch / "config.json").exists())
            self.assertTrue((watch / "state.json").exists())
            self.assertTrue((watch / "duty_log.md").exists())

            rendered = run(
                sys.executable,
                str(SCRIPTS / "render_prompt.py"),
                "--config",
                str(watch / "config.json"),
                "--format",
                "prompt",
            )
            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            for phrase in (
                "Read",
                "Feishu",
                "fetch again",
                "consecutive no-update",
                "screenshot loop",
                "pause or delete",
            ):
                self.assertIn(phrase, rendered.stdout)

            state_path = watch / "state.json"
            for index in range(3):
                recorded = run(
                    sys.executable,
                    str(SCRIPTS / "statectl.py"),
                    "record",
                    "--state",
                    str(state_path),
                    "--new-count",
                    "0",
                    "--now",
                    f"2026-01-01T00:0{index}:00+00:00",
                )
                self.assertEqual(recorded.returncode, 0, recorded.stderr)
            close_check = run(
                sys.executable,
                str(SCRIPTS / "statectl.py"),
                "should-close",
                "--state",
                str(state_path),
                "--threshold",
                "3",
            )
            self.assertTrue(json.loads(close_check.stdout)["should_close"])

            reset = run(
                sys.executable,
                str(SCRIPTS / "statectl.py"),
                "record",
                "--state",
                str(state_path),
                "--new-count",
                "1",
                "--seen",
                "official:test",
                "--revision",
                "9",
            )
            state = json.loads(reset.stdout)
            self.assertEqual(state["consecutive_no_updates"], 0)
            self.assertEqual(state["last_write_revision"], "9")
            self.assertIn("official:test", state["seen_items"])

    def test_clean_codex_home_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            env = os.environ.copy()
            env["CODEX_HOME"] = str(Path(temp) / "codex-home")
            installed = run("bash", str(ROOT / "install.sh"), env=env)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            target = Path(env["CODEX_HOME"]) / "skills" / "codex-feishu-auto"
            self.assertTrue((target / "SKILL.md").exists())
            doctor = run(
                sys.executable,
                str(target / "scripts" / "doctor.py"),
                "--skip-lark",
                "--config",
                str(SKILL / "assets" / "watch-config.example.json"),
                "--json",
            )
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            self.assertTrue(json.loads(doctor.stdout)["ok"])

        unsafe = run("bash", str(ROOT / "install.sh"), "--target", "/", "--force")
        self.assertEqual(unsafe.returncode, 2)
        self.assertIn("Refusing unsafe install target", unsafe.stderr)

    def test_all_modes_render_their_own_rules(self) -> None:
        expected = {
            "live-event": "Live-event rules",
            "topic-duty": "Topic-duty rules",
            "ops-check": "Operations-check rules",
        }
        with tempfile.TemporaryDirectory() as temp:
            for mode, marker in expected.items():
                watch = Path(temp) / mode
                initialized = run(
                    sys.executable,
                    str(SCRIPTS / "init_watch.py"),
                    "--name",
                    mode,
                    "--mode",
                    mode,
                    "--output-dir",
                    str(watch),
                    "--source",
                    "Official|https://example.com/source",
                )
                self.assertEqual(initialized.returncode, 0, initialized.stderr)
                rendered = run(
                    sys.executable,
                    str(SCRIPTS / "render_prompt.py"),
                    "--config",
                    str(watch / "config.json"),
                    "--format",
                    "prompt",
                )
                self.assertEqual(rendered.returncode, 0, rendered.stderr)
                self.assertIn(marker, rendered.stdout)
                self.assertIn("No Feishu target is configured", rendered.stdout)

    def test_safe_dry_run_alert(self) -> None:
        result = run(
            sys.executable,
            str(SCRIPTS / "alert.py"),
            "--message",
            "test",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["lark_configured"])


if __name__ == "__main__":
    unittest.main()

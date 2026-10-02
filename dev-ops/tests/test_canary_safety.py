import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".github" / "scripts"
DUMMY_URL = "https://hc-ping.com/00000000-0000-0000-0000-000000000000"


class CanarySafetyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.event = self.path / "event.json"
        self.capture = self.path / "curl.json"
        fake = self.path / "curl"
        fake.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, pathlib, sys\n"
            "pathlib.Path(os.environ['CURL_CAPTURE']).write_text(json.dumps("
            "{'args': sys.argv[1:], 'config': sys.stdin.read()}))\n"
            "sys.stdout.write(os.environ.get('FAKE_HTTP_CODE', '200'))\n"
            "sys.exit(int(os.environ.get('FAKE_CURL_EXIT', '0')))\n"
        )
        fake.chmod(0o700)
        self.env = {
            "PATH": str(self.path) + os.pathsep + os.environ["PATH"],
            "CURL_CAPTURE": str(self.capture),
        }

    def run_script(self, name, **env):
        return subprocess.run(
            ["bash", str(SCRIPTS / name)],
            env=self.env | env,
            text=True,
            capture_output=True,
            timeout=10,
        )

    def mode(self, event, inputs=None):
        self.event.write_text(json.dumps({"inputs": inputs or {}}))
        return self.run_script(
            "canary-mode.sh",
            GITHUB_EVENT_NAME=event,
            GITHUB_EVENT_PATH=str(self.event),
        )

    def ping(self, result="success", url=DUMMY_URL, **env):
        return self.run_script(
            "canary-heartbeat.sh",
            CANARY_HEARTBEAT_URL=url,
            CANARY_RESULT=result,
            **env,
        )

    def test_push_and_pr_keep_the_committed_lock(self):
        for event in ("push", "pull_request"):
            with self.subTest(event=event):
                result = self.mode(event, {"update_dependencies": True})
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout.strip(), "locked")

    def test_schedule_always_selects_the_update_path(self):
        result = self.mode("schedule")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "update")

    def test_manual_default_and_explicit_false_keep_the_lock(self):
        for value in (None, False, "false"):
            with self.subTest(value=value):
                inputs = {} if value is None else {"update_dependencies": value}
                result = self.mode("workflow_dispatch", inputs)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout.strip(), "locked")

    def test_manual_true_exercises_the_scheduled_update_path(self):
        for value in (True, "true"):
            with self.subTest(value=value):
                result = self.mode("workflow_dispatch", {"update_dependencies": value})
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout.strip(), "update")

    def test_invalid_or_missing_event_data_does_not_fall_back_to_green(self):
        for value in ("$(touch injected)", 1, ["true"], {"enabled": True}):
            with self.subTest(value=value):
                result = self.mode("workflow_dispatch", {"update_dependencies": value})
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("update", result.stdout)
        missing = self.run_script("canary-mode.sh", GITHUB_EVENT_NAME="workflow_dispatch")
        self.assertNotEqual(missing.returncode, 0)
        self.assertNotEqual(self.mode("unknown").returncode, 0)
        self.assertFalse((ROOT / "injected").exists())

    def test_malformed_event_schema_and_multiple_documents_fail(self):
        for raw in ("null", "[]", '"event"', "{}", '{"inputs": null}',
                    '{"inputs": []}', '{"inputs": {"update_dependencies": null}}',
                    '{"inputs": {"update_dependencies": true}}\n'
                    '{"inputs": {"update_dependencies": false}}'):
            with self.subTest(raw=raw):
                self.event.write_text(raw)
                result = self.run_script(
                    "canary-mode.sh", GITHUB_EVENT_NAME="workflow_dispatch",
                    GITHUB_EVENT_PATH=str(self.event),
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_success_uses_post_and_stdin_without_exposing_url(self):
        result = self.ping()
        self.assertEqual(result.returncode, 0, result.stderr)
        call = json.loads(self.capture.read_text())
        self.assertEqual(call["config"], 'url = "' + DUMMY_URL + '"\n')
        self.assertEqual(call["args"][0], "--disable")
        self.assertIn("--fail", call["args"])
        self.assertIn("--max-time", call["args"])
        self.assertIn("--retry-max-time", call["args"])
        self.assertIn("POST", call["args"])
        self.assertEqual(call["args"][-2:], ["--config", "-"])
        self.assertNotIn(DUMMY_URL, " ".join(call["args"]))
        self.assertNotIn(DUMMY_URL, result.stdout + result.stderr)
        self.assertNotIn("--location", call["args"])

    def test_failed_cancelled_or_skipped_update_sends_fail_and_stays_failed(self):
        for status in ("failure", "cancelled", "skipped"):
            with self.subTest(status=status):
                result = self.ping(status)
                self.assertNotEqual(result.returncode, 0)
                call = json.loads(self.capture.read_text())
                self.assertEqual(call["config"], 'url = "' + DUMMY_URL + '/fail"\n')

    def test_missing_or_invalid_secret_never_calls_curl(self):
        for url in ("", "http://hc-ping.com/00000000-0000-0000-0000-000000000000",
                    DUMMY_URL + "/other", DUMMY_URL + "?token=x",
                    DUMMY_URL + '\nheader = "Authorization: injected"'):
            with self.subTest(url=url):
                result = self.ping(url=url)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.capture.exists())
                self.assertNotIn(url, result.stderr) if url else None

    def test_missing_or_invalid_canary_result_never_sends_success(self):
        for status in ("", "unknown"):
            with self.subTest(status=status):
                result = self.ping(status)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.capture.exists())

    def test_transport_errors_http_errors_and_redirects_fail(self):
        for exit_code, http_code in (("7", "000"), ("22", "500"),
                                     ("0", "302"), ("0", "200\n302")):
            with self.subTest(exit_code=exit_code, http_code=http_code):
                result = self.ping(FAKE_CURL_EXIT=exit_code, FAKE_HTTP_CODE=http_code)
                self.assertNotEqual(result.returncode, 0)


    def workflow_command(self, name):
        workflow = ROOT / ".github" / "workflows" / (
            "ddev-canary.yml" if (ROOT / ".github/workflows/ddev-canary.yml").exists()
            else "ddev-smoke.yml"
        )
        lines = workflow.read_text().splitlines()
        prefix = "      " + name + ": "
        for number, line in enumerate(lines):
            if line.startswith(prefix):
                value = line[len(prefix):]
                if value != "|":
                    return value
                block = []
                for following in lines[number + 1:]:
                    if following and not following.startswith("        "):
                        break
                    block.append(following[8:])
                return "\n".join(block)
        self.fail("Missing real workflow command: " + name)

    def nested_workflow_command(self, name, failure="", event="schedule", inputs=None):
        (self.path / ".github").mkdir(exist_ok=True)
        scripts = self.path / ".github" / "scripts"
        if not scripts.exists():
            scripts.symlink_to(SCRIPTS, target_is_directory=True)
        (self.path / ".env.example").write_text(
            "WP_HOME=https://sympress-starter.ddev.site\n"
        )
        self.event.write_text(json.dumps({"inputs": inputs or {}}))
        ddev = self.path / "ddev"
        ddev.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, pathlib, sys\n"
            "args = ' '.join(sys.argv[1:])\n"
            "with pathlib.Path(os.environ['DDEV_CAPTURE']).open('a') as stream:\n"
            "    stream.write(args + '\\n')\n"
            "if args == 'describe -j':\n"
            "    print(json.dumps({'raw': {'primary_url': 'https://fixture.invalid'}}))\n"
            "if args == os.environ.get('FAKE_DDEV_FAIL'):\n"
            "    sys.exit(17)\n"
        )
        ddev.chmod(0o700)
        calls = self.path / "ddev-calls.txt"
        calls.unlink(missing_ok=True)
        result = subprocess.run(
            ["bash", "-lc", 'export PATH="$CANARY_TEST_BIN:$PATH"\n'
             + self.workflow_command(name)],
            cwd=self.path,
            env=self.env | {
                "CANARY_TEST_BIN": str(self.path), "DDEV_CAPTURE": str(calls),
                "FAKE_DDEV_FAIL": failure, "GITHUB_EVENT_NAME": event,
                "GITHUB_EVENT_PATH": str(self.event),
            },
            text=True, capture_output=True, timeout=10,
        )
        return result, calls.read_text().splitlines() if calls.exists() else []

    def test_nested_setup_stops_after_a_failed_dependency_update(self):
        result, calls = self.nested_workflow_command(
            "setup_command",
            failure="composer update --with-all-dependencies --no-interaction --no-scripts",
        )
        self.assertEqual(result.returncode, 17, result.stderr)
        self.assertFalse(any(call.startswith("composer install") for call in calls))
        self.assertFalse(any(call.startswith("composer runtime:setup") for call in calls))

    def test_nested_setup_rejects_invalid_mode_before_installation(self):
        result, calls = self.nested_workflow_command(
            "setup_command", event="workflow_dispatch",
            inputs={"update_dependencies": 1},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(call.startswith("composer ") for call in calls))

    def test_nested_setup_stops_after_install_or_runtime_failure(self):
        for failure in ("composer install --no-interaction",
                        "composer runtime:setup --no-interaction"):
            with self.subTest(failure=failure):
                result, calls = self.nested_workflow_command(
                    "setup_command", failure=failure,
                )
                self.assertEqual(result.returncode, 17, result.stderr)
                self.assertEqual(calls[-1], failure)

    def test_nested_runtime_and_wordpress_checks_propagate_failures(self):
        failures = ["composer qa"]
        if (ROOT / ".github/workflows/ddev-smoke.yml").exists():
            failures += ["exec wp core is-installed", "exec wp db check"]
        for failure in failures:
            with self.subTest(failure=failure):
                result, calls = self.nested_workflow_command(
                    "playwright_run_command", failure=failure,
                )
                self.assertEqual(result.returncode, 17, result.stderr)
                self.assertEqual(calls[-1], failure)
                self.assertFalse(self.capture.exists())

    def test_only_scheduled_runs_can_update_the_external_weekly_check(self):
        workflow = ROOT / ".github" / "workflows" / (
            "ddev-canary.yml" if (ROOT / ".github/workflows/ddev-canary.yml").exists()
            else "ddev-smoke.yml"
        )
        text = workflow.read_text()
        self.assertIn("if: ${{ always() && github.event_name == 'schedule' }}", text)
        self.assertIn("CANARY_RESULT: ${{ needs.", text)
        self.assertIn("CANARY_HEARTBEAT_URL: ${{ secrets.CANARY_HEARTBEAT_URL }}", text)
        self.assertIn('canary_mode="$(bash .github/scripts/canary-mode.sh)"', text)
        self.assertIn("update_dependencies:", text)
        self.assertIn("default: false", text)


if __name__ == "__main__":
    unittest.main()

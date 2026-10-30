"""Regressões do instalador sem daemon Docker ou alteração de bancos reais."""

import contextlib
import io
import json
import os
import pty
import shutil
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]

FAKE_DOCKER = """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
entry = {
    "args": args,
    "inherited_overrides": [
        name for name in ("COMPOSE_PROJECT_NAME", "DB_PASSWORD", "DB_USER", "ERP_PORT")
        if name in os.environ
    ],
}
with open(os.environ["TEST_DOCKER_LOG"], "a") as log:
    log.write(json.dumps(entry) + "\\n")
if "build" in args and os.environ.get("TEST_BUILD_FAILURE") == "1":
    sys.exit(9)
if args[:2] == ["volume", "ls"] and os.environ.get("TEST_EXISTING_VOLUME") == "1":
    print("erp-development_postgres_dev_data")
if "exec" in args and "pg_dump" in " ".join(args):
    print("-- backup de teste sem dados reais")
if "run" in args and "--entrypoint" in args:
    Path(os.environ["TEST_DOCTOR_SOURCE"]).write_text(sys.stdin.read())
    sys.exit(int(os.environ.get("TEST_DOCTOR_EXIT", "0")))
sys.exit(0)
"""


class ErpctlRegressionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.project = self.root / "app"
        self.project.mkdir(mode=0o700)
        for name in ("erpctl", "compose.yml", "compose.dev.yml", "VERSION"):
            shutil.copy2(PROJECT / name, self.project / name)
        for name in (".env.dev.example", ".env.example"):
            shutil.copy2(PROJECT / name, self.project / name)
        for name in (".env.dev", ".env"):
            (self.project / name).write_text(
                "COMPOSE_PROJECT_NAME=erp-development\n"
                "DB_PASSWORD=senha-ficticia-local\n"
                "ERP_PORT=8021\n"
            )
            (self.project / name).chmod(0o600)
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        docker = self.bin_dir / "docker"
        docker.write_text(FAKE_DOCKER)
        docker.chmod(0o755)
        self.log = self.root / "docker.jsonl"
        self.doctor_source = self.root / "doctor.py"
        self.env = {
            **os.environ,
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "TEST_DOCKER_LOG": str(self.log),
            "TEST_DOCTOR_SOURCE": str(self.doctor_source),
            "COMPOSE_PROJECT_NAME": "projeto-exportado-no-terminal",
            "DB_PASSWORD": "senha-ficticia-exportada",
            "DB_USER": "usuario-exportado",
            "ERP_PORT": "9999",
        }

    def run_cli(self, *args, **overrides):
        return subprocess.run(
            ["sh", str(self.project / "erpctl"), *args],
            cwd=self.project,
            env={**self.env, **overrides},
            input="",
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def entries(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_exported_values_do_not_override_selected_environment(self):
        result = self.run_cli("status", "development")
        self.assertEqual(result.returncode, 0, result.stderr)
        entry = self.entries()[-1]
        self.assertEqual(entry["inherited_overrides"], [])
        self.assertEqual(entry["args"][1:5], ["--env-file", ".env.dev", "-f", "compose.dev.yml"])

    def test_deploy_makes_bind_mount_root_accessible_without_opening_env(self):
        result = self.run_cli("deploy", "development")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE(self.project.stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE((self.project / ".env.dev").stat().st_mode), 0o600)
        dump = next((self.project / "backups" / "development").glob("database-*.sql"))
        self.assertEqual(stat.S_IMODE(dump.stat().st_mode), 0o600)

    def test_build_failure_stops_before_up_and_does_not_report_success(self):
        result = self.run_cli("deploy", "development", TEST_BUILD_FAILURE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any("up" in entry["args"] for entry in self.entries()))
        self.assertNotIn("Deploy concluído", result.stdout)

    def test_password_recovery_is_rejected_for_production(self):
        result = self.run_cli("db-password", "production")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_password_recovery_requires_interactive_input(self):
        result = self.run_cli("db-password", "development")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_password_recovery_backs_up_before_opening_password_prompt(self):
        master, slave = pty.openpty()
        try:
            result = subprocess.run(
                ["sh", str(self.project / "erpctl"), "db-password", "development"],
                cwd=self.project,
                env=self.env,
                stdin=slave,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        finally:
            os.close(master)
            os.close(slave)
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = self.entries()
        backup_index = next(
            i for i, entry in enumerate(entries) if "pg_dump" in " ".join(entry["args"])
        )
        password_index = next(
            i for i, entry in enumerate(entries) if "\\password" in " ".join(entry["args"])
        )
        self.assertLess(backup_index, password_index)
        self.assertNotIn("senha-ficticia-local", result.stdout + result.stderr)

    def test_doctor_runs_read_only_without_app_entrypoint_or_dependencies(self):
        result = self.run_cli("doctor", "development", TEST_DOCTOR_EXIT="1")
        self.assertEqual(result.returncode, 1)
        args = self.entries()[-1]["args"]
        self.assertIn("--no-deps", args)
        self.assertIn("--entrypoint", args)
        self.assertNotIn("up", args)
        self.assertTrue(self.doctor_source.exists())

    def test_missing_env_with_existing_volume_does_not_generate_new_credentials(self):
        (self.project / ".env.dev").unlink()
        result = self.run_cli("install", "development", TEST_EXISTING_VOLUME="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.project / ".env.dev").exists())
        self.assertNotIn("build", " ".join(str(entry["args"]) for entry in self.entries()))
        self.assertIn("volume do banco já existe", result.stderr)

    def test_new_install_generates_private_configuration_and_accessible_root(self):
        (self.project / ".env.dev").unlink()
        result = self.run_cli("install", "development", "10.20.0.74")
        self.assertEqual(result.returncode, 0, result.stderr)
        configuration = (self.project / ".env.dev").read_text()
        self.assertNotIn("gerada-automaticamente", configuration)
        self.assertIn("DJANGO_ALLOWED_HOSTS=10.20.0.74,localhost,127.0.0.1", configuration)
        self.assertIn("DJANGO_CSRF_TRUSTED_ORIGINS=http://10.20.0.74:8021", configuration)
        self.assertEqual(stat.S_IMODE((self.project / ".env.dev").stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.project.stat().st_mode), 0o755)


class DoctorOutputTests(unittest.TestCase):
    def setUp(self):
        source = (PROJECT / "erpctl").read_text()
        self.source = source.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]

    def evaluate(self, failure=False, accessible=True):
        driver = types.ModuleType("psycopg2")

        class DatabaseError(Exception):
            pass

        driver.Error = DatabaseError
        connection = unittest.mock.MagicMock()
        if failure:
            driver.connect = unittest.mock.Mock(
                side_effect=DatabaseError("password authentication failed ficticio")
            )
        else:
            driver.connect = unittest.mock.Mock(return_value=connection)
        environment = {
            "ERP_ENVIRONMENT": "development",
            "DB_HOST": "db",
            "DB_PASSWORD": "senha-ficticia-que-nao-deve-aparecer",
        }
        output = io.StringIO()
        info = types.SimpleNamespace(st_mode=stat.S_IFDIR | 0o755)
        with (
            patch.dict(os.environ, environment, clear=True),
            patch.dict(sys.modules, {"psycopg2": driver}),
            patch.object(sys, "argv", ["-", "development"]),
            patch("os.stat", return_value=info),
            patch("os.access", return_value=accessible),
            contextlib.redirect_stdout(output),
            self.assertRaises(SystemExit) as exit_context,
        ):
            exec(compile(self.source, "erpctl-doctor", "exec"), {})
        self.assertNotIn(environment["DB_PASSWORD"], output.getvalue())
        return exit_context.exception.code, output.getvalue(), connection

    def test_success_checks_real_credentials_with_select(self):
        code, output, connection = self.evaluate()
        self.assertEqual(code, 0)
        self.assertIn("autenticação TCP e SELECT 1 aprovados", output)
        connection.cursor.return_value.__enter__.return_value.execute.assert_called_with("SELECT 1")
        connection.close.assert_called_once()

    def test_password_failure_explains_without_exposing_secret(self):
        code, output, _ = self.evaluate(failure=True)
        self.assertEqual(code, 1)
        self.assertIn("DB_PASSWORD não autentica", output)

    def test_inaccessible_mount_is_reported_even_with_valid_database(self):
        code, output, _ = self.evaluate(accessible=False)
        self.assertEqual(code, 1)
        self.assertIn("acesso=FALHA", output)


if __name__ == "__main__":
    unittest.main()

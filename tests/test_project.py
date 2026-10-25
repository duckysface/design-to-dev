#!/usr/bin/env python3
"""Tests : détection du projet (intention, écrans, contrat), skills compagnes et base de sécurité. Stdlib uniquement.

    python tests/test_project.py
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
DETECT = SKILL / "scripts" / "detect_project.py"
SECURITY = SKILL / "scripts" / "security_check.py"
PY = sys.executable

LOGIN = ('<html><head><title>Connexion Admin</title></head><body><form>'
         '<input type="email" name="email"><input type="password" name="password"></form></body></html>\n')
DASHBOARD = ('<html><body><aside class="sidebar"></aside><h1>Clients</h1><table><tr><th>Nom</th>'
             '<th>Email</th><th>Statut</th></tr></table><script>const mockClients = [{}];</script></body></html>\n')
# Secret factice assemblé à l'exécution : ce fichier ne contient aucune valeur littérale détectable.
FAKE_SECRET = "AbCd" + "Ef1234567890XYZ"
APP_JS = "\n".join([
    "el.innerHTML = data;",
    'localStorage.setItem("token", t);',
    'const q = "SELECT * FROM users WHERE id=" + id;',
    f'const api_key = "{FAKE_SECRET}";',
    'fetch("http://api.example.org/x");',
    "const k = process.env.API_KEY;",
]) + "\n"


def run(args):
    return subprocess.run([PY, "-I", *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", timeout=120)


class ProjectTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.src = self.tmp / "design"
        (self.src / "demos").mkdir(parents=True)
        (self.src / "login.html").write_text(LOGIN, encoding="utf-8")
        (self.src / "demos" / "dashboard.html").write_text(DASHBOARD, encoding="utf-8")
        (self.src / "app.js").write_text(APP_JS, encoding="utf-8")
        self.inv = self.tmp / "design-inventory.json"

    def tearDown(self):
        self._tmp.cleanup()

    def scan(self):
        r = run([DETECT, "scan", self.src, "--out", self.inv])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(self.inv.read_text(encoding="utf-8"))

    # ---- detect_project.py scan

    def test_intent_is_dashboard_with_backend(self):
        intent = self.scan()["intent"]
        self.assertEqual(intent["primary"], "dashboard")
        self.assertIn("backend", intent["secondary"])
        self.assertFalse(intent["ambiguous"])
        self.assertTrue(intent["questions"])

    def test_existing_screens_are_inventoried(self):
        screens = {s["path"]: s for s in self.scan()["screens"]}
        login = screens["login.html"]
        self.assertEqual(login["kind"], "page")
        self.assertIn("auth", login["features"])
        self.assertEqual({f["name"] for f in login["fields"]}, {"email", "password"})
        demo = screens["demos/dashboard.html"]
        self.assertEqual(demo["kind"], "demo")
        self.assertEqual(demo["status"], "mock-data")
        self.assertEqual(set(demo["table_columns"]), {"Nom", "Email", "Statut"})

    def test_backend_contract_from_design(self):
        contract = self.scan()["backend_contract"]
        self.assertTrue(contract["auth"])
        self.assertIn("admin", contract["roles"])
        self.assertIn("clients", contract["entities"])
        self.assertIn("POST /api/auth/login", contract["endpoints"])
        self.assertIn("GET /api/clients", contract["endpoints"])

    def test_empty_folder_is_ambiguous(self):
        empty = self.tmp / "vide"
        empty.mkdir()
        r = run([DETECT, "scan", empty, "--out", self.inv])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(json.loads(self.inv.read_text(encoding="utf-8"))["intent"]["ambiguous"])

    # ---- detect_project.py skills

    def test_skills_json_lists_companions(self):
        r = run([DETECT, "skills", "--json"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        data = json.loads(r.stdout)
        for name in ("superpowers", "security-audit"):
            self.assertIn(name, data)
            self.assertIn("installed", data[name])
            self.assertTrue(data[name]["install"])

    def test_skills_require_unknown_fails(self):
        r = run([DETECT, "skills", "--require", "skill-qui-nexiste-pas"])
        self.assertNotEqual(r.returncode, 0)

    # ---- security_check.py

    def test_security_scan_candidates(self):
        r = run([SECURITY, "scan", self.src, "--json"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        findings = json.loads(r.stdout)["findings"]
        rules = {f["rule"] for f in findings}
        for rule in ("xss-sink", "sql-concat", "cleartext-http", "token-localstorage", "hardcoded-secret"):
            self.assertIn(rule, rules)
        self.assertIn("deploy-headers", rules)
        for f in findings:
            self.assertIn(f["status"], ("candidate", "needs_validation"))
            self.assertNotIn("severity", f)
            self.assertTrue(f["cwe"].startswith("CWE-"))

    def test_security_scan_masks_secrets(self):
        r = run([SECURITY, "scan", self.src, "--json"])
        self.assertNotIn(FAKE_SECRET, r.stdout)
        r = run([SECURITY, "scan", self.src])
        self.assertNotIn(FAKE_SECRET, r.stdout)

    def test_env_var_is_not_a_secret(self):
        (self.src / "app.js").write_text("const k = process.env.API_KEY;\n", encoding="utf-8")
        r = run([SECURITY, "scan", self.src, "--json"])
        rules = {f["rule"] for f in json.loads(r.stdout)["findings"]}
        self.assertNotIn("hardcoded-secret", rules)

    def test_requirements_from_design(self):
        self.scan()
        out = self.tmp / "exigences.md"
        r = run([SECURITY, "requirements", "--intent", "dashboard", "--inventory", self.inv, "--out", out])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        text = out.read_text(encoding="utf-8")
        self.assertIn("Argon2id", text)
        self.assertIn("POST /api/auth/login", text)
        self.assertIn("V2.2.1", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)

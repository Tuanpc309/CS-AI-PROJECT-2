"""The web API must only ever expose public information."""
import json
import threading
import unittest
import urllib.request

from helpers import PUZZLE_DIR

from gridlogic.puzzle import Puzzle
from webapp.server import create_server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(PUZZLE_DIR, "127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, path, body=None, sid="test"):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data,
                                     headers={"X-Session-Id": sid, "Content-Type": "application/json"})
        with urllib.request.urlopen(req) as res:
            raw = res.read()
            return json.loads(raw) if res.headers.get_content_type() == "application/json" else raw

    def assert_no_hidden_data(self, state, puzzle):
        for cell in state["cells"]:
            if not cell["revealed"]:
                self.assertNotIn("status", cell)
                self.assertNotIn("clue", cell)
        text = json.dumps(state)
        for c in puzzle.board.cells:
            if not any(x["cell"] == c and x["revealed"] for x in state["cells"]):
                self.assertNotIn(puzzle.clues[c].text(puzzle.board), text)

    def test_index_served(self):
        html = self.call("/")
        self.assertIn(b"GridLogic", html)

    def test_public_state_and_verdicts(self):
        puzzle = Puzzle.load(PUZZLE_DIR / "tutorial" / "tutorial-3x3.json")
        state = self.call("/api/load", {"id": "tutorial-3x3"}, sid="s1")
        self.assertEqual(state["revealed"], 1)
        self.assert_no_hidden_data(state, puzzle)

        res = self.call("/api/verdict", {"cell": "A1", "verdict": "INNOCENT"}, sid="s1")
        self.assertEqual(res["result"]["outcome"], "NOT_PROVABLE")
        self.assert_no_hidden_data(res["state"], puzzle)

        res = self.call("/api/verdict", {"cell": "B1", "verdict": "CRIMINAL"}, sid="s1")
        self.assertEqual(res["result"]["outcome"], "ACCEPTED")
        self.assertEqual(res["state"]["revealed"], 2)
        self.assert_no_hidden_data(res["state"], puzzle)

        hint = self.call("/api/hint", {}, sid="s1")["hint"]
        self.assertEqual(hint["status"], "FORCED")

        run = self.call("/api/agent/solve", {}, sid="s1")
        self.assertEqual(run["run"]["status"], "SOLVED")
        self.assertTrue(run["state"]["solved"])

        state = self.call("/api/restart", {}, sid="s1")
        self.assertEqual(state["revealed"], 1)

    def test_sessions_are_independent(self):
        self.call("/api/load", {"id": "classic-3x3-a"}, sid="a")
        self.call("/api/load", {"id": "classic-4x4-a"}, sid="b")
        self.assertEqual(self.call("/api/state", sid="a")["puzzle"]["id"], "classic-3x3-a")
        self.assertEqual(self.call("/api/state", sid="b")["puzzle"]["id"], "classic-4x4-a")

    def test_upload_and_check(self):
        data = json.loads((PUZZLE_DIR / "3x3" / "classic-3x3-b.json").read_text(encoding="utf-8"))
        state = self.call("/api/load", {"puzzle": data, "filename": "x.json"}, sid="u")
        self.assertEqual(state["puzzle"]["source"], "x.json")
        check = self.call("/api/check", {}, sid="u")["check"]
        self.assertEqual(check["uniqueness"]["status"], "UNIQUE")
        self.assertTrue(check["no_guess_solvable"])
        self.assertNotIn("solutions", check["uniqueness"])


if __name__ == "__main__":
    unittest.main()

import unittest, ast
class T(unittest.TestCase):
    def _r(self):
        with open("bot.py", encoding="utf-8") as f: return f.read()
    def test_syntax(self): ast.parse(self._r())
    def test_env(self): self.assertIn("os.getenv", self._r())
    def test_route(self): self.assertIn("@app.route", self._r())
    def test_viber(self): self.assertTrue("viberbot" in self._r() or "Api(" in self._r())
    def test_send(self): self.assertIn("send_messages", self._r())
if __name__ == "__main__": unittest.main()

import unittest,ast
class T(unittest.TestCase):
 def _s(self):
  with open("bot.py",encoding="utf-8") as f:return f.read()
 def test_syntax(self):ast.parse(self._s())
 def test_env(self):self.assertIn("os.getenv",self._s())
 def test_webhook(self):self.assertIn("/webhook",self._s())
if __name__=="__main__":unittest.main()
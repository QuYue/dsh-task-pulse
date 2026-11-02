import io
import json
import sys
import unittest

import wordcount


class WordcountTest(unittest.TestCase):
    def test_counts_words(self):
        counts = wordcount.count_words("a b a c")
        self.assertEqual(counts["a"], 2)
        self.assertEqual(counts["b"], 1)

    def test_cli_total(self):
        buffer = io.StringIO()
        old = sys.stdout
        sys.stdout = buffer
        try:
            wordcount.main(["-"])
        finally:
            sys.stdout = old
        self.assertEqual(buffer.getvalue().strip(), "5")


if __name__ == "__main__":
    unittest.main()

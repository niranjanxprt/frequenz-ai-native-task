import unittest

import query


class TestQueryBuckets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = query.load_knowledge("project_knowledge.jsonld")

    def test_bucket_detection(self):
        cases = [
            ("What is the Frequenz SDK for?", "purpose"),
            ("How do I install the sdk?", "install"),
            ("Show me an example of how to use it.", "example"),
            ("What features does it have?", "features"),
            ("What license is it under?", "license"),
            ("Which python versions does it require?", "dependencies"),
        ]
        for q, expected in cases:
            with self.subTest(q=q):
                self.assertEqual(query.pick_bucket(q), expected)

    def test_answers_non_empty(self):
        # Verify answers for each bucket are present and non-default
        self.assertTrue(len(query.answer(self.data, "purpose")) > 0)

        inst = query.answer(self.data, "install")
        self.assertIn("Installation:", inst)
        self.assertTrue(len(inst.splitlines()) >= 2)

        ex = query.answer(self.data, "example")
        self.assertTrue(len(ex) > 20)
        self.assertIn("async def", ex)

        feats = query.answer(self.data, "features")
        self.assertIn("Key features:", feats)

        lic = query.answer(self.data, "license")
        self.assertIn("License:", lic)

        deps = query.answer(self.data, "dependencies")
        self.assertIn("Requirements:", deps)


if __name__ == "__main__":
    unittest.main()


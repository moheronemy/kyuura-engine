"""The timing wrapper must retain failures, fixture handling and test order."""

import io
import sys
import unittest
from types import ModuleType
from unittest.mock import patch

from tools.test_runner import TimedResult, iter_tests, timed_suite


class TimingRunnerTest(unittest.TestCase):
    def test_module_fixtures_and_explicit_test_order_match_unittest(self):
        events = []
        modules = {}
        classes = []
        for name in ("timing_fixture_a", "timing_fixture_b"):
            module = ModuleType(name)
            module.setUpModule = lambda name=name: events.append((name, "setup"))
            module.tearDownModule = lambda name=name: events.append((name, "teardown"))
            modules[name] = module
            classes.append(type("Example", (unittest.TestCase,), {
                "__module__": name,
                "test_example": lambda self, name=name: events.append((name, "test")),
            }))

        def suite():
            return unittest.TestSuite(cls("test_example") for cls in (classes[0], classes[1], classes[0]))

        with patch.dict(sys.modules, modules):
            standard = unittest.TextTestRunner(stream=io.StringIO()).run(suite())
            expected = events[:]
            events.clear()
            measured = unittest.TextTestRunner(stream=io.StringIO(), resultclass=TimedResult).run(timed_suite(suite()))
        self.assertTrue(standard.wasSuccessful() and measured.wasSuccessful())
        self.assertEqual(events, expected)
        self.assertEqual(len(measured.module_times), 3)

    def test_shared_fixtures_run_once_and_teardown_is_included(self):
        events = []

        class Example(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                events.append("setup")

            def test_a(self):
                events.append("a")

            def test_b(self):
                events.append("b")

            @classmethod
            def tearDownClass(cls):
                events.append("teardown")

        suite = unittest.TestLoader().loadTestsFromTestCase(Example)
        expected_ids = [test.id() for test in iter_tests(suite)]
        wrapped = timed_suite(suite)
        self.assertEqual([test.id() for test in iter_tests(wrapped)], expected_ids)
        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=TimedResult).run(wrapped)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(events, ["setup", "a", "b", "teardown"])
        self.assertEqual(len(result.test_times), 2)
        self.assertEqual(len(result.module_times), 1)
        self.assertGreaterEqual(result.module_times[0]["seconds"], sum(t["seconds"] for t in result.test_times))

    def test_fixture_error_is_a_failure_even_when_no_test_starts(self):
        class Broken(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                raise RuntimeError("fixture failed")

            def test_unreachable(self):
                self.fail("must not run")

        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=TimedResult).run(
            timed_suite(unittest.TestLoader().loadTestsFromTestCase(Broken)))
        self.assertFalse(result.wasSuccessful())
        self.assertEqual((result.testsRun, len(result.errors)), (0, 1))
        self.assertEqual(len(result.module_times), 1)

    def test_failure_skip_and_subtest_results_are_preserved(self):
        class Example(unittest.TestCase):
            def test_failure(self):
                with self.subTest(value=1):
                    self.fail("expected failure in the runner's own fixture")

            @unittest.skip("test fixture")
            def test_skip(self):
                pass

        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=TimedResult).run(
            timed_suite(unittest.TestLoader().loadTestsFromTestCase(Example)))
        self.assertFalse(result.wasSuccessful())
        self.assertEqual((result.testsRun, len(result.failures), len(result.skipped)), (2, 1, 1))
        self.assertEqual(len(result.test_times), 2)


if __name__ == "__main__":
    unittest.main()

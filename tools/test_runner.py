#!/usr/bin/env python3
"""Run unittest with module/fixture and individual-test timings (Python 3.11+)."""

import argparse
import json
import sys
import time
import unittest
from itertools import groupby
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TimedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_times = []
        self.module_times = []

    def startTest(self, test):
        super().startTest(test)
        self._started = time.perf_counter()

    def stopTest(self, test):
        self.test_times.append({"id": test.id(), "seconds": time.perf_counter() - self._started})
        super().stopTest(test)


class TimedModuleSuite(unittest.TestSuite):
    def __init__(self, name, tests):
        super().__init__(tests)
        self.name = name

    def run(self, result, debug=False):
        started = time.perf_counter()
        try:
            return super().run(result, debug=debug)
        finally:
            result.module_times.append({"module": self.name, "seconds": time.perf_counter() - started})


class ModuleSuite(unittest.TestSuite):
    def run(self, result, debug=False):
        # Each module runs as a top-level unittest suite so its timer includes
        # teardown. Clear unittest's previous-class pointer after that teardown;
        # otherwise the next suite would tear down that class a second time.
        for suite in self:
            if result.shouldStop:
                break
            try:
                suite.run(result, debug=debug)
            finally:
                result._previousTestClass = None
        return result


def iter_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_tests(item)
        else:
            yield item


def timed_suite(suite):
    """Preserve discovery order; include shared fixture time once per module."""
    modules = groupby(iter_tests(suite), key=lambda test: type(test).__module__)
    return ModuleSuite(TimedModuleSuite(name, list(tests)) for name, tests in modules)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="unittest module, class or method names; default: all tests")
    parser.add_argument("--report", type=Path, help="write timing and outcome JSON")
    parser.add_argument("--slowest", type=int, default=10, help="number of slow modules/tests to print")
    args = parser.parse_args(argv)
    loader = unittest.TestLoader()
    collected_at = time.perf_counter()
    if args.names:
        suite = loader.loadTestsFromNames(args.names)
    else:
        suite = loader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
    collection_seconds = time.perf_counter() - collected_at
    print(f"Collected {suite.countTestCases()} tests in {collection_seconds:.3f}s", file=sys.stderr)
    started = time.perf_counter()
    result = unittest.TextTestRunner(resultclass=TimedResult).run(timed_suite(suite))
    report = {
        "tests": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
        "successful": result.wasSuccessful(), "seconds": time.perf_counter() - started,
        "collection_seconds": collection_seconds,
        "modules": sorted(result.module_times, key=lambda x: x["seconds"], reverse=True),
        "test_times": sorted(result.test_times, key=lambda x: x["seconds"], reverse=True),
    }
    for key, label, name in (("modules", "Slow modules (including fixtures)", "module"),
                             ("test_times", "Slow tests (excluding shared fixtures)", "id")):
        print(label, file=sys.stderr)
        for entry in report[key][:max(0, args.slowest)]:
            print(f"{entry['seconds']:9.3f}s {entry[name]}", file=sys.stderr)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

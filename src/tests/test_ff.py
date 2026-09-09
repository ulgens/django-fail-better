import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from django_fail_better.runner import FailBetterRunner


class SampleTests(unittest.TestCase):
    __test__ = False

    def test_a(self):
        pass

    def test_b(self):
        pass

    def test_c(self):
        pass


def sample_tests():
    cls = SampleTests
    return [cls("test_a"), cls("test_b"), cls("test_c")]


class FailedFirstTests(SimpleTestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base_dir = Path(self._tmp.name)

    def make_runner(self, **kwargs):
        runner = FailBetterRunner(**kwargs)
        runner.cache_dir = self.base_dir / ".cache" / "fail_better"
        runner.last_failed_file = runner.cache_dir / "last_failed.json"
        return runner

    def write_cache(self, test_ids):
        cache_dir = self.base_dir / ".cache" / "fail_better"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "last_failed.json").write_text(json.dumps(list(test_ids)))

    def build_suite(self, runner):
        tests = sample_tests()
        with patch(
            "django.test.runner.DiscoverRunner.build_suite",
            return_value=unittest.TestSuite(tests),
        ):
            return runner.build_suite(test_labels=[])

    def test_ff_puts_failed_tests_first(self):
        self.write_cache(["tests.test_ff.SampleTests.test_a"])
        runner = self.make_runner(failed_first=True)

        suite = self.build_suite(runner)

        self.assertEqual(
            [t.id() for t in suite],
            [
                "tests.test_ff.SampleTests.test_a",
                "tests.test_ff.SampleTests.test_b",
                "tests.test_ff.SampleTests.test_c",
            ],
        )

    def test_ff_runs_all_tests(self):
        self.write_cache(["tests.test_ff.SampleTests.test_a"])
        runner = self.make_runner(failed_first=True)

        suite = self.build_suite(runner)

        self.assertEqual(len(list(suite)), 3)

    def test_ff_without_cache_runs_all_in_original_order(self):
        runner = self.make_runner(failed_first=True)

        suite = self.build_suite(runner)

        self.assertEqual(
            [t.id() for t in suite],
            [
                "tests.test_ff.SampleTests.test_a",
                "tests.test_ff.SampleTests.test_b",
                "tests.test_ff.SampleTests.test_c",
            ],
        )

    def test_ff_disabled_keeps_original_order(self):
        self.write_cache(["tests.test_ff.SampleTests.test_a"])
        runner = self.make_runner(failed_first=False)
        runner.failed_first = False

        suite = self.build_suite(runner)

        self.assertEqual(
            [t.id() for t in suite],
            [
                "tests.test_ff.SampleTests.test_a",
                "tests.test_ff.SampleTests.test_b",
                "tests.test_ff.SampleTests.test_c",
            ],
        )

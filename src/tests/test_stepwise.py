import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast
from unittest.mock import patch
from unittest.runner import TextTestRunner

from django.test import SimpleTestCase

from django_fail_better.result_classes import StepwiseResultMixin
from django_fail_better.runner import FailBetterRunner


class StepTests(unittest.TestCase):
    __test__ = False

    def test_a(self):
        pass

    def test_b(self):
        pass

    def test_c(self):
        pass


def step_fixtures():
    return [
        StepTests("test_a"),
        StepTests("test_b"),
        StepTests("test_c"),
    ]


class StepwiseTests(SimpleTestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base_dir = Path(self._tmp.name)

    def make_runner(self, **kwargs):
        runner = FailBetterRunner(**kwargs)
        runner.cache_dir = self.base_dir / ".cache" / "fail_better"
        runner.last_failed_file = runner.cache_dir / "last_failed.json"
        runner.stepwise_file = runner.cache_dir / "stepwise.json"
        return runner

    def write_stepwise(self, test_id):
        cache_dir = self.base_dir / ".cache" / "fail_better"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "stepwise.json").write_text(json.dumps(test_id))

    def assert_suite_ids(self, suite, expected):
        self.assertEqual([t.id() for t in suite], expected)

    def build_suite(self, runner, tests=None):
        suite_in = unittest.TestSuite(tests or step_fixtures())
        with patch(
            "django.test.runner.DiscoverRunner.build_suite",
            return_value=suite_in,
        ):
            return runner.build_suite(test_labels=[])

    def test_stepwise_without_resume_runs_all(self):
        runner = self.make_runner(stepwise=True)

        self.assert_suite_ids(
            self.build_suite(runner),
            [t.id() for t in step_fixtures()],
        )

    def test_stepwise_resumes_from_last_failure(self):
        resume = StepTests("test_b").id()
        self.write_stepwise(resume)
        runner = self.make_runner(stepwise=True)

        self.assert_suite_ids(
            self.build_suite(runner),
            ["tests.test_stepwise.StepTests.test_b", "tests.test_stepwise.StepTests.test_c"],
        )

    def test_stepwise_resume_not_found_runs_all(self):
        self.write_stepwise("nonexistent.Test.test_x")
        runner = self.make_runner(stepwise=True)

        self.assert_suite_ids(
            self.build_suite(runner),
            [t.id() for t in step_fixtures()],
        )

    def test_stepwise_result_stops_on_first_failure(self):
        runner = self.make_runner(stepwise=True)
        result = cast(StepwiseResultMixin, self.run_resultclass(runner, [StepTests("test_a"), StepTests("test_b")]))

        self.assertEqual(result.testsRun, 1)
        self.assertTrue(result.shouldStop)
        self.assertEqual(result.resume, StepTests("test_a").id())

    def test_stepwise_skip_ignores_resume_failure(self):
        resume = StepTests("test_a").id()
        self.write_stepwise(resume)
        runner = self.make_runner(stepwise=True, stepwise_skip=True)

        with patch("tests.test_stepwise.StepTests.test_b", side_effect=AssertionError):
            result = cast(StepwiseResultMixin, self.run_resultclass(runner, [StepTests("test_a"), StepTests("test_b")]))

        self.assertEqual(result.testsRun, 2)
        self.assertTrue(result.shouldStop)
        self.assertEqual(result.resume, StepTests("test_b").id())

    def run_resultclass(self, runner, tests):
        resultclass = runner.get_resultclass()
        with patch("tests.test_stepwise.StepTests.test_a", side_effect=AssertionError):
            return TextTestRunner(
                stream=io.StringIO(),
                resultclass=resultclass,
                verbosity=0,
            ).run(unittest.TestSuite(tests))

    def test_stepwise_skip_enables_stepwise(self):
        runner = self.make_runner(stepwise_skip=True)

        self.assertTrue(runner.stepwise)

    def test_stepwise_reset_enables_stepwise(self):
        runner = self.make_runner(stepwise_reset=True)

        self.assertTrue(runner.stepwise)

    def run_tests(self, runner):
        with patch("django.test.runner.DiscoverRunner.run_tests", return_value=0):
            return runner.run_tests([])

    def test_run_tests_stepwise_reset_clears_state(self):
        self.write_stepwise(StepTests("test_b").id())
        runner = self.make_runner(stepwise_reset=True)

        self.run_tests(runner)

        self.assertEqual(json.loads(runner.stepwise_file.read_text()), None)

    def test_run_tests_cache_clear_clears_stepwise_state(self):
        self.write_stepwise(StepTests("test_b").id())
        runner = self.make_runner(failure_cache_clear=True)

        self.run_tests(runner)

        self.assertEqual(json.loads(runner.stepwise_file.read_text()), None)

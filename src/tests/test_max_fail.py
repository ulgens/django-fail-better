import io
import unittest
from unittest.runner import TextTestRunner

from django.test import SimpleTestCase

from django_fail_better.result_classes import MaxFailResult
from django_fail_better.runner import FailBetterRunner


class FailingSuite(unittest.TestCase):
    __test__ = False

    def test_fail_1(self):
        msg = "failure"
        raise AssertionError(msg)

    def test_fail_2(self):
        msg = "failure"
        raise AssertionError(msg)

    def test_pass(self):
        assert True


def run_with_max_fail(max_fail):
    runner = FailBetterRunner(max_fail=max_fail)
    resultclass = runner.get_resultclass()
    suite = unittest.TestLoader().loadTestsFromTestCase(FailingSuite)

    return TextTestRunner(
        stream=io.StringIO(),
        resultclass=resultclass,
        verbosity=0,
    ).run(suite)


class MaxFailResultTests(SimpleTestCase):
    def test_stops_after_max_fail_failures(self):
        result = run_with_max_fail(max_fail=1)

        self.assertEqual(result.testsRun, 1)
        self.assertTrue(result.shouldStop)

    def test_zero_max_fail_runs_full_suite(self):
        result = run_with_max_fail(max_fail=0)

        self.assertEqual(result.testsRun, 3)
        self.assertFalse(result.shouldStop)

    def test_resultclass_is_callable_factory(self):
        resultclass = FailBetterRunner(max_fail=1).get_resultclass()

        self.assertTrue(callable(resultclass))

    def test_resultclass_produces_max_fail_result(self):
        resultclass = FailBetterRunner(max_fail=1).get_resultclass()

        result = resultclass(io.StringIO(), 1, 2)

        self.assertIsInstance(result, MaxFailResult)
        self.assertIsInstance(result, unittest.TextTestResult)

    def test_mixin_tracks_failure_count(self):
        result = run_with_max_fail(max_fail=2)

        self.assertEqual(result.failure_count, 2)

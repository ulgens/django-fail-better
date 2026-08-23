import unittest

from django_fail_better.result_classes import MaxFailResult


class FakeTest:
    failureException = AssertionError

    def id(self):
        return "test_fake"

    def __call__(self, result=None):
        return self


class MaxFailResultTests(unittest.TestCase):
    def test_no_maxfail_by_default(self):
        result = MaxFailResult(None, True, 0)
        self.assertEqual(result.maxfail, 0)
        self.assertEqual(result.failure_count, 0)

    def test_custom_maxfail(self):
        result = MaxFailResult(None, True, 0, maxfail=3)
        self.assertEqual(result.maxfail, 3)

    def test_failure_count_increments_on_failure(self):
        result = MaxFailResult(None, True, 0, maxfail=5)
        test = FakeTest()
        result.addFailure(test, (None, None, None))
        self.assertEqual(result.failure_count, 1)

    def test_failure_count_increments_on_error(self):
        result = MaxFailResult(None, True, 0, maxfail=5)
        test = FakeTest()
        result.addError(test, (None, None, None))
        self.assertEqual(result.failure_count, 1)

    def test_failure_count_increments_on_unexpected_success(self):
        result = MaxFailResult(None, True, 0, maxfail=5)
        test = FakeTest()
        result.addUnexpectedSuccess(test)
        self.assertEqual(result.failure_count, 1)

    def test_stops_after_maxfail_failures(self):
        result = MaxFailResult(None, True, 0, maxfail=2)
        test = FakeTest()
        self.assertFalse(result.shouldStop)
        result.addFailure(test, (None, None, None))
        self.assertFalse(result.shouldStop)
        result.addFailure(test, (None, None, None))
        self.assertTrue(result.shouldStop)

    def test_does_not_stop_when_maxfail_is_zero(self):
        result = MaxFailResult(None, True, 0, maxfail=0)
        test = FakeTest()
        for _ in range(100):
            result.addFailure(test, (None, None, None))
        self.assertFalse(result.shouldStop)

    def test_should_stop_resets_between_runs(self):
        result = MaxFailResult(None, True, 0, maxfail=1)
        test = FakeTest()
        result.addFailure(test, (None, None, None))
        self.assertTrue(result.shouldStop)
        result2 = MaxFailResult(None, True, 0, maxfail=1)
        self.assertFalse(result2.shouldStop)

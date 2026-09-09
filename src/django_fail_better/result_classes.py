import unittest
from typing import override


class MaxFailResult(unittest.TextTestResult):
    def __init__(self, *args, max_fail=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.max_fail = max_fail
        self.failure_count = 0

    def incr_failure_count(self):
        if not self.max_fail:
            return

        self.failure_count += 1

        if self.failure_count >= self.max_fail:
            self.shouldStop = True

    @override
    def addFailure(self, test, err):
        super().addFailure(test, err)

        self.incr_failure_count()

    @override
    def addError(self, test, err):
        super().addError(test, err)

        self.incr_failure_count()

    @override
    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)

        self.incr_failure_count()


class StepwiseResultMixin(unittest.TextTestResult):
    resume = None
    keep_on_fail = False

    def _stepwise_failure(self, test):
        if self.keep_on_fail and test.id() == self.resume:
            self.resume = None
            return

        self.resume = test.id()
        self.shouldStop = True

    @override
    def addFailure(self, test, err):
        super().addFailure(test, err)

        self._stepwise_failure(test)

    @override
    def addError(self, test, err):
        super().addError(test, err)

        self._stepwise_failure(test)

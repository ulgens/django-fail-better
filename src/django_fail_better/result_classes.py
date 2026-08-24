import unittest
from typing import override


class MaxFailResult(unittest.TextTestResult):
    def __init__(self, *args, max_fail=False, **kwargs):
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

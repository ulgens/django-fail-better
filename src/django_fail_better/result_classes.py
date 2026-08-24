import unittest
from typing import override


class MaxFailResult(unittest.TextTestResult):
    def __init__(self, *args, maxfail=0, **kwargs):
        super().__init__(*args, **kwargs)

        self.maxfail = maxfail
        self.failure_count = 0

    def check_max_fail(self):
        self.failure_count += 1

        if self.maxfail and self.failure_count >= self.maxfail:
            self.shouldStop = True

    @override
    def addFailure(self, test, err):
        super().addFailure(test, err)

        self.check_max_fail()

    @override
    def addError(self, test, err):
        super().addError(test, err)

        self.check_max_fail()

    @override
    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)

        self.check_max_fail()

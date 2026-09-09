import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase

from django_fail_better.runner import FailBetterRunner


class LastFailedNoFailuresTests(SimpleTestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base_dir = Path(self._tmp.name)

    def make_runner(self, **kwargs):
        runner = FailBetterRunner(last_failed=True, **kwargs)
        runner.cache_dir = self.base_dir / ".cache" / "fail_better"
        runner.last_failed_file = runner.cache_dir / "last_failed.json"
        return runner

    def write_cache(self, test_ids):
        cache_dir = self.base_dir / ".cache" / "fail_better"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "last_failed.json").write_text(json.dumps(list(test_ids)))

    def run_tests(self, runner):
        with patch("django.test.runner.DiscoverRunner.run_tests", return_value=0) as mocked:
            result = runner.run_tests([])
        return result, mocked.called

    def test_none_skips_when_no_cache(self):
        runner = self.make_runner(last_failed_no_failures="none")

        result, suite_ran = self.run_tests(runner)

        self.assertEqual(result, 0)
        self.assertFalse(suite_ran)

    def test_none_skips_when_cache_is_empty(self):
        self.write_cache([])
        runner = self.make_runner(last_failed_no_failures="none")

        result, suite_ran = self.run_tests(runner)

        self.assertEqual(result, 0)
        self.assertFalse(suite_ran)

    def test_none_runs_when_cache_has_failures(self):
        self.write_cache({"some.Test.test_x"})
        runner = self.make_runner(last_failed_no_failures="none")

        result, suite_ran = self.run_tests(runner)

        self.assertEqual(result, 0)
        self.assertTrue(suite_ran)

    def test_all_runs_when_no_cache(self):
        runner = self.make_runner(last_failed_no_failures="all")

        result, suite_ran = self.run_tests(runner)

        self.assertEqual(result, 0)
        self.assertTrue(suite_ran)

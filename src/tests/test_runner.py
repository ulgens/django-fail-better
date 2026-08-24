import tempfile
import unittest
from argparse import ArgumentParser
from pathlib import Path
from unittest.mock import Mock, patch

import django
from django.conf import settings

settings.configure(
    BASE_DIR=tempfile.mkdtemp(),
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
    INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"],
    DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
)
django.setup()

from django.test.runner import DiscoverRunner, ParallelTestSuite  # noqa: E402

from django_fail_better.runner import FailBetterRunner  # noqa: E402


class FakeTest:
    failureException = AssertionError

    def __init__(self, test_id=None):
        self._id = test_id or "test_fake"

    def id(self):
        return self._id

    def __call__(self, result=None):
        return self


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_dir = self.temp_dir / ".cache" / "fail_better"
        self.lastfailed_file = self.cache_dir / "lastfailed"
        self.stepwise_file = self.cache_dir / "stepwise"
        self.test_node_file = self.cache_dir / "nodeids"

    def _runner(self, **kwargs):
        r = FailBetterRunner(**kwargs)
        r.cache_dir = self.cache_dir
        r.last_failed_file = self.lastfailed_file
        r.stepwise_file = self.stepwise_file
        r.test_node_file = self.test_node_file
        return r

    def test_load_lastfailed_returns_none_when_no_cache(self):
        runner = self._runner()
        self.assertIsNone(runner.load_last_failed())

    def test_save_and_load_lastfailed(self):
        runner = self._runner()
        test_ids = {"test_a", "test_b"}
        runner.save_last_failed(test_ids)
        loaded = runner.load_last_failed()
        self.assertEqual(loaded, test_ids)

    def test_load_lastfailed_handles_corrupted_file(self):
        runner = self._runner()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.lastfailed_file.write_text("not valid json")
        self.assertIsNone(runner.load_last_failed())

    def test_update_cache_saves_failed_tests(self):
        runner = self._runner()
        mock_result = Mock()
        mock_result.failures = [(FakeTest("test_a"), "traceback")]
        mock_result.errors = [(FakeTest("test_b"), "traceback")]
        mock_result.unexpectedSuccesses = []
        runner.update_cache(mock_result)
        loaded = runner.load_last_failed()
        self.assertEqual(loaded, {"test_a", "test_b"})

    def test_update_cache_excludes_unexpected_successes(self):
        runner = self._runner()
        mock_result = Mock()
        mock_result.failures = []
        mock_result.errors = []
        mock_result.unexpectedSuccesses = [FakeTest("test_c")]
        runner.update_cache(mock_result)
        loaded = runner.load_last_failed()
        self.assertEqual(loaded, set())

    def test_clear_cache_removes_existing_cache(self):
        runner = self._runner()
        runner.save_last_failed({"test_a"})
        self.assertTrue(self.lastfailed_file.exists())
        runner.clear_cache()
        self.assertIsNone(runner.load_last_failed())

    def test_clear_cache_noop_when_no_cache(self):
        runner = self._runner()
        runner.clear_cache()
        self.assertIsNone(runner.load_last_failed())

    def test_clear_cache_removes_cache_file(self):
        runner = self._runner()
        runner.save_last_failed({"test_a"})
        self.assertTrue(self.lastfailed_file.exists())
        runner.clear_cache()
        self.assertFalse(self.lastfailed_file.exists())

    def test_cross_instance_cache_persistence(self):
        runner1 = self._runner()
        runner1.save_last_failed({"test_a", "test_b"})
        runner2 = self._runner()
        loaded = runner2.load_last_failed()
        self.assertEqual(loaded, {"test_a", "test_b"})

    def test_save_and_load_stepwise(self):
        runner = self._runner()
        runner.save_stepwise("test_a")
        self.assertEqual(runner.load_stepwise(), "test_a")

    def test_load_stepwise_returns_none_when_no_cache(self):
        runner = self._runner()
        self.assertIsNone(runner.load_stepwise())

    def test_clear_stepwise(self):
        runner = self._runner()
        runner.save_stepwise("test_a")
        runner.clear_stepwise()
        self.assertIsNone(runner.load_stepwise())

    def test_update_stepwise_clears_on_success(self):
        runner = self._runner()
        runner.save_stepwise("test_a")
        mock_result = Mock()
        mock_result.wasSuccessful.return_value = True
        runner.update_stepwise(mock_result)
        self.assertIsNone(runner.load_stepwise())

    def test_update_stepwise_saves_first_failure(self):
        runner = self._runner()
        mock_result = Mock()
        mock_result.wasSuccessful.return_value = False
        mock_result.failures = [(FakeTest("test_x"), "traceback")]
        mock_result.errors = [(FakeTest("test_y"), "traceback")]
        runner.update_stepwise(mock_result)
        self.assertEqual(runner.load_stepwise(), "test_x")

    def test_update_stepwise_uses_errors_when_no_failures(self):
        runner = self._runner()
        mock_result = Mock()
        mock_result.wasSuccessful.return_value = False
        mock_result.failures = []
        mock_result.errors = [(FakeTest("test_z"), "traceback")]
        runner.update_stepwise(mock_result)
        self.assertEqual(runner.load_stepwise(), "test_z")

    def test_load_test_nodes_returns_none_when_no_cache(self):
        runner = self._runner()
        self.assertIsNone(runner.load_test_nodes())

    def test_save_and_load_test_nodes(self):
        runner = self._runner()
        test_ids = ["test_a", "test_b", "test_c"]
        runner.save_test_nodes(test_ids)
        loaded = runner.load_test_nodes()
        self.assertEqual(loaded, test_ids)

    def test_load_test_nodes_handles_corrupted_file(self):
        runner = self._runner()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.test_node_file.write_text("not valid json")
        self.assertIsNone(runner.load_test_nodes())

    def test_clear_test_nodes(self):
        runner = self._runner()
        runner.save_test_nodes(["test_a"])
        self.assertTrue(self.test_node_file.exists())
        runner.clear_test_nodes()
        self.assertIsNone(runner.load_test_nodes())

    def test_clear_test_nodes_noop_when_no_cache(self):
        runner = self._runner()
        runner.clear_test_nodes()
        self.assertIsNone(runner.load_test_nodes())

    def test_update_test_nodes_from_suite(self):
        runner = self._runner()
        test_ids = ["test_a", "test_b"]
        runner.update_test_nodes(test_ids)
        self.assertEqual(runner.load_test_nodes(), test_ids)

    def test_run_tests_full_flow(self):
        from django.test import SimpleTestCase

        runner = self._runner()

        class PassingTest(SimpleTestCase):
            def test_pass(self):
                pass

        suite = unittest.TestSuite()
        suite.addTest(PassingTest("test_pass"))

        with (
            patch.object(runner, "setup_test_environment"),
            patch.object(runner, "setup_databases", return_value=()),
            patch.object(runner, "run_checks"),
            patch.object(runner, "teardown_databases"),
            patch.object(runner, "teardown_test_environment"),
            patch.object(runner, "build_suite", return_value=suite),
            patch.object(runner, "log"),
        ):
            result = runner.run_tests(test_labels=[])

        self.assertEqual(result, 0)
        self.assertTrue(self.lastfailed_file.exists())
        self.assertEqual(runner.load_last_failed(), set())

    def test_run_tests_full_flow_with_failures(self):
        from django.test import SimpleTestCase

        runner = self._runner()

        class FailingTest(SimpleTestCase):
            def test_fail(self):
                self.fail("boom")

        suite = unittest.TestSuite()
        suite.addTest(FailingTest("test_fail"))

        with (
            patch.object(runner, "setup_test_environment"),
            patch.object(runner, "setup_databases", return_value=()),
            patch.object(runner, "run_checks"),
            patch.object(runner, "teardown_databases"),
            patch.object(runner, "teardown_test_environment"),
            patch.object(runner, "build_suite", return_value=suite),
            patch.object(runner, "log"),
        ):
            result = runner.run_tests(test_labels=[])

        self.assertEqual(result, 1)
        self.assertTrue(self.lastfailed_file.exists())
        cached = runner.load_last_failed()
        self.assertEqual(len(cached), 1)
        self.assertTrue(next(iter(cached)).endswith("FailingTest.test_fail"))


class BuildSuiteFilteringTests(unittest.TestCase):
    def _patch_build_suite(self, runner, tests):
        return patch.object(DiscoverRunner, "build_suite", return_value=tests)

    def test_last_failed_filters_to_failed_tests(self):
        runner = FailBetterRunner(last_failed=True)
        runner.parallel = 0
        tests = [FakeTest("a"), FakeTest("b"), FakeTest("c")]
        with (
            patch.object(runner, "load_last_failed", return_value={"b"}),
            patch.object(runner, "log"),
            self._patch_build_suite(runner, tests),
        ):
            result = runner.build_suite()
        self.assertEqual([t.id() for t in result], ["b"])

    def test_last_failed_with_empty_cache_and_lfnf_none(self):
        runner = FailBetterRunner(last_failed=True, lfnf="none")
        runner.parallel = 0
        tests = [FakeTest("a")]
        with (
            patch.object(runner, "load_last_failed", return_value=set()),
            patch.object(runner, "log"),
            self._patch_build_suite(runner, tests),
        ):
            result = runner.build_suite()
        self.assertEqual(result.countTestCases(), 0)

    def test_last_failed_with_empty_cache_and_lfnf_all(self):
        runner = FailBetterRunner(last_failed=True, lfnf="all")
        runner.parallel = 0
        tests = [FakeTest("a"), FakeTest("b")]
        with (
            patch.object(runner, "load_last_failed", return_value=set()),
            patch.object(runner, "log"),
            self._patch_build_suite(runner, tests),
        ):
            result = runner.build_suite()
        self.assertEqual([t.id() for t in result], ["a", "b"])

    def test_last_failed_runs_all_when_no_cache(self):
        runner = FailBetterRunner(last_failed=True)
        runner.parallel = 0
        tests = [FakeTest("a")]
        with (
            patch.object(runner, "load_last_failed", return_value=None),
            patch.object(runner, "log"),
            self._patch_build_suite(runner, tests),
        ):
            result = runner.build_suite()
        self.assertEqual([t.id() for t in result], ["a"])

    def test_failed_first_orders_failed_tests_first(self):
        runner = FailBetterRunner(failed_first=True)
        runner.parallel = 0
        tests = [FakeTest("a"), FakeTest("b"), FakeTest("c")]
        with (
            patch.object(runner, "load_last_failed", return_value={"b"}),
            patch.object(runner, "log"),
            self._patch_build_suite(runner, tests),
        ):
            result = runner.build_suite()
        self.assertEqual([t.id() for t in result], ["b", "a", "c"])

    def test_last_failed_and_failed_first_together(self):
        runner = FailBetterRunner(last_failed=True, failed_first=True)
        runner.parallel = 0
        tests = [FakeTest("a"), FakeTest("b"), FakeTest("c")]
        with (
            patch.object(runner, "load_last_failed", return_value={"b"}),
            patch.object(runner, "log"),
            self._patch_build_suite(runner, tests),
        ):
            result = runner.build_suite()
        self.assertEqual([t.id() for t in result], ["b"])

    def test_no_filtering_when_no_flags(self):
        runner = FailBetterRunner()
        runner.parallel = 0
        tests = [FakeTest("a"), FakeTest("b")]
        with (
            patch.object(runner, "log"),
            self._patch_build_suite(runner, tests),
        ):
            result = runner.build_suite()
        self.assertEqual([t.id() for t in result], ["a", "b"])

    def test_stepwise_resumes_from_cached_test(self):
        runner = FailBetterRunner(stepwise=True)
        runner.parallel = 0
        tests = [FakeTest("a"), FakeTest("b"), FakeTest("c")]
        with (
            patch.object(runner, "log"),
            patch.object(runner, "load_stepwise", return_value="b"),
            self._patch_build_suite(runner, tests),
        ):
            result = runner.build_suite()
        self.assertEqual([t.id() for t in result], ["b", "c"])

    def test_stepwise_runs_all_when_no_cache(self):
        runner = FailBetterRunner(stepwise=True)
        runner.parallel = 0
        tests = [FakeTest("a"), FakeTest("b")]
        with (
            patch.object(runner, "log"),
            patch.object(runner, "load_stepwise", return_value=None),
            self._patch_build_suite(runner, tests),
        ):
            result = runner.build_suite()
        self.assertEqual([t.id() for t in result], ["a", "b"])

    def test_stepwise_skip_ignores_cache(self):
        runner = FailBetterRunner(stepwise=True, stepwise_skip=True)
        runner.parallel = 0
        tests = [FakeTest("a"), FakeTest("b"), FakeTest("c")]
        with (
            patch.object(runner, "log"),
            patch.object(runner, "load_stepwise", return_value="b"),
            self._patch_build_suite(runner, tests),
        ):
            result = runner.build_suite()
        self.assertEqual([t.id() for t in result], ["a", "b", "c"])

    def test_stepwise_not_active_by_default(self):
        runner = FailBetterRunner()
        runner.parallel = 0
        tests = [FakeTest("a"), FakeTest("b"), FakeTest("c")]
        with (
            patch.object(runner, "log"),
            self._patch_build_suite(runner, tests),
        ):
            result = runner.build_suite()
        self.assertEqual([t.id() for t in result], ["a", "b", "c"])


class CacheShowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_dir = self.temp_dir / ".cache" / "fail_better"
        self.lastfailed_file = self.cache_dir / "lastfailed"

    def _runner(self, **kwargs):
        r = FailBetterRunner(**kwargs)
        r.cache_dir = self.cache_dir
        r.last_failed_file = self.lastfailed_file
        return r

    def test_cache_show_no_cache(self):
        runner = self._runner(cache_show=True)
        with patch.object(runner, "log") as mock_log:
            runner.show_cache()
            mock_log.assert_called_once_with("No cache found")

    def test_cache_show_with_failures(self):
        runner = self._runner(cache_show=True)
        runner.save_last_failed({"test_a", "test_b"})
        with patch.object(runner, "log") as mock_log:
            runner.show_cache()
            mock_log.assert_any_call("Previously failed tests (2):")
            mock_log.assert_any_call("  test_a")
            mock_log.assert_any_call("  test_b")

    def test_cache_show_returns_zero(self):
        runner = self._runner(cache_show=True)
        runner.save_last_failed({"test_a"})
        result = runner.run_tests(test_labels=[])
        self.assertEqual(result, 0)


class GetResultClassTests(unittest.TestCase):
    def test_returns_same_class_every_call(self):
        runner = FailBetterRunner()
        cls1 = runner.get_resultclass()
        cls2 = runner.get_resultclass()
        self.assertIs(cls1, cls2)


class AddArgumentsTests(unittest.TestCase):
    def test_last_failed_defaults_to_false(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args([])
        self.assertFalse(options.last_failed)

    def test_failed_first_defaults_to_false(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args([])
        self.assertFalse(options.failed_first)

    def test_lfnf_defaults_to_all(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args([])
        self.assertEqual(options.last_failed_no_failures, "all")

    def test_max_fail_defaults_to_zero(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args([])
        self.assertEqual(options.maxfail, 0)

    def test_cache_show_defaults_to_false(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args([])
        self.assertFalse(options.cache_show)

    def test_cache_clear_defaults_to_false(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args([])
        self.assertFalse(options.cache_clear)

    def test_short_flags_parse(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args(["--lf", "--ff", "--maxfail=3", "--cache-show", "--cache-clear"])
        self.assertTrue(options.last_failed)
        self.assertTrue(options.failed_first)
        self.assertEqual(options.maxfail, 3)
        self.assertTrue(options.cache_show)
        self.assertTrue(options.cache_clear)

    def test_lfnf_accepts_all_and_none(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args(["--lfnf", "none"])
        self.assertEqual(options.last_failed_no_failures, "none")
        options = parser.parse_args(["--lfnf", "all"])
        self.assertEqual(options.last_failed_no_failures, "all")

    def test_lfnf_accepts_long_form(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args(["--last-failed-no-failures", "none"])
        self.assertEqual(options.last_failed_no_failures, "none")

    def test_long_flags_parse(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args(["--last-failed", "--failed-first", "--maxfail=5", "--cache-show", "--cache-clear"])
        self.assertTrue(options.last_failed)
        self.assertTrue(options.failed_first)
        self.assertEqual(options.maxfail, 5)
        self.assertTrue(options.cache_show)
        self.assertTrue(options.cache_clear)

    def test_stepwise_defaults_to_false(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args([])
        self.assertFalse(options.stepwise)

    def test_stepwise_skip_defaults_to_false(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args([])
        self.assertFalse(options.stepwise_skip)

    def test_stepwise_short_flag_parses(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args(["--sw"])
        self.assertTrue(options.stepwise)

    def test_stepwise_long_flag_parses(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args(["--stepwise"])
        self.assertTrue(options.stepwise)

    def test_stepwise_skip_short_flag_parses(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args(["--skip-sw"])
        self.assertTrue(options.stepwise_skip)

    def test_stepwise_skip_long_flag_parses(self):
        parser = ArgumentParser()
        FailBetterRunner.add_arguments(parser)
        options = parser.parse_args(["--stepwise-skip"])
        self.assertTrue(options.stepwise_skip)


class BuildSuiteParallelTests(unittest.TestCase):
    def test_parallel_build_creates_parallel_suite(self):
        runner = FailBetterRunner()
        runner.parallel = 2

        class CaseA(unittest.TestCase):
            def test_a(self):
                pass

        class CaseB(unittest.TestCase):
            def test_b(self):
                pass

        tests = [CaseA("test_a"), CaseB("test_b")]
        with (
            patch.object(DiscoverRunner, "build_suite", return_value=tests),
            patch.object(runner, "log"),
        ):
            result = runner.build_suite()
        self.assertIsInstance(result, ParallelTestSuite)

    def test_no_parallel_when_single_case(self):
        runner = FailBetterRunner()
        runner.parallel = 2

        class SingleCase(unittest.TestCase):
            def test_a(self):
                pass

            def test_b(self):
                pass

        tests = [SingleCase("test_a"), SingleCase("test_b")]
        with (
            patch.object(DiscoverRunner, "build_suite", return_value=tests),
            patch.object(runner, "log"),
        ):
            result = runner.build_suite()
        self.assertNotIsInstance(result, ParallelTestSuite)

    def test_parallel_build_with_last_failed(self):
        runner = FailBetterRunner(last_failed=True)
        runner.parallel = 2

        class CaseA(unittest.TestCase):
            def test_a(self):
                pass

        class CaseB(unittest.TestCase):
            def test_b(self):
                pass

        all_tests = [CaseA("test_a"), CaseB("test_b")]
        with (
            patch.object(DiscoverRunner, "build_suite", return_value=all_tests),
            patch.object(runner, "load_last_failed", return_value={t.id() for t in all_tests}),
            patch.object(runner, "log"),
        ):
            result = runner.build_suite()
        self.assertIsInstance(result, ParallelTestSuite)
        self.assertEqual(runner.parallel, 2)


class MaxFailRuntimeTests(unittest.TestCase):
    def test_stops_after_maxfail(self):
        from django.test import SimpleTestCase

        runner = FailBetterRunner(maxfail=2, verbosity=0)

        class FailingTest(SimpleTestCase):
            def test_01(self):
                self.fail("1")

            def test_02(self):
                self.fail("2")

            def test_03(self):
                self.fail("3")

        suite = unittest.TestSuite()
        suite.addTest(FailingTest("test_01"))
        suite.addTest(FailingTest("test_02"))
        suite.addTest(FailingTest("test_03"))

        with patch.object(runner, "log"):
            result = runner.run_suite(suite)

        self.assertEqual(result.failure_count, 2)
        self.assertTrue(result.shouldStop)

    def test_continues_when_maxfail_is_zero(self):
        from django.test import SimpleTestCase

        runner = FailBetterRunner(maxfail=0, verbosity=0)

        class FailingTest(SimpleTestCase):
            def test_01(self):
                self.fail("1")

            def test_02(self):
                self.fail("2")

            def test_03(self):
                self.fail("3")

        suite = unittest.TestSuite()
        suite.addTest(FailingTest("test_01"))
        suite.addTest(FailingTest("test_02"))
        suite.addTest(FailingTest("test_03"))

        with patch.object(runner, "log"):
            result = runner.run_suite(suite)

        self.assertEqual(result.failure_count, 3)
        self.assertFalse(result.shouldStop)

    def test_maxfail_greater_than_failures(self):
        from django.test import SimpleTestCase

        runner = FailBetterRunner(maxfail=5, verbosity=0)

        class FailingTest(SimpleTestCase):
            def test_01(self):
                self.fail("1")

        suite = unittest.TestSuite()
        suite.addTest(FailingTest("test_01"))

        with patch.object(runner, "log"):
            result = runner.run_suite(suite)

        self.assertEqual(result.failure_count, 1)
        self.assertFalse(result.shouldStop)


class RunSuiteTests(unittest.TestCase):
    def test_uses_maxfail_result_class(self):
        from django.test import SimpleTestCase

        runner = FailBetterRunner(maxfail=3, verbosity=0)

        class PassingTest(SimpleTestCase):
            def test_pass(self):
                pass

        suite = unittest.TestSuite()
        suite.addTest(PassingTest("test_pass"))

        with patch.object(runner, "log"):
            result = runner.run_suite(suite)

        from django_fail_better.result_classes import MaxFailResult

        self.assertIsInstance(result, MaxFailResult)
        self.assertEqual(result.maxfail, 3)

    def test_result_has_maxfail_zero_by_default(self):
        from django.test import SimpleTestCase

        runner = FailBetterRunner(verbosity=0)

        class PassingTest(SimpleTestCase):
            def test_pass(self):
                pass

        suite = unittest.TestSuite()
        suite.addTest(PassingTest("test_pass"))

        with patch.object(runner, "log"):
            result = runner.run_suite(suite)

        self.assertEqual(result.maxfail, 0)


class StepwiseRuntimeTests(unittest.TestCase):
    def test_stepwise_saves_first_failure_id(self):
        from django.test import SimpleTestCase

        runner = FailBetterRunner(stepwise=True, verbosity=0)
        runner.cache_dir = Path(tempfile.mkdtemp()) / ".cache" / "fail_better"
        runner.last_failed_file = runner.cache_dir / "lastfailed"
        runner.stepwise_file = runner.cache_dir / "stepwise"
        runner.test_node_file = runner.cache_dir / "nodeids"

        class FailingTest(SimpleTestCase):
            def test_01(self):
                self.fail("1")

            def test_02(self):
                self.fail("2")

        suite = unittest.TestSuite()
        suite.addTest(FailingTest("test_01"))
        suite.addTest(FailingTest("test_02"))

        with (
            patch.object(runner, "setup_test_environment"),
            patch.object(runner, "setup_databases", return_value=()),
            patch.object(runner, "run_checks"),
            patch.object(runner, "teardown_databases"),
            patch.object(runner, "teardown_test_environment"),
            patch.object(runner, "build_suite", return_value=suite),
            patch.object(runner, "log"),
        ):
            runner.run_tests(test_labels=[])

        cached = runner.load_stepwise()
        self.assertIsNotNone(cached)
        self.assertIn("FailingTest.test_01", cached)

    def test_stepwise_clears_cache_on_success(self):
        from django.test import SimpleTestCase

        runner = FailBetterRunner(stepwise=True, verbosity=0)
        runner.cache_dir = Path(tempfile.mkdtemp()) / ".cache" / "fail_better"
        runner.last_failed_file = runner.cache_dir / "lastfailed"
        runner.stepwise_file = runner.cache_dir / "stepwise"
        runner.test_node_file = runner.cache_dir / "nodeids"
        runner.save_stepwise("some.stale.test")

        class PassingTest(SimpleTestCase):
            def test_pass(self):
                pass

        suite = unittest.TestSuite()
        suite.addTest(PassingTest("test_pass"))

        with (
            patch.object(runner, "setup_test_environment"),
            patch.object(runner, "setup_databases", return_value=()),
            patch.object(runner, "run_checks"),
            patch.object(runner, "teardown_databases"),
            patch.object(runner, "teardown_test_environment"),
            patch.object(runner, "build_suite", return_value=suite),
            patch.object(runner, "log"),
        ):
            runner.run_tests(test_labels=[])

        self.assertIsNone(runner.load_stepwise())

    def test_stepwise_with_cache_show_does_not_affect_stepwise(self):
        runner = FailBetterRunner(stepwise=True, cache_show=True)
        runner.cache_dir = Path(tempfile.mkdtemp()) / ".cache" / "fail_better"
        runner.last_failed_file = runner.cache_dir / "lastfailed"
        runner.stepwise_file = runner.cache_dir / "stepwise"
        runner.test_node_file = runner.cache_dir / "nodeids"
        runner.save_stepwise("some.test")
        with patch.object(runner, "log"):
            result = runner.run_tests(test_labels=[])
        self.assertEqual(result, 0)
        self.assertEqual(runner.load_stepwise(), "some.test")


class ArgumentDefaultsTests(unittest.TestCase):
    def test_max_fail_default_is_single_source_of_truth(self):
        self.assertEqual(FailBetterRunner.max_fail_default, 0)
        runner = FailBetterRunner()
        self.assertEqual(runner.maxfail, 0)

    def test_lastfailed_file_is_instance_level(self):
        r1 = FailBetterRunner()
        r2 = FailBetterRunner()
        self.assertIsNot(r1.last_failed_file, r2.last_failed_file)

import json
from pathlib import Path
from typing import cast
from unittest import TestCase

from django.conf import settings
from django.test.runner import (
    DiscoverRunner,
    ParallelTestSuite,
    partition_suite_by_case,
)

from .result_classes import MaxFailResult


class FailBetterRunner(DiscoverRunner):
    # TODO: Can this be replaced with inf?
    max_fail_default: int = 0

    def __init__(self, *args, **kwargs):
        self.last_failed = kwargs.pop("last_failed", False)
        self.failed_first = kwargs.pop("failed_first", False)
        self.lfnf = kwargs.pop("lfnf", "all")
        self.maxfail = kwargs.pop("maxfail", self.max_fail_default)
        self.cache_show = kwargs.pop("cache_show", False)
        self.cache_clear = kwargs.pop("cache_clear", False)
        self.stepwise = kwargs.pop("stepwise", False)
        self.stepwise_skip = kwargs.pop("stepwise_skip", False)

        base_dir = getattr(settings, "BASE_DIR", Path.cwd())
        self.cache_dir = Path(base_dir) / ".cache" / "fail_better"
        self.last_failed_file = self.cache_dir / "lastfailed"
        self.stepwise_file = self.cache_dir / "stepwise"
        self.test_node_file = self.cache_dir / "nodeids"

        super().__init__(*args, **kwargs)

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        # 🌸Better failures 🌸
        parser.add_argument(
            "--last-failed",
            "--lf",
            action="store_true",
            default=False,
            help="Run only the tests that failed at the last run (or all if none failed)",
        )
        parser.add_argument(
            "--failed-first",
            "--ff",
            action="store_true",
            default=False,
            help="Run all tests, but run the last failures first.",
        )
        parser.add_argument(
            "--last-failed-no-failures",
            "--lfnf",
            choices=["all", "none"],
            default="all",
            help="With ``--lf``, determines whether to execute tests when there are no previously (known) failures or "
            "when no cached ``lastfailed`` data was found. ``all`` (the default) runs the full test suite again. "
            "``none`` just emits a message about no known failures and exits successfully.",
        )
        parser.add_argument(
            "--maxfail",
            type=int,
            default=cls.max_fail_default,
            help="Exit after first num failures or errors",
        )

        # Cache
        parser.add_argument(
            "--cache-show",
            action="store_true",
            default=False,
            # TODO: Do I want to add "glob"? (check pytest help text)
            help=" Show cache contents, don't perform collection or tests.",
        )
        parser.add_argument(
            "--cache-clear",
            action="store_true",
            default=False,
            help="Remove all cache contents at start of test run",
        )

        # Stepwise
        parser.add_argument(
            "--stepwise",
            "--sw",
            action="store_true",
            default=False,
            help="Exit on test failure and continue from last failing test next time",
        )
        parser.add_argument(
            "--stepwise-skip",
            "--sw-skip",
            action="store_true",
            default=False,
            help="Ignore the first failing test but stop on the next failing test. Implicitly enables --stepwise.",
        )
        parser.add_argument(
            "--stepwise-reset",
            "--sw-reset",
            action="store_true",
            default=False,
            help="Resets stepwise state, restarting the stepwise workflow. Implicitly enables --stepwise.",
        )

    def load_last_failed(self):
        if not self.last_failed_file.exists():
            return None

        try:
            with self.last_failed_file.open() as f:
                return set(json.load(f))
        except (OSError, ValueError):
            return None

    def save_last_failed(self, test_ids):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with self.last_failed_file.open("w") as f:
            json.dump(sorted(test_ids), f)

    def show_cache(self):
        last_failed = self.load_last_failed()

        if last_failed is None:
            self.log("No cache found")
        elif len(last_failed) == 0:
            self.log("No previously failed tests")
        else:
            self.log(f"Previously failed tests ({len(last_failed)}):")

            for test_id in sorted(last_failed):
                self.log(f"  {test_id}")

    def clear_cache(self):
        try:
            if self.last_failed_file.exists():
                self.last_failed_file.unlink()
        except OSError:
            pass

    def load_stepwise(self):
        if not self.stepwise_file.exists():
            return None
        try:
            with self.stepwise_file.open() as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def save_stepwise(self, test_id):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with self.stepwise_file.open("w") as f:
            json.dump(test_id, f)

    def clear_stepwise(self):
        try:
            if self.stepwise_file.exists():
                self.stepwise_file.unlink()
        except OSError:
            pass

    def update_stepwise(self, result):
        if result.wasSuccessful():
            self.clear_stepwise()
        else:
            for test, _ in result.failures + result.errors:
                self.save_stepwise(test.id())
                break

    def load_test_nodes(self):
        if not self.test_node_file.exists():
            return None
        try:
            with self.test_node_file.open() as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def save_test_nodes(self, test_ids):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with self.test_node_file.open("w") as f:
            json.dump(test_ids, f)

    def clear_test_nodes(self):
        try:
            if self.test_node_file.exists():
                self.test_node_file.unlink()
        except OSError:
            pass

    def update_test_nodes(self, test_ids):
        self.save_test_nodes(test_ids)

    def update_cache(self, result):
        failed_ids = set()

        for test, _ in result.failures + result.errors:
            failed_ids.add(test.id())

        self.save_last_failed(failed_ids)

    def build_suite(self, test_labels=None, **kwargs):
        parallel = self.parallel
        self.parallel = 0

        suite = super().build_suite(test_labels=test_labels, **kwargs)

        self.parallel = parallel

        lastfailed = self.load_last_failed()

        if self.last_failed and lastfailed is not None:
            if len(lastfailed) == 0:
                if self.lfnf == "none":
                    return self.test_suite()
            else:
                all_tests = list(suite)
                filtered = [t for t in all_tests if t.id() in lastfailed]
                suite = self.test_suite(filtered)

        if self.failed_first and lastfailed:
            all_tests = list(suite)
            failed = [t for t in all_tests if cast(TestCase, t).id() in lastfailed]
            passed = [t for t in all_tests if cast(TestCase, t).id() not in lastfailed]
            suite = self.test_suite(failed + passed)

        if self.stepwise and not self.stepwise_skip:
            stepwise_state = self.load_stepwise()
            if stepwise_state is not None:
                all_tests = list(suite)
                for i, test in enumerate(all_tests):
                    if cast(TestCase, test).id() == stepwise_state:
                        suite = self.test_suite(all_tests[i:])
                        break

        if parallel > 1:
            subsuites = partition_suite_by_case(suite)
            processes = min(parallel, len(subsuites))
            self.parallel = processes
            if processes > 1:
                suite = ParallelTestSuite(
                    subsuites,
                    processes,
                    self.failfast,
                    self.debug_mode,
                    self.buffer,
                )

        return suite

    def get_resultclass(self):
        return MaxFailResult

    def run_suite(self, suite, **kwargs):
        kwargs = self.get_test_runner_kwargs()
        resultclass = self.get_resultclass()
        kwargs["resultclass"] = lambda s, d, v: resultclass(
            s,
            d,
            v,
            maxfail=self.maxfail,
        )
        runner = self.test_runner(**kwargs)

        try:
            return runner.run(suite)
        finally:
            if self._shuffler is not None:
                seed_display = self._shuffler.seed_display
                self.log(f"Used shuffle seed: {seed_display}")

    def run_tests(self, test_labels, **kwargs):
        if self.cache_show:
            self.show_cache()
            return 0

        if self.cache_clear:
            self.clear_cache()

        if self.stepwise:
            self.failfast = True

        self.setup_test_environment()
        suite = self.build_suite(test_labels)
        databases = self.get_databases(suite)
        suite.serialized_aliases = {alias for alias, serialize in databases.items() if serialize}
        suite.used_aliases = set(databases)
        test_ids = [cast(TestCase, t).id() for t in suite]
        with self.time_keeper.timed("Total database setup"):
            old_config = self.setup_databases(
                aliases=databases,
                serialized_aliases=suite.serialized_aliases,
            )
        run_failed = False
        try:
            self.run_checks(databases)
            result = self.run_suite(suite)
        except Exception:
            run_failed = True
            raise
        finally:
            try:
                with self.time_keeper.timed("Total database teardown"):
                    self.teardown_databases(old_config)
                self.teardown_test_environment()
            except Exception:
                if not run_failed:
                    raise
        self.time_keeper.print_results()

        self.update_cache(result)
        self.update_test_nodes(test_ids)

        if self.stepwise:
            self.update_stepwise(result)

        return self.suite_result(suite, result)

import json
from pathlib import Path

from django.conf import settings
from django.test.runner import DiscoverRunner
from django.test.utils import iter_test_cases


class FailBetterRunner(DiscoverRunner):
    # TODO: Can this be replaced with inf?
    max_fail_default: int = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: Do we want to handle args at class level so they can be overridden by children?

        self.last_failed = kwargs.get("last_failed", False)
        self.cache_show = kwargs.get("failure_cache_show", False)
        self.cache_clear = kwargs.get("failure_cache_clear", False)

        base_dir = getattr(settings, "BASE_DIR", Path.cwd())
        self.cache_dir = Path(base_dir) / ".cache" / "fail_better"
        self.last_failed_file = self.cache_dir / "last_failed.json"

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
            "--failure-cache-show",
            action="store_true",
            default=False,
            # TODO: Do I want to add "glob"? (check pytest help text)
            help="Show failure cache contents, don't perform collection or tests.",
        )
        parser.add_argument(
            "--failure-cache-clear",
            action="store_true",
            default=False,
            help="Remove all failure cache contents at start of test run.",
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

    def save_last_failed(self, test_ids):
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        with self.last_failed_file.open("w") as f:
            json.dump(sorted(test_ids), f)

    def load_last_failed(self):
        if not self.last_failed_file.exists():
            return None

        try:
            with self.last_failed_file.open() as f:
                return set(json.load(f))
        except (OSError, ValueError):
            return None

    def build_suite(self, test_labels=None, **kwargs):
        suite = super().build_suite(test_labels=test_labels, **kwargs)

        if not self.last_failed:
            return suite

        last_failed = self.load_last_failed()

        if not last_failed:
            return suite

        # iter_test_cases flattens nested suites into their constituent TestCase objects.
        # This is required when running under --parallel, where build_suite returns
        # a ParallelTestSuite wrapping sub-suites that do not expose a top-level id().
        all_tests = list(iter_test_cases(suite))
        failed = [t for t in all_tests if t.id() in last_failed]

        if not failed:
            self.log("No previously failed tests found, running all tests")
            return suite

        self.log(f"Running {len(failed)} previously failed test(s)")
        return self.test_suite(failed)

    @staticmethod
    def _collect_failed_ids(result):
        failed = [test for test, _ in result.failures + result.errors]
        failed += list(result.unexpectedSuccesses)

        return [test.id() for test in failed if test.id()]

    def run_suite(self, suite, **kwargs):
        result = super().run_suite(suite, **kwargs)
        self.save_last_failed(self._collect_failed_ids(result))

        return result

    def run_tests(self, test_labels, **kwargs):
        if self.cache_show:
            self.show_cache()
            return 0

        if self.cache_clear:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.save_last_failed([])

        return super().run_tests(test_labels, **kwargs)

    def show_cache(self):
        last_failed = self.load_last_failed()

        if last_failed:
            self.log(f"last_failed contains {len(last_failed)} test(s):")
            for test_id in sorted(last_failed):
                self.log(f"  {test_id}")
        else:
            self.log("cache is empty")

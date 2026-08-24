import json
from pathlib import Path

from django.conf import settings
from django.test.runner import DiscoverRunner

from .result_classes import MaxFailResult


class FailBetterRunner(DiscoverRunner):
    # TODO: Can this be replaced with inf?
    max_fail_default: int = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: Do we want to handle args at class level so they can be overridden by children?

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
            ...

            suite = super().build_suite(test_labels=test_labels, **kwargs)

            last_failed = self.load_last_failed()

            # TODO: Handle --lfnf
            if self.last_failed:
                all_tests = list(suite)
                failed = [t for t in all_tests if t.id() in last_failed]
                suite = self.test_suite(failed)

            ...

            return suite

        def get_resultclass(self):
            return MaxFailResult

        def run_tests(tests, *args, **kwargs): ...

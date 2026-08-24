from django.test.runner import DiscoverRunner


class FailBetterRunner(DiscoverRunner):
    # TODO: Can this be replaced with inf?
    max_fail_default: int = 0

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

        def run_tests(tests, *args, **kwargs): ...

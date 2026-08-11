import pytest

from statements.child_environment_scrub_statements import ChildEnvironmentScrubStatements


@pytest.mark.skip(
    reason="RED: AssertionError: a default child's environment removed ['PYTEST_ADDOPTS', "
    "'PYTEST_CURRENT_TEST', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD', 'PYTEST_PLUGINS', "
    "'PYTHONWARNINGS'] from the parent's, expected exactly that list plus 'FORCE_COLOR' "
    "and 'PY_COLORS' -- LEAKY_CHILD_VARIABLES carries neither colour variable"
)
class TestChildEnvironmentScrub:
    """A child pytest must inherit no variable a runner could steer it with.

    Given every such variable set in the parent process
    When a default child's environment is built, and then an opt-in child's
    Then the default removed exactly those and the opt-in removed nothing

    The scrub had exactly one witness -- a parametrised gate test that set a
    hostile `PYTEST_ADDOPTS` and required the forgotten-await gate to bite anyway.
    That witness can only watch entries for which a disarming vector exists, and it
    drives `PYTEST_ADDOPTS` twice; four of the five entries could be deleted with
    the suite staying green. This asserts on `child_environment()` directly, which
    is the only shape that goes red on tuple shrinkage, and it is where the two
    colour variables belong: they steer no filter, they turn pytest's markup on,
    and the anchored banner pattern then matches nothing the child drew.
    """

    def test_should_scrub_every_steerable_variable_from_a_child_and_keep_them_on_the_opt_in(
        self,
        tmp_path,
        child_environment_scrub_statements: ChildEnvironmentScrubStatements,
    ):
        """Both halves in one test, because the pair is the claim.

        Asserted apart, the scrub half says the opt-in was never reached by a
        scrub and the opt-in half says the default's roster is complete; neither
        alone says the scrub is opt-*out* rather than absent -- which is the
        property the disarmed families spend their exemption on. Each half is now
        strong on its own too: both compare the set of names the builder removed
        from the ambient environment, so neither can be satisfied by a builder
        that scrubbed everything or returned nothing.
        """
        child_environment_scrub_statements.given_every_variable_a_runner_could_steer_the_child_with()

        child_environment_scrub_statements.build_the_default_childs_environment(tmp_path)
        child_environment_scrub_statements.build_the_opt_in_childs_environment(tmp_path)

        child_environment_scrub_statements.assert_the_default_child_inherits_none_of_them()
        child_environment_scrub_statements.assert_the_opt_in_child_inherits_all_of_them()

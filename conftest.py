"""
Project-root pytest hook: registers TEST-ONLY command-line options.

pytest only reads options from a conftest.py at (or above) the folder you
run it from, which is why this lives at the project root.
"""


def pytest_addoption(parser):
    parser.addoption(
        "--day2-fault",
        action="store",
        default=None,
        choices=["ownership", "missing-status", "wrong-status-type"],
        help="TEST-ONLY: inject a named fault into the app for Day 2 demos.",
    )

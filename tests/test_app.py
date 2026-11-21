"""Smoke test: every page of the app renders without an error."""

from pathlib import Path

import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")

APP = str(Path(__file__).resolve().parent.parent / "app" / "main.py")


@pytest.mark.parametrize("page", ["New return", "Tax expert queue", "Results"])
def test_page_renders(page):
    app = streamlit_testing.AppTest.from_file(APP, default_timeout=30)
    app.run()
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception

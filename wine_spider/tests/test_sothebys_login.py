from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from wine_spider.helpers.sothebys import login


class FakePage:
    def __init__(self, password_visible=False):
        self.frames = []
        self._password_visible = password_visible
        self.fills = []
        self.clicks = []
        self.waits = []
        self.load_states = []

    def wait_for_selector(self, selector, **kwargs):
        self.waits.append((selector, kwargs))
        if selector == login.PASSWORD_SELECTOR and not self._password_visible:
            raise Exception("password not visible")
        return object()

    def fill(self, selector, value):
        self.fills.append((selector, value))

    def click(self, selector):
        self.clicks.append(selector)
        if selector == login.SUBMIT_SELECTOR:
            self._password_visible = True

    def wait_for_load_state(self, state, **kwargs):
        self.load_states.append((state, kwargs))


class SothebysLoginTests(unittest.TestCase):
    def test_get_credentials_prefers_sothebys_specific_env(self):
        env = {
            "SOTHEBYS_EMAIL": "sothebys@example.com",
            "SOTHEBYS_PASSWORD": "sothebys-pass",
            "EMAIL": "shared@example.com",
            "PASSWORD": "shared-pass",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                login.get_credentials(),
                ("sothebys@example.com", "sothebys-pass"),
            )

    def test_get_credentials_raises_clear_error_when_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "SOTHEBYS_EMAIL"):
                login.get_credentials()

    def test_submit_auth0_login_handles_two_step_identifier_flow(self):
        page = FakePage(password_visible=False)

        login.submit_auth0_login(page, "user@example.com", "secret")

        self.assertEqual(
            page.fills,
            [
                (login.USERNAME_SELECTOR, "user@example.com"),
                (login.PASSWORD_SELECTOR, "secret"),
            ],
        )
        self.assertEqual(page.clicks, [login.SUBMIT_SELECTOR, login.SUBMIT_SELECTOR])
        self.assertEqual(page.load_states[0][0], "networkidle")

    def test_submit_auth0_login_supports_one_page_password_flow(self):
        page = FakePage(password_visible=True)

        login.submit_auth0_login(page, "user@example.com", "secret")

        self.assertEqual(page.clicks, [login.SUBMIT_SELECTOR])


if __name__ == "__main__":
    unittest.main()

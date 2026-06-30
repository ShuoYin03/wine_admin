import json
import time

from wine_spider.middlewares.login_middleware import WineauctioneerLoginMiddleware


def test_wineauctioneer_login_state_refreshes_when_auth_cookie_is_expired(tmp_path, monkeypatch):
    state_path = tmp_path / "wineauctioneer_cookies.json"
    state_path.write_text(
        json.dumps(
            {
                "cookies": [
                    {
                        "name": "Wa_Role",
                        "value": "buyer",
                        "expires": time.time() - 60,
                    },
                    {
                        "name": "_ga",
                        "value": "analytics",
                        "expires": time.time() + 86400,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    calls = []

    def fake_run(args, check):
        calls.append((args, check))

    monkeypatch.setattr("wine_spider.middlewares.login_middleware.subprocess.run", fake_run)

    middleware = WineauctioneerLoginMiddleware(
        state_path=str(state_path),
        expire_days=107,
        login_script="wine_spider/helpers/wineauctioneer/login.py",
    )

    middleware._ensure_fresh_state()

    assert calls == [(["python", "wine_spider/helpers/wineauctioneer/login.py"], True)]

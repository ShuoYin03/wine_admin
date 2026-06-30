import importlib
import os


def test_run_spiders_defaults_to_project_settings(monkeypatch):
    monkeypatch.delenv("SCRAPY_SETTINGS_MODULE", raising=False)

    import wine_spider.run_spiders as run_spiders

    importlib.reload(run_spiders)

    assert os.environ["SCRAPY_SETTINGS_MODULE"] == "wine_spider.settings"

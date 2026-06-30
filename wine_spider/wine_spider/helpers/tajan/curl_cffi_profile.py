import os
import re
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit


DEFAULT_TAJAN_CURL_CFFI_IMPERSONATES = (
    "chrome142",
    "chrome136",
    "chrome131",
    "chrome124",
)

DEFAULT_TAJAN_ACCEPT_LANGUAGE = (
    "en,zh-CN;q=0.9,zh;q=0.8,it;q=0.7,en-GB;q=0.6,en-US;q=0.5"
)


@dataclass(frozen=True)
class TajanCurlCffiProfile:
    impersonate: str
    proxy_url: str | None = None

    @property
    def proxies(self) -> dict[str, str] | None:
        if not self.proxy_url:
            return None
        return {
            "http": self.proxy_url,
            "https": self.proxy_url,
        }


def parse_tajan_proxy_entry(entry: str) -> dict:
    entry = (entry or "").strip()
    if not entry:
        raise ValueError("Empty Tajan proxy entry")

    if "://" in entry:
        parsed = urlsplit(entry)
        if not parsed.hostname or not parsed.port:
            raise ValueError(f"Invalid Tajan proxy URL: {entry!r}")
        proxy = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
        if parsed.username:
            proxy["username"] = unquote(parsed.username)
        if parsed.password:
            proxy["password"] = unquote(parsed.password)
        return proxy

    parts = entry.split(":", 3)
    if len(parts) not in (2, 4):
        raise ValueError(f"Invalid Tajan proxy entry: {entry!r}")

    host, port = parts[0].strip(), parts[1].strip()
    if not host or not port:
        raise ValueError(f"Invalid Tajan proxy host/port: {entry!r}")

    proxy = {"server": f"http://{host}:{port}"}
    if len(parts) == 4:
        proxy["username"] = parts[2]
        proxy["password"] = parts[3]
    return proxy


def build_tajan_proxy_contexts(raw_proxies: str | None = None) -> dict:
    return {
        f"tajan_proxy_{index}": {"proxy": parse_tajan_proxy_entry(entry)}
        for index, entry in enumerate(split_proxy_entries(raw_proxies))
    }


def split_proxy_entries(raw_proxies: str | None = None) -> list[str]:
    raw_proxies = os.getenv("TAJAN_PROXY_URLS", "") if raw_proxies is None else raw_proxies
    return [
        entry.strip()
        for entry in re.split(r"[\s,]+", raw_proxies or "")
        if entry.strip()
    ]


def build_tajan_proxy_urls(raw_proxies: str | None = None) -> list[str]:
    proxy_urls = []
    for entry in split_proxy_entries(raw_proxies):
        proxy = parse_tajan_proxy_entry(entry)
        server = proxy["server"]
        username = proxy.get("username")
        password = proxy.get("password")
        if not username:
            proxy_urls.append(server)
            continue

        parts = urlsplit(server)
        auth = quote(username, safe="")
        if password is not None:
            auth = f"{auth}:{quote(password, safe='')}"
        proxy_urls.append(f"{parts.scheme}://{auth}@{parts.hostname}:{parts.port}")
    return proxy_urls


def build_tajan_curl_cffi_profiles(
    raw_proxies: str | None = None,
    impersonates: tuple[str, ...] | list[str] | None = None,
) -> tuple[TajanCurlCffiProfile, ...]:
    impersonates = tuple(impersonates or DEFAULT_TAJAN_CURL_CFFI_IMPERSONATES)
    proxy_urls = build_tajan_proxy_urls(raw_proxies)
    if not proxy_urls:
        return tuple(TajanCurlCffiProfile(impersonate=name) for name in impersonates)

    profiles = []
    used_pairs = set()
    for offset in range(len(impersonates)):
        for proxy_index, proxy_url in enumerate(proxy_urls):
            impersonate = impersonates[(proxy_index + offset) % len(impersonates)]
            pair = (proxy_url, impersonate)
            if pair in used_pairs:
                continue
            used_pairs.add(pair)
            profiles.append(TajanCurlCffiProfile(impersonate=impersonate, proxy_url=proxy_url))
    return tuple(profiles)


def build_tajan_curl_cffi_headers(
    impersonate: str,
    referer: str | None = None,
    accept_language: str | None = None,
) -> dict[str, str]:
    major = chrome_major_version(impersonate)
    headers = {
        "accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.7"
        ),
        "accept-language": accept_language or DEFAULT_TAJAN_ACCEPT_LANGUAGE,
        "cache-control": "max-age=0",
        "priority": "u=0, i",
        "sec-ch-ua": (
            f'"Google Chrome";v="{major}", "Chromium";v="{major}", '
            '"Not)A;Brand";v="24"'
        ),
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin" if referer else "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{major}.0.0.0 Safari/537.36"
        ),
    }
    if referer:
        headers["referer"] = referer
    return headers


def chrome_major_version(impersonate: str) -> str:
    match = re.search(r"chrome(\d+)", impersonate)
    if not match:
        return "142"
    return match.group(1)

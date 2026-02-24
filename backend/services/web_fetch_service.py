"""웹 페이지 URL 감지 및 콘텐츠 가져오기 서비스 (보안 필터링 포함).

변경 이력 (v2 → v3):
  - DNS 조회를 asyncio thread-pool로 이전 (이벤트 루프 블로킹 방지)
  - HTTP/HTTPS 기본 포트 수정 (http→80, https→443)
  - User-Agent를 일반 브라우저 문자열로 교체 (403 차단 방지)
  - httpx 내장 리다이렉트 처리 사용 (max_redirects=5, 최종 URL도 검증)
  - MAX_CHARS_PER_PAGE 8000 → 15000
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx
import structlog

log = structlog.get_logger()

# ── URL extraction ───────────────────────────────────────────────────
_URL_RE = re.compile(
    r"https?://[^\s<>\"'\)\]]+",
    re.IGNORECASE,
)

# ── HTML stripping ───────────────────────────────────────────────────
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE
)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\n{3,}")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)

# ── Limits ───────────────────────────────────────────────────────────
MAX_URLS = 3
MAX_CHARS_PER_PAGE = 15_000         # raised from 8 000
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB
FETCH_TIMEOUT = 15
MAX_REDIRECTS = 5

# ── SSRF: blocked IP ranges ──────────────────────────────────────────
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),    # loopback
    ipaddress.ip_network("10.0.0.0/8"),      # private class A
    ipaddress.ip_network("172.16.0.0/12"),   # private class B
    ipaddress.ip_network("192.168.0.0/16"),  # private class C
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("0.0.0.0/8"),       # "this" network
    ipaddress.ip_network("100.64.0.0/10"),   # carrier-grade NAT
    ipaddress.ip_network("198.18.0.0/15"),   # benchmark testing
    ipaddress.ip_network("240.0.0.0/4"),     # reserved / future
    ipaddress.ip_network("::1/128"),         # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),        # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),       # IPv6 link-local
]

# ── Blocked schemes / ports ──────────────────────────────────────────
_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_PORTS = {22, 25, 53, 110, 143, 445, 3306, 5432, 6379, 11434, 27017}

# ── User-Agent: use a common browser string so sites don't block us ──
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def _is_private_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable → block
    return any(addr in net for net in _BLOCKED_NETWORKS)


async def _validate_url_async(url: str) -> str | None:
    """Async URL validation — DNS check runs in thread pool.

    Returns an error message if the URL should be blocked, or None if safe.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return "잘못된 URL 형식"

    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return f"허용되지 않는 프로토콜: {parsed.scheme}"

    hostname = parsed.hostname
    if not hostname:
        return "호스트명 없음"

    if hostname.startswith(".") or ".." in hostname:
        return "잘못된 호스트명"

    port = parsed.port
    if port and port in _BLOCKED_PORTS:
        return f"차단된 포트: {port}"

    # Use correct default port per scheme (was always 443 before — bug)
    default_port = 443 if parsed.scheme.lower() == "https" else 80

    # DNS resolution in thread pool — does NOT block the event loop
    loop = asyncio.get_event_loop()
    try:
        addr_infos: list = await loop.run_in_executor(
            None,
            lambda: socket.getaddrinfo(
                hostname, port or default_port, proto=socket.IPPROTO_TCP
            ),
        )
    except socket.gaierror:
        return f"DNS 조회 실패: {hostname}"

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        if _is_private_ip(ip_str):
            log.warning(
                "SSRF 차단",
                action="ssrf_block",
                url=url,
                resolved_ip=ip_str,
            )
            return f"내부 네트워크 접근 차단 ({hostname})"

    return None


def extract_urls(text: str) -> list[str]:
    """텍스트에서 URL을 추출한다 (최대 MAX_URLS개)."""
    seen: set[str] = set()
    urls: list[str] = []
    for m in _URL_RE.finditer(text):
        url = m.group().rstrip(".,;:!?")
        if url not in seen:
            seen.add(url)
            urls.append(url)
            if len(urls) >= MAX_URLS:
                break
    return urls


def _strip_html(html: str) -> tuple[str, str]:
    """HTML → (title, plain_text)."""
    title_m = _TITLE_RE.search(html)
    title = _TAG_RE.sub("", title_m.group(1)).strip() if title_m else ""

    text = _SCRIPT_STYLE_RE.sub("", html)
    text = _TAG_RE.sub(" ", text)
    for entity, char in [
        ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
        ("&nbsp;", " "), ("&quot;", '"'), ("&#39;", "'"),
    ]:
        text = text.replace(entity, char)
    text = _WHITESPACE_RE.sub("\n\n", text.strip())
    return title, text


async def fetch_page_text(
    url: str,
    max_chars: int = MAX_CHARS_PER_PAGE,
) -> dict:
    """URL의 텍스트 콘텐츠를 가져온다 (보안 검증 포함).

    Returns: {"url": str, "title": str, "text": str, "error": str | None}
    """
    error_result = {"url": url, "title": "", "text": ""}

    # ── Validate initial URL ──────────────────────────────────────────
    validation_error = await _validate_url_async(url)
    if validation_error:
        log.warning("URL 보안 차단", action="url_blocked", url=url, reason=validation_error)
        return {**error_result, "error": f"보안 차단: {validation_error}"}

    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT,
            follow_redirects=True,          # let httpx handle the hop loop
            max_redirects=MAX_REDIRECTS,    # hard cap
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            resp = await client.get(url)

            # ── Validate final URL after any redirects ────────────────
            final_url = str(resp.url)
            if final_url != url:
                redirect_error = await _validate_url_async(final_url)
                if redirect_error:
                    log.warning(
                        "리다이렉트 SSRF 차단",
                        action="redirect_ssrf_block",
                        original_url=url,
                        final_url=final_url,
                    )
                    return {**error_result, "error": f"보안 차단 (리다이렉트): {redirect_error}"}

            resp.raise_for_status()

            # Response size check
            content_length = resp.headers.get("content-length")
            if content_length and int(content_length) > MAX_RESPONSE_BYTES:
                return {
                    **error_result,
                    "error": f"응답 크기 초과 ({int(content_length) // 1024}KB)",
                }

            content_type = resp.headers.get("content-type", "")
            if "text/html" in content_type or "text/plain" in content_type or "xhtml" in content_type:
                html = resp.text[:MAX_RESPONSE_BYTES]
                title, text = _strip_html(html)
                if len(text) > max_chars:
                    text = text[:max_chars] + "\n... (내용 생략)"
                return {"url": final_url, "title": title, "text": text, "error": None}

            return {**error_result, "error": f"지원하지 않는 콘텐츠 유형: {content_type}"}

    except httpx.TooManyRedirects:
        return {**error_result, "error": "리다이렉트 횟수 초과"}
    except httpx.TimeoutException:
        return {**error_result, "error": "시간 초과"}
    except httpx.HTTPStatusError as e:
        return {**error_result, "error": f"HTTP {e.response.status_code}"}
    except Exception as e:  # noqa: BLE001
        return {**error_result, "error": str(e)[:200]}


async def fetch_all_urls(
    text: str,
    max_urls: int = MAX_URLS,
) -> list[dict]:
    """텍스트 내 URL을 감지하고 병렬로 콘텐츠를 가져온다."""
    urls = extract_urls(text)[:max_urls]
    if not urls:
        return []

    log.info("웹 페이지 가져오기", action="web_fetch", url_count=len(urls))
    results = await asyncio.gather(
        *(fetch_page_text(u) for u in urls),
        return_exceptions=True,
    )
    fetched: list[dict] = []
    for r in results:
        if isinstance(r, Exception):
            fetched.append({"url": "unknown", "title": "", "text": "", "error": str(r)[:200]})
        else:
            fetched.append(r)
    return fetched


def build_augmented_prompt(
    user_message: str,
    fetched_pages: list[dict],
) -> str:
    """사용자 메시지에 가져온 웹 페이지 내용을 추가한다."""
    if not fetched_pages:
        return user_message

    parts = [user_message, "\n\n[참고 웹 페이지 내용]"]
    for page in fetched_pages:
        if page["error"]:
            parts.append(f"--- {page['url']} ---\n(실패: {page['error']})\n--- end ---")
        else:
            title_line = f" ({page['title']})" if page["title"] else ""
            parts.append(f"--- {page['url']}{title_line} ---\n{page['text']}\n--- end ---")
    return "\n\n".join(parts)


# Backward-compatible alias
build_augmented_instruction = build_augmented_prompt

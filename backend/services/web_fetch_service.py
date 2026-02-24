"""웹 페이지 URL 감지 및 콘텐츠 가져오기 서비스 (보안 필터링 포함)."""

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
MAX_CHARS_PER_PAGE = 8000
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MB
FETCH_TIMEOUT = 15
MAX_REDIRECTS = 5

# ── SSRF: blocked IP ranges ─────────────────────────────────────────
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # loopback
    ipaddress.ip_network("10.0.0.0/8"),         # private class A
    ipaddress.ip_network("172.16.0.0/12"),      # private class B
    ipaddress.ip_network("192.168.0.0/16"),     # private class C
    ipaddress.ip_network("169.254.0.0/16"),     # link-local
    ipaddress.ip_network("0.0.0.0/8"),          # "this" network
    ipaddress.ip_network("100.64.0.0/10"),      # carrier-grade NAT
    ipaddress.ip_network("198.18.0.0/15"),      # benchmark testing
    ipaddress.ip_network("240.0.0.0/4"),        # reserved / future
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
]

# ── Blocked schemes / ports ──────────────────────────────────────────
_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_PORTS = {22, 25, 53, 110, 143, 445, 3306, 5432, 6379, 11434, 27017}


def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address falls within blocked (private/reserved) ranges."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable → block
    return any(addr in net for net in _BLOCKED_NETWORKS)


def _validate_url(url: str) -> str | None:
    """Validate URL for security. Returns error message or None if safe."""
    try:
        parsed = urlparse(url)
    except Exception:
        return "잘못된 URL 형식"

    # Scheme check
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return f"허용되지 않는 프로토콜: {parsed.scheme}"

    # Hostname required
    hostname = parsed.hostname
    if not hostname:
        return "호스트명 없음"

    # Block suspicious hostnames
    if hostname.startswith(".") or ".." in hostname:
        return "잘못된 호스트명"

    # Port check
    port = parsed.port
    if port and port in _BLOCKED_PORTS:
        return f"차단된 포트: {port}"

    # DNS resolution → IP check (prevents DNS rebinding)
    try:
        addr_infos = socket.getaddrinfo(hostname, port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return f"DNS 조회 실패: {hostname}"

    for family, _, _, _, sockaddr in addr_infos:
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
    for entity, char in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                         ("&nbsp;", " "), ("&quot;", '"'), ("&#39;", "'")]:
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

    # ── Security validation ──
    validation_error = _validate_url(url)
    if validation_error:
        log.warning("URL 보안 차단", action="url_blocked", url=url, reason=validation_error)
        return {**error_result, "error": f"보안 차단: {validation_error}"}

    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT,
            follow_redirects=False,  # handle redirects manually for safety
            headers={"User-Agent": "GM-AI-Hub/2.0 (Document Assistant)"},
            max_redirects=0,
        ) as client:
            # Manual redirect loop with validation at each hop
            current_url = url
            for _ in range(MAX_REDIRECTS):
                resp = await client.get(current_url)

                if resp.is_redirect:
                    next_url = str(resp.next_request.url) if resp.next_request else None
                    if not next_url:
                        return {**error_result, "error": "리다이렉트 대상 없음"}
                    redirect_error = _validate_url(next_url)
                    if redirect_error:
                        log.warning(
                            "리다이렉트 SSRF 차단",
                            action="redirect_ssrf_block",
                            original_url=url,
                            redirect_url=next_url,
                        )
                        return {**error_result, "error": f"보안 차단 (리다이렉트): {redirect_error}"}
                    current_url = next_url
                    continue

                resp.raise_for_status()

                # Response size check
                content_length = resp.headers.get("content-length")
                if content_length and int(content_length) > MAX_RESPONSE_BYTES:
                    return {**error_result, "error": f"응답 크기 초과 ({int(content_length) // 1024}KB)"}

                content_type = resp.headers.get("content-type", "")
                if "text/html" in content_type or "text/plain" in content_type:
                    html = resp.text[:MAX_RESPONSE_BYTES]
                    title, text = _strip_html(html)
                    if len(text) > max_chars:
                        text = text[:max_chars] + "\n... (내용 생략)"
                    return {"url": url, "title": title, "text": text, "error": None}

                return {**error_result, "error": f"지원하지 않는 콘텐츠 유형: {content_type}"}

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
    """텍스트 내 URL을 감지하고 병렬로 콘텐츠를 가져온다 (보안 검증 포함)."""
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

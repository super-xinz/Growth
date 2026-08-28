import hashlib
import re
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "RedditGrowthAgent/0.1 product-ingestion"}
PATHS = ["", "/features", "/pricing", "/faq", "/docs", "/about"]


def clean_html(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:30000]
    return title, text


async def ingest_url(url: str, github: bool = False) -> list[dict]:
    urls = []
    if github:
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")
        if parsed.netloc == "github.com" and len(parts) >= 2:
            urls = [f"https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/HEAD/README.md"]
        else:
            urls = [url]
    else:
        root = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        urls = [urljoin(root, p) for p in PATHS]
    results = []
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        for item in dict.fromkeys(urls[:20]):
            try:
                response = await client.get(item)
                if response.status_code >= 400 or len(response.text) < 40:
                    continue
                title, content = (
                    (item.rsplit("/", 1)[-1] or "README", response.text[:30000])
                    if github
                    else clean_html(response.text)
                )
                if content:
                    results.append(
                        {
                            "url": str(response.url),
                            "type": "github" if github else "website",
                            "title": title,
                            "content": content,
                            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
                        }
                    )
            except httpx.HTTPError:
                continue
    return results

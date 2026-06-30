import httpx
from bs4 import BeautifulSoup


def fetch_page(url):
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=15)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        return f"Error fetching {url}: {e}"
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return text[:4000]

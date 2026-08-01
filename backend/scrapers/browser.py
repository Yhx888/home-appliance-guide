"""本地浏览器低频补采 — 覆盖联盟 API 匹配不到的价格/参数

使用 playwright 驱动真实浏览器（复用用户登录态时使用持久化用户目录），
仅访问搜索列表页，低频限速由 Collector 统一控制。

环境要求：
  pip install playwright && playwright install chromium

未安装时自动降级为提示，不阻塞其他通道。
"""

import re
from typing import Optional


def _playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def fetch_jd_search_prices(keyword: str, max_items: int = 5) -> list[dict]:
    """打开京东搜索页，提取前 N 个商品 {title, price, url}。"""
    if not _playwright_available():
        print("[browser] playwright 未安装，跳过浏览器补采（pip install playwright）")
        return []
    from playwright.sync_api import sync_playwright

    url = "https://search.jd.com/Search?keyword=" + keyword
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        ))
        try:
            page.goto(url, timeout=20000)
            page.wait_for_timeout(3000)
            items = page.query_selector_all("li.gl-item")
            for item in items[:max_items]:
                title_el = item.query_selector(".p-name em")
                price_el = item.query_selector(".p-price i")
                link_el = item.query_selector(".p-img a")
                if title_el and price_el:
                    title = title_el.inner_text().strip()
                    price_text = price_el.inner_text().strip()
                    m = re.search(r"\d+\.?\d*", price_text)
                    results.append({
                        "title": title,
                        "price": float(m.group()) if m else None,
                        "url": link_el.get_attribute("href") if link_el else "",
                    })
        except Exception as e:
            print(f"[browser] 京东搜索失败 {keyword}: {e}")
        finally:
            browser.close()
    return results


def fetch_suning_search_prices(keyword: str, max_items: int = 5) -> list[dict]:
    """苏宁搜索页补采（结构简单，反爬较弱）。"""
    if not _playwright_available():
        print("[browser] playwright 未安装，跳过浏览器补采")
        return []
    from playwright.sync_api import sync_playwright

    url = "https://search.suning.com/" + keyword
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=20000)
            page.wait_for_timeout(3000)
            # 苏宁商品卡: .item-b-wrap 结构（选择器随改版可能变化，失败不致命）
            items = page.query_selector_all(".item-b-wrap")
            for item in items[:max_items]:
                title_el = item.query_selector(".title-selling-point")
                price_el = item.query_selector(".price-box .price")
                if title_el and price_el:
                    title = title_el.inner_text().strip()
                    price_text = price_el.inner_text().strip()
                    m = re.search(r"\d+\.?\d*", price_text)
                    results.append({
                        "title": title,
                        "price": float(m.group()) if m else None,
                        "url": item.query_selector("a").get_attribute("href") if item.query_selector("a") else "",
                    })
        except Exception as e:
            print(f"[browser] 苏宁搜索失败 {keyword}: {e}")
        finally:
            browser.close()
    return results


def fetch_rendered_specs(url: str, selectors: Optional[dict] = None) -> dict:
    """渲染页面后提取规格表（厂商官网 JS 页兜底）。

    selectors 示例：
      {"table": "table.spec", "row": "tr", "cell": "td"}
    缺省时尝试多种常见结构，返回 {标签: 值}。
    """
    if not _playwright_available():
        print("[browser] playwright 未安装，跳过渲染兜底")
        return {}
    from playwright.sync_api import sync_playwright

    selectors = selectors or {}
    result: dict[str, str] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        ))
        try:
            page.goto(url, timeout=25000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            # 常见规格表选择器逐个尝试
            for table_sel in (selectors.get("table"), "table", ".spec-table", ".parameter-table"):
                if not table_sel:
                    continue
                tables = page.query_selector_all(table_sel)
                for table in tables[:2]:
                    rows = table.query_selector_all("tr")
                    for row in rows:
                        cells = row.query_selector_all("td, th")
                        if len(cells) >= 2:
                            label = cells[0].inner_text().strip()
                            value = cells[1].inner_text().strip()
                            if label and value:
                                result[label] = value
                if result:
                    break
            if not result:
                # dl/dt/dd 定义列表兜底
                dls = page.query_selector_all("dl")
                for dl in dls:
                    dt = dl.query_selector("dt")
                    dd = dl.query_selector("dd")
                    if dt and dd:
                        label = dt.inner_text().strip()
                        value = dd.inner_text().strip()
                        if label and value:
                            result[label] = value
        except Exception as e:
            print(f"[browser] 渲染失败 {url}: {e}")
        finally:
            browser.close()
    return result


if __name__ == "__main__":
    import sys
    kw = sys.argv[1] if len(sys.argv) > 1 else "美的508冰箱"
    print(fetch_jd_search_prices(kw))

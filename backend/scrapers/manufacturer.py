"""厂商官网参数采集

使用方法：
  from backend.scrapers.manufacturer import search_manufacturer_site, extract_specs_from_manufacturer_html

注意：
  - search_manufacturer_site 为接口定义，实际采集需配合浏览器工具
  - extract_specs_from_manufacturer_html 解析常见厂商官网规格表
"""

import re
from bs4 import BeautifulSoup


def search_manufacturer_site(brand: str, category: str) -> list[dict]:
    """搜索厂商官网产品页。

    返回产品列表，每项含 title, url, specs。
    当前为占位实现，实际采集需配合 Kimi WebBridge / playwright 使用。
    """
    return []


def extract_specs_from_manufacturer_html(html: str, dim_keys: list[str]) -> dict:
    """从厂商官网 HTML 中提取规格参数。

    支持多种官网常见结构：
    - table.product-specs 结构
    - dl/dt/dd 定义列表结构
    - div.spec-item 结构
    返回 {dim_key: raw_value} 字典。
    """
    result: dict[str, str] = {}
    soup = BeautifulSoup(html, 'html.parser')

    # 策略1：table 规格表
    tables = soup.find_all('table', class_=re.compile(r'(spec|parameter|attribute)', re.I))
    if not tables:
        tables = soup.find_all('table')
    for table in tables:
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                label = _clean_text(cells[0].get_text(strip=True))
                value = _clean_text(cells[1].get_text(strip=True))
                key = _match_dim_key(label, dim_keys)
                if key:
                    result[key] = value
        if result:
            return result

    # 策略2：dl/dt/dd 定义列表
    for dl in soup.find_all('dl', class_=re.compile(r'(spec|parameter|attr)', re.I)):
        dt = dl.find('dt')
        dd = dl.find('dd')
        if dt and dd:
            label = _clean_text(dt.get_text(strip=True))
            value = _clean_text(dd.get_text(strip=True))
            key = _match_dim_key(label, dim_keys)
            if key:
                result[key] = value

    if not result:
        # 策略3：div.spec-item 结构
        for item in soup.find_all('div', class_=re.compile(r'(spec|param|attr)', re.I)):
            label_el = item.find(['span', 'label', 'div'], class_=re.compile(r'(name|label|title)', re.I))
            value_el = item.find(['span', 'div', 'p'], class_=re.compile(r'(value|desc|content)', re.I))
            if label_el and value_el:
                label = _clean_text(label_el.get_text(strip=True))
                value = _clean_text(value_el.get_text(strip=True))
                key = _match_dim_key(label, dim_keys)
                if key:
                    result[key] = value

    return result


def _clean_text(text: str) -> str:
    """清理文本：去空白、去冒号"""
    text = re.sub(r'\s+', '', text)
    text = text.rstrip('：:')
    return text


def _match_dim_key(label: str, dim_keys: list[str]) -> str | None:
    """匹配 label 到 dim_key"""
    label_to_prefix = {
        '风量': '风量',
        '静压': '静压',
        '噪音': '噪音',
        '能效': '能效等级',
        '容量': '容量',
        '火力': '火力',
        '热效率': '热效率',
        '价格': '价格',
        '保修': '保修',
        '功率': '功率',
        '尺寸': '尺寸',
        '重量': '重量',
        '面板': '面板材质',
        '电机': '电机类型',
        '烘干': '烘干方式',
        '消毒': '消毒方式',
        '过滤': '过滤等级',
        '吸力': '吸力',
        '型号': '型号',
    }

    prefix = label_to_prefix.get(label)
    if prefix:
        for dk in dim_keys:
            if dk.startswith(prefix):
                return dk

    for dk in dim_keys:
        if label == dk.split('_')[0]:
            return dk
    return None

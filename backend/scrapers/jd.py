"""京东商品数据采集 — HTML 解析 + 截图多模态兜底

使用方法：
  from backend.scrapers.jd import search_jd_products, extract_specs_from_html

注意：
  - search_jd_products 为接口定义，实际采集需配合 Kimi WebBridge / playwright
  - extract_specs_from_html 可独立使用，解析京东规格表 HTML
"""

import re

# 京东规格表常见 HTML 结构模式
# 特征：<th>标签名</th><td>值</td> 或 <td class="parameter">名<td><td>值</td>
_JD_SPEC_PATTERNS = [
    re.compile(r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>', re.DOTALL),
    re.compile(r'<td[^>]*class="[^"]*parameter[^"]*"[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>', re.DOTALL),
    re.compile(r'<div[^>]*class="[^"]*spec-item[^"]*"[^>]*>.*?<span[^>]*class="[^"]*name[^"]*"[^>]*>(.*?)</span>.*?<span[^>]*class="[^"]*value[^"]*"[^>]*>(.*?)</span>', re.DOTALL),
]


def search_jd_products(keyword: str, limit: int = 20) -> list[dict]:
    """搜索京东商品，返回商品列表。

    每个商品包含：title, price, url, image_url。
    当前为占位实现，实际采集需配合 Kimi WebBridge / playwright 使用。
    """
    return []


def extract_specs_from_html(html: str, dim_keys: list[str]) -> dict:
    """从京东商品详情页 HTML 中提取规格参数。

    依次匹配多种常见京东规格表 HTML 结构，返回 {dim_key: raw_value}。
    若无匹配则返回空字典。
    """
    from bs4 import BeautifulSoup

    result: dict[str, str] = {}
    soup = BeautifulSoup(html, 'html.parser')

    # 策略1：找 class=Ptable 的标准规格表
    ptable = soup.find(class_='Ptable')
    if ptable:
        for item in ptable.find_all(class_='PtableItem'):
            name_el = item.find(class_='PtableItem__name')
            value_el = item.find(class_='PtableItem__value')
            if name_el and value_el:
                label = _normalize_label(name_el.get_text(strip=True))
                value = value_el.get_text(strip=True)
                key = _match_dim_key(label, dim_keys)
                if key:
                    result[key] = value
        if result:
            return result

    # 策略2：找 class=parameter2 的规格表
    param2 = soup.find(class_='parameter2')
    if param2:
        for li in param2.find_all('li'):
            text = li.get_text(strip=True)
            if '：' in text:
                label, value = text.split('：', 1)
                key = _match_dim_key(_normalize_label(label), dim_keys)
                if key:
                    result[key] = value.strip()
        if result:
            return result

    # 策略3：通用正则提取
    for pattern in _JD_SPEC_PATTERNS:
        for match in pattern.finditer(html):
            label = _normalize_label(match.group(1).strip())
            value = match.group(2).strip()
            key = _match_dim_key(label, dim_keys)
            if key and key not in result:
                result[key] = value
        if result:
            return result

    return result


def _normalize_label(text: str) -> str:
    """清理标签文本：去空格、去换行、去冒号"""
    text = re.sub(r'\s+', '', text)
    text = text.rstrip('：:')
    return text


def _match_dim_key(label: str, dim_keys: list[str]) -> str | None:
    """通过维度 label 反向匹配 dim_key。

    利用 SCHEMA.md 中 label ↔ dim_key 的对应关系，
    简单判断 label 是否与已知 dim_key 的中文部分匹配。
    """
    # 常见 label -> dim_key 前缀映射
    label_to_key_prefix = {
        '风量': '风量',
        '静压': '静压',
        '噪音': '噪音',
        '能效': '能效等级',
        '容量': '容量',
        '火力': '火力',
        '热效率': '热效率',
        '价格': '价格',
        '型号': '型号',
        '尺寸': '尺寸',
        '保修': '保修',
        '功率': '功率',
        '重量': '重量',
        '电压': '电压',
        '频率': '频率',
    }

    prefix = label_to_key_prefix.get(label)
    if prefix:
        for dk in dim_keys:
            if dk.startswith(prefix):
                return dk

    # 完全匹配
    for dk in dim_keys:
        if label == dk.split('_')[0]:
            return dk

    return None


def parse_numeric(text: str) -> float | None:
    """从文本中解析数值。

    支持格式：
      "22m³/min" → 22.0
      "450Pa" → 450.0
      "48-52dB" → 50.0 (取中值)
      "5.0kW+" → 5.0
      "≥1000" → 1000
      "99.9%" → 99.9
      "5年" → 5.0
    """
    if not text:
        return None

    text = text.strip()

    # 去除千位分隔符
    text = text.replace(',', '')

    # 提取数字部分（支持范围取中值）
    nums = re.findall(r'(\d+\.?\d*)', text)
    if not nums:
        return None

    values = [float(n) for n in nums]
    if len(values) == 1:
        return values[0]
    return sum(values) / len(values)

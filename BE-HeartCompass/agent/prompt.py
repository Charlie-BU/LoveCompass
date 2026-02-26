import json
import html as html_lib
import re
from typing import Optional, Any, List

from request import fetch


def extractPromptFromPromptMinder(
    html: str, variables: dict | None = None
) -> Optional[str]:
    """
    从 Prompt Minder 的分享页 HTML 中提取 prompt 文本。
    返回 prompt 字符串；失败返回 None。
    """

    def _normalize(s: str) -> str:
        # 统一换行、解 HTML 实体、去掉首尾空白
        s = s.replace("\r\n", "\n").replace("\r", "\n")
        s = html_lib.unescape(s).strip()
        return s

    def _findJsonlds(doc: str) -> List[str]:
        # 抓取所有 <script type="application/ld+json">...</script>
        # 用非贪婪 + DOTALL，尽量不受换行影响
        pattern = re.compile(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            re.IGNORECASE | re.DOTALL,
        )
        return [m.group(1).strip() for m in pattern.finditer(doc)]

    def _iterCreativeworks(obj: Any):
        # JSON-LD 里可能是 dict / list，或 {"@graph":[...]}
        if isinstance(obj, dict):
            if "@graph" in obj and isinstance(obj["@graph"], list):
                for item in obj["@graph"]:
                    yield from _iterCreativeworks(item)

            t = obj.get("@type")
            # @type 可能是 "CreativeWork" 或 ["CreativeWork", ...]
            if t == "CreativeWork" or (isinstance(t, list) and "CreativeWork" in t):
                yield obj

            # 继续递归，避免 CreativeWork 嵌套在别处
            for v in obj.values():
                yield from _iterCreativeworks(v)

        elif isinstance(obj, list):
            for item in obj:
                yield from _iterCreativeworks(item)

    # ---- JSON-LD CreativeWork.text）----
    for raw in _findJsonlds(html):
        try:
            data = json.loads(raw)
        except Exception:
            # 有些站点会塞入无效 JSON（比如多余逗号），这里直接跳过
            continue
        for cw in _iterCreativeworks(data):
            text = cw.get("text")
            if isinstance(text, str) and text.strip():
                result = _normalize(text)
                if variables:
                    for k, v in variables.items():
                        val = "" if v is None else str(v)
                        pattern = re.compile(r"{{\s*" + re.escape(k) + r"\s*}}")
                        result = pattern.sub(lambda _: val, result)
                return result

    return None


async def getPrompt(
    prompt_minder_url: str, variables: dict | None = None
) -> Optional[str]:
    if not prompt_minder_url:
        return None
    html = await fetch(prompt_minder_url)
    return extractPromptFromPromptMinder(html, variables)

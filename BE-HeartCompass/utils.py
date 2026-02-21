def cleanList(items: list):
    """
    清理列表中的重复字符串项，保留首次出现的项。
    参数:
    items (list): 包含字符串的列表。
    返回:
    list: 清理后的列表，仅包含唯一的非空字符串项。
    """
    if not items:
        return []
    result = []
    seen = set()
    for item in items:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result

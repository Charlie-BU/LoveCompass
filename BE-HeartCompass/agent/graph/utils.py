def getValueFromEntity(item, key):
        if isinstance(item, dict):
            value = item.get(key)
        else:
            value = getattr(item, key, None)
        return value.value if hasattr(value, "value") else value  # 同时处理Enum类型

def formatList(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return "、".join(
            [str(v) for v in value if v is not None and str(v).strip()]
        )
    return str(value)

def appendLabelIfValue(label, value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return f"{label}：{text}\n"

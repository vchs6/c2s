"""固定自然语言表单规范化为现行来源选择器。"""
import re
def normalize_request(request: str) -> list[str]:
    """Map explicit natural-language query forms; preserve unsupported text as a gap key."""
    text = request.strip()
    if not text:
        return ["unrecognized:"]
    if any(term in text.lower() for term in ("classes", "class list", "有哪些类", "所有类", "类清单")):
        return ["classes"]
    member = (re.fullmatch(r"\s*members\s+of\s+(.+?)\s*", text, re.I)
              or re.fullmatch(r"(.+?)(?:的成员(?:有哪些)?|成员有哪些)[？?]?", text, re.I))
    if member:
        target = member.group(1).strip(" ：:，,")
        if target:
            return [f"members:{target}"]
    function = re.search(r"(?:函数|function)\s+([A-Za-z_][\w.:]*)", text, re.I)
    if function:
        return [f"function:{function.group(1)}"]
    if any(term in text.lower() for term in ("functions", "函数列表", "有哪些函数")):
        return ["functions"]
    return [f"unrecognized:{text}"]

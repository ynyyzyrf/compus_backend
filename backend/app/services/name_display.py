import re

from pypinyin import lazy_pinyin


_COMPOUND_SURNAMES = {"欧阳", "歐陽", "司马", "司馬", "上官", "诸葛", "諸葛", "司徒", "夏侯", "东方", "東方", "尉迟", "尉遲", "皇甫", "令狐", "公孙", "公孫", "慕容", "长孙", "長孫"}
_SURNAME_PINYIN = {"单": "shan", "單": "shan", "区": "ou", "區": "ou", "仇": "qiu", "曾": "zeng", "解": "xie", "查": "zha", "朴": "piao", "乐": "yue", "樂": "yue", "尉迟": "yuchi", "尉遲": "yuchi", "长孙": "zhangsun", "長孫": "zhangsun"}


def display_name_en(name: str, custom: str | None) -> str | None:
    if custom and custom.strip():
        return custom.strip()
    name = "".join(name.split())
    if name in {"未命名校友", "未命名用戶", "未命名用户"} or not re.fullmatch(r"[\u3400-\u9fff]+", name):
        return None
    surname_length = 2 if len(name) > 2 and name[:2] in _COMPOUND_SURNAMES else 1
    surname, given_name = name[:surname_length], name[surname_length:]
    family = _SURNAME_PINYIN.get(surname) or "".join(lazy_pinyin(surname))
    given = "".join(lazy_pinyin(given_name))
    result = " ".join(part for part in (given, family) if part).upper()
    return result if result.isascii() else None

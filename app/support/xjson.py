import orjson


def loads(s):
    if type(s) is str:
        return orjson.loads(s.encode(encoding='utf-8', errors="ignore"))
    return orjson.loads(s)


def dumps(obj):
    return orjson.dumps(obj).decode(encoding='utf-8', errors="ignore")

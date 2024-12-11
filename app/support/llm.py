
from typing import Generator, Union
import re
import tiktoken
from config.config import BASE_DIR
import os

tiktoken_cache_dir = os.path.join(BASE_DIR, "app/libs/tiktoken")
os.environ["TIKTOKEN_CACHE_DIR"] = tiktoken_cache_dir
# encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
encoder = tiktoken.get_encoding("cl100k_base")


def num_tokens_from_string(string: str) -> int:
    """Returns the number of tokens in a text string."""
    try:
        return len(encoder.encode(string))
    except Exception:
        return 0


def truncate(string: str, max_len: int) -> str:
    """Returns truncated text if the length of text exceed max_len."""
    return encoder.decode(encoder.encode(string)[:max_len])


def is_english(texts):
    eng = 0
    if not texts:
        return False
    for t in texts:
        if re.match(r"[ `a-zA-Z.,':;/\"?<>!\(\)-]", t.strip()):
            eng += 1
    if eng / len(texts) > 0.8:
        return True
    return False


def generator_wrapper(generator: Generator[Union[str, int], None, None]) -> Generator[dict, None, None]:
    last_value = ""
    for value in generator:
        if isinstance(value, int):
            yield dict(
                data=dict(
                    total_token=value,
                    content=last_value
                )
            )
        else:
            delta = value[len(last_value):]
            delta_prefix = "data: "
            if delta.startswith(delta_prefix):
                delta = delta[len(delta_prefix):]
            content = last_value + delta
            last_value = content
            yield dict(
                data=dict(
                    delta=delta,
                )
            )

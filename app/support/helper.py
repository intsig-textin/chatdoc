

from functools import wraps
import gzip
from io import BytesIO
import logging
import math
import time
import uuid
import base62

import numpy as np
import requests
from PIL import Image


def log_duration(prefix: str = ""):
    # 外层函数接受 prefix 参数
    def decorator(func):
        @wraps(func)
        def with_logging(*args, **kwargs):
            start_time = time.time()
            ret = func(*args, **kwargs)
            logging.info(f"[{prefix}{func.__name__}] duration: {(time.time() - start_time)*1000:.1f}ms")
            return ret
        return with_logging
    return decorator


def async_log_duration(prefix: str = ""):
    # 外层函数接受 prefix 参数
    def decorator(func):
        @wraps(func)
        async def with_logging(*args, **kwargs):
            start_time = time.time()
            ret = await func(*args, **kwargs)
            logging.info(f"[async, {prefix}{func.__name__}] duration: {(time.time() - start_time)*1000:.1f}ms")
            return ret
        return with_logging
    return decorator


def retry_exponential_backoff(max_retries=3, base_delay=1):
    def decorator(func):
        @ wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            func_name = func.__name__
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    wait_time = base_delay * (2 ** retries)
                    logging.warning(f"{func_name}请求失败，{wait_time}秒后重试...{e}")
                    logging.warning(f"{func_name}正在尝试第{retries + 1}次请求")
                    time.sleep(wait_time)
                    retries += 1
            logging.error(f'{func_name}达到最大重试次数，请求失败')
            raise Exception(f"{func_name}达到最大重试次数，请求失败")

        return wrapper

    return decorator


def uuid_base62():
    # 生成 UUID4
    uuid4_str = uuid.uuid4().hex  # 32 个十六进制字符

    # 将 UUID4 字符串转换为整数
    uuid_int = int(uuid4_str, 16)

    # 使用 pybase62 进行 Base62 编码
    short_str = base62.encode(uuid_int)

    return short_str


def batch_generator(iterator, batch_size):
    batch = []
    iterator = iter(iterator)
    try:
        while True:
            for _ in range(batch_size):
                batch.append(next(iterator))
            yield batch
            batch = []
    except StopIteration:
        if batch:  # 如果最后一个批次不足 batch_size 也返回
            yield batch


def split_list(input_list, chunk_size):
    """将列表input_list按照chunk_size拆分成多个子列表"""
    # 初始化空子列表的列表
    sublists = []
    # 遍历列表，步长为chunk_size
    for i in range(0, len(input_list), chunk_size):
        # 添加子列表到结果列表中
        sublists.append(input_list[i:i + chunk_size])
    return sublists


def softmax(x) -> list[float]:
    if not x:
        return []

    e_x = np.exp(x - np.max(x))  # 防止指数溢出
    return (e_x / np.sum(e_x)).tolist()


def sigmoid(x):
    try:
        return 1 / (1 + math.exp(-x))
    except OverflowError:
        # Handle the case where x is very large and exp(-x) might underflow to 0
        if x > 0:
            return 1.0
        else:
            return 0.0


def duplicates_list(items, item_func=lambda x: x):
    """
    简单列表去重
    """
    new_items = []
    new_set = set()

    for item in items:
        key = hash(item_func(item))
        if key not in new_set:
            new_set.add(key)
            new_items.append(item)

    return new_items


def group_by_func(entities: list[object], keyfunc: callable) -> list[tuple]:

    groups = []
    group_keys = []
    for entity in entities:
        index_value = keyfunc(entity)
        if index_value not in group_keys:
            groups.append((index_value, [entity]))
            group_keys.append(index_value)
        else:
            rindex = group_keys.index(index_value)
            groups[rindex][1].append(entity)

    return groups


def compress(data):
    json_bytes = data.encode('utf-8')
    buffer = BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
        f.write(json_bytes)
    return buffer.getvalue()


def convert_base64_to_webp(base64_stream):
    # 将字节加载为图像文件
    image = Image.open(BytesIO(base64_stream))

    # 创建一个内存中的输出流
    output_buffer = BytesIO()

    # 将图像保存为WebP格式到内存中的输出流
    image.save(output_buffer, format="WEBP")

    # 获取内存中输出流的内容
    webp_data = output_buffer.getvalue()

    return webp_data

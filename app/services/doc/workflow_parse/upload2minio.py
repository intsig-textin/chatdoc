import base64
from concurrent.futures import ThreadPoolExecutor
import logging
from math import inf
import traceback
from loguru import logger

from app.exceptions.http.doc import UploadFile2MinioException
from app.libs.textin_pic_download import TextinDownload
from app.schemas.doc import DocOriginSchema, Pdf2MdSchema
from app.services.doc.workflow_parse.schemas import Context
from app.support import xjson
from app.support.helper import compress, convert_base64_to_webp, log_duration
from app.libs.minio import MinioClient


@log_duration()
def upload2minio(context: Context) -> tuple[dict, str]:
    try:
        pdf2md_url = upload_pdf2md_result(context.file_uuid, context.pdf2md_result)
        pic_urls = upload_pics(context.file_uuid, context.pdf2md_result)
        cross_page_elements = get_cross_page_elements(context.origin_slices)
        return dict(
            pdf2md_url=pdf2md_url,
            pic_urls=pic_urls,
            toc=[item.model_dump() for item in context.catalog_tree.generate],
            cross_page_elements=cross_page_elements,
        ), pic_urls[0]

    except Exception as e:
        logging.error(f'upload2minio error: {e}, {traceback.format_exc()}')
        raise UploadFile2MinioException()


@log_duration(prefix="upload2minio_")
def upload_pdf2md_result(file_id, pdf2md_result: Pdf2MdSchema):
    def find_bounding_rectangle(rectangles):
        # 初始化边界值为无穷大或无穷小
        min_x = inf
        min_y = inf
        max_x = -inf
        max_y = -inf

        # 遍历每个矩形
        for rect in rectangles:
            # 每个矩形的坐标是按顺序排列的
            x1, y1, x2, y2 = rect[0], rect[1], rect[4], rect[5]

            # 更新边界值
            min_x = min(min_x, x1, x2)
            min_y = min(min_y, y1, y2)
            max_x = max(max_x, x1, x2)
            max_y = max(max_y, y1, y2)

        return [min_x, min_y, max_x, min_y, max_x, max_y, min_x, max_y]

    def update_page_structure(page):
        # 更新 structure的位置信息, 为所有content坐标的最大外接矩
        contents = page.get("content", [])
        for structured in page.get("structured", []):
            content_positions = [
                contents[content_id]["pos"] for content_id in structured.get("content", []) if isinstance(content_id, int)
            ]
            if content_positions and structured.get("type") == "textblock":
                structured["pos"] = find_bounding_rectangle(content_positions)

    [update_page_structure(page) for page in pdf2md_result.result.pages]
    object_name = f"pdf2md/{file_id}.gz"
    MinioClient().upload_content(object_name, compress(xjson.dumps(pdf2md_result.model_dump())))

    return object_name


@log_duration(prefix="upload2minio_")
def upload_pics(file_id, pdf2md_result: Pdf2MdSchema):

    def backup_img(file_id, page_idx, pic: Pdf2MdSchema.Metric):
        try:
            file_img_base64 = TextinDownload().download_textin_img(pic.image_id)
        except Exception as e:
            logger.error(f"download textin image {pic.image_id} error: {e}")
            raise e

        try:
            file_img_stream = base64.b64decode(file_img_base64)
            webp_bytes = convert_base64_to_webp(file_img_stream)
            object_name = f"pics/{file_id}_{page_idx}.webp"
            MinioClient().upload_content(object_name, webp_bytes)
        except Exception as e:
            logger.error(f"convert_base64_to_webp image {pic.image_id} error: {e}")
            object_name = f"pics/{file_id}_{page_idx}.png"
            MinioClient().upload_content(object_name, file_img_base64)

        return object_name

    object_names = []
    futures = []
    workers = min(len(pdf2md_result.metrics) + 1, 20)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for idx, pic in enumerate(pdf2md_result.metrics):
            futures.append(executor.submit(backup_img, file_id, idx, pic))

    for future in futures:
        object_names.append(future.result())

    return object_names


def get_cross_page_elements(origin_slices: list[DocOriginSchema]):

    def get_cross_page_slices(origin_slices: list[DocOriginSchema]) -> list[DocOriginSchema]:
        cross_page_slices = []
        for _slice in origin_slices:
            if not _slice.ori_ids:
                continue
            # 是否跨页
            curr_ori_id = _slice.ori_ids[0]
            first_page = curr_ori_id.split(",")[0]
            has_merge = False
            if len(_slice.ori_ids) > 1:
                for ori_id in _slice.ori_ids[1:]:
                    if not ori_id.startswith(first_page):
                        has_merge = True

            if has_merge:
                cross_page_slices.append(_slice)
                continue

            if _slice.type == "table":
                cross_page_slices.append(_slice)

        return cross_page_slices

    cross_page_elements = []
    for _slice in get_cross_page_slices(origin_slices):
        if _slice.type == "table":
            table_htmls = merge_table(_slice.content_html)
            html = table_htmls[0] if table_htmls else ""
        else:
            html = _slice.content_html

        cross_page_elements.append(dict(
            content=_slice.content_md,
            ori_ids=_slice.ori_ids,
            type=_slice.type,
            html=html
        ))

    return cross_page_elements


def merge_table(infos):
    """
    合并表格，合并逻辑为连续的表格进行合并
    :param lst:
    :return:
    """

    def end_id(i, infos):
        while i < len(infos) - 1:
            if """<table border="1">""" in infos[i] and """<table border="1">""" in infos[i + 1]:
                i += 1
            else:
                break
        return i

    result = []
    i = 0
    while i < len(infos):
        if """<table border="1">""" in infos[i]:
            j = end_id(i, infos)
            result.append("""<table border="1">"""
                          + "".join([r.replace("""<table border="1">""", "").replace("""</table>""", "") for r in infos[i:j + 1]])
                          + """</table>""")
            i = j + 1
        else:
            result.append(infos[i])
            i += 1
    return result

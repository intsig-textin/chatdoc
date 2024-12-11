import logging
import traceback
from typing import List

from app.exceptions.http.doc import GenTableSlicesException
from app.schemas.doc import DocOriginSchema, DocTableRowSchema

from app.services.doc.workflow_parse.schemas import Context
from app.support.helper import log_duration, uuid_base62
from app.support.transform import list2markdown, markdown2list


@log_duration()
def gen_table_slices(context: Context) -> List[DocTableRowSchema]:
    try:
        table_slices = [origin_slice for origin_slice in context.origin_slices if origin_slice.type == "table"]
        table_row_slices = []
        for table in table_slices:
            row_slices = extract_row_data_from_table(table)
            table_row_slices.extend(row_slices)

        return table_row_slices

    except Exception as e:
        logging.error(f'gen_table_slices error: {e}, {traceback.format_exc()}')
        raise GenTableSlicesException()


def extract_row_data_from_table(origin_table: DocOriginSchema) -> list[DocTableRowSchema]:
    """
    从普通表格中抽取并上报
    """
    row_data_list = []
    table_list = markdown2list(origin_table.content_md)

    title_row = []

    table_title = origin_table.titles[-1] if origin_table.titles else ""

    for row_idx, row_data in enumerate(table_list):
        if not row_data:
            # 跳过空行
            continue

        if not title_row:
            # 第一行非空行为标题
            title_row = row_data
            continue

        title_len, row_len = len(title_row), len(row_data)

        # row_data = [x if not is_financial_string(x) else "" for x in row_data]
        per_row_table = []
        # 补齐长度
        if row_len < title_len:
            per_row_table = [
                title_row,
                row_data + [""] * (title_len - row_len)
            ]

        elif row_len > title_len:
            per_row_table = [
                title_row + [""] * (row_len - title_len),
                row_data
            ]

        else:
            per_row_table = [
                title_row,
                row_data
            ]

        row_data_list.append(
            DocTableRowSchema(
                uuid=uuid_base62(),
                title=table_title,
                origin_slice_uuid=origin_table.uuid,
                row_id=row_idx,
                keywords=list(filter(lambda x: x, row_data)),
                embed_text=f"## {table_title} \n" + list2markdown(per_row_table)
            )
        )

    return row_data_list

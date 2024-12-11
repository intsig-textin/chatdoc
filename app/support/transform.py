import re
from bs4 import BeautifulSoup


def _html_to_list_info(html, encoding='utf-8'):
    def __get_cell_val(cell, encoding):
        text = cell.get_text(separator=' ').replace(' ', '').replace(',', '')  # bs4
        if not isinstance(text, str):
            text = text.encode(encoding)
        if text is None or text == " ":
            text = ""
        return text
    soup = BeautifulSoup(html, 'lxml')  # change html.parser to lxml
    table = []
    nb_col = 0
    nb_row = 0
    # Transform BF object to list 2d with metadata (text, colspan, rowspan)
    tr_list = soup.find_all('tr')
    for i_tr, tr in enumerate(tr_list):
        td_th_list = tr.find_all(re.compile(r'(td|th)'))
        table.append([])
        for cell in td_th_list:
            # Calculate rowspan and colspan
            colspan_val = 1
            rowspan_val = 1
            if 'colspan' in cell.attrs:
                colspan_val = int(cell.attrs['colspan'])
            if 'rowspan' in cell.attrs:
                rowspan_val = int(cell.attrs['rowspan'])
            cell_info = {'colspan': colspan_val, 'rowspan': rowspan_val, 'text': __get_cell_val(cell, encoding)}
            table[-1].append(cell_info)
        if len(td_th_list) > nb_col:
            nb_col = len(td_th_list)

    nb_row = len(tr_list)
    return table, nb_row, nb_col


def _html_info_to_text_list(table, nb_row, nb_col):
    def __add_cell(table, i_line, i_col, val, nb_line, nb_col):
        while len(table) <= i_line:
            table.append([])
            nb_line += 1
        # Repair table
        while len(table[i_line]) < i_col:
            table[i_line].append('')
        table[i_line].insert(i_col, val)
        if len(table[i_line]) > nb_col:
            nb_col = len(table[i_line])
        return nb_line, nb_col

    i_col = 0
    # Transform list 2d with metadata to a list of string
    # Split rowspan and colspan
    while i_col < nb_col:
        i_line = 0
        while i_line < nb_row:
            # Repair table
            while i_col >= len(table[i_line]):
                table[i_line].append('')
            cell = table[i_line][i_col]
            if type(cell) is not dict:
                i_line += 1
                continue
            for i_colspan in range(i_col, i_col + cell['colspan']):
                for i_rowspan in range(i_line, i_line + cell['rowspan']):
                    if i_colspan == i_col and i_rowspan == i_line:
                        continue
                    # 合并单元格拆分
                    # nb_row, nb_col = __add_cell(table, i_rowspan, i_colspan, cell['text'], nb_row, nb_col)
                    # 不拆分
                    nb_row, nb_col = __add_cell(table, i_rowspan, i_colspan, "", nb_row, nb_col)
            # Update cell value to string
            table[i_line][i_col] = cell['text']
            i_line += 1
        i_col += 1
    return table


def html2list(html, encoding='utf-8') -> list:
    """
    Transform a HTML table to a list of 2 dimensions
    Split values of colspan and rowspan
    Repair table (maybe not stable)
    Note : Untested with a lot of encoding
    :param html: html code
    :type html: str
    :param encoding: document encoding
    :rtype encoding: str
    :rtype: list[list[str]]
    """

    table, nb_row, nb_col = _html_to_list_info(html, encoding=encoding)

    return _html_info_to_text_list(table, nb_row, nb_col)


def list2markdown(table_list) -> str:
    markdown = ""
    for ind, row in enumerate(table_list):
        if ind == 0:
            markdown += "|" + "|".join(str(cell) for cell in row) + "|" + "\n" + "|" + "-|" * len(row) + "\n"
        else:
            markdown += "|" + "|".join(str(cell) for cell in row) + "|" + "\n"
    return markdown


def uneven_list_to_markdown_table(data, fill_value=""):
    """
    将长度不一致的二维列表转换为Markdown格式的表格，使用指定的值填充缺失项。

    :param data: 二维列表，表示表格数据，行长度可以不一致。
    :param fill_value: 用于填充缺失单元格的值，默认为空字符串。
    :return: Markdown格式的表格字符串。
    """
    # 找到最长的子列表长度
    max_length = max(len(row) for row in data)

    # 填充较短的行
    padded_data = [row + [fill_value] * (max_length - len(row)) for row in data]

    return list2markdown(padded_data)


def markdown2list(table_markdown) -> list:
    table_lists = []
    table_list = table_markdown.split("\n")
    tmp_lists = [i.split("|")[1:-1] for i in table_list]
    for ind, info in enumerate(tmp_lists):
        if ind != 1:
            table_lists.append(info)
    return table_lists


def html2markdown(html, encoding='utf-8') -> str:
    lst = html2list(html, encoding)
    return list2markdown(lst)


def financial_string_to_number(s):
    """
    将包含千位分隔符和可能的货币符号的金融数字字符串转换为浮点数。

    参数:
    s (str): 金融数字字符串，例如 "$1,234.56" 或 "1.234,56 €"

    返回:
    float: 转换后的数值

    # 示例
    print(financial_string_to_number("$1,234.56"))  # 输出: 1234.56
    print(financial_string_to_number("1.234,56 €"))  # 输出: 1234.56
    """
    # 去除可能的货币符号（这里简单示例去除了$和€，根据实际情况可能需要调整）
    s = s.replace("$", "").replace("€", "").replace("￥", "")

    # 替换千位分隔符，这里假设千位分隔符可能是逗号或点，根据具体情况调整
    s = s.replace(",", "").replace(".", "")

    # 根据原字符串判断是否有小数点，并正确还原
    if ',' in s:  # 如果原字符串中有千位分隔符，且已被替换，则认为小数点被保留下来
        return float(s)
    else:  # 否则，合理假设最后一个点为小数点
        return float(s.replace(".", "", 1))  # 仅替换第一个点，保留可能的小数部分


def is_financial_string(s):
    try:
        financial_string_to_number(s)
        return True
    except ValueError:
        return False

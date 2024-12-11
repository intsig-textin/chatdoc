import gradio as gr
import requests
import json

from requests import HTTPError


# 获取文件数据
def fetch_files(api_url):
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        return response.json().get("files", [])
    except Exception:
        return []

# 全局问答接口


def files_stream_answer(question, file_ids):
    url = "http://localhost:8000/api/v1/chat/files"
    headers = {
        "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
        "Content-Type": "application/json",
        "Accept": "*/*",
    }
    payload = {
        "question": question,
        "file_ids": file_ids,
        "stream": True
    }

    # 发起流式请求
    response = requests.post(url, json=payload, headers=headers, stream=True)
    response.raise_for_status()  # 如果请求失败则抛出异常

    answer = ""
    retrieval_results = []

    # 逐步解析响应内容
    for chunk in response.iter_content(chunk_size=None):
        if chunk:
            # 解码每个数据块
            raw_chunk = chunk.decode("utf-8")
            json_part = raw_chunk.strip("data: ").strip() if raw_chunk.startswith("data: ") else raw_chunk

            try:
                json_data = json.loads(json_part).get("data", {})
                # 更新回答内容
                if "delta" in json_data and json_data["delta"]:
                    answer += json_data["delta"]

                # 处理召回结果
                if "retrieval" in json_data:
                    retrieval_results = [
                        f"## retrieval_type: {r['retrieval_type']}\n"
                        + f"## file_id: {r['file_id']}\n"
                        + f"## tree_text: \n{r['tree_text']}\n"
                        for r in json_data["retrieval"]
                    ]

                # 实时返回
                yield answer, "\n\n**********Next************\n\n".join(retrieval_results) if retrieval_results else "No retrieval results."
            except Exception as e:
                print(json_part, e)
                continue


# 文件问答接口

def qa_with_files(question, file_df):
    answer = ""
    retrieval = ""
    if not question:
        return gr.update(value="<div style=\"color: red font-weight: bold;\">⚠️ 请输入问题！</div>", visible=True), "", ""
    if file_df.empty:
        return gr.update(value="<div style=\"color: red font-weight: bold;\">⚠️ 请先选择文件！</div>", visible=True), "", ""
    file_ids = file_df["文件id"].tolist()
    for part_answer, part_retrieval in files_stream_answer(question, file_ids):
        answer = part_answer
        retrieval = part_retrieval
        yield gr.update(value="", visible=False), answer, retrieval


def global_stream_answer(question):
    url = "http://localhost:8000/api/v1/chat/global"
    headers = {
        "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
        "Content-Type": "application/json",
        "Accept": "*/*",
    }
    payload = {
        "question": question,
        "stream": True
    }

    # 发起流式请求
    response = requests.post(url, json=payload, headers=headers, stream=True)
    response.raise_for_status()  # 如果请求失败则抛出异常

    answer = ""
    retrieval_results = []

    # 逐步解析响应内容
    for chunk in response.iter_content(chunk_size=None):
        if chunk:
            # 解码每个数据块
            raw_chunk = chunk.decode("utf-8")
            json_part = raw_chunk.strip("data: ").strip() if raw_chunk.startswith("data: ") else raw_chunk

            try:
                json_data = json.loads(json_part).get("data", {})
                # 更新回答内容
                if "delta" in json_data and json_data["delta"]:
                    answer += json_data["delta"]

                # 处理召回结果
                if "retrieval" in json_data:
                    retrieval_results = [
                        f"## retrieval_type: {r['retrieval_type']}\n"
                        + f"## file_id: {r['file_id']}\n"
                        + f"## tree_text: \n{r['tree_text']}\n"
                        for r in json_data["retrieval"]
                    ]

                # 实时返回
                yield answer, "\n\n**********Next************\n\n".join(retrieval_results) if retrieval_results else "No retrieval results."
            except Exception as e:
                print(json_part, e)
                continue


def global_qa(question):
    answer = ""
    retrieval = ""
    if not question:
        return gr.update(value="<div style=\"color: red font-weight: bold;\">⚠️ 请输入问题！</div>", visible=True), "", ""
    for part_answer, part_retrieval in global_stream_answer(question):
        answer = part_answer
        retrieval = part_retrieval
        yield gr.update(value="", visible=False), answer, retrieval

# 文件上传接口


def upload_file(file, api_url="http://localhost:8000/api/v1/doc/parse"):
    try:
        with open(file, "rb") as f:
            response = requests.post(api_url, files={"file": f})
            response.raise_for_status()
            return f"上传成功：{response.json()}"
    except HTTPError:
        return f"上传成功：{response.json()}"
    except Exception as e:
        return f"上传失败：{e}"


def post_delete_file(file_id, api_url="http://localhost:8000/api/v1/doc/{file_id}"):
    api_url = api_url.format(file_id=file_id)
    try:
        response = requests.delete(api_url)
        response.raise_for_status()
        return True, f"删除成功：{response.json()}"
    except Exception as e:
        return False, f"删除失败：{e}"


def go_to_qa(file_names):
    """
    将选中的文件值传递到目标 Tab 中的多选框
    """
    if not file_names:
        # 提示信息
        return gr.update(value="<div style=\"color: red font-weight: bold;\">⚠️ 请先选择文件！</div>", visible=True), gr.update(selected="upload"), []

    file_datas = [file_mapper[fn] for fn in file_names]
    return gr.update(value="", visible=False), gr.update(selected="qa"), file_datas


def delete_files(file_names):
    if not file_names:
        # 提示信息
        return gr.update(value="<div style=\"color: red font-weight: bold;\">⚠️ 请先选择文件！</div>", visible=True), None

    file_datas = [file_mapper[fn] for fn in file_names]
    for _, file_id, _, _ in file_datas:
        success, msg = post_delete_file(file_id)
        if not success:
            return gr.update(value=msg, visible=True), gr.update(value="重新筛选", interactive=True)

    return gr.update(value="删除成功", visible=True), gr.update(value="重新筛选", interactive=True)


# 主界面
with gr.Blocks() as demo:
    gr.Markdown("# 文件管理与问答系统")

    with gr.Tabs() as tabs:
        # 全局问答 Tab
        with gr.Tab("全局问答", id="global_qa"):
            with gr.Row():
                global_question_input = gr.Textbox(label="问题", placeholder="请输入您的问题")
            global_ask_button = gr.Button("开始问答")
            global_qa_message_box = gr.Markdown(label="提示信息", visible=True)
            global_output_answer = gr.Textbox(label="回答", lines=5, interactive=False)
            # 动态生成召回结果框
            global_output_retrievals = gr.Textbox(label="召回结果", lines=10, interactive=False, elem_id="global_output_retrievals")

        with gr.Tab("文件管理", id="file_management"):
            with gr.Row():
                # api_url_input = gr.Textbox(label="文件接口 URL", value="http://localhost:8000/api/v1/chat/files", interactive=True)
                filter_input = gr.Textbox(label="筛选文件名", placeholder="输入关键字筛选", interactive=True)
            with gr.Row():
                refresh_button = gr.Button("刷新文件列表")

            # 文件列表区域
            file_list = gr.DataFrame(headers=["文件名", "文件id", "类型", "日期"], interactive=False)
            selected_files = gr.CheckboxGroup(label="选择文件", choices=[], value=[], interactive=True)
            # 刷新文件列表
            file_mapper = {}

            def update_file_list(filter_keyword):
                files = fetch_files("http://localhost:8000/api/v1/doc/files")
                if filter_keyword:
                    files = [f for f in files if filter_keyword in f["file_name"] or filter_keyword in f["file_id"]]
                file_table = [[f["file_name"], f["file_id"], f["file_name"].split(".")[-1], f["created_at"]] for f in files]
                file_names = [f["file_name"] + " | " + f["file_id"] for f in files]
                for fn, ft in zip(file_names, file_table):
                    file_mapper[fn] = ft
                # 使用 gr.update 来更新 File 的内容
                return file_table, gr.update(choices=file_names)

            refresh_button.click(
                update_file_list, inputs=[filter_input], outputs=[file_list, selected_files]
            )

            go_to_qa_button = gr.Button("去问答")
            go_to_delete_button = gr.Button("删除文件")

            # 提示信息组件（初始隐藏）
            message_box = gr.HTML(label="提示信息")

        # 问答 Tab
        with gr.Tab("问答", id="qa"):
            with gr.Row():
                question_input = gr.Textbox(label="问题", placeholder="请输入您的问题")

            with gr.Row():
                qa_file_list = gr.DataFrame(headers=["文件名", "文件id", "类型", "日期"], interactive=False)

            ask_button = gr.Button("开始问答")
            qa_message_box = gr.Markdown(label="提示信息", visible=True)

            # 输出答案框
            output_answer = gr.Textbox(label="回答", lines=5, interactive=False)
            # 动态生成召回结果框
            output_retrievals = gr.Textbox(label="召回结果", lines=10, interactive=False, elem_id="output_retrievals")

        # 文件管理 Tab
        with gr.Tab("上传文件", id="file_upload"):
            # 上传文件区域
            with gr.Row():
                # upload_file_input = gr.File(label="上传文件", type="binary")
                upload_file_input = gr.File(label="上传文件", type="filepath")
                upload_button = gr.Button("上传文件")

            # 提示信息组件（初始隐藏）
            upload_message_box = gr.Textbox(label="上传响应", interactive=False)
            # 上传文件
            upload_button.click(
                upload_file, inputs=[upload_file_input], outputs=[upload_message_box]
            )

        # 全局问答
        global_ask_button.click(
            fn=global_qa,
            inputs=global_question_input,
            outputs=[global_qa_message_box, global_output_answer, global_output_retrievals]
        )

        # 按钮点击事件
        go_to_qa_button.click(
            fn=go_to_qa,
            inputs=selected_files,  # 获取选中的文件值
            outputs=[message_box, tabs, qa_file_list]  # 更新目标 Tab 的多选框和切换 Tab
        )

        go_to_delete_button.click(
            fn=delete_files,
            inputs=[selected_files],  # 获取选中的文件值
            outputs=[message_box, refresh_button]  # 更新目标 select_files 的多选框和切换 Tab
        )

        # 提交问题触发问答
        ask_button.click(
            fn=qa_with_files,
            inputs=[question_input, qa_file_list],
            outputs=[qa_message_box, output_answer, output_retrievals]
        )


demo.launch(server_name="0.0.0.0", share=True)

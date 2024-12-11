# chatdoc

## 目录
- [项目简介](#项目简介)
- [快速开始](#安装)
- [QA](#使用方法)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 项目简介
### 💡chatdoc是什么？
chatdoc是一款基于[TextIn ParseX](https://www.textin.com/market/detail/pdf_to_markdown)解析服务构建的开源RAG(Retrieval-Augmented-Generation)引擎。支持解析多种文件格式，为企业和个人轻松打造知识库，通过结合知识检索与大语言模型(LLM)技术，提供可靠的知识问答以及答案溯源功能。

### 👉产品体验
请登陆网址(https://www.textin.com/product/textin_intfinq)

### ⭐️主要功能
- 基于[TextIn ParseX](https://www.textin.com/market/detail/pdf_to_markdown),提供通用文档解析服务，一个接口，支持PDF/Word(doc/docx)、常见图片(jpg/png/webp/tiff)、HTML等多种文件格式。一次请求，即可获取文字、表格、标题层级、公式、手写字符、图片信息
- 支持单文档、多文档、知识库全局问答
- 支持前端高亮展示检索原文

### 🚩[acge](https://www.textin.com/market/detail/acge_text_embedding)文本向量模型
- 自研文本向量模型[acge](https://www.textin.com/market/detail/acge_text_embedding)，为检索精度提供保障
- 提供接口调用方式，本地无需显卡资源
- 本地部署调用请参考[此链接](https://github.com/intsig-textin/acge_text_embedding)

### 🌱文档目录树切片策略
- 文本、表格、标题分别处理，应对各类复杂场景
- 标题层级递归切片，保留文档内在逻辑结构的完整性
- small2big兼顾检索准确性与语义完整性，保证答案全面

### 🍱有理有据、减少幻觉
- 多路召回、融合排序等，丰富搜索信息
- 答案溯源，确保答案准确性

## 系统架构(未完待续...)


## 快速开始(未完待续...)
### 🔨︎克隆仓库

### 🔮系统配置


### 📝技术文档

## QA

## 贡献指南
欢迎贡献代码！在开始之前，请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 以了解贡献流程和指南。

## 许可证
此项目基于 [CC-NC License](LICENSE) 进行许可。
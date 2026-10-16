# AI 分析模块

本目录是共用 Python 模块，由后端和 worker 导入；没有独立监听端口。配置、运行方式与依赖安装统一由 [后端](../backend/README.md) 管理。

| 文件 | 中文标注 |
|---|---|
| `ai_service/taxonomy.py` | 统一定义政治、金融、科技、AI 四领域及中国/国际两区域 |
| `ai_service/classifier.py` | 规则预分类与候选重要程度评分 |
| `ai_service/prompt.py` | 中文分析提示词，要求区分原文事实、影响推断和条件情景 |
| `ai_service/schemas.py` | Pydantic 输出结构与字段校验 |
| `ai_service/analyzer.py` | 调用模型接口、重试、校验和来源摘要回退 |

采集正文来自 RSS 的标题与摘要，不等于获取了文章完整内容。模型输入包含来源信息，输出经结构校验后再进入日报。分类包括 `politics`、`finance`、`technology`、`ai`；不相关内容可标为 `other` 并被发布流程排除。

AI 领域覆盖大模型、机器学习、智能体、AI 产品、AI 产业与监管；以 AI 为主体的芯片或融资归 AI。一般芯片、软件、新能源和网络安全归科技。每条新闻进入一个领域，规则或模型分类可能出错，读者仍可查看原始来源核对。

在项目根 `.env` 配置 `AI_BASE_URL`、`AI_MODEL`，并按供应商要求配置 `AI_API_KEY`。接口适配使用 `/chat/completions`。不设置模型时标记为 `extractive`；请求或输出校验失败时标记为 `fallback`；只有校验通过的模型结果标为 `ai`。

每栏最多 10 条由 [后端配置](../backend/app/config.py) 和 [日报流程](../backend/app/pipeline.py) 控制，前端不负责凑满数量。默认每格预选 20 条、八格最多 160 个候选参与整理，最终最多发布 80 条。

分析缓存包含内容、模型服务和提示词版本。变更提示词语义时应更新 `PROMPT_VERSION`，避免直接使用旧规则生成的分析。回归测试位于 `backend/tests/test_ai.py`、`test_ai_category.py` 和 `test_pipeline.py`。

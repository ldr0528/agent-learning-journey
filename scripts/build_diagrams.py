"""Generate the handbook's original overview diagrams with the standard library.

Run from any directory: python scripts/build_diagrams.py.
SVG text remains editable; visual QA should follow regeneration.
"""

from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INK = "#20293A"
MUTED = "#6B7585"
LINE = "#D9DFE8"
BLUE = "#3867D6"
GREEN = "#27816C"
ORANGE = "#B36535"


def text(x, y, value, size=20, color=INK, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(value)}</text>')


def line(x1, y1, x2, y2, color=LINE, arrow=False, dashed=False):
    marker = ' marker-end="url(#arrow)"' if arrow else ""
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    return f'<path d="M{x1} {y1}L{x2} {y2}" fill="none" stroke="{color}" stroke-width="1.6"{marker}{dash}/>'


def path(d, color=BLUE):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6" marker-end="url(#arrow)"/>'


def box(x, y, w, title, detail, color=BLUE, height=90):
    fill = "#F5F8FF" if color == BLUE else "#F3FAF7" if color == GREEN else "#FFFFFF"
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{height}" rx="7" '
            f'fill="{fill}" stroke="{LINE}" stroke-width="1.5"/>'
            + text(x + 18, y + 34, title, 23, color, 600)
            + text(x + 18, y + 65, detail, 17, MUTED))


def write(name, title, subtitle, body, height=760):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{height}" '
           f'viewBox="0 0 1280 {height}" role="img" aria-labelledby="title desc">'
           f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc>'
           '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" '
           'markerUnits="userSpaceOnUse"><path d="M0 0L7 4L0 8" fill="none" stroke="#798596" '
           'stroke-width="1.4"/></marker></defs>'
           f'<rect width="1280" height="{height}" fill="white"/>'
           '<g font-family="Segoe UI, Microsoft YaHei, sans-serif">'
           + text(48, 35, "AGENT LEARNING JOURNEY  /  ORIGINAL DIAGRAM", 12, MUTED, 600)
           + text(48, 80, title, 30, INK, 600)
           + text(48, 113, subtitle, 18, MUTED)
           + line(48, 140, 1232, 140)
           + "".join(body) + "</g></svg>\n")
    (ROOT / "docs/assets" / name).write_text(svg, encoding="utf-8")


def course_map():
    body = []
    columns = [
        (64, "01—04", "模型、工具与循环", ["请求 · 工具回传", "有限循环 · 来源引用"], "消息轨迹表"),
        (370, "05—07", "上下文与任务组织", ["状态 · 历史与预算", "规划 · 评审与修订"], "计划与修订对照"),
        (676, "08—09", "检索与质量", ["切分 · 检索 · 证据", "引用 · 评估与失败分析"], "带来源的回答"),
        (982, "10—11", "框架与协议", ["LangGraph · 状态流转", "MCP · 跨进程工具"], "节点与通信表"),
    ]
    for index, (x, number, title, items, outcome) in enumerate(columns):
        body.extend([text(x, 194, number, 17, BLUE, 600), text(x, 234, title, 22, INK, 600)])
        for row, item in enumerate(items):
            body.append(text(x, 283 + row * 34, item, 19, MUTED))
        body.extend([line(x, 341, x + 234, 341), text(x, 377, outcome, 21, GREEN, 600)])
        if index < 3:
            body.append(line(x + 244, 227, x + 291, 227, BLUE, True))
    body.extend([
        line(64, 413, 1216, 413),
        text(64, 457, "实践主线", 18, GREEN, 600),
        text(210, 457, "模拟天气看清机制；本地资料问答练习证据；研究任务连接迁移练习。", 21),
    ])
    write("learning-path-zh.svg", "课程路线 · 从理解机制到完成实践", "11 章，四个阶段。先解释，再修改，最后用证据检查结果。", body, 500)


def architecture():
    body = [
        text(64, 198, "阅读与运行入口", 18, MUTED, 600),
        box(64, 220, 335, "手册正文", "docs / learning · 原理与结果"),
        box(474, 220, 335, "章节示例", "examples · 参数与运行模式"),
        box(884, 220, 332, "验证与报告", "tests · scripts · evaluation", GREEN),
        line(640, 310, 640, 362, BLUE, True),
        text(64, 365, "任务组织", 18, MUTED, 600),
        box(64, 386, 335, "逐轮决策", "天气 / 基础 Research Agent"),
        box(474, 386, 335, "计划与修订", "Plan-and-Solve / Reflection"),
        box(884, 386, 332, "证据问答", "检索 → 证据 → 回答与引用", GREEN),
        line(232, 476, 232, 536, BLUE, True), line(642, 476, 642, 536, BLUE, True),
        line(1050, 476, 1050, 536, GREEN, True),
        box(64, 548, 335, "运行控制", "消息 · 上下文 · 预算 · 停止", GREEN),
        box(474, 548, 335, "模型接入", "配置 → 一次请求 → 文本回复"),
        box(884, 548, 332, "工具与资料", "模拟天气 · 本地语料 · 来源", GREEN),
        line(64, 686, 1216, 686),
        text(64, 730, "可选集成", 18, GREEN, 600),
        text(210, 730, "LangGraph 表达流程与状态；MCP 连接客户端与工具服务端。", 21),
        text(64, 775, "核心机制通过函数组合；框架与协议层复用模型接入和工具。", 18, MUTED),
    ]
    write("architecture-zh.svg", "项目架构 · 课程、任务与底层能力", "示例组织输入；任务控制流程；工具和模型提供能力；检查独立验证结果。", body, 830)


def planning_reflection():
    body = [text(64, 196, "PLAN-AND-SOLVE  /  先制定计划，再依次执行", 18, BLUE, 600)]
    for x, title, detail, color in [(64, "原始问题", "目标与已知条件", BLUE), (366, "规划器", "一次请求生成步骤列表", BLUE),
                                   (668, "执行当前步骤", "计划 + 历史结果 + 本步", BLUE), (970, "记录结果", "供后续步骤使用", GREEN)]:
        body.append(box(x, 232, 246, title, detail, color))
    for x in (310, 612, 914):
        body.append(line(x, 277, x + 49, 277, BLUE, True))
    body.extend([path("M1093 322V384H791V328", GREEN), text(818, 372, "还有步骤且预算足够", 17, GREEN),
                 text(64, 409, "全部步骤完成 → 返回最终结果；预算耗尽 → 保留已完成部分并说明未完成。", 18, MUTED),
                 line(64, 456, 1216, 456), text(64, 506, "REFLECTION  /  依据反馈，有限次地修订", 18, BLUE, 600),
                 box(64, 608, 278, "初始回答", "围绕原问题生成草稿"),
                 box(501, 608, 278, "评审", "给出通过或修改建议", GREEN),
                 box(938, 608, 278, "修订", "使用草稿与评审反馈"),
                 line(342, 651, 493, 651, BLUE, True), line(779, 651, 930, 651, BLUE, True),
                 text(797, 617, "需修改", 17, MUTED), text(797, 640, "预算足够", 17, MUTED),
                 path("M1077 608V555H640V600", GREEN), text(719, 544, "修订后再次评审", 17, GREEN),
                 line(640, 698, 640, 766, GREEN, True), text(660, 741, "通过", 17, GREEN),
                 box(501, 778, 278, "结束", "标明是否通过评审", GREEN),
                 text(64, 920, "达到预算上限 → 保留草稿并标未通过；评审通过仍需外部事实或测试核验。", 18, MUTED)])
    write("planning-reflection-zh.svg", "两种任务组织方式 · 计划执行与评审修订", "流程中的每次模型请求都计入预算；中间产物由程序保存并回传。", body, 970)


def rag_evaluation():
    body = [text(64, 198, "离线准备", 18, GREEN, 600),
            box(64, 228, 290, "资料与出处", "教学语料 · 来源链接", GREEN),
            box(464, 228, 290, "切分与编号", "段落 / 片段 / 可追溯标识", GREEN),
            box(864, 228, 352, "检索索引", "本课程基线：词法相关性", GREEN),
            line(354, 273, 456, 273, GREEN, True), line(754, 273, 856, 273, GREEN, True),
            text(64, 385, "处理问题", 18, BLUE, 600),
            box(64, 414, 246, "用户问题", "明确研究目标"),
            box(366, 414, 246, "检索", "返回排名与来源片段", GREEN),
            box(668, 414, 246, "组织证据", "选中内容与引用编号", GREEN),
            box(970, 414, 246, "回答与报告", "依据证据 · 标注来源"),
            line(310, 459, 358, 459, BLUE, True), line(612, 459, 660, 459, GREEN, True),
            line(914, 459, 962, 459, BLUE, True), path("M1040 318V354H489V406", GREEN),
            line(64, 565, 1216, 565), text(64, 607, "分别评估", 18, MUTED, 600),
            box(64, 632, 352, "检索质量", "相关资料是否命中、排在哪里", GREEN),
            box(464, 632, 352, "引用与覆盖", "引用能否追溯、主张是否标注", GREEN),
            box(864, 632, 352, "答案质量", "人工核对事实与证据支持", BLUE),
            text(64, 770, "检索分数、引用合法和答案正确是不同判断；没有证据时要明确说明。", 18, MUTED)]
    write("rag-evaluation-zh.svg", "RAG 与评估 · 从资料到可追溯回答", "先构造证据，再生成回答；用固定问题分别检查检索与生成。", body, 820)


def framework_protocol():
    body = [text(64, 198, "LANGGRAPH  /  用图组织状态与节点", 18, BLUE, 600),
            box(64, 228, 290, "understand", "准备查询词"),
            box(464, 228, 290, "search", "读取本地资料", GREEN),
            box(864, 228, 352, "answer", "根据返回证据作答"),
            line(354, 273, 456, 273, BLUE, True), line(754, 273, 856, 273, GREEN, True),
            text(64, 365, "State 在节点间传递；检查点示例保存进程内快照。天气循环另用条件边决定继续或结束。", 18, MUTED),
            line(64, 407, 1216, 407), text(64, 458, "MCP  /  客户端与工具服务端的实际通信", 18, BLUE, 600),
            box(64, 501, 290, "MCP 客户端", "会话与请求"),
            box(464, 501, 290, "stdio 通道", "跨进程传输", GREEN),
            box(864, 501, 352, "MCP 服务端", "注册工具并执行本地函数", GREEN),
            line(354, 545, 456, 545, BLUE, True), line(754, 545, 856, 545, BLUE, True),
            path("M1040 591V666H209V599", GREEN), text(471, 653, "工具结果返回客户端", 18, GREEN),
            text(64, 725, "initialize  →  list_tools  →  call_tool", 22, INK, 600),
            text(64, 770, "协议负责发现与调用；工具负责具体工作；模型是否参与决策由应用决定。", 18, MUTED)]
    write("framework-protocol-zh.svg", "框架与协议 · 两种不同职责", "LangGraph 表达执行流程；MCP 让工具能力通过标准会话被调用。", body, 820)


def evidence_checks():
    body = []
    gates = [(64, "01  检索命中", "词语相关，能找到候选", GREEN),
             (360, "02  纳入上下文", "预算内选入模型请求", GREEN),
             (656, "03  引用合法", "编号来自本轮证据", GREEN),
             (952, "04  语义支持", "结论没有越过证据", BLUE)]
    for x, title, detail, color in gates:
        body.append(box(x, 208, 264, title, detail, color))
    for x in (328, 624, 920):
        body.append(line(x, 253, x + 24, 253, BLUE, True))
    body.extend([text(64, 356, "前三项可做程序检查；最后一项还需要逐条读证据、看限定条件。", 21),
                 line(64, 395, 1216, 395), text(64, 447, "案例  /  RAG 为什么要保留来源与引用？", 20, BLUE, 600),
                 box(64, 478, 545, "D08-C01 · 资料中的要求", "只引用实际纳入上下文的资料；仍需核对语义。", GREEN),
                 box(671, 478, 545, "模型回答 · 需要审慎理解的词", "“确保”生成的回答仅基于上下文证据。", BLUE),
                 line(609, 523, 663, 523, BLUE, True),
                 text(64, 621, "引用编号存在 ≠ 已证明“确保”。", 25, ORANGE, 600),
                 text(64, 665, "这一句可表达设计目标，但保留来源本身不能保证模型绝不引入外部信息。", 20),
                 text(64, 705, "阅读顺序：找到编号 → 对照原句 → 检查因果与强弱 → 给出判读。", 19, MUTED),
                 text(64, 774, "检查结论是否比资料说得更强，尤其关注因果、范围和保证性措辞。", 17, MUTED)])
    write("evidence-checks-zh.svg", "从检索命中到结论可信 · 四个检查点", "排序、上下文、引用编号和语义支持，需要分别判断。", body, 820)


def mcp_model_roundtrip():
    body = [box(64, 190, 292, "模型", "原生 tool_calls / 最终文本"),
            box(494, 190, 292, "Python 应用", "模型 API + MCP 客户端", GREEN),
            box(924, 190, 292, "MCP 服务端", "子进程中的本地工具", GREEN)]
    for x in (210, 640, 1070):
        body.append(line(x, 280, x, 1020, LINE, dashed=True))
    steps = [(640, 1070, 330, "initialize / list_tools", GREEN),
             (1070, 640, 390, "返回工具名与参数 schema", GREEN),
             (640, 210, 475, "请求 1：问题 + 工具定义", BLUE),
             (210, 640, 535, "tool_calls：weather（北京）", BLUE),
             (640, 1070, 595, "call_tool：weather（北京）", GREEN),
             (1070, 640, 655, "返回模拟天气：12℃", GREEN),
             (640, 210, 740, "请求 2：加入 role=tool 结果", BLUE)]
    for x1, x2, y, label, color in steps:
        body.extend([line(x1, y, x2, y, color, True), text((x1+x2)/2, y-15, label, 18, color, anchor="middle")])
    body.extend([f'<rect x="64" y="790" width="1152" height="66" rx="7" fill="#F3FAF7" stroke="{LINE}"/>',
                 text(640, 830, "模型再请求上海 → MCP 实际执行 → 返回模拟天气 22℃", 21, GREEN, anchor="middle"),
                 line(640, 915, 210, 915, BLUE, True), text(425, 900, "请求 3：携带两地工具结果", 18, BLUE, anchor="middle"),
                 line(210, 985, 640, 985, BLUE, True), text(425, 970, "最终文本：上海更暖和", 18, BLUE, anchor="middle"),
                 line(64, 1050, 1216, 1050),
                 text(64, 1096, "3 次模型请求，2 次 MCP 工具调用。", 23, INK, 600),
                 text(64, 1137, "tool_call_id 将结果关联到对应的工具请求；MCP 会话负责另一层通信。", 19, MUTED),
                 text(64, 1174, "模型无需直接连接 MCP 服务端；Python 应用负责发现、映射、执行与回传。", 19, MUTED)])
    write("mcp-model-roundtrip-zh.svg", "MCP 工具回传 · 模型与程序各做什么", "应用将模型的工具请求转换为 MCP 调用，再把结果送回下一轮消息。", body, 1220)


if __name__ == "__main__":
    course_map()
    architecture()
    planning_reflection()
    rag_evaluation()
    framework_protocol()
    evidence_checks()
    mcp_model_roundtrip()
    print("已生成 7 张原创课程 SVG。")

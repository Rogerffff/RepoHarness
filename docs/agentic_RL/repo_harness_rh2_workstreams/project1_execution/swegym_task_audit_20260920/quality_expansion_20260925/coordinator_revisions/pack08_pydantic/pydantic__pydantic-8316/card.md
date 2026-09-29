# 8316 静态短卡

目标是 `to_snake('HTTPResponse') == 'http_response'`，base `20c0c6d9219e29a95f5e1cadeb05ec39d8c15c24`。建议 `needs_review/static_review`、`development_diagnostic`；主目标清楚，数字边界兼容性待核。

| 要求/旧行为 | 依据/断言 | 判断 |
|---|---|---|
| 缩写接正常词分隔 | 题面HTTPResponse；唯一新增CAMELToSnake参数 | 同类局部覆盖，原例及更多字符串未直接验 |
| 旧数字/下划线转换 | 17个旧to_snake参数 | 全读并见PASS，但数字前都小写 |
| 大写接数字旧规则 | base `[a-zA-Z]`，gold收窄`[a-z]` | A1 a_1→a1、API2 api_2→api2静态可证；精确兼容契约待确认 |

完整读gold四条正则、helper和alias实际调用者。数字变化可传播到模型validation/serialization alias；保旧数字规则并补缩写边界是合理非gold路线，未见形状强制。题面to_camel附注可由公开ConfigDict原名/别名语义消解，不需要依赖旧记录转述的维护者hints；不可泛化为任意输入key归一化要求。

原install-v1两次安装RC0；noop158 passed/1 failed/14 skipped，gold159 passed/14 skipped；143个expected P2P均PASS。完整语义审查为38项旧alias转换，其他utility仅核状态。初态pyproject/pdm.lock差异、命令/镜像/可信恢复见前稿。实际actor输入、工作树、资产/权限/PATH/依赖/网络/资源unknown；合法源码可投影，控制面与留出重叠未穷审。审查者私有/历史暴露与actor泄漏unknown分开。

旧L1也指出数字规则收窄，其纯re实验原件未获准读取，不升格为本次实证。唯一下一步：任务二做HTTPResponse、A1/API2及alias模型入参/导出的窄base/gold对照，捕获actor入口，确认旧key工作流影响。无本次实验或修题。独立reviewer未读/未知；详见前稿与历史差异稿。

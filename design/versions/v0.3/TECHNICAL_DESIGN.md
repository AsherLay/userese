# Userese v0.3.0 技术设计

## 采集边界

v0.3.0 使用 Python 标准库完成确定性提取，不新增浏览器运行时依赖。静态页面由 `discover_content.py` 直接读取；浏览器 DOM、SSR、API、CMS、国际化和运行时模板由宿主以 `userese-capture/v1` 清单交给提取器。清单只保存与目标 Surface 相关的展示字段、来源定位和状态，不保存完整响应、Cookie、Authorization 或凭据。

采集器不执行目标项目里的命令。登录态和测试数据由宿主按现有授权边界取得；不可访问状态写入 `surface-map.json` 的限制，不伪造覆盖。

## 来源关联

结构化 capture entry 是 v0.3.0 的通用扩展缝：每条记录同时包含显示文本、`rendered_at`、`origin_type`、`source_locator`、`editability`、`trace_confidence` 和内容性质。浏览器 instrumentation、框架适配器或人工导出都可以生成同一清单，核心协议不绑定某个浏览器。

## 稳定 ID 与重复项

候选 ID 对 Surface、route、state、locale、viewport、来源定位、显示位置和文本模板的规范 JSON 计算 SHA-256 前缀。相同输入稳定复现；同文不同位置保留为不同候选；完全相同的规范身份归并消费者位置。

## 机械预分类

HTML 标签、属性和显式 `data-userese-*` 标记只产生 `core`、`supplemental`、`noncopy` 三类机械提示。标题、正文、关键链接和 CTA 默认进入核心；alt、ARIA、元信息、状态、装饰和数据默认进入覆盖摘要。宿主在所选模式下复核性质、用途和重要性，不能把启发式当成事实证明。

## 项目与知识分片

一次候选文件以一个 Surface map 为审计根；`project` 模式允许其中包含多个 route 和渠道。大型项目按 Surface 分片，报告再汇总。知识读取通过 observation 中的 `knowledge_reads` 记录来源、服务条目和字符量；同一内容摘要重复读取会增加 `duplicate_full_reads`，供验收发现浪费。

## 兼容性

新 inventory 使用 `userese-inventory/v2`，但保留 v0.2.0 的 `surface`、`coverage`、`selection`、`items` 和 item 必填字段。`validate_artifacts.py` 同时接受旧清单；进入 `userese-brief/v1` 的仍是用户确认的 `copy-*` 条目，因此 Writer 无需改协议。

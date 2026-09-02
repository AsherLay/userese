# Userese v0.3.0 本地验收记录

- 状态：功能、协议、文档和自动测试完成；真实登录态与第三方 CMS 试点不作为 v0.3.0 公开发布门槛
- 验收日期：2026-09-02
- 基线：v0.2.0

## 需求追踪

| 需求 | 实现 | 自动证据 |
|---|---|---|
| R-01 Surface 确认 | `references/surface-discovery.md`、`validate_surface_map` | `test_surface_map_requires_user_and_state_boundary` |
| R-02 低成本勘察 | `scripts/scan_surface.py`、结构化 capture | `test_low_cost_scan_reports_signals_without_secret_contents`、端到端 CLI 测试 |
| R-03 勘察卡与模式确认 | `scripts/render_scan_plan.py`、`SKILL.md` 模式闸门 | `test_scan_plan_shows_all_modes_and_unconfirmed_gate` |
| R-04 机械候选提取 | `scripts/discover_content.py` 的 HTML/capture 提取与稳定哈希 | `test_cli_is_deterministic`、端到端 CLI 测试 |
| R-05 内容来源追踪 | candidate/inventory v2 的 rendered/source/editability/confidence 字段 | `test_a02_api_title_keeps_endpoint_and_field`、`test_v2_inventory_requires_source_trace` |
| R-06 内容性质分类 | 六类 `content_nature` 与 Writer 边界 | A-03、A-04 测试 |
| R-07 分组覆盖摘要 | `coverage.groups`、v2 渲染与一致性校验 | A-01、A-05、grouped-only 校验 |
| R-08 渐进式知识发现 | Skill 路由规则与 observations.knowledge_reads | A-07 测试 |
| R-09 产物 | surface map、scan plan、candidates、inventory 和 Markdown renderer | 端到端 CLI 测试 |
| R-10 现有流程兼容 | v0.2 inventory 继续接受；brief/result v1 不变 | 原 0.2 测试、A-08 v2→v1 handoff 测试 |
| R-11 读取与上下文观测 | candidate/inventory observations 与重复读取计数 | A-07、candidate metrics 测试 |
| R-12 覆盖声明 | inventory/report 分列发现、分析、选择、Writer 和应用 | renderer 输出与端到端测试 |

## 场景追踪

| 场景 | 结果 | 证据 |
|---|---|---|
| A-01 静态核心首页 | 通过 | `test_a01_core_and_surface_share_discovery_evidence` |
| A-02 API 核心标题 | 通过 | `test_a02_api_title_keeps_endpoint_and_field` |
| A-03 业务数据与产品文案 | 通过 | `test_a03_business_data_is_not_a_writer_item` |
| A-04 用户生成内容 | 通过 | `test_a04_user_content_is_not_a_writer_item` |
| A-05 运行时与无障碍内容 | 通过 | `test_a05_accessibility_and_runtime_expand_only_in_surface` |
| A-06 不可访问后台 | 通过 | `test_a06_unavailable_state_prevents_complete_claim` |
| A-07 渐进式知识读取 | 通过 | `test_a07_observations_route_knowledge_to_items` |
| A-08 兼容与审批 | 通过 | v0.2 回归测试、`test_a08_v2_selected_item_hands_off_to_v1_brief`、Skill 授权闸门 |

## 有意保留的边界

- 浏览器和框架适配器通过 `userese-capture/v1` 接入；v0.3.0 不绑定 Playwright 或执行目标项目命令。
- 登录凭据、CMS 写入、数据库修改、生产发布和无限状态组合仍不在版本范围内。
- 自动测试使用本地 HTML、API、runtime 和不可访问状态夹具；尚未执行真实登录态或第三方 CMS 的人工试点。该项保留为后续验证，不阻止 v0.3.0 公开。

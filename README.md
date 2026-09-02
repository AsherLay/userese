# Userese

Userese 是一个面向网站和 Web 应用的内容设计 Skill：先发现目标用户实际会看到的内容、项目知识和事实边界，再让用户确认范围、表达方向与 Writer，最终生成可核实的文案提案。

## 当前状态

- 最近正式发布版本：`v0.2.0`
- 当前项目版本：`v0.3.0`
- v0.3.0 状态：功能、协议、文档和本地验收已完成，进入项目集成测试；尚未推送、打 tag、发布或部署
- 当前运行入口：`SKILL.md`
- 当前需求事实源：`spec/v0.3/REQUIREMENTS.md`
- 当前设计事实源：`design/versions/v0.3/DESIGN_SPEC.md`
- 仓库可见性：私有

## 仓库结构

| 路径 | 职责 |
|---|---|
| `SKILL.md` | 已发布 Skill 的运行入口和核心工作流 |
| `agents/` | Skill 的界面元数据与调用策略 |
| `references/` | 运行时按条件读取的协议和契约 |
| `scripts/` | 可重复执行的提取、校验和报告工具 |
| `tests/` | 自动测试和版本验收证据 |
| `spec/` | 按版本保存正式需求、边界与验收条件 |
| `design/` | 设计继承和按版本保存的交互表达 |
| `docs/agents/` | 版本开发与 Agent 工作协议 |
| `docs/adr/` | 已接受的长期结构或架构决定 |
| `.working/` | 被 Git 忽略的访谈、草稿、运行日志和实验过程 |
| `private/` | 被 Git 忽略的私有输入、输出和凭据相关材料 |

仓库根目录同时是可安装 Skill 包。该项目不采用嵌套 `skill/`，原因记录在 `docs/adr/0001-keep-installable-skill-at-repository-root.md`。

## 开发入口

开始 v0.3.0 开发前依次阅读：

1. `AGENTS.md`
2. `CONTEXT.md`
3. `spec/v0.3/REQUIREMENTS.md` 与 `spec/v0.3/ACCEPTANCE.md`
4. `design/versions/v0.3/DESIGN_SPEC.md` 与 `design/versions/v0.3/TECHNICAL_DESIGN.md`
5. `docs/agents/version-development.md`

基础验证：

```bash
python3 /home/asher/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
python3 -m unittest discover -s tests -v
```

建立规格、设计或本地实现不授权提交、推送、发布、部署，也不授权改变 GitHub 仓库可见性。

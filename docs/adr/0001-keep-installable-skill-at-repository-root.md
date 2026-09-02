# ADR 0001：保留仓库根目录为可安装 Skill 包

- 状态：Accepted
- 日期：2026-09-02

## 背景

Asher 项目结构母规范建议 Agent skill 项目使用 `skill/` 目录。但 Userese 已经以仓库根目录的 `SKILL.md`、`agents/`、`references/` 和 `scripts/` 被安装、同步和版本化。直接搬入 `skill/` 会改变安装路径，并可能破坏现有 Agent 的发现方式。

## 决定

Userese 仓库根目录继续作为可安装 Skill 包，同时在根目录增加项目开发层：`spec/`、`design/`、`docs/`、`AGENTS.md`、`README.md` 和 `CONTEXT.md`。

- `SKILL.md` 和 `references/` 只承载运行时规则。
- `spec/`、`design/` 和 `docs/` 不从 `SKILL.md` 自动加载。
- `.working/` 和 `private/` 被 Git 忽略。
- 后续若需要发布精简安装包，应通过打包脚本选择运行时文件，而不是重新移动源码入口。

## 结果

现有安装保持兼容；开发 Session 能找到正式需求和设计事实源。代价是仓库根目录同时包含运行时与开发资料，需要通过目录职责和打包边界保持分离。

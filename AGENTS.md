# Userese Agent 入口

## 开始工作前

1. 读取 `README.md`，确认当前发布版本、开发版本和目录职责。
2. 读取 `CONTEXT.md`，确认 Userese 的领域对象和不可混淆边界。
3. 涉及运行行为时读取 `SKILL.md` 及其直接指向的 `references/`；不要为了理解 Skill 而预读全部脚本实现。
4. 涉及版本开发时读取 `docs/agents/version-development.md`、当前 `spec/` 和对应的 `design/versions/`。
5. 涉及目录迁移时读取 Asher 项目结构母规范：`/home/asher/ai-engineering/Asher-ProjectRules/docs/standards/Asher_project_structure.md`。

## 当前事实源

- 当前项目运行行为：`SKILL.md`、`references/`、`scripts/`、`tests/` 为 `0.3.0`；最近正式发布版本仍为 `0.2.0`，当前版本用于项目集成测试。
- 当前版本需求与验收：`spec/v0.3/REQUIREMENTS.md`、`spec/v0.3/ACCEPTANCE.md`。
- 当前版本交互与技术设计：`design/versions/v0.3/DESIGN_SPEC.md`、`design/versions/v0.3/TECHNICAL_DESIGN.md`。
- 项目结构决定：`docs/adr/`。

## 项目约束

- 仓库根目录本身就是可安装的 Skill 包；保留根目录 `SKILL.md`，不搬入嵌套的 `skill/`。
- `references/` 只保存运行时按需读取的协议；需求、设计、ADR 和过程材料分别进入 `spec/`、`design/`、`docs/` 和 `.working/`。
- 正式需求不直接修改现行行为。实现必须有对应验收证据，并保持提案、工作区修改和生产发布的授权边界。
- `VERSION` 只在版本完成并准备发布时更新；创建下一版规格不等于发布。
- 仓库及配套 Writer 当前保持私有。没有用户明确授权，不改变可见性、推送、发布或部署。

## 交付检查

报告变更文件、当前版本状态、运行的检查、检查结果和未验证事项。需求、实现、测试和版本号必须能相互对应。

在Harness Engineering中，**Rule（规则）是给AI设定的“工程纪律”或“行为准则”**。如果说Harness是给AI这匹“野马”套上的缰绳，那么Rule就是缰绳上最核心的“力道”和“方向”指令。

它的核心目的不是让AI更聪明，而是**阻止其反复犯低级、可避免的错误**，将大模型的“创造力”转化为工程系统的“可控力”。

### 🎯 Rule的本质：软约束

Rule的核心是**软约束**。它通过自然语言向AI阐明项目的“**什么能做、什么严格禁止、完成后必须验证什么**”。例如，一条典型的Rule会要求：修改代码后，必须编译、必须运行测试、必须执行后置校验，否则任务就不算完成。

### ⚠️ 为什么“软约束”是不够的？

AI并不总是严格遵守Rule，因为它是“软”的，可能出现以下问题：

- **遗忘**：AI可能直接忘记某条Rule的存在。
- **选择性失效**：AI可能主观判断某条Rule“不适用于”当前情境。
- **偷懒绕过**：AI为了节省算力，可能跳过Rule并给自己找理由。

### 🛠️ 如何让Rule更有效？

为了弥补“软约束”的不足，在实践中需要构建一个完整的约束体系。

- **明确且可执行**：Rule必须用清晰、具体的语言描述。例如，与其说“代码要安全”，不如说“所有数据库操作必须通过ORM框架封装”。
- **分层管理**：参考Harness平台的实践，Rule可按范围分层：
  - **账户级 (Account)**：全局安全要求、合规性控制。
  - **组织级 (Organization)**：团队通用标准。
  - **项目级 (Project)**：具体项目的服务规则。
  - **个人级 (Personal)**：个人偏好设置。
- **分类清晰**：将Rule按类别（如Pipeline、Builds、Security等）组织，方便AI在不同场景下调用。
- **工具化落地**：可使用`jsharness`这类工具，将Markdown格式的Rule自动注入到Cursor、Copilot等AI编程助手的配置中。

### 🚧 Rule的局限与进化：走向“硬约束”与“自我进化”

认识到Rule是“软约束”后，Harness Engineering发展出了更强大的机制：

- **引入“硬约束”**：Rule之上可叠加**Gate（门禁）** 或**Script（脚本）** 等“硬约束”。这些是可执行的检查脚本，不通过就会直接拦截，从“AI知道规则”变成“AI无法打破规则”。
- **Rule的自我进化**：前沿研究如“**Self-Harness**”框架，能让AI Agent**自己重写和改进规则**，在测试中性能提升高达60%。

### 💎 总结

在Harness Engineering中，Rule是基础。它通过自然语言为AI的行为设定了最初的边界和期望。然而，由于AI可能“遗忘”或“绕过”Rule，一个成熟的系统需要通过**脚本（Script）**、**门禁（Gate）** 等机制，将软性的Rule升级为强制的“硬关卡”，最终形成一个让AI可靠、稳定工作的工程化环境。

如果你对Rule的具体编写格式，或者如何将Rule与Script、Gate等“硬约束”结合感兴趣，我们可以继续深入探讨。

## 最佳工业实践

Rule 的最佳实践，在于将其视为一套从“软性指引”到“硬性关卡”的完整工程体系。它的核心思想是：**用规则（Rule）明确“应该做什么”，用脚本（Script）强制“必须通过什么”**。

一个好的实践，不仅仅是写一份 Markdown 文档，更需要有一套完整的工程化方法来管理它。

### 🧱 核心原则：软硬兼施的工程化体系

一个成熟的 Rule 实践是分层递进的：

- **Rules (软约束)**：用 Markdown 编写的自然语言规范，告诉 AI “什么能做，什么不能做”。
- **Skills (半硬约束)**：步骤化的操作手册，指导 AI “具体怎么做”。
- **Gate Scripts (硬约束)**：可执行的检查脚本（如 linters、tests），是最后的把关者，不通过就拦截。

文档会过时，人会遗忘，但 **Lint 规则和 CI 检查每次都会执行**。这个体系成功的关键，在于用“硬约束”来兜底“软约束”的失效。

### 🏗️ 组织与编写：结构化的 Rule 文件

一个结构清晰的 Rule 文件是实践的基础。

**1. 目录结构 (以 `jsharness` 为例)**

一个推荐的项目级 Rule 目录结构如下：

```
.harness/
├── rules/
│   ├── global/                    # 全局规则
│   │   ├── coding-standard.md     # 通用编码规范
│   │   ├── commit-convention.md   # Commit 信息规范
│   │   └── security-baseline.md   # 安全红线
│   └── project/                   # 项目特定规则
│       ├── frontend-vue3.md       # Vue3 技术栈规则
│       └── java-backend.md        # Java 后端规则
└── scripts/                       # Gate Scripts (硬约束)
    └── validate.sh
```

**2. 编写规范 (以 `coding-standard.md` 为例)**

一个优秀的 Rule 文件应具备以下特征：

```markdown
---
# 可选：通过 paths 字段声明规则生效的文件范围
paths:
  - "**/*.py"
  - "**/*.js"
---

# 编码规范

## 1. 命名规范

- **类名**: 必须使用 `PascalCase`
- **变量/函数**: 必须使用 `snake_case`

## 2. 错误处理

- 必须捕获的异常类型: `IOError`, `DatabaseError`
- 日志级别: `ERROR`

## 3. 架构约束

- **禁止**: 直接编写 SQL 查询 (`direct_sql_query`)
- **禁止**: 硬编码凭证 (`hardcoded_credentials`)
- **必须**: 使用 Repository 模式
- **必须**: 使用依赖注入

## 4. 完成标准

- [ ] 代码必须通过编译
- [ ] 必须通过所有单元测试
- [ ] 必须通过 Lint 检查
```

### 📋 场景化 Rule 示例

Rule 可以应用于软件开发生命周期的各个领域。

#### 场景一：Pipeline 部署策略 (Harness AI)

当 AI 在 Pipeline Studio 中工作时，Rule 可以要求其遵循特定的部署策略。

```markdown
# Pipeline - Production Deploy

生产环境的部署流水线必须使用**蓝绿部署**或**金丝雀发布**策略。
```

#### 场景二：安全与合规 (Security)

在金融、医疗等敏感领域，Rule 可以强制实施安全编码规范。

```markdown
# Security Baseline

- **禁止**: 在代码中硬编码任何凭证
- **禁止**: 使用不安全的加密算法
- **必须**: 对所有用户输入进行校验，防止 OWASP Top 10 漏洞
```

#### 场景三：技术栈锁定 (Tech Stack)

为了防止 AI 随意引入不兼容的技术，Rule 可以锁定技术栈。

```yaml
# 项目级规则文件示例
project_name: "E-commerce Backend"
tech_stack:
  language: "Python 3.9+"
  framework: "Django 4.2"
  database: "PostgreSQL 15"
```

#### 场景四：Agent 任务结果过滤

在 Agent 执行任务后，可以设置规则来过滤其结果，确保输出符合预期。

```python
# 示例：金融场景下的规则配置
rules = {
    "max_response_length": 200,          # 限制回答长度
    "blocked_keywords": ["内部数据", "未公开信息"], # 敏感词过滤
    "fallback_strategy": "ESCALATE_TO_HUMAN" # 异常时转人工
}
```

### 🚀 实施与集成

- **分层管理**：Rule 应按**账户 (Account)**、**组织 (Organization)**、**项目 (Project)** 和个人 (Personal) 分层管理，不同层级拥有不同的优先级。
- **自动化工具**：可以使用 `jsharness` 等工具，将 `.harness/rules/` 下的 Rule 自动注入到 Cursor、Copilot 等 AI 编程助手的配置中。
- **版本控制**：将 Rule 文件（如 `.rules/` 文件夹）纳入 Git 等版本控制系统，确保团队协作时规则同步。
- **持续优化**：Rule 需要像代码一样被维护。当发现新的错误模式时，应及时更新 Rule，将经验固化为规范。

总而言之，Rule 的最佳实践是一个从“写好文档”到“建好系统”的工程化过程。它通过结构化的文档、分层管理和自动化工具的辅助，将团队的集体智慧转化为 AI 可理解、可执行的硬性约束，是实现 AI 在项目中稳定、可靠工作的基石。

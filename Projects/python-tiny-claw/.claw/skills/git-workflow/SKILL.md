---
name: git-workflow
description: 当用户要求提交代码、保存变更或执行 Git 操作时触发
---

## Git 提交流程

1. **检查状态**: 先用 `git status` 查看当前修改
2. **暂存文件**: 用 `git add <files>` 暂存需要提交的文件
3. **提交**: 用 `git commit -m "message"` 提交，message 用英文描述改动
4. **确认**: 提交后用 `git log -1` 确认提交成功

## 重要规则

- 新增的源代码文件使用 git add 明确指定，避免将构建产物或密钥文件提交
- 提交信息简洁有力，描述做了什么
- 如果仓库尚未初始化，先执行 `git init`

# 提交流程 SOP

1. 先使用 `bash` 调用 `git status` 确认当前有哪些文件发生了改动。
2. 你的 commit message 必须使用 Emoji 开头，例如：`🚀 feat: 增加新功能` 或 `🐛 fix: 修复 Bug`。
3. 严禁使用 `git commit -am "update"` 这种敷衍的提交。

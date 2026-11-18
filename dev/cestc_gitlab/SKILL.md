---
name: cestc_gitlab
description: 当任务涉及 code.cestc.cn 时使用：通过本机已授权的 glab 查看或修改仓库元数据、分支与文件、提交历史、Merge Request、Tags 和 Issues，并解析、读取该域名的 blob/raw 文件 URL。即使用户只粘贴一个该域名的链接，或只说公司 GitLab、CESTC 代码库、MR、issue、标签、提交，也要主动使用本 skill。包含认证校验、写后验证，以及 CLI 与 GitLab 实例不兼容时的版本处理。不用于其他 GitLab 实例或纯本地 Git 操作。
compatibility: 需要 Python 3 和 glab；支持 Windows、macOS、Linux。
---

# CESTC GitLab

把 `glab` 作为访问 `code.cestc.cn` 的唯一远端数据通道。所有 API 调用显式指定 `--hostname code.cestc.cn`，避免当前目录的 Git remote 或默认 `gitlab.com` 改变目标。认证失败时恢复 glab 认证，不切换匿名 HTTP、其他 API 客户端或直接 `git push`。

## 每次调用

1. **确定目标和权限。** 从用户输入提取项目完整路径、ref、commit SHA、MR `!iid` 或 Issue `#iid`。只处理 `code.cestc.cn`；其他域名交给相应工具。确认用户要求的是读取还是远端修改。
2. **验证 CLI 和授权。** 执行：

   ```bash
   glab version
   glab auth status --hostname code.cestc.cn
   glab api --hostname code.cestc.cn user
   glab api --hostname code.cestc.cn version
   ```

   `/user` 证明当前 token 可用并确认身份，`/version` 记录实例版本。不要使用 `--show-token`，也不要读取或复制配置文件中的 token。未登录时让用户通过 `glab auth login --hostname code.cestc.cn` 交互登录；401/403 时说明所需授权或权限，而不是把 404 当成资源不存在。
3. **选择操作路径。**
   - 对 `blob`/`raw` 文件 URL，运行 `python <skill目录>/scripts/read_file.py <URL>`；脚本通过 glab 解析项目、branch/tag/SHA 和文件路径，原始内容写到 stdout，解析结果写到 stderr。重定向 stdout 可保存文件。版本切换时用 `--glab <路径>` 或 `GLAB` 环境变量选择二进制。
   - 对仓库元数据、分支代码、提交、MR、Tag、Issue，读取 [references/api.md](references/api.md)，用其中的 `glab api` 操作。高层子命令只有在本机 `--help` 确认支持、且能显式固定 host/project 时才使用；REST API 是跨版本底座。
4. **写前读取，最小修改。** 修改前取得目标当前状态，只提交用户要求的字段。代码修改使用 Commits API，使远端写入仍经过 glab。合并或关闭 MR、删除文件/Tag/Issue、改变仓库可见性等破坏性或公开操作，若未被用户明确授权，先说明目标与影响并请求确认。
5. **写后验证。** 重新读取对应资源：代码核对返回的 commit SHA 与文件内容，元数据核对字段，MR/Issue 核对 `iid` 和状态，Tag 核对名称与 target。写请求超时或结果不明时先查状态，避免重试产生重复提交、评论或 MR。
6. **报告实际结果。** 给出项目、ref/SHA 或 IID、执行的操作和验证证据。文件读取说明解析出的 project/ref/path；只给结论而未读取成功时，不声称看过文件。

完成标准：请求涉及的每个资源都由授权后的 glab 成功读取或修改并回读验证；任何未执行、无权限或未验证的部分都明确列出。

## 兼容性恢复

当前 CLI 正常工作时不升级。只有实际错误表明 CLI 与实例的 API/协议不兼容时，才读取 [references/compatibility.md](references/compatibility.md) 并安装经过验证的兼容版本；缺少某个高层子命令本身不构成冲突，优先使用 `glab api`。GitLab 与 glab 的版本号独立，不能按数字相同来选型。

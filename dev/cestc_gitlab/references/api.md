# code.cestc.cn API 操作参考

统一使用 `glab api --hostname code.cestc.cn`。GitLab REST API 的路径参数和查询值都要 URL 编码；不要手工拼接未经编码的项目路径、ref 或文件路径。

## 约定

先解析项目完整路径，再优先使用返回 JSON 中的数值 `id` 作为后续 `$PID`：

```bash
HOST=code.cestc.cn
PROJECT='group/subgroup/project'
ENCODED_PROJECT=$(python -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$PROJECT")
glab api --hostname "$HOST" "projects/$ENCODED_PROJECT"
PID=<返回JSON中的id>
```

下文的 `$REF`、`$SHA`、`$FILE`、`$TAG` 均表示已经用 `urllib.parse.quote(value, safe="")` 编码的值。查询字符串整体加引号。列表默认加 `per_page=100`，需要全部结果时加 `--paginate`；若要把输出当成单个 JSON 文档解析，则按 `page` 逐页读取，因为多页输出可能是多个 JSON 数组。

写操作使用显式 HTTP 方法。字段较少时可用 `--raw-field key=value`；复杂文本、数组或代码内容写入临时 JSON 文件后用 `--input payload.json`，避免 shell 引号破坏内容。临时文件只含任务所需数据，用后删除。

```bash
glab api --hostname "$HOST" --method PUT --input payload.json "projects/$PID"
```

## 仓库元数据

| 目标 | 请求 |
|---|---|
| 查看元数据、默认分支、可见性 | `GET projects/$PID` |
| 查看分支 | `GET projects/$PID/repository/branches` |
| 创建分支 | `POST projects/$PID/repository/branches`，JSON：`branch`、`ref` |
| 修改元数据 | `PUT projects/$PID`，只带要求的字段，如 `name`、`description`、`default_branch`、`visibility` |

先 GET 再 PUT；服务端不认识的字段不要反复提交。可见性修改遵循主 skill 的确认规则。

## 分支代码

| 目标 | 请求 |
|---|---|
| 列目录 | `GET projects/$PID/repository/tree?ref=<ref>&path=<path>&recursive=false&per_page=100` |
| 读文件元数据/Base64 | `GET projects/$PID/repository/files/$FILE?ref=<ref>` |
| 读原始文件 | `GET projects/$PID/repository/files/$FILE/raw?ref=<ref>` |
| 新建/修改/删除文件 | `POST projects/$PID/repository/commits` |

原子代码提交示例：

```json
{
  "branch": "main",
  "commit_message": "Update configuration",
  "actions": [
    {"action": "update", "file_path": "config/app.yml", "content": "..."}
  ]
}
```

`action` 可为 `create`、`update`、`delete`；同一请求可携带多个 actions。新分支提交可增加 `start_branch`。删除 action 不需要 `content`。提交后用返回的 SHA 和文件 raw 请求验证。

## 提交历史

| 目标 | 请求 |
|---|---|
| 分支历史 | `GET projects/$PID/repository/commits?ref_name=<ref>&per_page=100` |
| 某文件历史 | 同上，增加 `&path=<path>`；可选 `since`、`until` 使用 ISO 8601 |
| 单个提交 | `GET projects/$PID/repository/commits/$SHA` |
| 提交 diff | `GET projects/$PID/repository/commits/$SHA/diff` |
| 比较两个 ref | `GET projects/$PID/repository/compare?from=<from>&to=<to>` |

## Merge Requests

| 目标 | 请求 |
|---|---|
| 列表/筛选 | `GET projects/$PID/merge_requests?state=opened&per_page=100` |
| 查看 `!IID` | `GET projects/$PID/merge_requests/$IID` |
| 查看改动 | `GET projects/$PID/merge_requests/$IID/changes` |
| 创建 | `POST projects/$PID/merge_requests`，JSON：`source_branch`、`target_branch`、`title`，可选 `description` |
| 修改 | `PUT projects/$PID/merge_requests/$IID`，只带要求字段；关闭/重开用 `state_event=close/reopen` |
| 评论 | `POST projects/$PID/merge_requests/$IID/notes`，JSON：`body` |
| 合并 | `PUT projects/$PID/merge_requests/$IID/merge`，仅带用户要求的合并选项 |

创建或修改后回读同一 IID；合并后同时核对 `state`、`merge_commit_sha` 和目标分支。IID 是项目内编号，不是全局 `id`。

## Tags

| 目标 | 请求 |
|---|---|
| 列表 | `GET projects/$PID/repository/tags?per_page=100` |
| 查看 | `GET projects/$PID/repository/tags/$TAG` |
| 创建 | `POST projects/$PID/repository/tags`，JSON：`tag_name`、`ref`，可选 `message` |
| 删除 | `DELETE projects/$PID/repository/tags/$TAG` |

Tag 没有独立的“编辑”语义；更改指向需要明确授权后删除并重建。创建后回读并核对 `commit.id` 或 `target`。

## Issues

| 目标 | 请求 |
|---|---|
| 列表/筛选 | `GET projects/$PID/issues?state=opened&per_page=100` |
| 查看 `#IID` | `GET projects/$PID/issues/$IID` |
| 创建 | `POST projects/$PID/issues`，JSON：`title`，可选 `description`、`labels`、`assignee_ids` |
| 修改 | `PUT projects/$PID/issues/$IID`，只带要求字段；关闭/重开用 `state_event=close/reopen` |
| 评论 | `POST projects/$PID/issues/$IID/notes`，JSON：`body` |
| 删除 | `DELETE projects/$PID/issues/$IID`，需要明确授权且服务端允许 |

创建或修改后回读同一 IID，核对标题、状态及其他目标字段。涉及指派人时，先通过项目上下文确认用户 ID，不按显示名猜测。

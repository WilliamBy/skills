#!/usr/bin/env python3
"""Read a code.cestc.cn blob/raw URL through the authenticated glab CLI."""

import argparse
import os
import subprocess
import sys
from urllib.parse import quote, unquote, urlsplit

HOST = "code.cestc.cn"
MARKERS = ("/-/blob/", "/-/raw/", "/blob/", "/raw/")


class ReadFileError(RuntimeError):
    pass


class ApiError(RuntimeError):
    pass


def parse_file_url(url):
    parsed = urlsplit(url)
    if (
        parsed.scheme.lower() not in ("http", "https")
        or parsed.hostname != HOST
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ReadFileError(f"仅接受 https://{HOST}/ 的仓库文件 URL")

    for marker in MARKERS:
        if marker not in parsed.path:
            continue
        project_part, target_part = parsed.path.split(marker, 1)
        project = unquote(project_part).strip("/")
        target = unquote(target_part).strip("/")
        if not project or not target:
            break
        return project, target

    raise ReadFileError("URL 必须包含 /-/blob/<ref>/<file> 或 /-/raw/<ref>/<file>")


def api(glab, endpoint):
    command = [glab, "api", "--hostname", HOST, endpoint]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise ReadFileError(f"无法执行 {glab}: {exc}") from exc

    if result.returncode:
        output = b"\n".join((result.stdout, result.stderr))
        message = output.decode("utf-8", errors="replace").strip()
        raise ApiError(message or f"glab 退出码 {result.returncode}")
    return result.stdout


def is_not_found(error):
    message = str(error).lower()
    return "404" in message or "not found" in message


def fetch_file(url, glab="glab"):
    project, target = parse_file_url(url)
    parts = target.split("/")
    if len(parts) < 2:
        raise ReadFileError("文件 URL 缺少 ref 或文件路径")

    encoded_project = quote(project, safe="")
    # GitLab refs may contain slashes. Match the longest ref first, as the web UI does.
    for split_at in range(len(parts) - 1, 0, -1):
        ref = "/".join(parts[:split_at])
        file_path = "/".join(parts[split_at:])
        endpoint = (
            f"projects/{encoded_project}/repository/files/"
            f"{quote(file_path, safe='')}/raw?ref={quote(ref, safe='')}"
        )
        try:
            content = api(glab, endpoint)
        except ApiError as exc:
            if is_not_found(exc):
                continue
            raise ReadFileError(f"glab 读取失败：{exc}") from exc
        return project, ref, file_path, content

    raise ReadFileError(
        "所有 branch/tag/SHA 与文件路径的组合均返回 404；"
        "请检查 URL、文件是否存在，以及当前账号是否有权查看该项目"
    )


def main():
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="code.cestc.cn 的 blob 或 raw 文件 URL")
    parser.add_argument(
        "--glab",
        default=os.environ.get("GLAB", "glab"),
        help="glab 可执行文件；也可用 GLAB 环境变量指定兼容版本",
    )
    args = parser.parse_args()

    try:
        project, ref, file_path, content = fetch_file(args.url, args.glab)
    except ReadFileError as exc:
        print(f"cestc_gitlab: {exc}", file=sys.stderr)
        return 1

    print(f"已解析：{project} | ref={ref} | file={file_path}", file=sys.stderr)
    sys.stdout.buffer.write(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

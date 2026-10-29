#!/usr/bin/env node
/**
 * Mermaid 语法校验器 —— 抽取 Markdown 中所有 ```mermaid 代码块并逐个 parse。
 *
 * 依赖 mermaid + jsdom，首次运行自动安装到 ~/.tech-review-lint（仅一次，约 30s）。
 * 若安装失败（离线/无 npm），退化为静态启发式检查并给出提示，不阻塞交付。
 *
 * 用法：
 *   node check_mermaid.mjs <file.md> [more.md ...]
 * 退出码：0 = 全部通过（或有降级警告），1 = 存在语法错误，2 = 文件不可读。
 */

import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { spawnSync } from "node:child_process";
import { pathToFileURL } from "node:url";

const CACHE = path.join(os.homedir(), ".tech-review-lint");
const MERMAID_ENTRY = path.join(CACHE, "node_modules", "mermaid", "dist", "mermaid.core.mjs");
const JSDOM_ENTRY = path.join(CACHE, "node_modules", "jsdom", "lib", "api.js");

function ensureDeps() {
  if (fs.existsSync(MERMAID_ENTRY) && fs.existsSync(JSDOM_ENTRY)) return true;
  if (!fs.existsSync(CACHE)) fs.mkdirSync(CACHE, { recursive: true });
  const pkg = path.join(CACHE, "package.json");
  if (!fs.existsSync(pkg)) {
    fs.writeFileSync(pkg, JSON.stringify({ name: "tech-review-lint", private: true, type: "module" }));
  }
  process.stdout.write("首次运行：正在安装 mermaid / jsdom 校验依赖（约 30 秒）...\n");
  const npm = process.platform === "win32" ? "npm.cmd" : "npm";
  const r = spawnSync(npm, ["install", "--prefix", CACHE, "mermaid@11", "jsdom@25", "--no-audit", "--no-fund", "--loglevel=error"], {
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  return r.status === 0 && fs.existsSync(MERMAID_ENTRY) && fs.existsSync(JSDOM_ENTRY);
}

/** 从 markdown 中抽取 mermaid 代码块，记录起始行号 */
function extractBlocks(md) {
  const lines = md.split(/\r?\n/);
  const blocks = [];
  let cur = null;
  let fenceMark = "";
  lines.forEach((line, i) => {
    const m = /^\s*(`{3,}|~{3,})\s*([^\s`]*)/.exec(line);
    if (m) {
      const marker = m[1];
      if (!cur) {
        cur = { lang: (m[2] || "").toLowerCase(), start: i + 1, body: [], mark: marker[0], len: marker.length };
      } else if (marker[0] === cur.mark && marker.length >= cur.len && (m[2] || "") === "") {
        if (cur.lang === "mermaid") blocks.push({ start: cur.start, code: cur.body.join("\n"), closed: true });
        cur = null;
      } else {
        cur.body.push(line);
      }
      return;
    }
    if (cur) cur.body.push(line);
  });
  if (cur && cur.lang === "mermaid") blocks.push({ start: cur.start, code: cur.body.join("\n"), closed: false });
  return blocks;
}

/** 无依赖降级检查：只查明显结构问题 */
function heuristic(code) {
  const errs = [];
  const first = (code.split("\n").find((l) => l.trim() && !l.trim().startsWith("%%")) || "").trim();
  const known = /^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram(-v2)?|erDiagram|gantt|pie|journey|gitGraph|mindmap|timeline|quadrantChart|C4Context|sankey-beta|xychart-beta|block-beta|packet-beta|architecture-beta)/;
  if (!known.test(first)) errs.push(`首行不是合法图表类型声明：${first.slice(0, 40)}`);
  for (const [i, line] of code.split("\n").entries()) {
    const s = line.trim();
    if (!s || s.startsWith("%%")) continue;
    const open = (s.match(/\[/g) || []).length;
    const close = (s.match(/\]/g) || []).length;
    if (open !== close) errs.push(`第 ${i + 2} 行中括号 [] 不成对`);
    const po = (s.match(/\(/g) || []).length;
    const pc = (s.match(/\)/g) || []).length;
    if (po !== pc) errs.push(`第 ${i + 2} 行圆括号 () 不成对`);
  }
  return errs;
}

async function main() {
  const files = process.argv.slice(2);
  if (!files.length) {
    console.error("用法：node check_mermaid.mjs <file.md>");
    process.exit(2);
  }

  const docs = files.map((f) => {
    if (!fs.existsSync(f)) {
      console.error(`文件不存在：${f}`);
      process.exit(2);
    }
    return { file: f, md: fs.readFileSync(f, "utf8") };
  });

  let totalBlocks = 0;
  const all = [];
  for (const d of docs) {
    const blocks = extractBlocks(d.md);
    totalBlocks += blocks.length;
    all.push({ file: d.file, blocks });
  }
  if (totalBlocks === 0) {
    console.log("未发现 mermaid 代码块，跳过 Mermaid 校验。");
    return 0;
  }

  const ready = ensureDeps();
  if (!ready) {
    console.log("[WARN ] 依赖安装失败，降级为启发式检查（未做完整语法解析）");
    let bad = 0;
    for (const { file, blocks } of all) {
      blocks.forEach((b, i) => {
        const errs = heuristic(b.code);
        if (errs.length) {
          bad++;
          console.log(`[ERROR] ${path.basename(file)}:${b.start}  mermaid 块 #${i + 1}`);
          errs.forEach((e) => console.log(`        - ${e}`));
        }
      });
    }
    console.log(`\n合计：${totalBlocks} 个 mermaid 块，${bad} 个疑似有问题（启发式）`);
    return bad ? 1 : 0;
  }

  const { JSDOM } = await import(pathToFileURL(JSDOM_ENTRY).href);
  const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>", { pretendToBeVisual: true });
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  Object.defineProperty(globalThis, "navigator", { value: dom.window.navigator, configurable: true });
  globalThis.DOMPurify = undefined;

  const mermaidMod = await import(pathToFileURL(MERMAID_ENTRY).href);
  const mermaid = mermaidMod.default ?? mermaidMod;
  mermaid.initialize({ startOnLoad: false, securityLevel: "loose", logLevel: "fatal" });

  let failed = 0;
  for (const { file, blocks } of all) {
    for (const [i, b] of blocks.entries()) {
      if (!b.closed) {
        failed++;
        console.log(`[ERROR] ${path.basename(file)}:${b.start}  mermaid 代码块未闭合`);
        continue;
      }
      try {
        await mermaid.parse(b.code);
      } catch (err) {
        failed++;
        const msg = String((err && err.message) || err).split("\n").slice(0, 6).join("\n          ");
        console.log(`[ERROR] ${path.basename(file)}:${b.start}  mermaid 块 #${i + 1} 语法错误`);
        console.log(`          ${msg}`);
      }
    }
  }

  if (failed === 0) {
    console.log(`OK  ${files.map((f) => path.basename(f)).join(", ")}  —  ${totalBlocks} 个 mermaid 块语法全部通过`);
    return 0;
  }
  console.log(`\n合计：${totalBlocks} 个 mermaid 块，${failed} 个语法错误（行号为代码块起始围栏行）`);
  return 1;
}

main()
  .then((code) => process.exit(code))
  .catch((err) => {
    console.error("校验器异常：", err);
    process.exit(2);
  });

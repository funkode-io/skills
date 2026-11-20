#!/usr/bin/env node
// Install or check the global skills listed in skills.json.
//   install [--dry-run] [--prune] [--agent <agents...>]
//   check   exit 0 silent when current, 1 with one line per finding, 2 on error
import { execFileSync, spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const SKILLS_CLI = process.env.FUNKODE_SKILLS_CLI || "skills@1";
const NPX = process.platform === "win32" ? "npx.cmd" : "npx";

const list = JSON.parse(readFileSync(new URL("../skills.json", import.meta.url), "utf8"));
const wanted = new Map(); // skill name -> source
for (const [source, names] of Object.entries(list)) for (const n of names) wanted.set(n, source);

// Same resolution as the skills CLI's getSkillLockPath().
function lockPath() {
  const xdg = process.env.XDG_STATE_HOME;
  return xdg ? join(xdg, "skills", ".skill-lock.json") : join(homedir(), ".agents", ".skill-lock.json");
}

function readLock() {
  let text;
  try {
    text = readFileSync(lockPath(), "utf8");
  } catch (e) {
    if (e.code === "ENOENT") return {};
    throw e;
  }
  return JSON.parse(text).skills ?? {};
}

function run(args, dryRun) {
  console.log(["npx", "-y", SKILLS_CLI, ...args].join(" "));
  if (dryRun) return;
  const r = spawnSync(NPX, ["-y", SKILLS_CLI, ...args], { stdio: "inherit" });
  if (r.status !== 0) {
    console.error(`failed: ${r.error?.message ?? `exit ${r.status}`}`);
    process.exit(1);
  }
}

function install(argv) {
  const dryRun = argv.includes("--dry-run");
  const prune = argv.includes("--prune");
  const ai = argv.indexOf("--agent");
  const agents = ai < 0 ? [] : argv.slice(ai + 1).filter((a) => !a.startsWith("--"));
  const agentArgs = agents.length ? ["-a", ...agents] : [];
  for (const [source, names] of Object.entries(list)) {
    run(["add", source, "-g", "-y", ...agentArgs, "-s", ...names], dryRun);
  }
  if (prune) {
    const extra = Object.keys(readLock()).filter((n) => !wanted.has(n));
    if (extra.length) run(["remove", "-g", "-y", ...extra], dryRun);
  }
}

function githubToken() {
  if (process.env.GITHUB_TOKEN) return process.env.GITHUB_TOKEN;
  if (process.env.GH_TOKEN) return process.env.GH_TOKEN;
  try {
    return execFileSync("gh", ["auth", "token"], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
  } catch {
    return "";
  }
}

const trees = new Map();
function fetchTree(source, ref, token) {
  const key = `${source}@${ref}`;
  if (!trees.has(key)) {
    trees.set(key, (async () => {
      const url = `https://api.github.com/repos/${source}/git/trees/${encodeURIComponent(ref)}?recursive=1`;
      const headers = { Accept: "application/vnd.github+json", "User-Agent": "funkode-skills" };
      if (token) headers.Authorization = `Bearer ${token}`;
      const res = await fetch(url, { headers, signal: AbortSignal.timeout(30000) });
      if (!res.ok) throw new Error(`GET ${url}: HTTP ${res.status}`);
      return res.json();
    })());
  }
  return trees.get(key);
}

function folderOf(skillPath) {
  return skillPath.replace(/\\/g, "/").replace(/\/?skill\.md$/i, "").replace(/\/$/, "");
}

async function check() {
  const lock = readLock();
  const findings = [];
  for (const [name, source] of wanted) {
    const entry = lock[name];
    if (!entry) findings.push(`missing ${name}: listed from ${source}, not installed`);
    else if (entry.source !== source) findings.push(`source ${name}: installed from ${entry.source}, listed from ${source}`);
  }
  for (const [name, entry] of Object.entries(lock)) {
    if (!wanted.has(name)) findings.push(`unlisted ${name}: installed from ${entry.source}, not in skills.json`);
  }

  const token = githubToken();
  const errors = [];
  await Promise.all(Object.entries(lock).map(async ([name, entry]) => {
    if (entry.sourceType !== "github" || !entry.skillPath) {
      findings.push(`unchecked ${name}: ${entry.sourceType} source, no upstream to compare`);
      return;
    }
    if (!entry.skillFolderHash) {
      findings.push(`unchecked ${name}: no skillFolderHash in the lock`);
      return;
    }
    try {
      const tree = await fetchTree(entry.source, entry.ref || "HEAD", token);
      const folder = folderOf(entry.skillPath);
      const sha = folder ? tree.tree.find((e) => e.type === "tree" && e.path === folder)?.sha : tree.sha;
      if (!sha) {
        if (tree.truncated) throw new Error(`${entry.source} tree is truncated; cannot find ${folder}`);
        findings.push(`gone ${name}: ${folder} no longer exists in ${entry.source}`);
      } else if (sha !== entry.skillFolderHash) {
        findings.push(`outdated ${name}: ${entry.source} has a newer version`);
      }
    } catch (e) {
      errors.push(`error ${name}: ${e.message}`);
    }
  }));

  for (const f of findings.sort()) console.log(f);
  if (errors.length) {
    for (const e of errors.sort()) console.error(e);
    process.exit(2);
  }
  process.exit(findings.length ? 1 : 0);
}

const [cmd, ...rest] = process.argv.slice(2);
try {
  if (cmd === "install") install(rest);
  else if (cmd === "check") await check();
  else {
    console.error("usage: funkode-skills install [--dry-run] [--prune] [--agent <agents...>] | check");
    process.exit(2);
  }
} catch (e) {
  console.error(`error: ${e.message}`);
  process.exit(2);
}

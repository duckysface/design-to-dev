#!/usr/bin/env node
// design-to-dev — installe la skill pour Claude Code et/ou Codex, lance le workflow, prépare la mémoire d'un projet.
// Aucune dépendance : Node 18+ uniquement.
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const readline = require("readline");
const { spawnSync } = require("child_process");

const SKILL_NAME = "design-to-dev";
const PKG_ROOT = path.resolve(__dirname, "..");
const PAYLOAD = ["SKILL.md", "LICENSE", "README.md", "scripts", "references", "templates"];
const SKIP = new Set(["__pycache__", ".DS_Store", "Thumbs.db"]);
const VERSION = require(path.join(PKG_ROOT, "package.json")).version;

const AGENTS = {
  claude: {
    label: "Claude Code",
    user: () => path.join(process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), ".claude"), "skills"),
    project: (dir) => path.join(dir, ".claude", "skills"),
    use: "/design-to-dev <dossier>",
    cli: "claude",
    prompt: (src) => `/design-to-dev ${src}`,
  },
  codex: {
    label: "Codex",
    user: () => path.join(os.homedir(), ".agents", "skills"),
    project: (dir) => path.join(dir, ".agents", "skills"),
    use: "$design-to-dev <dossier>",
    cli: "codex",
    prompt: (src) => `$design-to-dev ${src}`,
  },
};

const HELP = `design-to-dev ${VERSION} — export de design → projet agent-ready dès le premier jour

Juste la mémoire, en 10 secondes, sur n'importe quel projet (rien d'autre n'est touché) :
  npx design-to-dev init .               mémoire multi-agents + hooks + etat.md avec la prochaine étape détectée

Usage :
  npx design-to-dev                      installation interactive (choix de l'agent)
  npx design-to-dev install [options]    installe ou met à jour la skill
  npx design-to-dev uninstall [options]  retire la skill
  npx design-to-dev run <dossier>        installe si besoin puis lance le workflow dans Claude Code ou Codex
  npx design-to-dev init [dossier]       mémoire multi-agents seule (projet neuf ou déjà commencé)
  npx design-to-dev doctor               vérifie Python, les installations et les skills compagnes
  npx design-to-dev path                 affiche le dossier de la skill installée ($SKILL)

Outils (lecture seule, sans agent) :
  npx design-to-dev scan <dossier> [--out f.json]       intention, écrans/démos existants, contrat backend
  npx design-to-dev inventory <dossier> [--out f.json]  inventaire des fichiers (refs, doublons, signaux)
  npx design-to-dev security <dossier> [--out f.json]   base de sécurité statique (candidats, CWE/ASVS)
  npx design-to-dev requirements --intent dashboard     exigences de sécurité par stack
  npx design-to-dev skills                              superpowers et security-audit installées ?

Options de run :
  --claude | --codex  agent à lancer (défaut : celui qui est installé, Claude Code en priorité)
  --print             affiche seulement la commande à lancer

Options d'installation :
  --claude            Claude Code  (~/.claude/skills/design-to-dev)
  --codex             Codex        (~/.agents/skills/design-to-dev)
  --all               les deux
  --project [dossier] installe dans le projet (.claude/skills, .agents/skills) au lieu du dossier utilisateur
  -y, --yes           ne pose aucune question (remplace une installation existante)

Options de init :
  --name "<Nom>"      nom du projet (défaut : nom du dossier)
  --agents <liste>    claude,codex,cursor,gemini,copilot (défaut : claude,codex)
  --private-memory    la mémoire n'est pas versionnée (.gitignore)
  --file-map <json>   pré-remplit changements.md depuis un file-map de nettoyage
  --inventory <json>  reprend un design-inventory.json (sinon le projet est analysé en lecture seule)
  --next-step "<txt>" impose la prochaine étape écrite dans etat.md
  --no-detect         n'analyse pas le projet : etat.md reste à compléter
  --check             vérifie une installation existante sans rien écrire
  --update            met à jour le hook et les blocs gérés (hook modifié à la main : conservé)
`;

function parseArgs(argv) {
  const opts = { _: [], agents: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => (argv[i + 1] && !argv[i + 1].startsWith("-") ? argv[++i] : null);
    if (a === "--claude" || a === "--codex") opts.agents.push(a.slice(2));
    else if (a === "--all") opts.agents.push("claude", "codex");
    else if (a === "-y" || a === "--yes") opts.yes = true;
    else if (a === "--project") opts.project = next() || ".";
    else if (a === "--name") opts.name = next();
    else if (a === "--agents") opts.agentList = next();
    else if (a === "--private-memory") opts.privateMemory = true;
    else if (a === "--file-map") opts.fileMap = next();
    else if (a === "--inventory") opts.inventory = next();
    else if (a === "--next-step") opts.nextStep = next();
    else if (a === "--no-detect") opts.noDetect = true;
    else if (a === "--check") opts.check = true;
    else if (a === "--update") opts.update = true;
    else if (a === "--print") opts.print = true;
    else if (a === "-h" || a === "--help") opts.help = true;
    else if (a === "-v" || a === "--version") opts.version = true;
    else if (a.startsWith("-")) fail(`Option inconnue : ${a}\n\n${HELP}`);
    else opts._.push(a);
  }
  opts.agents = [...new Set(opts.agents)];
  return opts;
}

function fail(msg) {
  console.error(msg);
  process.exit(1);
}

function ask(question) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => rl.question(question, (answer) => { rl.close(); resolve(answer.trim()); }));
}

async function chooseAgents(opts) {
  if (opts.agents.length) return opts.agents;
  if (!process.stdin.isTTY || opts.yes) {
    fail("Préciser l'agent : --claude, --codex ou --all (pas de terminal interactif pour le demander).");
  }
  console.log(`\ndesign-to-dev ${VERSION} — pour quel agent installer la skill ?\n`);
  console.log("  1) Claude Code");
  console.log("  2) Codex");
  console.log("  3) Les deux\n");
  const answer = await ask("Choix [3] : ");
  const choice = { "1": ["claude"], "2": ["codex"], "3": ["claude", "codex"], "": ["claude", "codex"] }[answer];
  if (!choice) fail(`Choix invalide : « ${answer} ».`);
  return choice;
}

function targetDir(agent, opts) {
  const base = opts.project ? AGENTS[agent].project(path.resolve(opts.project)) : AGENTS[agent].user();
  return path.join(base, SKILL_NAME);
}

// N'efface jamais un dossier qui ne contient pas cette skill.
function isOurSkill(dir) {
  const skill = path.join(dir, "SKILL.md");
  return fs.existsSync(skill) && /^name:\s*design-to-dev\s*$/m.test(fs.readFileSync(skill, "utf8"));
}

function copyTree(src, dst) {
  const stat = fs.lstatSync(src);
  if (stat.isSymbolicLink()) return;
  if (stat.isDirectory()) {
    fs.mkdirSync(dst, { recursive: true });
    for (const entry of fs.readdirSync(src)) {
      if (!SKIP.has(entry)) copyTree(path.join(src, entry), path.join(dst, entry));
    }
  } else {
    fs.copyFileSync(src, dst);
  }
}

async function installOne(agent, opts) {
  const dst = targetDir(agent, opts);
  if (fs.existsSync(dst)) {
    if (!isOurSkill(dst)) fail(`${dst} existe et ne contient pas design-to-dev : rien n'a été modifié.`);
    if (!opts.yes && process.stdin.isTTY) {
      const answer = await ask(`${dst} existe déjà. Mettre à jour ? [O/n] : `);
      if (/^n/i.test(answer)) return console.log(`  ${AGENTS[agent].label} : ignoré`);
    }
  }
  // copie dans un dossier voisin puis bascule : une installation interrompue ne laisse pas de skill à moitié copiée
  const tmp = `${dst}.tmp-${process.pid}`;
  fs.rmSync(tmp, { recursive: true, force: true });
  fs.mkdirSync(tmp, { recursive: true });
  for (const item of PAYLOAD) {
    const src = path.join(PKG_ROOT, item);
    if (fs.existsSync(src)) copyTree(src, path.join(tmp, item));
  }
  fs.writeFileSync(path.join(tmp, ".version"), `${VERSION}\n`);
  if (fs.existsSync(dst)) fs.rmSync(dst, { recursive: true, force: true });
  fs.renameSync(tmp, dst);
  console.log(`  ✓ ${AGENTS[agent].label} : ${dst}`);
}

function findPython() {
  for (const cmd of process.platform === "win32" ? ["python", "py", "python3"] : ["python3", "python"]) {
    const r = spawnSync(cmd, ["-c", "import sys; print(sys.version_info >= (3, 9))"], { encoding: "utf8" });
    if (r.status === 0 && r.stdout.trim() === "True") return cmd;
  }
  return null;
}

async function install(opts) {
  const agents = await chooseAgents(opts);
  console.log("");
  for (const agent of agents) await installOne(agent, opts);
  const py = findPython();
  console.log(py ? `\nPython détecté : ${py}` : "\n⚠ Python 3.9+ introuvable : l'installer avant d'utiliser la skill.");
  console.log("\nUtilisation :");
  for (const agent of agents) console.log(`  ${AGENTS[agent].label.padEnd(12)} ${AGENTS[agent].use}`);
  console.log("\nRedémarrer l'agent pour qu'il découvre la skill.");
}

async function uninstall(opts) {
  const agents = opts.agents.length ? opts.agents : ["claude", "codex"];
  for (const agent of agents) {
    const dst = targetDir(agent, opts);
    if (!fs.existsSync(dst)) {
      console.log(`  ${AGENTS[agent].label} : non installée`);
    } else if (!isOurSkill(dst)) {
      console.log(`  ${AGENTS[agent].label} : ${dst} ne contient pas design-to-dev, laissé intact`);
    } else {
      fs.rmSync(dst, { recursive: true, force: true });
      console.log(`  ✓ ${AGENTS[agent].label} : ${dst} supprimé`);
    }
  }
}

function init(opts) {
  const py = findPython();
  if (!py) fail("Python 3.9+ est nécessaire pour installer la mémoire.");
  const project = path.resolve(opts._[1] || ".");
  const args = [path.join(PKG_ROOT, "scripts", "scaffold_memory.py"), project];
  if (opts.check) args.push("--check");
  else {
    args.push("--name", opts.name || path.basename(project), "--python", py);
    if (opts.agentList) args.push("--agents", opts.agentList);
    if (opts.privateMemory) args.push("--private-memory");
    if (opts.fileMap) args.push("--file-map", path.resolve(opts.fileMap));
    if (opts.inventory) args.push("--inventory", path.resolve(opts.inventory));
    if (opts.nextStep) args.push("--next-step", opts.nextStep);
    if (opts.noDetect) args.push("--no-detect");
    if (opts.update) args.push("--update");
  }
  const r = spawnSync(py, args, { stdio: "inherit" });
  process.exit(r.status ?? 1);
}

// Commandes qui passent leurs arguments tels quels à un script Python de la skill.
const PY_TOOLS = {
  scan: ["detect_project.py", "scan"],
  skills: ["detect_project.py", "skills"],
  inventory: ["organize.py", "inventory"],
  security: ["security_check.py", "scan"],
  requirements: ["security_check.py", "requirements"],
};

function pyTool(cmd, rest) {
  const py = findPython();
  if (!py) fail("Python 3.9+ est nécessaire.");
  const [script, sub] = PY_TOOLS[cmd];
  const r = spawnSync(py, [path.join(PKG_ROOT, "scripts", script), sub, ...rest], { stdio: "inherit" });
  process.exit(r.status ?? 1);
}

function installedDir() {
  for (const cfg of Object.values(AGENTS)) {
    const dir = path.join(cfg.user(), SKILL_NAME);
    if (isOurSkill(dir)) return dir;
  }
  return null;
}

function hasCli(cmd) {
  const r = process.platform === "win32"
    ? spawnSync(`${cmd} --version`, { encoding: "utf8", shell: true })
    : spawnSync(cmd, ["--version"], { encoding: "utf8" });
  return r.status === 0;
}

// cmd.exe : guillemets doubles (internes doublés) ; POSIX : guillemets simples
function shellQuote(arg) {
  if (/^[\w./:\-]+$/.test(arg)) return arg;
  return process.platform === "win32" ? `"${arg.replace(/"/g, '""')}"` : `'${arg.replace(/'/g, "'\''")}'`;
}

async function run(opts) {
  const source = opts._[1];
  if (!source) fail("Usage : npx design-to-dev run <dossier> [--claude|--codex]");
  const src = path.resolve(source);
  if (!fs.existsSync(src) || !fs.statSync(src).isDirectory()) fail(`Dossier introuvable : ${src}`);
  let agent = opts.agents[0];
  if (!agent) {
    agent = ["claude", "codex"].find((a) => isOurSkill(path.join(AGENTS[a].user(), SKILL_NAME)) && hasCli(AGENTS[a].cli))
      || ["claude", "codex"].find((a) => hasCli(AGENTS[a].cli)) || "claude";
  }
  const cfg = AGENTS[agent];
  const prompt = cfg.prompt(/\s/.test(src) ? `"${src}"` : src);
  const command = `${cfg.cli} ${shellQuote(prompt)}`;
  if (opts.print) return console.log(command);
  if (!isOurSkill(path.join(cfg.user(), SKILL_NAME))) {
    console.log(`Installation de la skill pour ${cfg.label}…`);
    await installOne(agent, { ...opts, yes: true, project: null });
  }
  if (!hasCli(cfg.cli)) {
    console.log(`
${cfg.label} (${cfg.cli}) introuvable dans le PATH. Lancer l'agent dans ${path.dirname(src)} puis taper :

  ${prompt}
`);
    return;
  }
  console.log(`Lancement de ${cfg.label} : ${prompt}
`);
  const r = process.platform === "win32"
    ? spawnSync(command, { stdio: "inherit", shell: true, cwd: path.dirname(src) })
    : spawnSync(cfg.cli, [prompt], { stdio: "inherit", cwd: path.dirname(src) });
  process.exit(r.status ?? 1);
}

function doctor() {
  const py = findPython();
  console.log(`design-to-dev ${VERSION}`);
  console.log(`  Python 3.9+ : ${py || "INTROUVABLE"}`);
  for (const [agent, cfg] of Object.entries(AGENTS)) {
    const dst = path.join(cfg.user(), SKILL_NAME);
    const ver = fs.existsSync(path.join(dst, ".version")) ? fs.readFileSync(path.join(dst, ".version"), "utf8").trim() : null;
    console.log(`  ${cfg.label.padEnd(12)}: ${isOurSkill(dst) ? `installée (${ver || "version inconnue"}) — ${dst}` : "non installée"}`);
  }
  if (py) {
    console.log("\nSkills compagnes :");
    spawnSync(py, [path.join(PKG_ROOT, "scripts", "detect_project.py"), "skills"], { stdio: "inherit" });
  }
  if (!py) process.exit(1);
}

async function main() {
  const argv = process.argv.slice(2);
  if (PY_TOOLS[argv[0]]) return pyTool(argv[0], argv.slice(1));
  const opts = parseArgs(argv);
  if (opts.version) return console.log(VERSION);
  if (opts.help) return console.log(HELP);
  const cmd = opts._[0] || "install";
  if (cmd === "install") return install(opts);
  if (cmd === "uninstall" || cmd === "remove") return uninstall(opts);
  if (cmd === "init") return init(opts);
  if (cmd === "doctor") return doctor();
  if (cmd === "run") return run(opts);
  if (cmd === "path") {
    const dir = installedDir();
    if (!dir) fail("design-to-dev n'est pas installée (npx design-to-dev install).");
    return console.log(dir);
  }
  fail(`Commande inconnue : ${cmd}\n\n${HELP}`);
}

main().catch((err) => fail(`Erreur : ${err.message}`));

// TaskPulse host plugin: bundled skill provider + /tp command.
import { execFile } from 'node:child_process'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)
const ASSET_DIR = fileURLToPath(new URL('../assets/task-pulse/', import.meta.url))
const BOARD = fileURLToPath(new URL('../assets/task-pulse/scripts/board.py', import.meta.url))
const SKILL_PATH = fileURLToPath(new URL('../assets/task-pulse/SKILL.md', import.meta.url))
const HUB = 'http://127.0.0.1:8770'
const HUB_HOME = process.env.DSH_TASK_PULSE_HOME || join(homedir(), '.dsh', 'progress')
const BOARD_RANK = 600

function parseSkill(raw) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/u.exec(raw)
  if (!match) return { description: 'Live task progress for DSH', content: raw.trim() }
  const description = /(?:^|\n)description:\s*(.+)/u.exec(match[1])?.[1]?.trim() || 'Live task progress for DSH'
  return { description, content: raw.slice(match[0].length).trim() }
}

async function readSkill() {
  const raw = await readFile(SKILL_PATH, 'utf8')
  return parseSkill(raw)
}

const RESOURCE_BASE = { kind: 'directory', path: ASSET_DIR.replace(/\/$/, '') }
const CANDIDATE = {
  name: 'task-pulse',
  description: '多步任务实时进度看板：计划、事件、步骤进度与 DSH 输入框卡片。',
  invocation: { modelInvocable: true, userInvocable: true },
  provider: 'task-pulse',
  source: 'bundled',
  rank: BOARD_RANK,
  resourceBase: RESOURCE_BASE,
  locator: SKILL_PATH,
}

const provider = {
  name: 'task-pulse',
  list: () => Promise.resolve([CANDIDATE]),
  async get() {
    const skill = await readSkill()
    return {
      ...CANDIDATE,
      description: skill.description,
      content: skill.content + `\n\n## 运行路径（由插件注入）\n\nBOARD: ${BOARD}\nASSETS: ${ASSET_DIR}\n`,
    }
  },
}

function stripQuotes(value) {
  const text = String(value || '').trim()
  if ((text.startsWith('"') && text.endsWith('"')) || (text.startsWith("'") && text.endsWith("'"))) {
    return text.slice(1, -1)
  }
  return text
}

async function runBoard(agent, args) {
  const cwd = agent?.session?.header?.cwd || agent?.session?.meta?.cwd || process.cwd()
  const sessionId = String(agent?.session?.id || '')
  const command = [process.env.PYTHON || 'python3', BOARD, '--home', HUB_HOME]
  if (sessionId) command.push('--session', sessionId)
  command.push(...args)
  try {
    const { stdout, stderr } = await execFileAsync(command[0], command.slice(1), {
      cwd,
      timeout: 30000,
      maxBuffer: 10 * 1024 * 1024,
      env: process.env,
    })
    return { ok: true, stdout: stdout.trim(), stderr: stderr.trim() }
  } catch (error) {
    return {
      ok: false,
      stdout: String(error.stdout || '').trim(),
      stderr: String(error.stderr || error.message || '').trim(),
    }
  }
}

function followup(agent, text) {
  if (!agent || typeof agent.followup !== 'function') return false
  agent.followup({
    id: crypto.randomUUID(),
    role: 'user',
    content: [{ type: 'text', text }],
    source: { kind: 'user' },
  })
  return true
}

function titleFromContent(content) {
  const first = String(content || '').split(/\r?\n/).map((line) => line.trim()).find(Boolean) || ''
  const clean = first.replace(/^#+\s*/u, '').trim()
  const chars = Array.from(clean)
  return chars.length > 30 ? chars.slice(0, 30).join('') + '…' : clean
}

function defaultTaskTitle(content) {
  return titleFromContent(content) || '任务'
}

function touchAfterResume(agent) {
  setTimeout(() => {
    void runBoard(agent, ['heartbeat', '--agent', 'lead', '--current', '继续任务'])
  }, 800)
}

function newPrompt(title, content, autoTitle) {
  const detail = content ? `\n任务内容：${content}` : ''
  const naming = autoTitle
    ? `\n当前标题是根据内容自动生成的临时标题；请根据任务内容自行判断一个更准确的名字，并用 board.py rename --name "你的标题" 更新。`
    : ''
  return `TaskPulse 新任务已创建：${title}。${detail}${naming}\n先用 board.py status 查看当前步骤，再用 revise 换成真实计划并继续执行；不要重复 init。`
}

function updatePrompt(task, content) {
  const detail = content ? `\n补充说明：${content}` : ''
  const project = task.localProjectName ? `，project=${task.localProjectName}` : ''
  return `继续当前 TaskPulse 任务：${task.title || task.taskTitle || task.id}（taskId=${task.id}${project}）。${detail}\n先用 board.py status 查看当前步骤，然后继续未完成的工作；不要新建任务。`
}

function parseTaskArgs(raw) {
  const text = String(raw || '').trim()
  if (!text) return { title: '', content: '' }
  const first = text[0]
  if (first === '"' || first === "'") {
    let value = ''
    let closed = false
    for (let i = 1; i < text.length; i += 1) {
      const ch = text[i]
      if (ch === '\\' && text[i + 1] === first) { value += first; i += 1; continue }
      if (ch === first) { closed = true; value = value.trim(); break }
      value += ch
    }
    if (closed) {
      let content = text.slice(value.length + 2).trim()
      content = content.replace(/^(?:--|—|:)\s*/u, '').trim()
      return { title: value, content }
    }
  }
  return { title: '', content: text.replace(/^(?:--|—|:)\s*/u, '').trim() }
}

async function currentTask(agent) {
  const result = await runBoard(agent, ['--json', 'current'])
  if (!result.ok) return { error: result.stderr || result.stdout || 'cannot read current task' }
  try {
    const parsed = JSON.parse(result.stdout)
    return { task: parsed.task, pointer: parsed.pointer }
  } catch (error) {
    return { error: `invalid current task output: ${error.message}` }
  }
}

async function serverStatus(agent) {
  const health = await fetch(`${HUB}/api/health`).then((r) => (r.ok ? r.json() : null)).catch(() => null)
  const current = await currentTask(agent)
  const lines = []
  if (health?.ok) lines.push(`hub: ${HUB}/ (running)`)
  else lines.push(`hub: ${HUB}/ (down)`)
  if (current.task) {
    const task = current.task
    lines.push(`current: ${task.title || task.id} [${task.status}] ${task.progress?.done ?? 0}/${task.progress?.total ?? 0}`)
    if (task.url) lines.push(`board: ${HUB}${task.url}`)
  } else if (current.pointer) {
    lines.push(`current: ${current.pointer.name} (view missing)`)
  } else {
    lines.push('current: none')
  }
  return lines.join('\n')
}

let startupEnsureStarted = false
async function ensureHubOnStartup() {
  if (startupEnsureStarted) return
  startupEnsureStarted = true
  try {
    await execFileAsync(process.env.PYTHON || 'python3', [BOARD, '--home', HUB_HOME, 'ensure'], {
      cwd: homedir(),
      timeout: 15000,
      maxBuffer: 1024 * 1024,
      env: process.env,
    })
  } catch (error) {
    // The client card retries; a later /tp server start can also recover.
  }
}

async function execute(agent, rawInput) {
  const text = rawInput.trim()
  if (!text || text === 'help') {
    return { kind: 'success', text: [
      '/tp server start|stop|status',
      '/tp project new [名称]',
      '/tp project use <名称>',
      '/tp project rename "新名称"',
      '/tp project delete [名称]',
      '/tp project list',
      '/tp task new ["标题"] [内容...]',
      '/tp task update ["标题"] [内容...]',
      '/tp task auto ["标题"] [内容...]',
      '/tp task list',
      '/tp task rename "新名称"',
      '/tp help',
    ].join('\n') }
  }
  const match = /^(\S+)(?:\s+([\s\S]*))?$/u.exec(text)
  const group = match?.[1] || ''
  const rest = (match?.[2] || '').trim()
  if (group === 'server') {
    const action = rest || 'status'
    if (action === 'start') {
      const result = await runBoard(agent, ['ensure'])
      return result.ok
        ? { kind: 'success', text: result.stdout || `hub: ${HUB}/` }
        : { kind: 'error', text: result.stderr || 'failed to start hub' }
    }
    if (action === 'stop') {
      try {
        const response = await fetch(`${HUB}/api/shutdown`, { method: 'POST' })
        return response.ok
          ? { kind: 'success', text: 'TaskPulse hub stopped.' }
          : { kind: 'error', text: `shutdown failed: HTTP ${response.status}` }
      } catch (error) {
        return { kind: 'error', text: `shutdown failed: ${error.message}` }
      }
    }
    if (action === 'status') {
      return { kind: 'success', text: await serverStatus(agent) }
    }
    return { kind: 'error', text: 'usage: /tp server start|stop|status' }
  }
  if (group === 'project') {
    const command = /^(\S+)(?:\s+([\s\S]*))?$/u.exec(rest)
    const action = command?.[1] || 'list'
    const name = stripQuotes(command?.[2] || '')
    if (action === 'new' || action === 'use' || action === 'rename' || action === 'delete') {
      const boardArgs = ['local-project', action]
      if (name) boardArgs.push('--name', name)
      const result = await runBoard(agent, boardArgs)
      return result.ok
        ? { kind: 'success', text: result.stdout }
        : { kind: 'error', text: result.stderr || result.stdout || 'project command failed' }
    }
    if (action === 'list') {
      const result = await runBoard(agent, ['local-project', 'list'])
      return result.ok
        ? { kind: 'success', text: result.stdout }
        : { kind: 'error', text: result.stderr || 'failed to list projects' }
    }
    return { kind: 'error', text: 'usage: /tp project new|use|rename|delete|list' }
  }
  if (group === 'task') {
    const command = /^(\S+)(?:\s+([\s\S]*))?$/u.exec(rest)
    const action = command?.[1] || 'list'
    const args = parseTaskArgs(command?.[2] || '')
    if (action === 'new') {
      const title = args.title || defaultTaskTitle(args.content)
      const boardArgs = ['auto', '--title', title]
      if (args.content) boardArgs.push('--goal', args.content)
      const result = await runBoard(agent, boardArgs)
      if (!result.ok) return { kind: 'error', text: result.stderr || result.stdout || 'failed to create task' }
      followup(agent, newPrompt(title, args.content, !args.title))
      return { kind: 'success', text: result.stdout }
    }
    if (action === 'list') {
      const result = await runBoard(agent, ['local-project', 'tasks'])
      return result.ok
        ? { kind: 'success', text: result.stdout || '(no tasks in current project)' }
        : { kind: 'error', text: result.stderr || 'failed to list tasks' }
    }
    if (action === 'rename') {
      const name = stripQuotes(command?.[2] || '')
      if (!name) return { kind: 'error', text: 'usage: /tp task rename "新名称"' }
      const result = await runBoard(agent, ['rename', '--name', name])
      return result.ok
        ? { kind: 'success', text: result.stdout }
        : { kind: 'error', text: result.stderr || result.stdout || 'rename failed' }
    }
    if (action === 'update' || action === 'auto') {
      const current = await currentTask(agent)
      if (current.error) return { kind: 'error', text: current.error }
      const task = current.task
      const canContinue = task && task.status === 'running'
      if (args.title && canContinue) {
        const name = String(task.name || task.title || '')
        if (!name.includes(args.title)) {
          return { kind: 'error', text: `current task does not match "${args.title}"` }
        }
      }
      if (action === 'update' && !canContinue) {
        return { kind: 'error', text: '没有 running 的当前任务，请用 /tp task new 或 /tp task auto。' }
      }
      if (canContinue) {
        followup(agent, updatePrompt(task, args.content))
        touchAfterResume(agent)
        return { kind: 'success', text: `继续当前任务：${task.title || task.id}` }
      }
      const title = args.title || defaultTaskTitle(args.content)
      const boardArgs = ['auto', '--title', title]
      if (args.content) boardArgs.push('--goal', args.content)
      const result = await runBoard(agent, boardArgs)
      if (!result.ok) return { kind: 'error', text: result.stderr || result.stdout || 'failed to create task' }
      followup(agent, newPrompt(title, args.content, !args.title))
      return { kind: 'success', text: result.stdout }
    }
    return { kind: 'error', text: 'usage: /tp task new|update|auto|rename|list' }
  }
  return { kind: 'error', text: `unknown /tp command: ${group}` }
}

export const name = 'task-pulse'
export const inject = ['skills', 'commands']

export async function apply(ctx) {
  ctx.skills.registerProvider(() => provider)
  ctx.commands.register({
    name: 'tp',
    description: 'TaskPulse: server and task control',
    input: { hint: 'server ... / project ... / task ... / help' },
    handler: async ({ agent, rawInput }) => {
      try {
        return await execute(agent, rawInput)
      } catch (error) {
        return { kind: 'error', text: `TaskPulse error: ${error.message}` }
      }
    },
  })
  void ensureHubOnStartup()
}

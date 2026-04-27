import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(__dirname, '../..')
const defaultChromePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const chromePath = process.env.CHROME_PATH || defaultChromePath
const baseUrl = process.env.SCREENSHOT_BASE_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.SCREENSHOT_DIR || path.join(repoRoot, 'docs/screenshots')
const userDataDir = process.env.CHROME_USER_DATA_DIR || '/tmp/jons-gradebook-demo-screenshots'
const debugPort = Number(process.env.CHROME_DEBUG_PORT || 9223)
const viewport = {
  width: Number(process.env.SCREENSHOT_WIDTH || 1440),
  height: Number(process.env.SCREENSHOT_HEIGHT || 1000),
}

const routes = [
  { route: '/', filename: '01-dashboard.png', check: 'Action Dashboard' },
  { route: '/tasks', filename: '02-task-queue.png', check: 'Task Queue' },
  { route: '/courses/201/gradebook', filename: '03-gradebook.png', check: 'BIO 210: Research Methods' },
  { route: '/courses/201/matches', filename: '04-match-workbench.png', check: 'Match Queue Workbench' },
  { route: '/students/101', filename: '05-student-profile.png', check: 'Maya Chen' },
  { route: '/advising', filename: '06-advising.png', check: 'Advising' },
  { route: '/documents', filename: '07-documents.png', check: 'Methods Draft Feedback' },
  { route: '/reports', filename: '08-reports.png', check: 'Templates' },
  { route: '/llm', filename: '09-llm-workbench.png', check: 'LLM Workbench' },
  { route: '/settings', filename: '10-settings-demo-mode.png', check: 'Interface Preferences' },
]

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function getJson(url, options) {
  const response = await fetch(url, options)
  if (!response.ok) {
    throw new Error(`Request failed ${response.status}: ${await response.text()}`)
  }
  return response.json()
}

async function waitForCdp() {
  const versionUrl = `http://127.0.0.1:${debugPort}/json/version`
  for (let attempt = 0; attempt < 80; attempt += 1) {
    try {
      await getJson(versionUrl)
      return
    } catch {
      await sleep(125)
    }
  }
  throw new Error(`Chrome debugging endpoint did not start on port ${debugPort}`)
}

async function ensureChrome() {
  try {
    await getJson(`http://127.0.0.1:${debugPort}/json/version`)
    return null
  } catch {
    const chrome = spawn(
      chromePath,
      [
        '--headless=new',
        `--remote-debugging-port=${debugPort}`,
        `--user-data-dir=${userDataDir}`,
        `--window-size=${viewport.width},${viewport.height}`,
        '--hide-scrollbars',
        'about:blank',
      ],
      { stdio: 'ignore' },
    )
    await waitForCdp()
    return chrome
  }
}

async function newTarget(url = 'about:blank') {
  return getJson(`http://127.0.0.1:${debugPort}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' })
}

async function withCdp(webSocketDebuggerUrl, callback) {
  if (typeof WebSocket === 'undefined') {
    throw new Error('This script requires a Node runtime with global WebSocket support.')
  }

  const socket = new WebSocket(webSocketDebuggerUrl)
  await new Promise((resolve, reject) => {
    socket.addEventListener('open', resolve, { once: true })
    socket.addEventListener('error', reject, { once: true })
  })

  let nextId = 0
  const pending = new Map()
  const events = []
  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data)
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id)
      pending.delete(message.id)
      if (message.error) {
        reject(new Error(JSON.stringify(message.error)))
      } else {
        resolve(message.result || {})
      }
      return
    }
    if (message.method) events.push(message)
  })

  function command(method, params = {}) {
    const id = ++nextId
    socket.send(JSON.stringify({ id, method, params }))
    return new Promise((resolve, reject) => pending.set(id, { resolve, reject }))
  }

  async function waitForEvent(method, timeoutMs = 10000) {
    const existingIndex = events.findIndex((event) => event.method === method)
    if (existingIndex >= 0) return events.splice(existingIndex, 1)[0]

    return new Promise((resolve, reject) => {
      const startedAt = Date.now()
      const timer = setInterval(() => {
        const index = events.findIndex((event) => event.method === method)
        if (index >= 0) {
          clearInterval(timer)
          resolve(events.splice(index, 1)[0])
        } else if (Date.now() - startedAt > timeoutMs) {
          clearInterval(timer)
          reject(new Error(`Timed out waiting for ${method}`))
        }
      }, 50)
    })
  }

  try {
    return await callback(command, waitForEvent, events)
  } finally {
    socket.close()
  }
}

async function main() {
  await fs.mkdir(screenshotDir, { recursive: true })
  const chrome = await ensureChrome()
  const target = await newTarget('about:blank')

  try {
    const results = await withCdp(target.webSocketDebuggerUrl, async (command, waitForEvent, events) => {
      async function navigate(url) {
        events.length = 0
        await command('Page.navigate', { url })
        await waitForEvent('Page.loadEventFired', 15000).catch(() => {})
      }

      async function waitForText(text, timeoutMs = 10000) {
        const expression = `new Promise((resolve) => {
          const done = () => document.body && document.body.innerText.includes(${JSON.stringify(text)});
          if (done()) return resolve(true);
          const observer = new MutationObserver(() => {
            if (done()) {
              observer.disconnect();
              resolve(true);
            }
          });
          observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
          setTimeout(() => {
            observer.disconnect();
            resolve(done());
          }, ${timeoutMs});
        })`
        const result = await command('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
        return result.result?.value === true
      }

      await command('Page.enable')
      await command('Runtime.enable')
      await command('Emulation.setDeviceMetricsOverride', {
        width: viewport.width,
        height: viewport.height,
        deviceScaleFactor: 1,
        mobile: false,
      })

      await navigate(`${baseUrl}/settings`)
      await command('Runtime.evaluate', {
        expression: `
          localStorage.setItem('gradebook-demo-mode', 'enabled');
          localStorage.setItem('gradebook-app-theme', 'default');
          window.dispatchEvent(new CustomEvent('gradebook-ui-preferences-changed'));
        `,
        returnByValue: true,
      })

      const captured = []
      for (const item of routes) {
        await navigate(`${baseUrl}${item.route}`)
        const checkFound = await waitForText(item.check, 10000)
        await command('Runtime.evaluate', { expression: 'window.scrollTo(0, 0)', returnByValue: true })
        const screenshot = await command('Page.captureScreenshot', {
          format: 'png',
          fromSurface: true,
          captureBeyondViewport: false,
        })
        await fs.writeFile(path.join(screenshotDir, item.filename), Buffer.from(screenshot.data, 'base64'))
        const demoResult = await command('Runtime.evaluate', {
          expression: 'document.body.innerText.includes("Showing screenshot-safe example student and class data")',
          returnByValue: true,
        })
        captured.push({
          file: path.relative(repoRoot, path.join(screenshotDir, item.filename)),
          route: item.route,
          checkFound,
          demoBanner: demoResult.result?.value === true,
        })
      }
      return captured
    })

    console.log(JSON.stringify(results, null, 2))
  } finally {
    await getJson(`http://127.0.0.1:${debugPort}/json/close/${target.id}`).catch(() => {})
    if (chrome) chrome.kill()
  }
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})

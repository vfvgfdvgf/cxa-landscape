import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const chromeCandidates = [
  process.env.CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].filter(Boolean);
const chromePath = chromeCandidates.find((candidate) => existsSync(candidate));
if (!chromePath) throw new Error("Chrome or Edge was not found. Set CHROME_PATH to run the browser audit.");

const targetUrl = process.argv[2] || "http://127.0.0.1:3000/";
const width = Number(process.argv[3] || 390);
const height = Number(process.argv[4] || 844);
const navigationPath = process.argv[5] || "";
const profileDir = mkdtempSync(join(tmpdir(), "getsiaq-browser-audit-"));
const chrome = spawn(chromePath, [
  "--headless=new",
  "--disable-gpu",
  "--hide-scrollbars",
  "--no-first-run",
  "--remote-debugging-pipe",
  `--user-data-dir=${profileDir}`,
  "about:blank",
], { stdio: ["ignore", "ignore", "inherit", "pipe", "pipe"] });

let nextId = 0;
let incoming = "";
const pending = new Map();
chrome.stdio[4].setEncoding("utf8");
chrome.stdio[4].on("data", (chunk) => {
  incoming += chunk;
  const messages = incoming.split("\0");
  incoming = messages.pop() || "";
  for (const raw of messages) {
    if (!raw) continue;
    const message = JSON.parse(raw);
    if (!message.id || !pending.has(message.id)) continue;
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result);
  }
});

function send(method, params = {}, sessionId) {
  const id = ++nextId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    chrome.stdio[3].write(`${JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) })}\0`);
  });
}

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

try {
  await send("Browser.getVersion");
  const { targetId } = await send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: width <= 720 }, sessionId);
  await send("Page.enable", {}, sessionId);
  await send("Page.navigate", { url: targetUrl }, sessionId);
  await wait(5000);
  if (navigationPath) {
    const selector = JSON.stringify(`a[href="${navigationPath}"]`);
    await send("Runtime.evaluate", {
      expression: `document.querySelector(${selector})?.click()`,
      returnByValue: true,
    }, sessionId);
    await wait(5000);
  }
  const expression = `JSON.stringify({
    url: location.href,
    title: document.title,
    mainText: (document.querySelector('main')?.innerText || '').replace(/\\s+/g, ' ').slice(0, 220),
    viewport: { width: innerWidth, height: innerHeight, scrollWidth: document.documentElement.scrollWidth },
    hero: (() => { const node = document.querySelector('.cinematic-hero, .home-hero, .page-hero'); if (!node) return null; const r = node.getBoundingClientRect(); return { x: r.x, right: r.right, width: r.width, height: r.height }; })(),
    container: (() => { const node = document.querySelector('.cinematic-hero .container, .home-hero .container, .page-hero .container'); if (!node) return null; const r = node.getBoundingClientRect(); return { x: r.x, right: r.right, width: r.width }; })(),
    heading: (() => { const node = document.querySelector('h1'); if (!node) return null; const r = node.getBoundingClientRect(); return { x: r.x, right: r.right, width: r.width, fontSize: getComputedStyle(node).fontSize }; })(),
    header: (() => { const node = document.querySelector('.header-inner'); if (!node) return null; const r = node.getBoundingClientRect(); return { x: r.x, right: r.right, width: r.width }; })(),
    seo: {
      description: document.querySelector('meta[name="description"]')?.content || '',
      canonical: document.querySelector('link[rel="canonical"]')?.href || '',
      ogImage: document.querySelector('meta[property="og:image"]')?.content || '',
      h1Count: document.querySelectorAll('h1').length,
      jsonLd: [...document.querySelectorAll('script[type="application/ld+json"]')].map(node => { try { JSON.parse(node.textContent); return true; } catch { return false; } })
    },
    images: [...document.images].map(img => { const r = img.getBoundingClientRect(); return { alt: img.alt, loaded: img.complete && img.naturalWidth > 0, visible: r.bottom > 0 && r.top < innerHeight, top: Math.round(r.top), width: img.naturalWidth, src: img.currentSrc }; }).slice(0, 30),
    mediaUsage: (() => {
      const normalize = value => { try { const url = new URL(value, location.origin); return (url.host + url.pathname).toLowerCase(); } catch { return value.split(/[?#]/)[0].toLowerCase(); } };
      const sources = [
        ...[...document.images].map(node => ({ kind: 'image', src: node.currentSrc || node.src })),
        ...[...document.querySelectorAll('video')].map(node => ({ kind: 'video', src: node.currentSrc || node.querySelector('source')?.src || '' })),
      ].filter(item => item.src);
      const counts = sources.reduce((result, item) => { const key = item.kind + ':' + normalize(item.src); result[key] = (result[key] || 0) + 1; return result; }, {});
      return { counts, violations: Object.entries(counts).filter(([, count]) => count > 3) };
    })(),
    homepageSections: [...document.querySelectorAll('[data-section-key]')].map(node => {
      const rect = node.getBoundingClientRect();
      return { key: node.dataset.sectionKey, order: Number(node.dataset.sectionOrder || 0), top: Math.round(rect.top + scrollY), height: Math.round(rect.height) };
    }),
    buttons: [...document.querySelectorAll('a.cinematic-button, button.cinematic-button')].map(node => {
      const rect = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return { label: node.textContent.trim(), width: Math.round(rect.width), height: Math.round(rect.height), display: style.display, visible: rect.width > 0 && rect.height > 0 };
    }),
    fallbacks: document.querySelectorAll('.image-fallback, .hero-image-fallback').length
  })`;
  const evaluation = await send("Runtime.evaluate", { expression, returnByValue: true }, sessionId);
  process.stdout.write(`${evaluation.result.value}\n`);
} finally {
  const chromeExited = new Promise((resolve) => chrome.once("exit", resolve));
  chrome.kill();
  await Promise.race([chromeExited, wait(2000)]);
  try {
    rmSync(profileDir, { recursive: true, force: true, maxRetries: 4, retryDelay: 250 });
  } catch {
    // Chrome can briefly retain a Windows profile lock; audit results remain valid.
  }
}

#!/usr/bin/env node
/**
 * Visual compare: live explore-showrooms vs local replica.
 * Usage: node tools/compare-explore.mjs
 * Requires: npx playwright (chromium)
 */
import { chromium } from "playwright";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { createRequire } from "module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const out = path.join(root, "docs", "screenshots");
const REF = "https://www.themotorcoachstore.com/explore-showrooms";
const LOCAL = process.env.LOCAL_URL || "http://127.0.0.1:3460/explore-showrooms/";

const VIEWPORTS = [
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1366x768", width: 1366, height: 768 },
  { name: "1280x800", width: 1280, height: 800 },
  { name: "1024x768", width: 1024, height: 768 },
  { name: "768x1024", width: 768, height: 1024 },
  { name: "390x844", width: 390, height: 844 },
  { name: "375x812", width: 375, height: 812 },
];

function ensureDirs() {
  for (const d of ["ref", "local", "diff"]) {
    fs.mkdirSync(path.join(out, d), { recursive: true });
  }
}

async function waitReady(page) {
  await page.waitForLoadState("networkidle", { timeout: 45000 }).catch(() => {});
  await page.waitForTimeout(800);
  await page.evaluate(async () => {
    const imgs = [...document.images];
    await Promise.all(
      imgs.map((img) =>
        img.complete
          ? Promise.resolve()
          : new Promise((r) => {
              img.addEventListener("load", r, { once: true });
              img.addEventListener("error", r, { once: true });
            })
      )
    );
    if (document.fonts?.ready) await document.fonts.ready;
  });
}

async function measure(page) {
  return page.evaluate(() => {
    const header = document.querySelector("header, .site-header, .header");
    const h1 = document.querySelector("h1");
    const cards = [...document.querySelectorAll(".rail-card, [class*='card']")].slice(0, 20);
    const bands = [...document.querySelectorAll(".explore-band, section")];
    const firstCard = document.querySelector(".wide-cards .rail-card, .explore-band .rail-card");
    const firstImg = firstCard?.querySelector("img");
    const hr = header?.getBoundingClientRect();
    const cr = firstCard?.getBoundingClientRect();
    const ir = firstImg?.getBoundingClientRect();
    return {
      innerWidth: innerWidth,
      scrollHeight: document.documentElement.scrollHeight,
      headerH: hr ? Math.round(hr.height) : null,
      h1: h1
        ? {
            text: h1.innerText.trim(),
            fontSize: getComputedStyle(h1).fontSize,
            transform: getComputedStyle(h1).textTransform,
          }
        : null,
      firstCard: cr ? { w: Math.round(cr.width), h: Math.round(cr.height) } : null,
      firstImg: ir ? { w: Math.round(ir.width), h: Math.round(ir.height) } : null,
      bandCount: bands.length,
      cardSample: cards.length,
    };
  });
}

/** Simple pixel diff using PNG raw via sharp if available, else skip */
async function tryDiff(refPath, localPath, diffPath) {
  try {
    const require = createRequire(import.meta.url);
    let sharp;
    try {
      sharp = require("sharp");
    } catch {
      return { skipped: true, reason: "sharp not installed" };
    }
    const ref = sharp(refPath);
    const local = sharp(localPath);
    const rMeta = await ref.metadata();
    const lMeta = await local.metadata();
    const w = Math.min(rMeta.width, lMeta.width);
    const h = Math.min(rMeta.height, lMeta.height);
    const rBuf = await ref.extract({ left: 0, top: 0, width: w, height: h }).raw().ensureAlpha().toBuffer();
    const lBuf = await local.extract({ left: 0, top: 0, width: w, height: h }).raw().ensureAlpha().toBuffer();
    const outBuf = Buffer.alloc(w * h * 4);
    let diffPx = 0;
    const thresh = 28;
    for (let i = 0; i < w * h; i++) {
      const o = i * 4;
      const dr = Math.abs(rBuf[o] - lBuf[o]);
      const dg = Math.abs(rBuf[o + 1] - lBuf[o + 1]);
      const db = Math.abs(rBuf[o + 2] - lBuf[o + 2]);
      const d = (dr + dg + db) / 3;
      if (d > thresh) {
        diffPx++;
        outBuf[o] = 255;
        outBuf[o + 1] = 0;
        outBuf[o + 2] = 0;
        outBuf[o + 3] = 255;
      } else {
        outBuf[o] = rBuf[o];
        outBuf[o + 1] = rBuf[o + 1];
        outBuf[o + 2] = rBuf[o + 2];
        outBuf[o + 3] = 80;
      }
    }
    await sharp(outBuf, { raw: { width: w, height: h, channels: 4 } })
      .png()
      .toFile(diffPath);
    const pct = ((diffPx / (w * h)) * 100).toFixed(2);
    return { skipped: false, diffPx, pct, w, h };
  } catch (e) {
    return { skipped: true, reason: String(e.message || e) };
  }
}

async function main() {
  ensureDirs();
  const browser = await chromium.launch({ headless: true });
  const results = [];

  for (const vp of VIEWPORTS) {
    const row = { viewport: vp.name, ref: null, local: null, diff: null };
    for (const [label, url] of [
      ["ref", REF],
      ["local", LOCAL],
    ]) {
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        deviceScaleFactor: 1,
      });
      const page = await context.newPage();
      try {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
        await waitReady(page);
        const file = path.join(out, label, `${vp.name}-full.png`);
        await page.screenshot({ path: file, fullPage: true });
        const vpFile = path.join(out, label, `${vp.name}-viewport.png`);
        await page.screenshot({ path: vpFile, fullPage: false });
        row[label] = await measure(page);
        row[label].file = file;
      } catch (e) {
        row[label] = { error: String(e.message || e) };
      }
      await context.close();
    }

    if (row.ref?.file && row.local?.file) {
      const diffFile = path.join(out, "diff", `${vp.name}-diff.png`);
      row.diff = await tryDiff(row.ref.file, row.local.file, diffFile);
      if (!row.diff.skipped) row.diff.file = diffFile;
    }
    results.push(row);
    console.log(
      JSON.stringify({
        viewport: vp.name,
        refH: row.ref?.scrollHeight,
        localH: row.local?.scrollHeight,
        refCard: row.ref?.firstCard,
        localCard: row.local?.firstCard,
        diff: row.diff,
      })
    );
  }

  await browser.close();
  const reportPath = path.join(out, "compare-report.json");
  fs.writeFileSync(reportPath, JSON.stringify(results, null, 2));
  console.log("Wrote", reportPath);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

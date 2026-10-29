import fs from "fs";
import path from "path";

export default async function capture(page) {
  const outRoot = "/Users/joshuamkpanam/Desktop/bus/docs/screenshots";
  const viewports = [
    { name: "1440x900", width: 1440, height: 900 },
    { name: "1366x768", width: 1366, height: 768 },
    { name: "1280x800", width: 1280, height: 800 },
    { name: "1024x768", width: 1024, height: 768 },
    { name: "768x1024", width: 768, height: 1024 },
    { name: "390x844", width: 390, height: 844 },
    { name: "375x812", width: 375, height: 812 },
  ];
  const targets = [
    { label: "ref", url: "https://www.themotorcoachstore.com/explore-showrooms" },
    { label: "local", url: "http://127.0.0.1:3460/explore-showrooms/" },
  ];
  const results = [];
  for (const t of targets) {
    for (const vp of viewports) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(t.url, { waitUntil: "domcontentloaded", timeout: 60000 });
      await page.waitForTimeout(1400);
      await page.evaluate(async () => {
        const imgs = [...document.images];
        await Promise.all(
          imgs.map((img) =>
            img.complete
              ? 1
              : new Promise((r) => {
                  img.onload = img.onerror = r;
                })
          )
        );
        if (document.fonts?.ready) await document.fonts.ready;
      });
      const dir = path.join(outRoot, t.label);
      fs.mkdirSync(dir, { recursive: true });
      const full = path.join(dir, `${vp.name}-full.png`);
      const view = path.join(dir, `${vp.name}-viewport.png`);
      await page.screenshot({ path: full, fullPage: true });
      await page.screenshot({ path: view, fullPage: false });
      const metrics = await page.evaluate(() => {
        const header = document.querySelector("header, .site-header");
        const h1 = document.querySelector("h1");
        const bands = [...document.querySelectorAll(".explore-band")];
        const card =
          document.querySelector(".wide-cards .rail-card") ||
          document.querySelector(".rail-card");
        const ogvCard = bands[1]?.querySelector(".rail-card");
        const hr = header?.getBoundingClientRect();
        const cr = card?.getBoundingClientRect();
        const or = ogvCard?.getBoundingClientRect();
        const ir = card?.querySelector("img")?.getBoundingClientRect();
        return {
          scrollHeight: document.documentElement.scrollHeight,
          headerH: hr ? Math.round(hr.height) : null,
          h1Size: h1 ? getComputedStyle(h1).fontSize : null,
          lokiCard: cr ? { w: Math.round(cr.width), h: Math.round(cr.height) } : null,
          lokiImg: ir ? { w: Math.round(ir.width), h: Math.round(ir.height) } : null,
          ogvCard: or ? { w: Math.round(or.width), h: Math.round(or.height) } : null,
          bandCount: bands.length,
          overflowX: document.documentElement.scrollWidth > innerWidth + 2,
        };
      });
      results.push({ target: t.label, viewport: vp.name, ...metrics, full });
    }
  }
  fs.writeFileSync(path.join(outRoot, "compare-report.json"), JSON.stringify(results, null, 2));
  return results;
}

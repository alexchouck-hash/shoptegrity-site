import { chromium } from 'playwright';
import { mkdirSync } from 'fs';
import path from 'path';
import { pathToFileURL } from 'url';

const W = 760, H = 440;
mkdirSync('previews', { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(path.resolve('loop.html')).href);
await page.waitForFunction(() => typeof window.seek === 'function');

const sampleTimes = [1, 4, 7, 10, 13, 16, 20, 23];

for (const t of sampleTimes) {
  await page.evaluate((time) => window.seek(time), t);
  const outPath = `previews/shot_t${String(t).padStart(2, '0')}.png`;
  await page.screenshot({ path: outPath });
  console.log(`Captured preview at t = ${t}s -> ${outPath}`);
}

await browser.close();
console.log('All sample screenshots captured successfully.');

import { chromium } from 'playwright';
import { mkdirSync } from 'fs';
import path from 'path';

const FPS = 20, W = 760, H = 440;
mkdirSync('frames', { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
await page.goto('file:///' + path.resolve('loop.html').replace(/\\/g, '/'));
await page.waitForFunction(() => typeof window.seek === 'function');

const total = Math.round((await page.evaluate(() => window.DURATION)) * FPS);
console.log(`Starting capture: ${total} frames at ${FPS} fps (${W}x${H})...`);

for (let i = 0; i < total; i++) {
  await page.evaluate((t) => window.seek(t), i / FPS);
  await page.screenshot({ path: `frames/f_${String(i).padStart(4, '0')}.png` });
  if (i % 40 === 0 || i === total - 1) {
    console.log(`Captured frame ${i + 1} of ${total} (${Math.round(((i + 1) / total) * 100)}%)`);
  }
}

await browser.close();
console.log(`captured ${total} frames`);

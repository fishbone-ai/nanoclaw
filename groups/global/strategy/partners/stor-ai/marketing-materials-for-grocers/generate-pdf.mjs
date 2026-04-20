import puppeteer from 'puppeteer';
import { fileURLToPath } from 'url';
import path from 'path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const targets = [
  { html: 'israel/fishbone-grocery-il.html', pdf: 'israel/fishbone-grocery-il.pdf' },
  { html: 'us/fishbone-grocery-us.html', pdf: 'us/fishbone-grocery-us.pdf' },
];

const only = process.argv[2];
const selected = only ? targets.filter(t => t.html.startsWith(`${only}/`)) : targets;
if (only && selected.length === 0) {
  console.error(`no target matches "${only}" (use: israel | us)`);
  process.exit(1);
}

const browser = await puppeteer.launch({
  headless: 'new',
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

for (const { html, pdf } of selected) {
  const htmlPath = path.resolve(__dirname, html);
  const outputPath = path.resolve(__dirname, pdf);

  const page = await browser.newPage();
  await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle0' });
  await page.pdf({
    path: outputPath,
    format: 'A4',
    printBackground: true,
    margin: { top: '20px', right: '0', bottom: '0', left: '0' },
    preferCSSPageSize: false,
    scale: 0.8,
  });
  await page.close();
  console.log(`PDF saved to: ${outputPath}`);
}

await browser.close();

// Draws a Mermaid file with pele to SVG, then screenshots it in headless Chromium for the PNG.
import { readFileSync, writeFileSync } from 'node:fs'
import { render } from 'pele'
import { chromium } from 'playwright-core'

const [mmdPath, pngPath, chromePath] = process.argv.slice(2)
const { svg } = render(readFileSync(mmdPath, 'utf8'))
writeFileSync(pngPath.replace(/\.png$/, '.svg'), svg)

const browser = await chromium.launch({ executablePath: chromePath || undefined })
const page = await browser.newPage({ deviceScaleFactor: 2 })
await page.setContent(`<body style="margin:16px;background:#fff">${svg}</body>`)
await page.locator('svg.pele').screenshot({ path: pngPath })
await browser.close()

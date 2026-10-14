#!/usr/bin/env node

const fs = require("fs");

async function chromePng(svg, output, width, height, executablePath) {
  const { chromium } = require("playwright");
  const browser = await chromium.launch({
    headless: true,
    ...(executablePath ? { executablePath } : { channel: "chrome" }),
  });
  try {
    const context = await browser.newContext({
      viewport: { width, height }, deviceScaleFactor: 1,
    });
    // The approved renderer embeds all brand fonts and images in the SVG.
    // A missing external resource must not turn into an export substitute.
    await context.route("**/*", route => route.abort());
    const page = await context.newPage();
    await page.setContent(
      `<style>html,body{margin:0;width:${width}px;height:${height}px}svg{display:block}</style>${svg.toString("utf8")}`
    );
    await page.evaluate(async () => {
      await document.fonts.ready;
      await Promise.all(Array.from(document.querySelectorAll("svg image"), element =>
        new Promise((resolve, reject) => {
          const image = new Image();
          image.onload = resolve;
          image.onerror = () => reject(new Error("Immagine SVG incorporata non caricabile"));
          image.src = element.getAttribute("href") || element.getAttribute("xlink:href") || "";
        })
      ));
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    });
    const card = page.locator("body > svg");
    const bounds = await card.boundingBox();
    if (!bounds || Math.abs(bounds.width - width) > .01 || Math.abs(bounds.height - height) > .01) {
      throw new Error("Le dimensioni della prova SVG non corrispondono al PNG richiesto");
    }
    await card.screenshot({ path: output, type: "png" });
  } finally {
    await browser.close();
  }
}

async function main() {
  const [input, output, widthRaw, heightRaw, backend = "sharp", executablePath] = process.argv.slice(2);
  const width = Number(widthRaw);
  const height = Number(heightRaw);
  if (!input || !output || !Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1) {
    throw new Error("Uso: svg_to_png.cjs input.svg output.png width height [sharp|chrome] [browser]");
  }
  const svg = fs.readFileSync(input);
  if (backend === "chrome") {
    await chromePng(svg, output, width, height, executablePath);
    return;
  }
  if (backend !== "sharp") throw new Error(`Convertitore non supportato: ${backend}`);
  const sharp = require("sharp");
  await sharp(svg, { density: 144 })
    .resize(width, height, { fit: "fill" })
    .png({ compressionLevel: 9, adaptiveFiltering: true })
    .toFile(output);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exit(1);
});


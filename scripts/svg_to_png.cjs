#!/usr/bin/env node

const fs = require("fs");
const sharp = require("sharp");

async function main() {
  const [input, output, widthRaw, heightRaw] = process.argv.slice(2);
  const width = Number(widthRaw);
  const height = Number(heightRaw);
  if (!input || !output || !Number.isInteger(width) || !Number.isInteger(height)) {
    throw new Error("Uso: svg_to_png.cjs input.svg output.png width height");
  }
  const svg = fs.readFileSync(input);
  await sharp(svg, { density: 144 })
    .resize(width, height, { fit: "fill" })
    .png({ compressionLevel: 9, adaptiveFiltering: true })
    .toFile(output);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exit(1);
});


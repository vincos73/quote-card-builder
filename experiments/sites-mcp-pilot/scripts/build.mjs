import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";

const hosting = JSON.parse(await readFile(".openai/hosting.json", "utf8"));
if (!Object.hasOwn(hosting, "project_id")) {
  throw new Error("Provision the private Site before building its deployment artifact.");
}

await mkdir("dist/server", { recursive: true });
await mkdir("dist/.openai", { recursive: true });
await copyFile("src/worker.mjs", "dist/server/index.js");
await copyFile(".openai/hosting.json", "dist/.openai/hosting.json");
await writeFile("dist/server/wrangler.json", JSON.stringify({
  name: "quote-card-builder-sites-mcp-pilot",
  main: "index.js",
  compatibility_date: "2026-09-01",
  compatibility_flags: ["nodejs_compat"],
}, null, 2) + "\n");

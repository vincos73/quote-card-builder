/* File input stays in the editor; the server validates bytes before adoption. */
(function (root) {
  "use strict";
  const mime = {ttf:"font/ttf", otf:"font/otf", woff:"font/woff", woff2:"font/woff2", png:"image/png", jpg:"image/jpeg", jpeg:"image/jpeg", webp:"image/webp", svg:"image/svg+xml"};
  async function asset(file) {
    if (!file || file.size < 1 || file.size > 4 * 1024 * 1024) throw new Error("Each brand asset must be between 1 byte and 4 MB.");
    const type = mime[file.name.split(".").pop().toLowerCase()];
    if (!type) throw new Error("Use TTF, OTF, WOFF or WOFF2 fonts, or PNG, JPEG, WebP or SVG logos.");
    const bytes = new Uint8Array(await file.arrayBuffer());
    let binary = "";
    for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
    return {mime_type:type, data_base64:btoa(binary)};
  }
  function download(value, filename) {
    const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2) + "\n"], {type:"application/json"}));
    const link = document.createElement("a"); link.href = url; link.download = filename;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  root.QcbBrandKit = {asset, download};
})(typeof window !== "undefined" ? window : globalThis);

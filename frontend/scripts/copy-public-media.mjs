import { cp, mkdir, readdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const frontend = path.resolve(here, "..");
const source = path.resolve(frontend, "..", "imge");
const target = path.join(frontend, "public", "media");

await rm(target, { recursive: true, force: true });
await mkdir(target, { recursive: true });
const files = await readdir(source, { withFileTypes: true });
let copied = 0;
for (const item of files) {
  if (!item.isFile() || !/\.(?:webp|avif|png|jpe?g|svg)$/i.test(item.name)) continue;
  await cp(path.join(source, item.name), path.join(target, item.name));
  copied += 1;
}
console.log(`Mirrored ${copied} optimized media assets into frontend/public/media.`);

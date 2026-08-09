import { spawn } from "node:child_process";

const port = process.env.PORT || "3000";
const host = process.env.HOST || "0.0.0.0";
const child = spawn(process.execPath, ["node_modules/next/dist/bin/next", "start", "-p", port, "-H", host], {
  stdio: "inherit",
  env: process.env,
});

child.on("exit", (code) => process.exit(code ?? 1));

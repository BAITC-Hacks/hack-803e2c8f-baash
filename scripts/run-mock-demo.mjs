import { spawn } from "node:child_process";

const child = spawn(
  process.execPath,
  ["node_modules/next/dist/bin/next", "dev", "--hostname", "127.0.0.1"],
  {
    cwd: new URL("../apps/web/", import.meta.url),
    stdio: "inherit",
    env: { ...process.env, PULSE109_DEMO_MOCKS: "1", API_URL: "" },
    windowsHide: true,
  },
);

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => child.kill(signal));
}
child.on("exit", (code) => process.exit(code ?? 1));
child.on("error", (error) => {
  console.error(`Could not start the local demo: ${error.message}`);
  process.exit(1);
});

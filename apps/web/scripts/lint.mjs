import {spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";

const eslint = fileURLToPath(new URL("../node_modules/eslint/bin/eslint.js", import.meta.url));
const result = spawnSync(process.execPath, [eslint, "."], {
  stdio: "inherit",
  env: {...process.env, ESLINT_USE_FLAT_CONFIG: "false"},
});

process.exit(result.status ?? 1);

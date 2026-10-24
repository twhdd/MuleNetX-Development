import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "node_modules", "src/api/schema.d.ts"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: { ecmaVersion: 2022, globals: { ...globals.browser, ...globals.node } },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "no-restricted-globals": ["error", { name: "fetch", message: "HTTP goes through src/api/client.ts (SRS §20.2)." }],
      "no-restricted-properties": [
        "error",
        { object: "window", property: "localStorage", message: "The session lives in memory only (SRS §20.2)." },
        { object: "window", property: "sessionStorage", message: "The session lives in memory only (SRS §20.2)." },
      ],
    },
  },
  {
    files: ["src/api/client.ts", "tests/**"],
    rules: { "no-restricted-globals": "off" },
  },
);

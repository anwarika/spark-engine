#!/usr/bin/env node
/**
 * Esbuild React compiler for Spark components.
 * Resolves @/components/ui/* to window.ShadcnUI.
 * Usage: node esbuild-build.mjs input.tsx
 */
import * as esbuild from "esbuild";
import { readFileSync } from "fs";

const inputPath = process.argv[2];
if (!inputPath) {
  console.error("Usage: node esbuild-build.mjs <input.tsx>");
  process.exit(1);
}
const code = readFileSync(inputPath, "utf8");

const shadcnPlugin = {
  name: "shadcn-external",
  setup(build) {
    build.onResolve({ filter: /^@\/components\/ui\// }, () => ({
      path: "shadcn",
      namespace: "shadcn-external",
    }));
    build.onLoad({ filter: /.*/, namespace: "shadcn-external" }, () => ({
      contents: "module.exports = typeof window !== 'undefined' ? window.ShadcnUI : {}",
      loader: "js",
    }));
  },
};

const reactGlobalPlugin = {
  name: "react-global",
  setup(build) {
    build.onResolve({ filter: /^react$/ }, () => ({ path: "react", namespace: "react-global" }));
    build.onResolve({ filter: /^react-dom$/ }, () => ({ path: "react-dom", namespace: "react-global" }));
    build.onLoad({ filter: /.*/, namespace: "react-global" }, (args) => {
      const mod = args.path === "react-dom" ? "ReactDOM" : "React";
      return {
        contents: `module.exports = typeof window !== 'undefined' ? window.${mod} : {}`,
        loader: "js",
      };
    });
  },
};

const result = await esbuild.build({
  stdin: { contents: code, sourcefile: inputPath, loader: "tsx" },
  bundle: true,
  minify: true,
  format: "iife",
  target: "es2020",
  jsx: "automatic",
  jsxImportSource: "react",
  globalName: "SparkComponent",
  platform: "browser",
  plugins: [reactGlobalPlugin, shadcnPlugin],
  outfile: "/dev/null",
  write: false,
});

const out = result.outputFiles[0];
process.stdout.write(out.text);

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
    // Handle bare react / react-dom and the automatic JSX runtime sub-paths
    build.onResolve({ filter: /^react(\/jsx-runtime|\/jsx-dev-runtime)?$/ }, () => ({
      path: "react",
      namespace: "react-global",
    }));
    build.onResolve({ filter: /^react-dom(\/client)?$/ }, () => ({
      path: "react-dom",
      namespace: "react-global",
    }));
    build.onLoad({ filter: /.*/, namespace: "react-global" }, (args) => {
      if (args.path === "react-dom") {
        return {
          contents: `module.exports = typeof window !== 'undefined' ? window.ReactDOM : {}`,
          loader: "js",
        };
      }
      // react, react/jsx-runtime, react/jsx-dev-runtime all resolve to window.React
      return {
        contents: `
var React = typeof window !== 'undefined' ? window.React : {};
module.exports = React;
// Provide jsx-runtime exports from the same global
module.exports.jsx = React.createElement;
module.exports.jsxs = React.createElement;
module.exports.jsxDEV = React.createElement;
module.exports.Fragment = React.Fragment;
`,
        loader: "js",
      };
    });
  },
};

const rechartsGlobalPlugin = {
  name: "recharts-global",
  setup(build) {
    build.onResolve({ filter: /^recharts$/ }, () => ({
      path: "recharts",
      namespace: "recharts-global",
    }));
    build.onLoad({ filter: /.*/, namespace: "recharts-global" }, () => ({
      contents: `module.exports = typeof window !== 'undefined' ? window.Recharts : {}`,
      loader: "js",
    }));
  },
};

const lucideGlobalPlugin = {
  name: "lucide-global",
  setup(build) {
    build.onResolve({ filter: /^lucide-react$/ }, () => ({
      path: "lucide-react",
      namespace: "lucide-global",
    }));
    build.onLoad({ filter: /.*/, namespace: "lucide-global" }, () => ({
      // Use a Proxy so any missing icon returns a null-rendering stub rather
      // than undefined — prevents React error #130 when LucideReact isn't loaded.
      contents: `
var _icons = (typeof window !== 'undefined' && window.LucideReact) ? window.LucideReact : {};
module.exports = new Proxy(_icons, {
  get: function(target, key) {
    var icon = target[key];
    if (icon !== undefined) return icon;
    return function NullIcon() { return null; };
  }
});`,
      loader: "js",
    }));
  },
};

// Wrap the component module so its default export is reliably at window.SparkComponent.default.
// esbuild IIFE + globalName assigns the CJS exports object, but 'export default Fn' maps to
// exports.default — this wrapper ensures it works regardless of how the LLM writes the export.
const wrappedCode = `
// ---- user component ----
${code}
`;

const result = await esbuild.build({
  stdin: { contents: wrappedCode, sourcefile: inputPath, loader: "tsx" },
  bundle: true,
  minify: false,
  format: "iife",
  target: "es2020",
  jsx: "automatic",
  jsxImportSource: "react",
  globalName: "__spark_module__",
  platform: "browser",
  plugins: [reactGlobalPlugin, rechartsGlobalPlugin, lucideGlobalPlugin, shadcnPlugin],
  footer: {
    js: `
// Expose as window.SparkComponent with a reliable .default pointer
(function() {
  var m = window.__spark_module__;
  var comp = (m && (m.default || m)) || null;
  window.SparkComponent = { default: comp };
})();
`,
  },
  outfile: "/dev/null",
  write: false,
});

const out = result.outputFiles[0];
process.stdout.write(out.text);

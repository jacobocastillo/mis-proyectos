import { registerHooks } from "node:module";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const frontendRootUrl = pathToFileURL(path.resolve(import.meta.dirname, "..") + path.sep);

function resolveCandidate(basePath) {
  const candidates = [
    basePath,
    `${basePath}.ts`,
    `${basePath}.tsx`,
    `${basePath}.js`,
    `${basePath}.jsx`,
    path.join(basePath, "index.ts"),
    path.join(basePath, "index.tsx"),
    path.join(basePath, "index.js"),
    path.join(basePath, "index.jsx"),
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return pathToFileURL(candidate).href;
    }
  }

  return null;
}

function resolveAliasSpecifier(specifier) {
  const absolutePath = path.resolve(import.meta.dirname, "..", specifier.slice(2));
  const resolvedUrl = resolveCandidate(absolutePath);

  if (resolvedUrl) {
    return resolvedUrl;
  }

  return new URL(specifier.slice(2), frontendRootUrl).href;
}

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier.startsWith("@/")) {
      return nextResolve(resolveAliasSpecifier(specifier), context);
    }

    if (
      (specifier.startsWith("./") || specifier.startsWith("../")) &&
      context.parentURL?.startsWith(frontendRootUrl.href)
    ) {
      const parentPath = new URL(context.parentURL);
      const absolutePath = path.resolve(path.dirname(parentPath.pathname), specifier);
      const resolvedUrl = resolveCandidate(absolutePath);

      if (resolvedUrl) {
        return nextResolve(resolvedUrl, context);
      }
    }

    return nextResolve(specifier, context);
  },
});

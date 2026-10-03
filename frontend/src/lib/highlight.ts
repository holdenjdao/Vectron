// Syntax highlighting with highlight.js core and only the languages Vectron emits.

import hljs from "highlight.js/lib/core";
import ini from "highlight.js/lib/languages/ini";
import json from "highlight.js/lib/languages/json";
import markdown from "highlight.js/lib/languages/markdown";
import plaintext from "highlight.js/lib/languages/plaintext";
import python from "highlight.js/lib/languages/python";
import xml from "highlight.js/lib/languages/xml";
import yaml from "highlight.js/lib/languages/yaml";

import { extension } from "./format";

hljs.registerLanguage("python", python);
hljs.registerLanguage("json", json);
hljs.registerLanguage("ini", ini);
hljs.registerLanguage("markdown", markdown);
hljs.registerLanguage("yaml", yaml);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("plaintext", plaintext);

export type Language = "python" | "json" | "ini" | "markdown" | "yaml" | "xml" | "plaintext";

const BY_EXTENSION: Record<string, Language> = {
  py: "python",
  pyi: "python",
  json: "json",
  toml: "ini",
  ini: "ini",
  cfg: "ini",
  md: "markdown",
  markdown: "markdown",
  yaml: "yaml",
  yml: "yaml",
  svg: "xml",
  xml: "xml",
  mmd: "plaintext",
  txt: "plaintext",
};

const LABEL: Record<Language, string> = {
  python: "Python",
  json: "JSON",
  ini: "TOML",
  markdown: "Markdown",
  yaml: "YAML",
  xml: "XML",
  plaintext: "Text",
};

export function languageFor(path: string): Language {
  return BY_EXTENSION[extension(path)] ?? "plaintext";
}

export function languageLabel(path: string): string {
  const lang = languageFor(path);
  if (lang === "ini") return extension(path) === "toml" ? "TOML" : "INI";
  if (lang === "plaintext" && extension(path) === "mmd") return "Mermaid";
  return LABEL[lang];
}

/** Above this size highlighting is skipped to keep the viewer responsive. */
const MAX_HIGHLIGHT_CHARS = 400_000;

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** Returns escaped, highlighted HTML for `code` (safe to inject: hljs escapes the text). */
export function highlightCode(code: string, path: string): string {
  const language = languageFor(path);
  if (language === "plaintext" || code.length > MAX_HIGHLIGHT_CHARS) return escapeHtml(code);
  try {
    return hljs.highlight(code, { language, ignoreIllegals: true }).value;
  } catch {
    return escapeHtml(code);
  }
}

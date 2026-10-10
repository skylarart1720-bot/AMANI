import { Children, cloneElement, isValidElement, ReactNode, useCallback, useEffect, useState } from "react";
import bootstrap from "./locales/bootstrap.json";
import registry from "./locales/languages.json";
import source from "./locales/en.json";

export type Language = keyof typeof bootstrap;
export const languageOptions = registry;
const catalogues: Record<string, Record<string, string>> = bootstrap;
export function isLanguage(value: string | null): value is Language {
  return !!value && registry.some((item) => item.code === value);
}

export function translate(value: string, language: Language): string {
  if (language === "en") return value;
  const text = value.replace(/\s+/g, " ").trim();
  const dictionary = catalogues[language] || {};
  if (dictionary[text]) return dictionary[text];
  // Dates, counts and staff IDs remain unchanged; translate their fixed labels.
  let result = value;
  for (const fragment of ["Contact checked", "Last checked", "Needs re-checking before you rely on it.", "Checked", "Visit", "Human support request", "Response time is not guaranteed.", "organisations | Confirm availability directly. Listings do not imply a partnership.", "active accounts", "contacts need checking", "in progress", "queued", "resolved"])
    if (dictionary[fragment] && result.includes(fragment)) result = result.replace(fragment, dictionary[fragment]);
  return result;
}

export function useLanguage() {
  const [language, updateLanguage] = useState<Language>("en");
  const [coverage, setCoverage] = useState({status: "complete", translated: Object.keys(source).length, total: Object.keys(source).length});
  const [revision, setRevision] = useState(0);
  const setLanguage = useCallback((value: Language) => {
    if (!isLanguage(value)) return;
    updateLanguage(value);
    localStorage.setItem("amani-language", value);
  }, []);
  const refreshTranslations = useCallback(() => setRevision((value) => value + 1), []);
  useEffect(() => {
    const saved = localStorage.getItem("amani-language");
    if (isLanguage(saved)) updateLanguage(saved);
  }, []);
  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = registry.find((row) => row.code === language)?.direction || "ltr";
    let active = true;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const localCount = Object.keys(catalogues[language] || {}).length;
    setCoverage({status: localCount === Object.keys(source).length ? "complete" : "partial", translated: localCount, total: Object.keys(source).length});
    const load = async () => {
      try {
        const response = await fetch(`/api/support/languages/${encodeURIComponent(language)}`, {signal: controller.signal, cache: "no-store"});
        if (!response.ok) return;
        const result = await response.json();
        if (!active || result.language !== language) return;
        if (result.translations && typeof result.translations === "object") catalogues[language] = result.translations;
        setCoverage({status: result.status, translated: result.translated, total: result.total});
        if (result.status === "generating") timer = setTimeout(() => void load(), 10000);
      } catch { /* Offline navigation remains available from the bundled catalogue. */ }
    };
    void load();
    return () => { active = false; controller.abort(); clearTimeout(timer); };
  }, [language, revision]);
  return {language, setLanguage, coverage, refreshTranslations};
}

// Only UI wording is localised. Preserve original transcripts, proper names,
// identifiers and editable values; never alter event handlers or form values.
export function localize(tree: ReactNode, language: Language): ReactNode {
  if (language === "en") return tree;
  const walk = (node: ReactNode): ReactNode => {
    if (typeof node === "string") return translate(node, language);
    if (!isValidElement<Record<string, unknown>>(node)) return node;
    const props: Record<string, unknown> = {};
    for (const key of ["title", "aria-label", "placeholder"])
      if (typeof node.props[key] === "string") props[key] = translate(node.props[key] as string, language);
    return cloneElement(node, props, node.props["data-original-text"] ? node.props.children as ReactNode : Children.map(node.props.children as ReactNode, walk));
  };
  return Children.map(tree, walk);
}

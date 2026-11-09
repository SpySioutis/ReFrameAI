import { describe, expect, it } from "vitest";
import en from "../locales/en.json";
import el from "../locales/el.json";

function keys(obj: unknown, prefix = ""): string[] {
  if (typeof obj !== "object" || obj === null) return [prefix];
  return Object.entries(obj as Record<string, unknown>).flatMap(([k, v]) =>
    keys(v, prefix ? `${prefix}.${k}` : k)
  );
}

describe("i18n parity", () => {
  it("el.json has every key en.json has (English fallback covers the rest)", () => {
    const enKeys = new Set(keys(en));
    const elKeys = new Set(keys(el));
    const missing = Array.from(enKeys).filter((k) => !elKeys.has(k));
    expect(missing).toEqual([]);
  });

  it("no empty strings in either locale", () => {
    for (const [name, dict] of [["en", en], ["el", el]] as const) {
      const walk = (o: unknown, path: string) => {
        if (typeof o === "string") {
          expect(o.trim().length, `${name}:${path}`).toBeGreaterThan(0);
        } else if (typeof o === "object" && o !== null) {
          for (const [k, v] of Object.entries(o)) walk(v, `${path}.${k}`);
        }
      };
      walk(dict, name);
    }
  });
});

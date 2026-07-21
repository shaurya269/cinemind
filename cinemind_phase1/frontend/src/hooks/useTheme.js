import { useEffect, useState } from "react";

const STORAGE_KEY = "cinemind:theme";

function getInitialTheme() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "light" || saved === "dark") return saved;
  return null; // follow OS preference
}

export function useTheme() {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    const root = document.documentElement;
    if (theme) {
      root.setAttribute("data-theme", theme);
      localStorage.setItem(STORAGE_KEY, theme);
    } else {
      root.removeAttribute("data-theme");
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [theme]);

  function toggle() {
    setTheme((current) => {
      if (current === "dark") return "light";
      if (current === "light") return "dark";
      // No explicit preference yet: flip away from whatever the OS gives us.
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      return prefersDark ? "light" : "dark";
    });
  }

  const resolved =
    theme ?? (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");

  return { theme: resolved, toggle };
}

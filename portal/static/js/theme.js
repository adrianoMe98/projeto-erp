(function () {
    "use strict";

    const storageKey = "erp-theme";

    function systemTheme() {
        return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }

    function selectedTheme() {
        const savedTheme = window.localStorage.getItem(storageKey);
        return savedTheme === "dark" || savedTheme === "light" ? savedTheme : systemTheme();
    }

    function updateButtons(theme) {
        document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
            const switchesToDark = theme === "light";
            const icon = button.querySelector("[data-theme-icon]");
            const label = button.querySelector("[data-theme-label]");

            if (icon) {
                icon.textContent = switchesToDark ? "☾" : "☀";
            }
            if (label) {
                label.textContent = switchesToDark ? "Tema escuro" : "Tema claro";
            }

            const actionLabel = switchesToDark ? "Ativar tema escuro" : "Ativar tema claro";
            button.setAttribute("aria-label", actionLabel);
            button.setAttribute("title", actionLabel);
        });
    }

    function applyTheme(theme, persist) {
        document.documentElement.dataset.theme = theme;
        document.documentElement.setAttribute("data-bs-theme", theme);
        if (persist) {
            window.localStorage.setItem(storageKey, theme);
            window.localStorage.setItem("jazzmin-theme-mode", theme);
        }
        updateButtons(theme);
    }

    document.addEventListener("DOMContentLoaded", function () {
        applyTheme(selectedTheme(), false);
        document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
            button.addEventListener("click", function () {
                const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
                applyTheme(nextTheme, true);
            });
        });
    });

    window.addEventListener("storage", function (event) {
        if (event.key === storageKey && (event.newValue === "dark" || event.newValue === "light")) {
            applyTheme(event.newValue, false);
        }
    });
})();

(function () {
    "use strict";

    const portalStorageKey = "erp-theme";
    const adminStorageKey = "jazzmin-theme-mode";

    function currentTheme() {
        const savedTheme =
            window.localStorage.getItem(portalStorageKey) ||
            window.localStorage.getItem(adminStorageKey);
        if (savedTheme === "dark" || savedTheme === "light") {
            return savedTheme;
        }
        return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }

    function updateButton(theme) {
        const button = document.getElementById("erp-admin-theme-toggle");
        if (!button) {
            return;
        }
        const switchesToDark = theme === "light";
        button.innerHTML = switchesToDark ? "☾&nbsp; Escuro" : "☀&nbsp; Claro";
        button.setAttribute(
            "aria-label",
            switchesToDark ? "Ativar tema escuro" : "Ativar tema claro",
        );
    }

    function applyTheme(theme, persist) {
        document.documentElement.dataset.theme = theme;
        document.documentElement.setAttribute("data-bs-theme", theme);
        if (persist) {
            window.localStorage.setItem(portalStorageKey, theme);
            window.localStorage.setItem(adminStorageKey, theme);
        }
        updateButton(theme);
    }

    function createToggle() {
        if (document.getElementById("erp-admin-theme-toggle")) {
            return;
        }

        const navbar = document.querySelector(".main-header .navbar-nav:last-child");
        if (!navbar) {
            return;
        }

        const item = document.createElement("li");
        item.className = "nav-item d-flex align-items-center";

        const button = document.createElement("button");
        button.type = "button";
        button.id = "erp-admin-theme-toggle";
        button.className = "btn btn-sm btn-outline-light erp-admin-theme-toggle";
        button.addEventListener("click", function () {
            const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
            applyTheme(nextTheme, true);
        });

        item.appendChild(button);
        navbar.prepend(item);
    }

    document.addEventListener("DOMContentLoaded", function () {
        createToggle();
        applyTheme(currentTheme(), false);
    });

    window.addEventListener("storage", function (event) {
        if (
            (event.key === portalStorageKey || event.key === adminStorageKey) &&
            (event.newValue === "dark" || event.newValue === "light")
        ) {
            applyTheme(event.newValue, false);
        }
    });
})();

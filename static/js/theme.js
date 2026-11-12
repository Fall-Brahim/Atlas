(function () {
    const storageKey = 'atlascloud-theme';
    const root = document.documentElement;
    const toggles = document.querySelectorAll('[data-theme-toggle]');
    const sidebar = document.querySelector('[data-sidebar-toggle]');
    const sidebarPanel = document.getElementById('app-sidebar');
    const appContent = document.getElementById('app-content');
    const sidebarLabels = document.querySelectorAll('[data-sidebar-label]');
    const sidebarFooter = document.querySelector('[data-sidebar-footer]');
    const sidebarTheme = document.querySelector('[data-sidebar-theme]');
    const sidebarStorageKey = 'atlascloud-sidebar-collapsed';

    function preferredTheme() {
        const storedTheme = localStorage.getItem(storageKey);
        if (storedTheme === 'light' || storedTheme === 'dark') {
            return storedTheme;
        }
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function applyTheme(theme) {
        const isDark = theme === 'dark';
        root.classList.toggle('dark', isDark);
        toggles.forEach(function (toggle) {
            const icon = toggle.querySelector('[data-theme-icon]');
            const label = toggle.querySelector('[data-theme-label]');
            toggle.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
            if (icon) {
                icon.textContent = isDark ? '☀' : '☾';
            }
            if (label) {
                label.textContent = isDark ? 'Light mode' : 'Dark mode';
            }
        });
    }

    applyTheme(preferredTheme());

    toggles.forEach(function (toggle) {
        toggle.addEventListener('click', function () {
            const nextTheme = root.classList.contains('dark') ? 'light' : 'dark';
            localStorage.setItem(storageKey, nextTheme);
            applyTheme(nextTheme);
        });
    });

    function applySidebarState(collapsed) {
        if (!sidebarPanel || !appContent) {
            return;
        }
        sidebarPanel.classList.toggle('w-64', !collapsed);
        sidebarPanel.classList.toggle('w-20', collapsed);
        appContent.classList.toggle('lg:pl-64', !collapsed);
        appContent.classList.toggle('lg:pl-20', collapsed);
        sidebarLabels.forEach(function (label) {
            label.classList.toggle('hidden', collapsed);
        });
        if (sidebarFooter) {
            sidebarFooter.classList.toggle('flex-col', collapsed);
            sidebarFooter.classList.toggle('items-center', collapsed);
        }
        if (sidebarTheme) {
            sidebarTheme.classList.toggle('w-10', collapsed);
            sidebarTheme.classList.toggle('flex-none', collapsed);
            sidebarTheme.classList.toggle('p-2', collapsed);
            sidebarTheme.classList.toggle('px-2', !collapsed);
        }
        sidebarPanel.querySelectorAll('[data-sidebar-toggle-icon]').forEach(function (icon) {
            icon.innerHTML = collapsed
                ? '<path d="m9 6 6 6-6 6"/><path d="M5 5v14"/>'
                : '<path d="m15 6-6 6 6 6"/><path d="M19 5v14"/>';
        });
        sidebar.setAttribute('aria-label', collapsed ? 'Expand navigation' : 'Collapse navigation');
    }

    if (sidebar && sidebarPanel && appContent) {
        const collapsed = localStorage.getItem(sidebarStorageKey) === 'true';
        applySidebarState(collapsed);
        sidebar.addEventListener('click', function () {
            const nextState = !sidebarPanel.classList.contains('w-20');
            localStorage.setItem(sidebarStorageKey, String(nextState));
            applySidebarState(nextState);
        });
    }
})();

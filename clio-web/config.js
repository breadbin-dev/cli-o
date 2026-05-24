
// config.js
let CONFIG = {};
let configLoaded = false;

async function loadConfig() {
    try {
        const response = await fetch('/config.json');

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        CONFIG = await response.json();
        configLoaded = true;

        window.SITE_TITLE = CONFIG.site_title;
        window.SITE_THEME = CONFIG.site_theme;
        window.API_HOST = CONFIG.api_host;

        return CONFIG;

    } catch (error) {
        console.error('Failed to load configuration:', error);

        window.SITE_TITLE = "Cli-o";
        window.SITE_THEME = "theme_BLUE";
        window.API_HOST = "/router";

        throw error;
    }
}

function getConfig(key, defaultValue = null) {
    return configLoaded && CONFIG[key] !== undefined ? CONFIG[key] : defaultValue;
}

function isConfigLoaded() {
    return configLoaded;
}

export default loadConfig;

// JavaScript configuration loader
const fs = require('fs');
const path = require('path');

function loadConfig(configPath) {
    const fullPath = path.resolve(configPath);
    const content = fs.readFileSync(fullPath, 'utf8');
    return JSON.parse(content);
}

function mergeConfigs(defaultConfig, userConfig) {
    return { ...defaultConfig, ...userConfig };
}

module.exports = { loadConfig, mergeConfigs };

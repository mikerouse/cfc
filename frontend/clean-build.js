#!/usr/bin/env node

/**
 * Clean old Vite build files before building new ones
 * This prevents accumulation of main-*.js and main-*.css files
 */

const fs = require('fs');
const path = require('path');

const buildDir = path.join(__dirname, '..', 'static', 'frontend');

function cleanOldBuilds() {
  if (!fs.existsSync(buildDir)) {
    console.log('Build directory does not exist yet');
    return;
  }

  const files = fs.readdirSync(buildDir);
  let cleaned = 0;

  files.forEach(file => {
    // Remove old main-*.js and main-*.css files (but keep .vite directory)
    if (file.match(/^main-.*\.(js|css)$/)) {
      const filePath = path.join(buildDir, file);
      fs.unlinkSync(filePath);
      console.log(`Removed: ${file}`);
      cleaned++;
    }
  });

  console.log(`Cleaned ${cleaned} old build files`);
}

cleanOldBuilds();
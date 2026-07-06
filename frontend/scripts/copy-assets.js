import fs from "fs";
import path from "path";

const srcDir = path.resolve("../data");
const destDir = path.resolve("public/data");

function copyRecursiveSync(src, dest) {
  const exists = fs.existsSync(src);
  const stats = exists && fs.statSync(src);
  const isDirectory = exists && stats.isDirectory();
  if (isDirectory) {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }
    fs.readdirSync(src).forEach((childItemName) => {
      copyRecursiveSync(
        path.join(src, childItemName),
        path.join(dest, childItemName)
      );
    });
  } else {
    const parentDir = path.dirname(dest);
    if (!fs.existsSync(parentDir)) {
      fs.mkdirSync(parentDir, { recursive: true });
    }
    fs.copyFileSync(src, dest);
  }
}

try {
  copyRecursiveSync(path.join(srcDir, "heroes.json"), path.join(destDir, "heroes.json"));
  copyRecursiveSync(path.join(srcDir, "win_rates.json"), path.join(destDir, "win_rates.json"));
  copyRecursiveSync(path.join(srcDir, "portraits"), path.join(destDir, "portraits"));
  console.log("Static assets copied successfully (cross-platform).");
} catch (err) {
  console.error("Failed to copy assets:", err);
  process.exit(1);
}

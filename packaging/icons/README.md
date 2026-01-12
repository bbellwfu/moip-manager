# App Icons

This directory contains the application icons for MoIP Manager.

## Required Files

- `icon.icns` - macOS app icon (required for macOS builds)
- `icon.ico` - Windows app icon (required for Windows builds)
- `icon.png` - Source PNG (1024x1024 recommended)

## Generating Icons

### From a 1024x1024 PNG source:

**macOS (.icns):**
```bash
# Create iconset directory
mkdir icon.iconset
sips -z 16 16     icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32     icon.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32     icon.png --out icon.iconset/icon_32x32.png
sips -z 64 64     icon.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128   icon.png --out icon.iconset/icon_128x128.png
sips -z 256 256   icon.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256   icon.png --out icon.iconset/icon_256x256.png
sips -z 512 512   icon.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512   icon.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png
iconutil -c icns icon.iconset
rm -rf icon.iconset
```

**Windows (.ico):**
Use an online converter like https://convertico.com or ImageMagick:
```bash
convert icon.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico
```

## Placeholder Icons

If icons are missing, PyInstaller will use system defaults. Add proper icons before production release.

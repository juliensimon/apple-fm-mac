#!/bin/bash
# The square and oblong test images of REPORT 4.6, 8 and 27.2, rebuilt from a system icon with `sips`.
# On the Mac of 2026-10-24 these commands write files byte-identical to the ones measured (checked by MD5).
# The icon belongs to Apple, which is why the images are made here and not shipped.
#
# Run: bash data/make_square_images.sh        (writes data/img/*.png)
# The OCR, QR and barcode images come from: swiftc data/make_test_images.swift -o data/make_test_images && data/make_test_images data/img
set -eu
IMG="$(cd "$(dirname "$0")" && pwd)/img"
mkdir -p "$IMG"
sips -s format png /System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/Accounts.icns --out "$IMG/base.png" > /dev/null
for s in 64 128 256 512 768 1024 2048; do sips -z "$s" "$s" "$IMG/base.png" --out "$IMG/i$s.png" > /dev/null; done
sips -z 4000 4000 "$IMG/base.png" --out "$IMG/big4000.png" > /dev/null
sips -z 300 100 "$IMG/base.png" --out "$IMG/tall100x300.png" > /dev/null      # sips -z takes height, then width
sips -z 100 300 "$IMG/base.png" --out "$IMG/wide300x100.png" > /dev/null
sips -z 256 1024 "$IMG/base.png" --out "$IMG/w1024x256.png" > /dev/null
sips -z 1000 4000 "$IMG/base.png" --out "$IMG/pano4000x1000.png" > /dev/null
ls -la "$IMG"

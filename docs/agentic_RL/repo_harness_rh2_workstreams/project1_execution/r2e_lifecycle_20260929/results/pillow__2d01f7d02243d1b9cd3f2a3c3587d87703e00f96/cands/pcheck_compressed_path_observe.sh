#!/bin/bash
cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "from PIL import Image, features; print('libtiff', features.check('libtiff')); p='/tmp/r2e_pi_lzw.tif'; Image.new('L', (100, 100)).save(p, tiffinfo={262: 0}, compression='tiff_lzw'); r=Image.open(p); print('tag262', r.tag_v2[262], 'compression', r.info.get('compression'), 'pixel00', r.getpixel((0, 0)))"
echo RH2_CMD_RC=$?

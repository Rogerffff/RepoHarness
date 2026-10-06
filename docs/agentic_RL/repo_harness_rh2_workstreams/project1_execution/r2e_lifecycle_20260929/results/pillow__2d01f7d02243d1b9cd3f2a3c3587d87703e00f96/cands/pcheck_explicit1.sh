#!/bin/bash
cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "from PIL import Image; p='/tmp/r2e_pi_explicit1.tif'; Image.new('L', (8, 8), 77).save(p, tiffinfo={262: 1}); r=Image.open(p); print('tag262', r.tag_v2[262], 'pixel00', r.getpixel((0, 0))); assert r.tag_v2[262] == 1, 'explicit BlackIsZero not kept'"
echo RH2_CMD_RC=$?

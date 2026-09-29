#!/bin/bash
cd /testbed && PYTHONDONTWRITEBYTECODE=1 python -c "from PIL import Image; im=Image.open('Tests/images/hopper.ppm').convert('1'); p='/tmp/r2e_pi_g4.tif'; im.save(p, tiffinfo={262: 0}, compression='group4'); r=Image.open(p); print('tag262', r.tag_v2[262], 'same', r.tobytes() == im.tobytes()); assert r.tag_v2[262] == 0 and r.tobytes() == im.tobytes()"
echo RH2_CMD_RC=$?

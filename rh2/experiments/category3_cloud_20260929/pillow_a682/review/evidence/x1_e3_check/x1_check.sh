cd /testbed
echo "HEAD $(git rev-parse HEAD) date $(git log -1 --format=%cI HEAD)"
echo "fix_object_type: $(git cat-file -t a682ceaf47abbe28dc70c6bd4aab06f8f3f4ac90 2>&1)"
for pair in 2b061b68dbbf4fb590ab532b6fdffea8ee063ae8:608ccd059438d21f8b2b307e93066e4551376035 2d01f7d02243d1b9cd3f2a3c3587d87703e00f96:5db0969f6f9873bd15aededab9ef413f043f1ea4 3a61c9e95e5c0a2da5736956e2dbafa57a9ede07:355820742bc2ca8a90d9c25661e8988cbd7cb5de 3ac9396e8c991e7baab66187af2a35c3f4e83605:48e4e0722e6afd4cf38ffc70d9eeea235085ff4e 4bc6483564ae1a254911e98280b9a501f047a2e0:a6efaa1ae1d0bc83bf1cbbe7170f7734a7f4203d f9d3ee0f4888f7618071c0a5315c916062e78854:df4bb3460000d222b3ac077dad925c32093f6b32; do
  fix=${pair%%:*}; base=${pair##*:}
  fa=$(git merge-base --is-ancestor $fix HEAD 2>/dev/null && echo yes || echo no)
  ba=$(git merge-base --is-ancestor $base HEAD 2>/dev/null && echo yes || echo no)
  echo "task ${fix:0:8}: fix_is_ancestor=$fa base_is_ancestor=$ba"
done

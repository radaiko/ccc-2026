#!/bin/bash
# Rebuild every opus Level 6 binary from source (binaries are not committed: they are arm64/host specific).
# Usage: ./build.sh        (from levels/level6/candidates/opus)
# beam_e4 gets a profile-guided build (identical output, ~14% less CPU on Apple M5); A/B-test it on new hardware.
set -e
cd "$(dirname "$0")"
F="-O3 -march=native -std=c++17"
for pair in beam:beam.cpp beam_p:beam.cpp beamL:beamL.cpp beam_l2:beam_l2.cpp beam_e:beam_e.cpp beam_h:beam_h.cpp \
            cyc2:cyc2.cpp cyc3:cyc3.cpp cycle:cycle.cpp polish:polish.cpp retbeam:retbeam.cpp sweepdp:sweepdp.cpp; do
    out=${pair%%:*}; src=${pair#*:}
    [ -f "$src" ] && clang++ $F -o "$out" "$src" && echo "built $out"
done
cp beam_h beam_h2 2>/dev/null || true
# PGO build of the main beam (beam_e.cpp) -> beam_e4
D=../../data
T=$(mktemp -d)
clang++ -O3 -mcpu=native -std=c++17 -fprofile-instr-generate -o "$T/prof" beam_e.cpp
export HFORBID=1 WTM=2 WTS=2
LLVM_PROFILE_FILE=$T/p1.profraw "$T/prof" $D/in_level-6_4-enormous.txt 117 150 1 100 1 0.3 0.25 >/dev/null &
LLVM_PROFILE_FILE=$T/p2.profraw "$T/prof" $D/in_level-6_3-large.txt 64 300 1 100 1 0.3 0.25 >/dev/null &
LLVM_PROFILE_FILE=$T/p3.profraw "$T/prof" $D/in_level-6_2-medium.txt 50 500 1 100 1 0.3 0.25 >/dev/null &
wait
xcrun llvm-profdata merge -output="$T/b.profdata" "$T"/p*.profraw
clang++ -O3 -mcpu=native -std=c++17 -flto -fprofile-instr-use="$T/b.profdata" -o beam_e4 beam_e.cpp
echo "built beam_e4 (PGO)"

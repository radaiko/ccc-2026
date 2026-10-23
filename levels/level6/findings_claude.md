# Level 6 findings (cloud Claude agent, no input files)

- The inputs can be rebuilt from the output programs alone. At the first submission tick the pattern is exactly
  one connected matter component (its halo must be clean). Try every (tick, component) of a no-submission
  simulation, keep the ones whose program ends on a submission; count = number of submissions.
- The radius is often ambiguous: all six corner beams pass through the centre, so while every emitter stays
  within about R of its corner the same program gives the same centred pattern for every radius (medium 173/210,
  large 170/190, enormous 126/140 ambiguous). Programs in output2/ are checked against EVERY surviving reading.
  The opus harness re-validates output2/ against the real inputs anyway.
- Suffix re-beam (resuf_e.py, beam_h, HFORBID=1 WTM=2 WTS=2, w 100,1,0.3,0.25, width 1500, new seed 11,
  cuts d5,d9,s0,p0.9) still finds 1-2 line wins on large/enormous.

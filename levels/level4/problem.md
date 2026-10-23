# Level 4

Extracted automatically from data/level-4.pdf. Tables and figures may have lost their layout: if something is unclear, look at the PDF itself.

--- page 1 ---
LEVEL 4

--- page 2 ---
SIX ON THE RAIL
FAB-42 > program loaded: night_shift_FINAL_v3_really_final.fab
FAB-42 > RUN? [y/N] _
FAB-42 is finally complete: six emitters, one for each
direction, riding on a rail along the border.
Each emitter can move along the border, toggle on
and off or just sit there quietly.
The night shift left a stack of programs. No
comments, no notes, and no idea what any of them
will leave on the board.
Before anyone presses RUN on the real machine,
simulate each program and find out.
LEVEL 4

--- page 3 ---
The nanofabricator now has 6 emitters, one for each direction.
▪ Emitters always start in their corner
▪ Emitters can be moved along the border, but not rotated
▪ Multiple emitters can be in the same place at the same time
▪ Emitters can be active or inactive
▪ Active emitters produce laser beams
▪ Emitters are inactive at the start
▪ If they are activated, they stay active until they are deactivated
Your task is to simulate a program that controls the emitters.
▪ A program is a list of instruction lines
▪ An instruction line has 6 instructions, one for each emitter
Initial emitter positions
▪ Instructions are explained on the next page
F T - T B -
LEVEL 4

--- page 4 ---
Instruction Description
F move emitter one cell in clockwise direction
B move emitter one cell in counterclockwise direction
T
toggle emitter state:
activate if it was inactive,
deactivate if it was active
- no operation
Each tick, one instruction line is
processed
1. All 6 instructions are executed simultaneously
2. Matter is created and destroyed
▪ An example is provided on the next page
▪ You are given a list of radii and programs
▪ At the start of each program the board is empty
▪ Simulate each program
LEVEL 4

--- page 5 ---
---2-*-*-3---
--*-O-O-O-*--
-*-O-O-O-O-4-
*-O-M-M-O-M-*
-1-O-M-M-O-*-
--6-O-O-O-*--
---*-5-*-*---
Example state
Tick N
---2-*-*-3---
--*-O-O-O-*--
-*-O-O-O-O-4-
1-O-M-M-O-M-*
-*-O-M-M-O-*-
--6-O-O-O-*--
---*-*-5-*---
F T - T B -
is executed
---2-*-*-3---
--*-O-O-O-*--
-*-O-M-M-O-4-
1-O-M-O-O-M-*
-*-O-M-M-O-*-
--6-O-O-O-*--
---*-*-5-*---
Matter is created
and destroyed
Tick N+1
LEVEL 4

--- page 6 ---
Input
Name Description Example
N Number of programs 3
2
3
R The radius of the board
F T T F - -
repeated N times
T - - T - -
L Number of instruction lines
T B - B T -
3
6
Program A list of L instruction lines
Each line contains 6 instructions, separated by spaces
B B B B B B
- - - T T -
- - T - T -
- T - T - -
T - T - - -
Empty line between programs
...
Output
Name Description Example
repeated N times
--*-*-*--
-*-M-M-*-
Board The character representation of the board
You can print the border with emitters or without. Both will be judged as correct.
*-M-O-O-*
-*-M-M-*-
--*-*-*--
---*-*-*-*---
--*-O-O-O-*--
Mandatory empty line between boards
...

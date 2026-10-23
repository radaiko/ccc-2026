# Level 6

Extracted automatically from data/level-6.pdf. Tables and figures may have lost their layout: if something is unclear, look at the PDF itself.

--- page 1 ---
LEVEL 6

--- page 2 ---
MACHINE TIME ISN’T CHEAP
FAB-42 > operating system ..... FULLY OPERATIONAL
FAB-42 > incoming challenge ... PER TICK
FAB-42 is built and fully operational.
Dr. Ångström invites everyone into the lab. Everyone
must compete to produce a list of patterns.
The shortest programs win.
LEVEL 6

--- page 3 ---
Now you’re a real programmer.
▪ You are given a list of patterns and how many times each must be submitted
▪ For each, generate a program that creates the pattern the required number of times
This level is an optimization level.
▪ Your score is the total number of instruction lines in your programs
▪ A lower score is better
LEVEL 6

--- page 4 ---
Input
Name Description Example
N Number of patterns 3
3 7 13 3
---*-*-*-*---
Pattern info repeated N times
The radius of the board, the number of rows, the number of columns,
and the required count, separated by spaces
--*-O-O-O-*--
-*-O-M-M-O-*-
*-O-M-O-O-O-*
-*-O-M-M-O-*-
--*-O-O-O-*--
---*-*-*-*---
Pattern The character representation of a pattern
3 7 13 1
---*-*-*-*---
--*-M-M-M-*--
Empty line between patterns
...
Output
Name Description Example
F - - - - -
repeated N times
F - - - - -
- - B - - -
Program A list of instruction lines
Each line contains 6 instructions, separated by spaces
- - B - - -
- - T - - -
- - F - - -
B - - - - -
- - F - - -
- - B - - -
Mandatory empty line between programs
...

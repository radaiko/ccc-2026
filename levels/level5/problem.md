# Level 5

Extracted automatically from data/level-5.pdf. Tables and figures may have lost their layout: if something is unclear, look at the PDF itself.

--- page 1 ---
LEVEL 5

--- page 2 ---
THE PICKY ARM
FAB-42 > pick-up arm ... INSTALLED
FAB-42 > pattern ....... LOADED
FAB-42 now has a pick-up arm. It watches the board,
and the moment a specific pattern is complete, it lifts
it off and stores it.
The arm is picky: it only takes the pattern if it is in
exactly the given position and no other matter is
touching it. Otherwise, it waits.
Count how many patterns each program really
produces.
LEVEL 5

--- page 3 ---
The nanofabricator was made to produce patterns.
▪ You are given a list of programs and patterns
▪ A pattern is a group of connected matter
▪ Whenever the pattern is detected, it is submitted automatically
− Submitted means that all its matter is removed from the board
− “Pattern Detection” is explained on the next page
▪ Simulate each program and count how many patterns were submitted
LEVEL 5

--- page 4 ---
Pattern Detection
A pattern is submitted if:
▪ All matter of the pattern is present on the board in the exact same position as it is given
▪ There may be other matter on the board, but it must not be adjacent to any matter of the pattern
---*-*-*-*---
--*-O-O-O-*--
---*-*-*-*---
--*-O-O-O-*--
---*-*-*-*---
--*-O-O-O-*--
---*-*-*-*---
--*-O-O-O-*--
-*-O-M-M-O-*-
-*-O-M-M-M-*-
-*-M-M-O-O-*-
-*-O-M-M-O-*-
*-O-M-O-O-O-*
*-M-O-O-O-O-*
*-O-M-O-O-M-*
-*-O-M-M-O-*-
-*-M-M-O-O-*-
-*-O-M-M-O-*-
--*-O-O-O-*--
---*-*-*-*---
--*-O-O-O-*--
---*-*-*-*---
--*-O-O-O-*--
---*-*-*-*---
--*-O-O-O-*--
---*-*-*-*---
Example
pattern
Invalid because of
adjacent matter
Invalid because
it is shifted
Valid
LEVEL 5

--- page 5 ---
A tick now works in the following order:
1. 2. 3. One instruction line is executed
Matter is created and destroyed
If a valid pattern is present, it is submitted
---2-*-*-3---
--*-O-O-O-*--
-*-O-O-O-O-4-
--*-O-O-O-*--
-*-O-O-O-O-4-
-*-O-M-M-O-4-
*-O-M-M-O-M-*
1-O-M-M-O-M-*
1-O-M-O-O-M-*
-1-O-M-M-O-*-
-*-O-M-M-O-*-
--6-O-O-O-*--
---*-5-*-*---
--6-O-O-O-*--
---*-*-5-*---
--6-O-O-O-*--
---*-*-5-*---
Example state
F T - T B -
is executed
Matter is
created and
destroyed
---2-*-*-3---
--*-O-O-O-*--
-*-O-O-O-O-4-
1-O-O-O-O-M-*
-*-O-O-O-O-*-
--6-O-O-O-*--
---*-*-5-*---
Pattern is
submitted
LEVEL 5

--- page 6 ---
Input
Name Description Example
N Number of programs 2
3 7 13
---*-*-*-*---
Pattern dimensions The radius of the board, the number of rows, and the number of columns,
separated by spaces
--*-O-O-O-*--
-*-O-M-M-O-*-
*-O-M-O-O-O-*
-*-O-M-M-O-*-
--*-O-O-O-*--
repeated N times
Pattern The character representation of a pattern
---*-*-*-*---
7
F T T F - -
L Number of instruction lines
T - - T - -
T B - B T -
T F - F T -
T B - B T -
T F - F T -
Program A list of L instruction lines
Each line contains 6 instructions, separated by spaces
T B - B T -
3 7 13
---*-*-*-*---
--*-O-O-O-*--
Empty line between programs
...
Output
Name Description Example
3
Count
(repeated N times) The number of submitted patterns
5

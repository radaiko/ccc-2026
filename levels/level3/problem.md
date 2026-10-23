# Level 3

Extracted automatically from data/level-3.pdf. Tables and figures may have lost their layout: if something is unclear, look at the PDF itself.

--- page 1 ---
LEVEL 3

--- page 2 ---
TWO BEAMS BUILD. THREE BEAMS BURN.
FAB-42 > firmware 2.0 .. INSTALLED
FAB-42 > beam power .... 50%
A single laser beam turned out to be a blunt
instrument: everything it touched became matter,
wanted or not.
So, Dr. Ångström halved the power. One beam alone
now passes through the board without leaving a
trace. Only where two beams cross is there enough
energy to create matter.
Where three or more beams meet, there is far too
much: any matter in that cell is destroyed in a tiny,
very expensive puff of smoke.
Simulate the newly calibrated emitters.
LEVEL 3

--- page 3 ---
Multiple emitters are now used at the same time.
They are different from the previous level.
▪ Now only when 2 laser beams hit the same cell, matter is created
▪ When 3 or more laser beams hit the same cell, matter is destroyed
▪ You are given a list of boards with some matter already on it and up to 6 emitters
▪ Determine the state of the board after matter is created and destroyed
▪ The directions of the emitters work identical to the previous level
▪ Laser beams interact only with ‘O’ and ‘M’, not with ‘
’
-
‘*’ or ‘1’-’6’
,
LEVEL 3

--- page 4 ---
Input
Name Description Example
N Number of boards 3
3 7 13
---2-*-*-3---
Board dimensions The radius of the board, the number of rows, and the number of columns,
separated by spaces
--*-M-M-O-*--
-*-O-O-O-O-*-
repeated N times
1-O-O-M-O-O-*
-*-O-M-O-O-4-
--*-O-O-O-*--
---*-*-*-*---
Board The character representation of the board
4 9 17
----2-*-*-3-*----
---*-O-M-M-M-*---
...
Empty line between boards
Output
Name Description Example
---2-*-*-3---
repeated N times
--*-M-M-O-*--
-*-O-O-O-O-*-
Board The character representation of the board
You can print the border with emitters or without. Both will be judged as correct.
1-O-O-O-O-O-*
-*-O-M-M-O-4-
--*-O-O-O-*--
---*-*-*-*---
----2-*-*-3-*----
---*-O-M-M-M-*---
Mandatory empty line between boards
...

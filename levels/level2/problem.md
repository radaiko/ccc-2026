# Level 2

Extracted automatically from data/level-2.pdf. Tables and figures may have lost their layout: if something is unclear, look at the PDF itself.

--- page 1 ---
LEVEL 2

--- page 2 ---
FIRST LIGHT
FAB-42 > emitter ....... ARMED
FAB-42 > fire? [y/N] _
The engineers mount a single emitter on the border of
the board and fire. A perfectly straight line of matter
appears across the board.
Someone cheers, which is strictly against cleanroom
rules.
Simulate every laser beam.
LEVEL 2

--- page 3 ---
▪ The nanofabricator has an emitter that produces a laser beam
▪ The emitter is placed on the border of the board
▪ The laser beam is a straight line that starts from the emitter
▪ Wherever the laser beam hits a cell of the board, matter is created
▪ The laser beam interacts only with ‘O’, not with ‘
-
’ or ‘*’
▪ The direction of the emitter is indicted by a number
− Directions are explained on the next page
▪ You are given a list of boards with one emitter
▪ For each board, determine the state after matter is created
LEVEL 2

--- page 4 ---
Emitter Directions
1 = →
----*-*-*-*-*----
---*-O-O-O-O-*---
--*-O-O-O-O-O-*--
-*-O-O-O-O-O-O-*-
2 =
----*-*-*-*-*----
---2-O-O-O-O-*---
--*-M-O-O-O-O-*--
-*-O-M-O-O-O-O-*-
3 =
----*-*-3-*-*----
---*-O-M-O-O-*---
--*-O-M-O-O-O-*--
-*-O-M-O-O-O-O-*-
1-M-M-M-M-M-M-M-*
*-O-O-M-O-O-O-O-*
*-O-M-O-O-O-O-O-*
-*-O-O-O-O-O-O-*-
--*-O-O-O-O-O-*--
---*-O-O-O-O-*---
----*-*-*-*-*----
-*-O-O-M-O-O-O-*-
-*-M-O-O-O-O-O-*-
--*-O-O-M-O-O-*--
---*-O-O-M-O-*---
----*-*-*-*-*----
--*-O-O-O-O-O-*--
---*-O-O-O-O-*---
----*-*-*-*-*----
4 = ←
----*-*-*-*-*----
---*-O-O-O-O-*---
--*-O-O-O-O-O-*--
-*-O-O-O-O-O-O-*-
*-O-O-O-O-O-O-O-*
-*-O-O-O-O-O-O-*-
--*-M-M-M-M-M-4--
---*-O-O-O-O-*---
----*-*-*-*-*----
5 =
----*-*-*-*-*----
---*-M-O-O-O-*---
--*-O-M-O-O-O-*--
-*-O-O-M-O-O-O-*-
*-O-O-O-M-O-O-O-*
-*-O-O-O-M-O-O-*-
--*-O-O-O-M-O-*--
---*-O-O-O-M-*---
----*-*-*-*-5----
6 =
----*-*-*-*-*----
---*-O-O-O-O-*---
--*-O-O-O-O-M-*--
-*-O-O-O-O-M-O-*-
*-O-O-O-O-M-O-O-*
-*-O-O-O-M-O-O-*-
--*-O-O-M-O-O-*--
---*-O-M-O-O-*---
----*-6-*-*-*----
LEVEL 2

--- page 5 ---
Input
Name Description Example
N Number of boards 6
4 9 17
----*-*-*-*-*----
Board dimensions The radius of the board, the number of rows, and the number of columns, separated by
---*-O-O-O-O-*---
--*-O-O-O-O-O-*--
spaces
-*-O-O-O-O-O-O-*-
repeated N times
1-O-O-O-O-O-O-O-*
Board
A paragraph of characters
‘O’ represents an empty cell of the board
‘*’ represents the border of the board
‘
-’ is only necessary for the indentation
‘1’-‘6’ represents the emitter
-*-O-O-O-O-O-O-*-
--*-O-O-O-O-O-*--
---*-O-O-O-O-*---
----*-*-*-*-*----
4 9 17
----*-*-*-*-*----
---2-O-O-O-O-*---
--*-O-O-O-O-O-*--
Empty line between boards
...
Output
Name Description Example
----*-*-*-*-*----
repeated N times
Board
A paragraph of characters
‘O’ represents an empty cell of the board
‘M’ represents matter
‘*’ represents the border of the board
‘
-’ is only necessary for the indentation
‘1’-‘6’ represents the emitter
You can print the border with emitter or without. Both will be judged as correct.
---*-O-O-O-O-*---
--*-O-O-O-O-O-*--
-*-O-O-O-O-O-O-*-
1-M-M-M-M-M-M-M-*
-*-O-O-O-O-O-O-*-
--*-O-O-O-O-O-*--
---*-O-O-O-O-*---
----*-*-*-*-*----
---2-O-O-O-O-*---
--*-M-O-O-O-O-*--
Mandatory empty line between boards
...

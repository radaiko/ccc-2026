# Level 1

Extracted automatically from data/level-1.pdf. Tables and figures may have lost their layout: if something is unclear, look at the PDF itself.

--- page 2 ---
FAB-42 IS ONLINE
FAB-42 > power ......... OK
FAB-42 > lasers ........ OK
FAB-42 > software ...... NOT FOUND
In a cleanroom so clean that even the dust must wear
a hairnet, Dr. Ångström has just switched on FAB-42,
the world’s first nanofabricator.
It doesn’t print, carve or mill anything. It creates
matter with laser light, one hexagonal cell at a time.
It is the most precise machine ever built. Right now, it
can’t do a single thing, because nobody has written
its software yet.
That’s where you come in.
Start at the very beginning: teach FAB-42 what its
own board looks like.
Dr. Ångström and Professor Flux shared a lab once. Once.

--- page 3 ---
LEVEL 1

--- page 4 ---
▪ The board of a nanofabricator is a hexagon with hexagonal cells
▪ You are given a list of radii
▪ For each radius, print the character representation of the board
3---*-*-*-*---
--*-O-O-O-*--
-*-O-O-O-O-*-
*-O-O-O-O-O-*
-*-O-O-O-O-*-
--*-O-O-O-*--
---*-*-*-*---
Graphic representation
LEVEL 1

--- page 5 ---
Input
Name Description Example
N Number of radii 3
3
Radius
(repeated N times) 6
An integer representing the radius of the board
4
Output
Name Description Example
---*-*-*-*---
--*-O-O-O-*--
repeated N times
Board
A paragraph of characters
‘O’ represents a cell of the board
‘*’ represents the border of the board
‘
-’ is only necessary for the indentation
-*-O-O-O-O-*-
*-O-O-O-O-O-*
-*-O-O-O-O-*-
--*-O-O-O-*--
---*-*-*-*---
------*-*-*-*-*-*-*------
-----*-O-O-O-O-O-O-*-----
----*-O-O-O-O-O-O-O-*----
Mandatory empty line between boards
...
For each input file, determine the output and write it in a file.
Upload your output file to the coding contest platform.

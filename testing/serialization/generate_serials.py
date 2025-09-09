# This is a hacky script to generate a CSV of cell serial numbers to be printed
# onto labels and attached to each cell prior to running incoming quality tests.

import string

count = 0

# Print a header row.
print("Count,Box,Row,Column,Serial")

# I have three boxes of 130 cells arranged in a 13x10 grid.
for box in range(3):
  for row in string.ascii_uppercase[:10]:
    for column in range(13):
      count = count + 1
      box_friendly = box + 1
      column_friendly = column + 1
      print(f"{count},{box_friendly},{row},{column_friendly:02},{box_friendly}{row}{column_friendly:02}")
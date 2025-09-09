# Cell serialization

A lot of cells go into a solar car sized battery pack. I wanted to be able to do incoming quality tests on them in order to know which cells to keep or reject, and then to have enough data to do a good job of putting together parallel groups. I used a label printer and QR codes so that I could use a  (handheld barcode scanner)[https://www.amazon.com/dp/B01M264K5L] to get their serial numbers at test time.

The serial numbers are based on box number, row letter, and column number so that I could quickly find a specific cell within my inventory when it became time to populate cells into modules.

Edit the file `generate_serials.py` to generate whatever serial numbers you need. Run it with:

```
python3 generate_serials.py > serial_labels.csv
```

This produces a CSV file which is easy to use for printing.

# Printing

I'm using a Brother QL-720NW label printer, which has been obsolete for years. A modern equivalent appears to be the [Brother QL820NWBC](https://www.brother-usa.com/products/ql820nwbc).

For labels, either the [DK1221](https://www.brother-usa.com/products/dk1221) or [DK2214](https://www.brother-usa.com/products/dk2214) seem like reasonable labels. I used a [knock-off version](https://www.amazon.com/dp/B08Q7VB3YZ) of the latter because it was available as a plastic film which I prefer over paper for durability and thinness.

Follow [this guide](https://support.brother.com/g/b/faqend.aspx?c=us&lang=en&prod=3600eus&faqid=faqp00001040_003) to put together a label using the (P-Touch Editor software)[https://www.brother-usa.com/ptouch/ptouch-label-editor-software].

Of course there are many other ways to label the cells, including just a marker.
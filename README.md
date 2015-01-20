# gpx2ps

Visualize your GPS traces without any pesky maps getting in the way

## Overview

Given a directory full of `.gpx` files and a bounding box, `gpx2ps` will render them as a postscript file written to `STDOUT`.

## Usage

```
usage: gpx2ps.py [-h] [--inputdir INPUTDIR] [--fgcolor FGCOLOR]
                 [--bgcolor BGCOLOR]
                 [--autofit | --bbox MINLAT,MINLON,MAXLAT,MAXLON | --center LAT,LON]
                 [--radius RADIUS] [--landscape | --portrait]

In goes the GPX, out goes the PS

optional arguments:
  -h, --help            show this help message and exit
  --inputdir INPUTDIR   Directory that contains gpx files
  --fgcolor FGCOLOR     Foreground color in #RRGGBB format
  --bgcolor BGCOLOR     Background color in #RRGGBB format
  --autofit             Automatically crop output to fit data
  --bbox MINLAT,MINLON,MAXLAT,MAXLON
                        Crop output to fit within this bounding box
  --center LAT,LON      Center output on this point. Use with --radius
  --radius RADIUS       Radius of area to include in output. Use with --center
  --landscape           Print in landscape mode (default)
  --portrait            Print in portrait mode
```

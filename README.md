# gpx2ps

Visualize your GPS traces without any pesky maps getting in the way

## Overview

Given a directory full of `.gpx` files and a bounding box, `gpx2ps` will render them as a postscript file written to `STDOUT`.

## Usage

```
usage: gpx2ps.py [-h] [--inputdir INPUTDIR]
                 [--autofit | --bbox MINLAT,MINLON,MAXLAT,MAXLON | --center LAT,LON]
                 [--radius RADIUS]

optional arguments:
  -h, --help            show this help message and exit
  --inputdir INPUTDIR   Directory that contains gpx files
  --autofit             Automatically crop output to fit data
  --bbox MINLAT,MINLON,MAXLAT,MAXLON
                        Crop output to fit within this bounding box
  --center LAT,LON      Center ouput on this point. Use with --radius
  --radius RADIUS       Radius of area to include in output. Use with --center
```

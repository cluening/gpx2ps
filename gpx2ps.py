#!/usr/bin/env python

import xml.etree.ElementTree as elementtree
import sys, os
import argparse

# To do
# - specify inputdir on command line
# - specify output file on command line (default to sys.stdout)
# - take center and radius from command line
#     --center x,y --radius 5[mi|km|ft|m]
# - include presets (in a config file?)
# - if line length is over a limit, use moveto instead of lineto
# - put a logo on the page (command line option for .eps file?)
# - specify the page size?

def main():
#  inputfile = "20121202.gpx"  # aspect ratio: 2.375410
#  inputfile = "20130625.gpx"  # aspect ratio: 0.755854
#  inputfile = "20111127-20111210.gpx"
#  inputfile = "20130528.gpx"

  papersize = (612, 792)
  parser = argparse.ArgumentParser(description="In goes the GPX, out goes the PS")
  bbgroup = parser.add_argument_group("Bounding Box", "Crop the output to cover this area.")
  bbgroup.add_argument("--maxlat", dest="maxlat", default=-500, type=float, action="store")
  bbgroup.add_argument("--maxlon", dest="maxlon", default=-500, type=float, action="store")
  bbgroup.add_argument("--minlat", dest="minlat", default=500, type=float, action="store")
  bbgroup.add_argument("--minlon", dest="minlon", default=500, type=float, action="store")
  parser.add_argument("--autofit", dest="autofit", action="store_true", help="Automatically crop output to fit data")
  args = parser.parse_args()

  inputdir = "."
  inputfiles = ["20121202.gpx"]
  
  inputdir = "/Users/cluening/GPS/GPX/Archive"
  inputdir = "/Users/cluening/GPS/GPX/Archive.sanified"
  inputdir = "/Users/cluening/GPS/gpx.etrex"
  inputfiles = os.listdir(inputdir)

  maxlat = args.maxlat
  maxlon = args.maxlon
  minlat = args.minlat
  minlon = args.minlon

  print "90 rotate"
  print "%d %d translate" % (0, papersize[0]*-1)
  print "0 setlinewidth"  # '0' means "thinnest possible on device"
  print "1 setlinecap"    # rounded
  print "1 setlinejoin"   # rounded

  # First pass: figure out the bounds
  if args.autofit == True:
    for inputfile in inputfiles:
      try:
        tree = elementtree.parse(inputdir + "/" + inputfile)
      except elementtree.ParseError as detail:
        warn("Bad file: %s: %s" % (inputfile, detail))
        continue

      gpx = doelement(tree.getroot())
        
      # Find minimum and maximum latitude and longitude
      for track in gpx:
        for segment in track:
          for point in segment:
            if point[0] > maxlat:
              maxlat = point[0]
            if point[0] < minlat:
              minlat = point[0]
            if point[1] > maxlon:
              maxlon = point[1]
            if point[1] < minlon:
              minlon = point[1]
            
            
  # Below are approximately Los Alamos
#  maxlat =   35.925005
#  maxlon = -106.255603
#  minlat =   35.860472
#  minlon = -106.339116
  
  # Second pass: draw the lines
  for inputfile in inputfiles:
    try:
      tree = elementtree.parse(inputdir + "/" + inputfile)
    except elementtree.ParseError as detail:
      warn("Bad file: %s: %s" % (inputfile, detail))
      continue

    gpx = doelement(tree.getroot())
  
    if (maxlon-minlon)/(maxlat-minlat) < float(papersize[1])/float(papersize[0]):
      height = maxlat - minlat
      newwidth = height * (float(papersize[1])/float(papersize[0]))
      widthdiff = newwidth - (maxlon - minlon)
      maxlon = maxlon + (widthdiff/2)
      minlon = minlon - (widthdiff/2)
    else:
      width = maxlon - minlon
      newheight = width / (float(papersize[1])/float(papersize[0]))
      heightdiff = newheight - (maxlat - minlat)
      maxlat = maxlat + (heightdiff/2)
      minlat = minlat - (heightdiff/2)
  
    print "%% File: %s" % inputfile
    for track in gpx:
      print "% A track"
      for segment in track:
        print "% A segment"
        print "newpath"

        for i in range(len(segment)):
          if i == 0:
            print "%f %f moveto" % (scale(segment[i][1], (minlon,maxlon), (0,papersize[1])),
                                    scale(segment[i][0], (minlat,maxlat), (0,papersize[0])))
          else:
            if (((segment[i-1][0] > minlat and segment[i-1][0] < maxlat)  and
                 (segment[i][0]   > minlat and segment[i][0]   < maxlat)) or
                ((segment[i-1][1] > minlon and segment[i-1][1] < maxlon)  and
                 (segment[i][1]   > minlon and segment[i][1]   < maxlon))):

              print "%f %f lineto" % (scale(segment[i][1], (minlon,maxlon), (0,papersize[1])),
                                      scale(segment[i][0], (minlat,maxlat), (0,papersize[0])))
        
        print "stroke"



##
## doelement()
##

def doelement(element):

  if element.tag.endswith("gpx"):
    gpx = []
    for child in element:
      if child.tag.endswith("trk"):
        gpx.append(doelement(child))
    return gpx

  if element.tag.endswith("trk"):
    track = []
    for child in element:
      if child.tag.endswith("trkseg"):
        track.append(doelement(child))
    return track

  if element.tag.endswith("trkseg"):
    segment = []
    for child in element:
      segment.append(doelement(child))
    return segment
      
  if element.tag.endswith("trkpt"):
    lat = float(element.attrib['lat'])
    lon = float(element.attrib['lon'])
    return (lat, lon)


##
## warn()
##
def warn(message):
  sys.stderr.write(message + "\n")


##
## scale()
## Scales a value from tuple src to tuple dst
##
def scale(val, src, dst):
  return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]


if __name__ == "__main__":
  main()
#!/usr/bin/env python

import xml.etree.ElementTree as elementtree
import sys, os

# To do
# - take lat/lon bounds from command line
# - take center and radius from command line
# - include presets (in a config file?)
# - if line length is over a limit, use moveto instead of lineto
# - put a logo on the page (command line option for .eps file?)
# - specify the page size?

def main():
#  inputfile = "20121202.gpx"  # aspect ratio: 2.375410
#  inputfile = "20130625.gpx"  # aspect ratio: 0.755854
#  inputfile = "20111127-20111210.gpx"
#  inputfile = "20130528.gpx"

  inputdir = "."
  inputfiles = ["20121202.gpx"]
  
  inputdir = "/Users/cluening/GPS/GPX/Archive"
  inputdir = "/Users/cluening/GPS/gpx.etrex"
  inputfiles = os.listdir(inputdir)

  papersize = (612, 792)

  maxlat = -500
  maxlon = -500
  minlat = 500
  minlon = 500

  print "90 rotate"
  print "%d %d translate" % (0, papersize[0]*-1)
  print "0 setlinewidth"  # '0' means "thinnest possible on device"
  print "1 setlinecap"    # rounded
  print "1 setlinejoin"   # rounded

  # First pass: figure out the bounds
  for inputfile in inputfiles:
    try:
      tree = elementtree.parse(inputdir + "/" + inputfile)
    except elementtree.ParseError as detail:
      warn("Bad file: %s: %s" % (inputfile, detail))
#    tree.write(sys.stdout)

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
            
            
#  # Below are approximately Los Alamos
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
        print "0 0 moveto"
        if len(segment) > 0:
          print "%f %f moveto" % (scale(segment[0][1], (minlon,maxlon), (0,papersize[1])),
                                  scale(segment[0][0], (minlat,maxlat), (0,papersize[0])))
        for point in segment:
          print "%% A point: %f, %f" % point
          print "%f %f lineto" % (scale(point[1], (minlon,maxlon), (0,papersize[1])),
                                  scale(point[0], (minlat,maxlat), (0,papersize[0])))
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
#    print "      Got a point! %f, %f" % (lat, lon)
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
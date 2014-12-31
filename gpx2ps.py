#!/usr/bin/env python

import xml.etree.ElementTree as elementtree
import sys

def main():
  inputfile = "20121202.gpx"
  inputfile = "20121209.gpx"
  inputfile = "20130528.gpx"
  papersize = (612, 792)

  maxlat = -500
  maxlon = -500
  minlat = 500
  minlon = 500
  
  try:
    tree = elementtree.parse(inputfile)
  except elementtree.ParseError as detail:
    warn("Bad file: %s: %s" % (inputfile, detail))
#  tree.write(sys.stdout)

  gpx = doelement(tree.getroot())

#  for track in gpx:
#    print "A track"
#    for segment in track:
#      print "  A segment"
#      for point in segment:
#        print "    A point: %f, %f" % point
        
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
          
#  print "Max Lat: %f" % maxlat
#  print "Max Lon: %f" % maxlon
#  print "Min Lat: %f" % minlat
#  print "Min Lon: %f" % minlon

#  print "Rescaled: %f" % scale(35.903369, (minlat, maxlat), (0, papersize[1]))
  
  print "90 rotate"
  print "%d %d translate" % (0, papersize[0]*-1)
#  print "36 -612 translate" # Add .5 inch on either all sides
  print ".5 setlinewidth"
  print "1 setlinecap"
  print "1 setlinejoin"
  for track in gpx:
    print "% A track"
    for segment in track:
      print "% A segment"
      print "newpath"
      print "0 0 moveto"
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
## scale()
## Scales a value from tuple src to tuple dst
##
def scale(val, src, dst):
  return ((val - src[0]) / (src[1]-src[0])) * (dst[1]-dst[0]) + dst[0]


if __name__ == "__main__":
  main()
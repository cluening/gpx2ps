#!/usr/bin/env python

import xml.etree.ElementTree as elementtree
import sys, os, math, glob
import argparse

# To do
# - fix projection
# - specify output file on command line (default to sys.stdout)
# - include presets (in a config file?)
# - if line length is over a limit, use moveto instead of lineto
# - put title on page
#   - in lower right corner; with box around it; specify on command line
#   - or maybe centered at the bottom
# - put a logo on the page (command line option for .eps file?)
# - add landscape postscript header
# - specify the page size?

def main():
  papersize = (612, 792)

  parser = argparse.ArgumentParser(description="In goes the GPX, out goes the PS")
  parser.add_argument("--inputdir", dest="inputdir", action="store", default=".",
                      help="Directory that contains gpx files")
  parser.add_argument("--autofit", dest="autofit", action="store_true", 
                      help="Automatically crop output to fit data")
  parser.add_argument("--bbox", dest="bbox", action="store", 
                      metavar="MINLAT,MINLON,MAXLAT,MAXLON", 
                      help="Crop output to fit within this bounding box")
  parser.add_argument("--center", dest="center", action="store", metavar="LAT,LON", 
                      help="Center ouput on this point.  Use with --radius")
  parser.add_argument("--radius", dest="radius", action="store",
                      help="Radius of area to include in output.  Use with --center")
  args = parser.parse_args()

  inputfiles = glob.glob(args.inputdir + "/*.gpx")
  if len(inputfiles) == 0:
    sys.stderr.write("Error: no files found\n")
    sys.exit(1)

  if args.bbox == None:
    minlat = -90
    minlon = -180
    maxlat = 90
    maxlon = 180
  else:
    bbox = args.bbox.split(",")
    if len(bbox) != 4:
      sys.stderr.write("Error: not enough items in bounding box list\n")
      sys.exit(1)
    minlat = float(bbox[0])
    minlon = float(bbox[1])
    maxlat = float(bbox[2])
    maxlon = float(bbox[3])

  # FIXME: doesn't handle invalid things that end in 'm', like "fm"
  if args.radius != None:
    if args.radius.endswith("mi"):
      radius = 1.609334 * float(args.radius[:-2])
    elif args.radius.endswith("ft"):
      radius = .0003048 * float(args.radius[:-2])
    elif args.radius.endswith("km"):
      radius = float(args.radius[:-2])
    elif args.radius.endswith("m"):
      radius = .001 * float(args.radius[:-1])
    else:
      sys.stderr.write("Error: could not parse radius\n")
      sys.exit(1)

  if args.center != None:
    centerlat, centerlon = map(float, args.center.split(","))
    maxlat, maxlon = radiuspoint(centerlat, centerlon, math.sqrt(2*(radius**2)), 45)
    minlat, minlon = radiuspoint(centerlat, centerlon, math.sqrt(2*(radius**2)), 225)

  # First pass: figure out the bounds
  if args.autofit == True:
    if args.bbox != None:
      sys.stderr.write("Error: can't specify bounding box and autofit at the same time\n")
      sys.exit(1)
    minlat = 500
    minlon = 500
    maxlat = -500
    maxlon = -500
    for inputfile in inputfiles:
      try:
        tree = elementtree.parse(inputfile)
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

  # Fix the aspect ratio, expanding in one direction as needed 
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

  print "90 rotate"
  print "%d %d translate" % (0, papersize[0]*-1)
  print "0 setlinewidth"  # '0' means "thinnest possible on device"
  print "1 setlinecap"    # rounded
  print "1 setlinejoin"   # rounded
  
  # Second pass: draw the lines
  for inputfile in inputfiles:
    try:
      tree = elementtree.parse(inputfile)
    except elementtree.ParseError as detail:
      warn("Bad file: %s: %s" % (inputfile, detail))
      continue

    gpx = doelement(tree.getroot())
  
    print "%% File: %s" % inputfile
    for track in gpx:
      for segment in track:
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


## 
## radiuspoint()
## Given a point, a radius, and a direction, find the lat/lon of the new point
## lat, lon, and bearing all in degrees; distance in kilometers
##
def radiuspoint(lat, lon, dist, brng):
  R = 6367  # kilometers
  d = dist  # must come in in kilometers

  lat, lon = map(math.radians, [lat, lon])
  brng = math.radians(brng)

  newlat = math.asin(math.sin(lat)*math.cos(float(d)/float(R)) + 
                     math.cos(lat)*math.sin(float(d)/float(R))*math.cos(brng) )
  newlon = lon + math.atan2(math.sin(brng)*math.sin(float(d)/float(R))*math.cos(lat),
                            math.cos(float(d)/float(R))-math.sin(lat)*math.sin(newlat))

  return map(math.degrees, [newlat, newlon])



if __name__ == "__main__":
  main()
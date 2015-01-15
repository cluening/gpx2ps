#!/usr/bin/env python

import xml.etree.ElementTree as elementtree
import sys, os, math, re, glob
import argparse

# To do
# - add --portrait and --landscape options (with default as --landscape)
# - specify output file on command line (default to sys.stdout)
# - include presets (in a config file?)
# - if line length is over a limit, use moveto instead of lineto
# - put title on page
#   - in lower right corner; with box around it; specify on command line
#   - or maybe centered at the bottom
# - put a logo on the page (command line option for .eps file?)
# - add landscape postscript header
# - specify the page size?
# - lambertazimuthal looks weird at huge scales

# Tests
# ./gpx2ps.py --inputdir ~/gps/gpx.etrex --center 35.8958238,-106.2957513 --radius 2.5mi > /tmp/foo.ps
# ./gpx2ps.py --inputdir ~/gps/gpx.etrex --bbox 35.860472,-106.339116,35.925005,-106.255603 > /tmp/foo.ps
# ./gpx2ps.py --inputdir ~/gps/gpx.etrex --autofit > /tmp/foo.ps

def main():
  papersize = (612, 792)
  commandline = " ".join(sys.argv)

  #lambertazimuthal(35.896067, -106.276954, 35.884663, -106.252836)
  #lambertazimuthal(0.0, 0.0, 0.0, 180.0) # FIXME: this one causes a divide by zero error
  #sys.exit(1)

  parser = argparse.ArgumentParser(description="In goes the GPX, out goes the PS")
  boxgroup = parser.add_mutually_exclusive_group()
  parser.add_argument("--inputdir", dest="inputdir", action="store", default=".",
                      help="Directory that contains gpx files")
  boxgroup.add_argument("--autofit", dest="autofit", action="store_true", 
                      help="Automatically crop output to fit data")
  boxgroup.add_argument("--bbox", dest="bbox", action="store", 
                      metavar="MINLAT,MINLON,MAXLAT,MAXLON", 
                      help="Crop output to fit within this bounding box")
  boxgroup.add_argument("--center", dest="center", action="store", metavar="LAT,LON", 
                      help="Center ouput on this point.  Use with --radius")
  parser.add_argument("--radius", dest="radius", action="store",
                      help="Radius of area to include in output.  Use with --center")
  args = parser.parse_args()

  inputfiles = glob.glob(args.inputdir + "/*.gpx")
  if len(inputfiles) == 0:
    sys.stderr.write("Error: no files found\n")
    sys.exit(1)

  #
  # Bounding box mode:
  # Use the bounding box provided on the command line to calculate the center point
  #
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
    centerlat = minlat + (maxlat - minlat)/2.0
    centerlon = minlon + (maxlon - minlon)/2.0

  #
  # Center mode:
  # Use the center and radius provided on the command line to calculate the bounds
  #
  if args.center != None:
    if args.radius != None:
      radius = radiustokm(args.radius)
    else:
      sys.stderr.write("Error: --center requires --radius\n")
      sys.exit(1)
    centerlat, centerlon = map(float, args.center.split(","))
    maxlat, maxlon = radiuspoint(centerlat, centerlon, math.sqrt(2*(radius**2)), 45)
    minlat, minlon = radiuspoint(centerlat, centerlon, math.sqrt(2*(radius**2)), 225)


  #
  # Autofit mode:
  # Run through the files to find the bounds, then calculate the center point
  #
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
    centerlat = minlat + (maxlat - minlat)/2.0
    centerlon = minlon + (maxlon - minlon)/2.0
    

  #
  # By this point we should have the bounding box and center point calculated  
  # Now it's time to fix the aspect ratio, expanding in one direction as needed
  # Takes latitude into account to fix proportions
  #
  latdist = haversine(maxlat, centerlon, minlat, centerlon)
  londist = haversine(centerlat, maxlon, centerlat, minlon)

  if londist/latdist < float(papersize[1])/float(papersize[0]):
    height = latdist
    newwidth = height * (float(papersize[1])/float(papersize[0]))
    maxlon = radiuspoint(centerlat, centerlon, newwidth/2.0, 90)[1]
    minlon = radiuspoint(centerlat, centerlon, newwidth/2.0, 270)[1]
  else:
    width = londist
    newheight = width / (float(papersize[1])/float(papersize[0]))
    maxlat = radiuspoint(centerlat, centerlon, newheight/2.0, 0)[0]
    minlat = radiuspoint(centerlat, centerlon, newheight/2.0, 180)[0]
  
  minx, miny = lambertazimuthal(centerlat, centerlon, minlat, minlon)
  maxx, maxy = lambertazimuthal(centerlat, centerlon, maxlat, maxlon)

  #
  # Start printing out the postscript
  #

  print "%!PS"
  print "%% Generated with %s" % commandline
  print "90 rotate"
  print "%d %d translate" % (0, papersize[0]*-1)
  print "0 setlinewidth"  # '0' means "thinnest possible on device"
  print "1 setlinecap"    # rounded
  print "1 setlinejoin"   # rounded
  
  #
  # Run through all of the files and print out postscript commands when appropriate
  #
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
        # FIXME: pull this out into azimuthal projection function
        for i in range(len(segment)):
          x, y = lambertazimuthal(centerlat, centerlon, segment[i][0], segment[i][1])
          if i == 0:
            print "%f %f moveto" % (scale(x, (minx,maxx), (0,papersize[1])),
                                    scale(y, (miny,maxy), (0,papersize[0])))
          else:
            if (((segment[i-1][0] > minlat and segment[i-1][0] < maxlat)  and
                 (segment[i][0]   > minlat and segment[i][0]   < maxlat)) or
                ((segment[i-1][1] > minlon and segment[i-1][1] < maxlon)  and
                 (segment[i][1]   > minlon and segment[i][1]   < maxlon))):

              print "%f %f lineto" % (scale(x, (minx,maxx), (0,papersize[1])),
                                      scale(y, (miny,maxy), (0,papersize[0])))
        print "stroke"
            
        # FIXME: pull this out into a equirectangular projection function
#         print "newpath % Next"
#         for i in range(len(segment)):
#           if i == 0:
#             print "%f %f moveto" % (scale(segment[i][1], (minlon,maxlon), (0,papersize[1])),
#                                     scale(segment[i][0], (minlat,maxlat), (0,papersize[0])))
#           else:
#             if (((segment[i-1][0] > minlat and segment[i-1][0] < maxlat)  and
#                  (segment[i][0]   > minlat and segment[i][0]   < maxlat)) or
#                 ((segment[i-1][1] > minlon and segment[i-1][1] < maxlon)  and
#                  (segment[i][1]   > minlon and segment[i][1]   < maxlon))):
# 
#               print "%f %f lineto" % (scale(segment[i][1], (minlon,maxlon), (0,papersize[1])),
#                                       scale(segment[i][0], (minlat,maxlat), (0,papersize[0])))        
#         print "stroke"



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
## lambertazimuthal()
## performs the azimuthal projection calculation
## x, y range from -2 to 2
##
def lambertazimuthal(centlat, centlon, lat, lon):
  p1, l0, p, l = map(math.radians, [centlat, centlon, lat, lon])
  k = math.sqrt(2/(1+math.sin(p1)*math.sin(p) + math.cos(p1)*math.cos(p)*math.cos(l-l0)))
  
  x = k * math.cos(p) * math.sin(l-l0)
  y = k * (math.cos(p1)*math.sin(p) - math.sin(p1)*math.cos(p)*math.cos(l - l0))
  
  return (x, y)

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


##
## radiustokm()
## Takes a <number><unit> string and converts it to kilometers
##
def radiustokm(radiusstring):
  result = re.search("^(\d+\.?\d*)(\w+)$", radiusstring)

  if result == None:
    sys.stderr.write("Error: radius string could not be parsed\n")
    sys.exit(1)

  radius = result.group(1)
  units = result.group(2)

  if units == "mi":
    return 1.609334 * float(radius)
  elif units == "ft":
    return .0003048 * float(radius)
  elif units == "km":
    return float(radius)
  elif units == "m":
    return .001 * float(radius)
  else:
    sys.stderr.write("Error: radius units not recognized\n")
    sys.exit(1)


##
##  haversine() function.  Stolen from stackoverflow
##
def haversine(lat1, lon1, lat2, lon2):
  """
  Calculate the great circle distance between two points 
  on the earth (specified in decimal degrees)
  """
  # convert decimal degrees to radians 
  lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

  # haversine formula 
  dlon = lon2 - lon1 
  dlat = lat2 - lat1 
  a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
  c = 2 * math.asin(math.sqrt(a)) 

  # 6367 km is the radius of the Earth
  km = 6367 * c
  return km 


if __name__ == "__main__":
  main()
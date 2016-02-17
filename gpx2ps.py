#!/usr/bin/env python

import xml.etree.ElementTree as elementtree
import sys, os, math, re, glob
import argparse

# To do
# - specify date range
# - specify output file on command line (default to sys.stdout)
# - specify projection on command line
# - include presets (in a config file?)
# - if line length is over a limit, use moveto instead of lineto
# - put a logo on the page (command line option for .eps file?)
# - add landscape postscript header
# - specify the page size?
# - handle titles
#   - location (UL, UC, UR, LL, LC, LR)
#   - thin and bold font selection
#   - font size
#   - "shadow" to separate text from map lines when there is overlap
#   - missing font fallback
#   - subtitle?

# Tests
# ./gpx2ps.py --inputdir ~/gps/gpx.etrex --center 35.8958238,-106.2957513 --radius 2.5mi > /tmp/foo.ps
# ./gpx2ps.py --inputdir ~/gps/gpx.etrex --bbox 35.860472,-106.339116,35.925005,-106.255603 > /tmp/foo.ps
# ./gpx2ps.py --inputdir ~/gps/gpx.etrex --autofit > /tmp/foo.ps

def main():
  commandline = " ".join(sys.argv)

  #lambertazimuthal(35.896067, -106.276954, 35.884663, -106.252836)
  #lambertazimuthal(0.0, 0.0, 0.0, 180.0) # FIXME: this one causes a divide by zero error
  #sys.exit(1)

  parser = argparse.ArgumentParser(description="In goes the GPX, out goes the PS")
  boxgroup = parser.add_mutually_exclusive_group()
  parser.add_argument("--inputdir", dest="inputdir", action="store", default=".",
                      help="Directory that contains gpx files")
  parser.add_argument("--fgcolor", dest="fgcolor", action="store", default="#000000",
                      help="Foreground color in #RRGGBB format")
  parser.add_argument("--bgcolor", dest="bgcolor", action="store", default="#FFFFFF",
                      help="Background color in #RRGGBB format")
  boxgroup.add_argument("--autofit", dest="autofit", action="store_true", 
                      help="Automatically crop output to fit data")
  boxgroup.add_argument("--bbox", dest="bbox", action="store", 
                      metavar="MINLAT,MINLON,MAXLAT,MAXLON", 
                      help="Crop output to fit within this bounding box")
  boxgroup.add_argument("--center", dest="center", action="store", metavar="LAT,LON", 
                      help="Center output on this point.  Use with --radius")
  parser.add_argument("--radius", dest="radius", action="store",
                      help="Radius of area to include in output.  Use with --center")
  parser.add_argument("--title", dest="title", action="store",
                      help="Optional map title.  Can be in the format 'Thin Text [Bold Text]' for two sets of contrasting text weights")
  pagegroup = parser.add_mutually_exclusive_group()
  pagegroup.add_argument("--landscape", dest="orientation", 
                         action="store_const", const="landscape", 
                         default="landscape", 
                         help="Print in landscape mode (default)")
  pagegroup.add_argument("--portrait", dest="orientation", 
                         action="store_const", const="portrait", 
                         default="landscape", help="Print in portrait mode")
  args = parser.parse_args()

  fgrgb = rgbhextofloat(args.fgcolor)
  bgrgb = rgbhextofloat(args.bgcolor)
  projfunc = millercylindrical  # FIXME: this should come from the command line

  if args.orientation == "portrait":
    papersize = (792, 612)
  else:
    papersize = (612, 792)

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
    centerlat = 0
    centerlon = 0
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
  
  minx, miny = projfunc(centerlat, centerlon, minlat, minlon)
  maxx, maxy = projfunc(centerlat, centerlon, maxlat, maxlon)

  #
  # Start printing out the postscript
  #
  print "%!PS"
  print "%% Generated with %s" % commandline
  if args.orientation == "landscape":
    print "90 rotate"
    print "%d %d translate" % (0, papersize[0]*-1)
  print "0 setlinewidth"  # '0' means "thinnest possible on device"
  print "1 setlinecap"    # rounded
  print "1 setlinejoin"   # rounded
  print "%f %f %f setrgbcolor clippath fill" % bgrgb  # set the background fill
  print "%f %f %f setrgbcolor" % fgrgb                # set the foreground color
  
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
        prevdrawn = False
        for i in range(len(segment)):
          x, y = projfunc(centerlat, centerlon, segment[i][0], segment[i][1])
          if i == 0:
            # For the first point, we just want to move to its position
            print "%f %f moveto" % (scale(x, (minx,maxx), (0,papersize[1])),
                                    scale(y, (miny,maxy), (0,papersize[0])))
          else:
            # Check to see if this point is in the bounding box
            if ((segment[i][0] > minlat and segment[i][0] < maxlat) and
                (segment[i][1] > minlon and segment[i][1] < maxlon)):
              # We're in the bounding box.  If the previous point was not drawn, we need 
              # to moveto it.
              if prevdrawn == False:
                px, py = projfunc(centerlat, centerlon, segment[i-1][0], segment[i-1][1])
                print "%f %f moveto" % (scale(px, (minx,maxx), (0,papersize[1])),
                                        scale(py, (miny,maxy), (0,papersize[0])))
              # Always draw the current point since it is in the bounding box (see above)
              print "%f %f lineto" % (scale(x, (minx,maxx), (0,papersize[1])),
                                      scale(y, (miny,maxy), (0,papersize[0])))
              prevdrawn = True
            else:
              # We're not in the bounding box.  But if the previous point was drawn, we 
              # need a line out to this point
              if prevdrawn == True:
                print "%f %f lineto" % (scale(x, (minx,maxx), (0,papersize[1])),
                                        scale(y, (miny,maxy), (0,papersize[0])))
              prevdrawn = False
        print "stroke"

  if args.title != None:
    print "% Title stuff"
    print """/showthin {
  /BebasNeue-Thin findfont
  48 scalefont
  setfont
  show
} def

/showbold {
  /BebasNeueRegular findfont
  48 scalefont
  setfont
  show
} def

/showshadowthin {
  /BebasNeue-Thin findfont
  48 scalefont
  setfont
  false charpath
  15 setlinewidth stroke
} def

/showshadowbold {
  /BebasNeueRegular findfont
  48 scalefont
  setfont
  false charpath
  15 setlinewidth stroke
} def

/rjmoveto {
  772 20 moveto
  % Thin weight text
  /BebasNeue-Thin findfont
  48 scalefont
  setfont
  stringwidth pop
  neg 0 rmoveto
  % Bold weight text
  /BebasNeueRegular findfont
  48 scalefont
  setfont
  stringwidth pop
  neg 0 rmoveto
} def"""

    # First check for thin/bold combination
    result = re.search(r'^(.*?)\[(.*?)\]$', args.title)
    if result != None:
      thintitlestring = result.group(1)
      boldtitlestring = result.group(2)

      print "%f %f %f setrgbcolor" % (bgrgb)
      print "(%s) (%s) rjmoveto" % (boldtitlestring, thintitlestring)
      print "(%s) showshadowthin" % (thintitlestring)
      print "(%s) () rjmoveto" % (boldtitlestring)
      print "(%s) showshadowbold" % (boldtitlestring)
      print "%f %f %f setrgbcolor" % (fgrgb)
      print "(%s) (%s) rjmoveto" % (boldtitlestring, thintitlestring)
      print "(%s) showthin" % (thintitlestring)
      print "(%s) showbold" % (boldtitlestring)
    else:
      # Assume it is just thin  FIXME: should probably allow for just bold too
      print "%f %f %f setrgbcolor" % (bgrgb)
      print "() (%s) rjmoveto" % (args.title)
      print "(%s) showshadowthin" % (args.title)
      print "%f %f %f setrgbcolor" % (fgrgb)
      print "() (%s) rjmoveto" % (args.title)
      print "(%s) showthin" % (args.title)


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
  return ((float(val) - float(src[0])) / (float(src[1])-float(src[0]))) * (float(dst[1])-float(dst[0])) + float(dst[0])

##
## equirectangular()
## Performs the equirectangular projection calculation
##
def equirectangular(centlat, centlon, lat, lon):
  return (lon, lat)


##
## millercylindrical()
## Performs the miller cylindrical projection calculation
## 
def millercylindrical(centlat, centlon, lat, lon):
  p1, l0, p, l = map(math.radians, [centlat, centlon, lat, lon])

  x = l - l0
  y = 1.25*math.asinh(math.tan(.8*p))

  return (x, y)


##
## lambertazimuthal()
## Performs the azimuthal projection calculation
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
## rgbhextofloat()
##
def rgbhextofloat(rgb):
  result = re.search("^#(..)(..)(..)$", rgb)
  
  if result == None:
    sys.stderr.write("Error: color string '%s' could not be parsed\n" % rgb)
    sys.exit(1)
    
  red = scale(int(result.group(1), 16), (0, 255), (0, 1))
  green = scale(int(result.group(2), 16), (0, 255), (0, 1))
  blue = scale(int(result.group(3), 16), (0, 255), (0, 1))

  return (red, green, blue)
  
  
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

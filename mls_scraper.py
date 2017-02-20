#!/usr/bin/python

import json
import logging
from math import cos, asin, sqrt
from optparse import OptionParser
import re
import requests
import subprocess
import sys

parser = OptionParser(usage="usage: %prog [options] <city>", description="This script scrapes mlslistings and uncovers matches based on specified criteria")
parser.add_option("-c", "--zipcodes", action="store", default=None, help="Comma-separated list of zipcodes.") # e.g. 94085,94086,94087 for sunnyvale, or 95051,95054,95055 for santa clara
parser.add_option("-s", "--lotSize", action="store", dest="lotSize", default=None, help="Minimum lot size.")
parser.add_option("-b", "--beds", action="store", dest="beds", default=None, help="Minimum number of beds.")
parser.add_option("-a", "--baths", action="store", dest="baths", default=None, help="Minimum number of baths.")
parser.add_option("-p", "--price", action="store", dest="price", default=None, help="Maximum price.")
parser.add_option("-z", "--zones", action="store", dest="zones", default=None, help="Comma-separated list of zones.") # e.g. R0,R1,R1AB,R-1,SU
parser.add_option("-x", "--excludeZones", action="store_const", const=True, default=False, help="Whether the list of zones provided should be treated as an blacklist.")
parser.add_option("-t", "--types", action="store", dest="types", default=None, help="Comma-separated list of property types (e.g. Condominium, Townhouse).") # e.g. Townhouse,Condominium,Triplex,Fourplex
parser.add_option("-e", "--excludeTypes", action="store_const", const=True, default=False, help="Whether the list of types provided should be treated as a blacklist.")
parser.add_option("-l", "--location", action="store", dest="location", default=None, help="Approximate location where you want the house, in latitude,longitude coordinates.")
parser.add_option("-d", "--distance", action="store", dest="distance", default=2, help="Distance from location where you want the house (in miles).")
parser.add_option("-g", "--schools", action="store", dest="schools", default=None, help="Comma-separated list of schools to filter by, in the Fremont Union High or Los Gatos-Saratoga Joint Union High districts.")
parser.add_option("-H", "--Homestead", action="store_const", const=True, default=False, help="House should be within Homestead High boundaries.")
parser.add_option("-W", "--Wilcox", action="store_const", const=True, default=False, help="House should be within Wilcox High boundaries.")
parser.add_option("-f", "--jsonFilename", action="store", dest="filename", default=None, help="Write json results to provided file name.")

(options, args) = parser.parse_args()
if len(args) != 1:
    parser.error("Need exactly one city.")
cityName = args[0]

# gives distance in miles between two lat/lon points
# http://stackoverflow.com/questions/27928/calculate-distance-between-two-latitude-longitude-points-haversine-formula
def distance(lat1, lon1, lat2, lon2):
    p = 0.017453292519943295
    a = 0.5 - cos((lat2 - lat1) * p)/2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2
    return 0.621371 * 12742 * asin(sqrt(a)) # 0.621371 converts from km to miles

def matchesFilters(json):
    response = requests.get("http://api.mlslistings.com/api/search/PropertyDetailsByMLSNumber/" + json['MLSNumber'])
    if response.status_code != 200:
        sys.stderr.write("ERROR GETTING MLS LISTING:\n")
        sys.stderr.write(str(response.status_code) + '\n')
        sys.stderr.write(str(response.content) + '\n')
        sys.stderr.write(str(json) + '\n')
        return True # not sure, so return true

    jsonRes = response.json()

    # filter out zones
    zones = jsonRes['features']['Zoning']['m_Item1'] # for some reason this is an array...
    if options.zones:
        zonesArr = options.zones.split(',')
        if options.excludeZones:
            filteredZones  = filter(lambda x: x not in zonesArr, zones)
        else:
            filteredZones  = filter(lambda x: x in zonesArr, zones)
        if len(filteredZones) == 0:
            return False

    # filter out certain home types
    if options.types:
        typesArr = options.types.split(',')
        subclass = jsonRes['propertyInfo']['subClass']
        if subclass in typesArr:
            if options.excludeTypes:
                return False
        elif not options.excludeTypes:
            return False

    # filter by lot size
    if options.lotSize:
        lotSize = int(options.lotSize)
        lotSizeStr = jsonRes['propertyInfo']['lotSizeArea']
        if lotSizeStr:
            m = re.search('^[0-9]+', lotSizeStr)
            if m and int(m.group(0)) < lotSize:
                return False
            elif not m:
                sys.stderr.write("MISSING LOT SIZE!\n")
                sys.stderr.write(json["siteMapDetailUrlPath"] + '\n')
        else:
            sys.stderr.write("MISSING LOT SIZE!\n")
            sys.stderr.write(json["siteMapDetailUrlPath"] + '\n')

    # filter by latitude longitude
    if options.location:
        try:
            lat1 = float(jsonRes['propertyInfo']['latitude'])
            lon1 = float(jsonRes['propertyInfo']['longitude'])
            location = options.location.split(',')
            lat2 = float(location[0])
            lon2 = float(location[1])
            dist = distance(lat1, lon1, lat2, lon2)
            if dist > float(options.distance):
                return False
        except ValueError:
            sys.stderr.write("FAILED TO GET DISTANCE!\n")
            sys.stderr.write("LATITUDE: " + str(jsonRes['propertyInfo']['latitude']) + "\n")
            sys.stderr.write("LONGITUDE: " + str(jsonRes['propertyInfo']['longitude']) + "\n")

    # filter by highschool district
    if options.schools:
        highschools = jsonRes['features']["High School District"]['m_Item1'] # for some reason this is an array...
        if highschools[0] != "Fremont Union High" and highschools[0] != "Los Gatos-Saratoga Joint Union High":
            return False
        schoolsArr = options.schools.split(',')
        found = False
        for school in schoolsArr:
            description = jsonRes['propertyInfo']['publicRemarks']
            if school in description:
                found = True
        if found == False:
            return False

    if options.Homestead or options.Wilcox:
        try:
            if options.Homestead:
                script = "homestead.js"
            else:
                script = "wilcox.js"
            lat1 = float(jsonRes['propertyInfo']['latitude'])
            lon1 = float(jsonRes['propertyInfo']['longitude'])
            output = subprocess.Popen(["node", script, str(lat1), str(lon1)], stdout=subprocess.PIPE).communicate()[0]
            output = output.strip()
            if output == "false":
                return False
        except ValueError:
            sys.stderr.write("FAILED TO GET DISTANCE!\n")
            sys.stderr.write("LATITUDE: " + str(jsonRes['propertyInfo']['latitude']) + "\n")
            sys.stderr.write("LONGITUDE: " + str(jsonRes['propertyInfo']['longitude']) + "\n")

    return True

payload = {
    "display": {
        "itemsPerPage": 200,
        "pageNumber": 1
    },
    "generatePropertySearchResultsHash": "true",
    "query": {
        "address": "",
        "baths": {
            "minMaxSelection": "Min",
            "value": options.baths if options.baths is not None else ""
        },
        "beds": {
            "minMaxSelection": "Min",
            "value": options.beds if options.beds is not None else ""
        },
        "cityName": cityName,
        "countyName": "",
        "listSalePrice": {
            "minMaxSelection": "Max",
            "value": options.price if options.price is not None else ""
        },
        "listingStatus": "1,2",
        "lotSize": {
            "minMaxSelection": "Min",
            "value": options.lotSize if options.lotSize is not None else ""
        },
        "mlsNumber": "",
        "openHouse": "",
        "parking": "",
        "searchType": "property",
        "sortBy": "PriceAscending",
        "sqft": {
            "minMaxSelection": "Min",
            "value": ""
        },
        "subClass": "",
        "type": "1,2,7",
        "yearBuiltMax": "",
        "yearBuiltMin": "",
        "zipCode": "",
        "zipCodeList": options.zipcodes.split(',') if options.zipcodes is not None else []
    }
}

response = requests.post("http://api.mlslistings.com/api/search", headers={"Content-Type": "application/json;charset=UTF-8"}, json=payload)
if response.status_code != 200:
    sys.stderr.write(str(response.status_code) + '\n')
    sys.stderr.write(str(response.content) + '\n')
    sys.exit(234)

jsonRes = response.json()
if not jsonRes['pagingInfo']:
    sys.stderr.write("NO RESULTS!\n")
    sys.exit(0)

elif jsonRes['pagingInfo']['totalPagesCount'] > 1:
    sys.stderr.write("TOO MANY RESULTS!\n")

results = jsonRes['propertySearchResults']
filteredRes = []
for r in results:
    if matchesFilters(r): # need to do post-filtering because some criteria can't be specified in search. Also lotSize criteria in search doesn't actually seem to work
        filteredRes.append(r)

sys.stderr.flush()
if options.filename:
    f = open(options.filename, 'w')
    for r in filteredRes:
        f.write(json.dumps(r, indent=4) + '\n')
    f.close()
else:
    for r in filteredRes:
        sys.stdout.write(r["siteMapDetailUrlPath"] + " ")
    sys.stdout.write('\n')
    sys.stdout.flush()

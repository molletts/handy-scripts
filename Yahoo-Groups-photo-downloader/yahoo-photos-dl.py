#!/usr/bin/env python3

# Hacky script to dump photos from a Yahoo group

import browser_cookie3
import requests
import argparse
import pathlib
import string
import csv

# Speed things up by using an HTTP session
session = requests.Session()

# Fetch the JSON data from an API url
def get_yg_data(url, cookiejar):
    response = session.get(url, cookies = cookiejar)

    # Extract the content type of the returned document
    ctype = response.headers["Content-Type"].split(';')[0]

    if ctype != "application/json":
        # We didn't get a JSON response - assume login required
        result = { "result": "no-access" }
    else:
        # Get the JSON content
        j = response.json()

        if "ygError" in j:
            # The server returned an error - return the status code
            result = { "result": "error",
                       "status": int(j["ygError"]["httpStatus"]),
                       "message": j["ygError"]["errorMessage"] }
        elif "ygData" not in j:
            # There wasn't an error but no data was present in the reply
            result = { "result": "no-data" }
        else:
            result = { "result": "success",
                       "data": j["ygData"] }

    return result

# Find out the number of albums and photos in the group
def get_group_stats(groupname, cookiejar):
    # Make a tentative request for just one album
    j = get_yg_data("https://groups.yahoo.com/api/v3/groups/" +
                    groupname + "/albums?start=0&count=1",
                    cookiejar)

    if j["result"] != "success":
        # An error occurred - just return it as-is
        result = j
    else:
        albumCount = int(j["data"]["total"])

        # Now try requesting just one photo
        j = get_yg_data("https://groups.yahoo.com/api/v3/groups/" +
                        groupname + "/photos?start=0&count=1",
                        cookiejar)

        if j["result"] != "success":
            # An error occurred
            result = j
        else:
            photoCount = int(j["data"]["totalPhotos"])

            result = { "result": "success",
                       "albums": albumCount,
                       "photos": photoCount }

    return result

# Get a list of all the albums in the group
def get_album_list(groupname, cookiejar):
    start = 0
    albumCount = 1
    albums = []

    while start < albumCount:
        j = get_yg_data("https://groups.yahoo.com/api/v3/groups/" +
                        groupname + "/albums?start=" + str(start) +
                        "&count=100",
                        cookiejar)

        if j["result"] != "success":
            # An error occurred. I'm too lazy to deal with it properly.
            # Just bail out with an empty list
            albums = []
            start = albumCount
        else:
            # Update the total number of albums
            albumCount = int(j["data"]["total"])

            # Update where the next chunk needs to start
            start += 100

            # Add the albums to our list
            for album in j["data"]["albums"]:
                albums.append({ "ID":           album["albumId"],
                                "name":         album["albumName"],
                                "creator":      album["creatorNickname"],
                                "description":  album["description"],
                                "photos":       int(album["total"]) })

    return albums

def list_albums_long(albums):
    for album in albums:
        print("\nAlbum ID:      " + str(album["ID"]))
        print("Album name:    " + album["name"])
        print("Description:   " + album["description"])
        print("Created by:    " + album["creator"])
        print("No. of photos: " + str(album["photos"]))

def list_albums_csv(albums, filename):
    with open(filename, 'w', newline='') as csvfile:
        fields = [ "ID", "name", "description", "creator", "photos" ]

        writer = csv.DictWriter(csvfile, fieldnames = fields)
        writer.writeheader()

        for a in albums:
            writer.writerow(a)

def list_album_ids(albums):
    print("\nID          Photos  Name")
    print(  "==          ======  ====")
    for album in albums:
        print("{:<10}  {:>6}  {}".format(album["ID"],
                                         album["photos"],
                                         album["name"]))

# Get a list of all the photos in an album
def get_photo_list_album(groupname, cookiejar, albumid):
    start = 0
    photoCount = 1
    photos = []

    while start < photoCount:
        j = get_yg_data("https://groups.yahoo.com/api/v3/groups/" +
                        groupname + "/albums/" + str(albumid) +
                        "?start=" + str(start) + "&count=100",
                        cookiejar)

        if j["result"] != "success":
            # An error occurred. I'm too lazy to deal with it properly.
            # Just bail out with an empty list
            photos = []
            start = photoCount
        else:
            photoCount = int(j["data"]["total"])
            start += 100

            # Add the photos to our list
            # Not sure what photoGroups are but I'll iterate the list anyway
            for photoGroup in j["data"]["photoGroupByDetails"]:
                for photo in photoGroup["photos"]:
                    # Find the biggest version of the photo
                    photoInfo = { "height": 0 }
                    for v in photo["photoInfo"]:
                        if v["height"] > photoInfo["height"]:
                            photoInfo = v

                    photos.append({ "ID":           photo["photoId"],
                                    "albumID":      photo["albumId"],
                                    "name":         photo["photoName"],
                                    "filename":     photo["photoFilename"],
                                    "filetype":     photo["fileType"],
                                    "creator":      photo["creatorNickname"],
                                    "description":  "" if "description" \
                                                       not in photo
                                                    else photo["description"],
                                    "height":       photoInfo["height"],
                                    "width":        photoInfo["width"],
                                    "filesize":     photoInfo["size"],
                                    "url":          photoInfo["displayURL"] })

    return photos

# Get a list of all the photos in the group
def get_photo_list_group(groupname, cookiejar):
    start = 0
    photoCount = 1
    photos = []

    while start < photoCount:
        j = get_yg_data("https://groups.yahoo.com/api/v3/groups/" +
                        groupname + "/photos/?start=" + str(start) +
                        "&count=100",
                        cookiejar)

        if j["result"] != "success":
            # An error occurred. I'm too lazy to deal with it properly.
            # Just bail out with an empty list
            photos = []
            start = photoCount
        else:
            photoCount = int(j["data"]["totalPhotos"])
            start += 100

            # Add the photos to our list
            for photo in j["data"]["photos"]:
                # Find the biggest version of the photo
                photoInfo = { "height": 0 }
                for v in photo["photoInfo"]:
                    if v["height"] > photoInfo["height"]:
                        photoInfo = v

                photos.append({ "ID":           photo["photoId"],
                                "albumID":      photo["albumId"],
                                "name":         photo["photoName"],
                                "filename":     photo["photoFilename"],
                                "filetype":     photo["fileType"],
                                "creator":      photo["creatorNickname"],
                                "description":  "" if "description" not in photo
                                                else photo["description"],
                                "height":       photoInfo["height"],
                                "width":        photoInfo["width"],
                                "filesize":     photoInfo["size"],
                                "url":          photoInfo["displayURL"] })

    return photos

def list_photos_long(photos, show_album_id = False):
    for photo in photos:
        print("\nPhoto ID:    " + str(photo["ID"]))
        if show_album_id:
            print("Album ID:    " + str(photo["albumID"]))
        print("Photo name:  " + photo["name"])
        print("Description: " + photo["description"])
        print("Created by:  " + photo["creator"])
        print("Height:      " + str(photo["height"]))
        print("Width:       " + str(photo["width"]))
        print("Filename:    " + photo["filename"])
        print("Filetype:    " + photo["filetype"])
        print("File size:   " + str(photo["filesize"]))

def list_photos_csv(photos, filename):
    with open(filename, 'w', newline='') as csvfile:
        fields = [ "ID", "albumID", "name", "filename", "filetype",
                   "description", "creator", "height", "width", "filesize",
                   "url" ]

        writer = csv.DictWriter(csvfile, fieldnames = fields)
        writer.writeheader()

        for p in photos:
            writer.writerow(p)

def list_photo_ids(photos):
    print("\nID          Name")
    print(  "==          ====")
    for photo in photos:
        print("{:<10}  {}".format(photo["ID"], photo["name"]))

# Download an URL to a file. The filename can either be a string or a Path
def download(url, cookiejar, filename, extraheaders = None):
    response = session.get(url, cookies = cookiejar, headers = extraheaders)

    if response.status_code == 200:
        pathlib.Path(filename).write_bytes(response.content)

    return response.status_code

# Replace anything we don't want in a filename with an underscore
def sanitise_filename(filename):
    # A moderately-conservative list of allowed characters
    allowed = string.ascii_letters + string.digits + " !()-_=+,.~"

    return ''.join(c if c in allowed else '_' for c in filename)

# Return a suitable filename for a photo
def make_photo_filename(photo):
    # Map some common MIME types to Windows file extensions
    exts = { "image/jpeg":  ".jpg",
             "image/pjpeg": ".jpg",
             "image/png":   ".png",
             "image/gif":   ".gif",
             "image/bmp":   ".bmp" }

    # Choose a suitable file extension. If we don't know about the MIME type,
    # use it as an extension so we can at least save the file
    fileext = exts[photo["filetype"]] if photo["filetype"] in exts \
                else "." + sanitise_filename(photo["filetype"])

    if photo["filename"] == "n/a":
        fn = "ID_" + str(photo["ID"]) + " - " + \
             sanitise_filename(photo["name"]) + fileext
    else:
        fn = sanitise_filename(photo["filename"])

    return fn

def download_photo(photo, cookiejar, filename = None, extraheaders = None):
    if filename:
        fn = filename
    else:
        fn = make_photo_filename(photo)

    print("\nDownloading as " + fn)

    return download(photo["url"] + "?download=1", cookiejar, fn, extraheaders)

def main():
    parser = argparse.ArgumentParser(
        description = "Yahoo! Groups bulk photo downloader",
        epilog = "You should ensure that you are logged into Yahoo in either "
                 "Chrome/Chromium or Firefox and specify the appropriate "
                 "browser option to import the login details.")

    parser.add_argument("groupname", help = "The name of the group")

    bselect = parser.add_mutually_exclusive_group(required = True)

    bselect.add_argument("--chrome",
                        help = "Use login cookies from Chrome/Chromium",
                        action = "store_true")

    bselect.add_argument("--firefox",
                        help = "Use login cookies from Firefox",
                        action = "store_true")

    parser.add_argument("--list-albums", "-l",
                        help = "List available albums",
                        action = "store_true")

    parser.add_argument("--list-albums-csv", "-c",
                        help = "List available albums to a CSV file",
                        metavar = "FILENAME")

    parser.add_argument("--list-album-ids", "-L",
                        help = "List available albums with just names, "
                               "photo counts and IDs",
                        action = "store_true")

    aselect = parser.add_mutually_exclusive_group()

    aselect.add_argument("--album", "-a",
                         help = "Select an album by name")

    aselect.add_argument("--album-id", "-A",
                         help = "Select an album by ID number",
                         type = int)

    parser.add_argument("--list-photos", "-p",
                        help = "List photos in the group or the selected album",
                        action = "store_true")

    parser.add_argument("--list-photos-csv", "-C",
                        help = "List photos in the group or the selected album "
                               "to a CSV file",
                        metavar = "FILENAME")

    parser.add_argument("--list-photo-ids", "-P",
                        help = "List photos in the group or the selected album "
                               "with just names and IDs",
                        action = "store_true")

    pselect = parser.add_mutually_exclusive_group()

    pselect.add_argument("--download-photo", "-d",
                         help = "Download a photo by name")

    pselect.add_argument("--download-photo-id", "-D",
                         help = "Download a photo by ID number",
                         type = int)

    pselect.add_argument("--download-all", "-g",
                         help = "Download all photos in the selected album or "
                                "the whole group into folder(s) named with the "
                                "album ID and album name",
                         action = "store_true")

    parser.add_argument("--filename", "-f",
                        help = "Specify a filename when downloading a single "
                               "photo")

    parser.add_argument("--log-csv", "-G",
                        help = "Log results of --download-all to a CSV file",
                        metavar = "FILENAME")

    args = parser.parse_args()

    if args.chrome:
        print("\nLoading Chrome/Chromium cookies...")
        cookiejar = browser_cookie3.chrome()
        # Pretend to be Chrome 58 on Win10 x64
        # This doesn't seem to be necessary but we might as well as it's easy
        session.headers.update({ "User-Agent": "Mozilla/5.0 (Windows NT 10.0; "
                                 "Win64; x64) AppleWebKit/537.36 (KHTML, like "
                                 "Gecko) Chrome/58.0.3029.110 Safari/537.36" })

    if args.firefox:
        print("\nLoading Firefox cookies...")
        cookiejar = browser_cookie3.firefox()
        # Pretend to be Firefox 53 on Win10 x64
        session.headers.update({ "User-Agent": "Mozilla/5.0 (Windows NT 10.0; "
                                 "Win64; x64; rv:53.0) Gecko/20100101 "
                                 "Firefox/53.0" })

    print("\nTesting access to group '" + args.groupname + "'...")
    stats = get_group_stats(args.groupname, cookiejar)

    if stats["result"] == "no-access":
        print("No access to group - have you logged in?")
        exit(1)

    if stats["result"] == "error":
        print("Server returned error code " + str(stats["status"]) +
            " and error message '" + stats["message"] + "'")
        if stats["status"] == 404 and \
           stats["message"] == \
                "ResourceNotFoundException{resourceType=GROUP Group...":
            print("Yahoo! could not find the group - please double-check")
            print("the name you specified.")
        else:
            print("This may indicate a problem on Yahoo!'s servers.")

        exit(2)

    if stats["result"] == "no-data":
        print("The server returned no data.")
        print("This may indicate a problem on Yahoo!'s servers.")

        exit(3)

    print("\nSuccessfully connected to the group. The server reports:")
    print("Number of albums: " + str(stats["albums"]))
    print("Number of photos: " + str(stats["photos"]))
    print("These numbers may be inaccurate.")

    album = None

    if args.list_albums or \
       args.list_albums_csv or \
       args.list_album_ids or \
       args.album or \
       args.album_id or \
       args.download_all:
        print("\nFetching album list...")
        albums = get_album_list(args.groupname, cookiejar)

        # Did we get any albums back?
        if not albums:
            # No. Empty list.
            print("\nFetching the album list failed.")
            exit(4)

        print("\nRetrieved details of " + str(len(albums)) + " albums.")

        if args.list_albums:
            list_albums_long(albums)

        if args.list_albums_csv:
            list_albums_csv(albums, args.list_albums_csv)
            print("\nSaved file " + args.list_albums_csv)

        if args.list_album_ids:
            list_album_ids(albums)

        if args.album:
            a = [ i for i in albums if i["name"].upper() == args.album.upper() ]

            if not a:
                print("\nUnable to find the album called '" + args.album + "'.")
                print("Please double-check the name.")
                exit(5)

            if len(a) == 1:
                # Just one hit - good
                #albumid = a[0]["ID"]
                album = a[0]
                print("\nSelected the following album:")
                list_albums_long(a)
            else:
                # Is this possible?
                print("\nSearch returned " + str(len(album)) +
                      " albums with that name!")
                print("Please use --album-id with the ID number from the "
                      "following list:")
                list_albums_long(a)
                exit(6)

        if args.album_id:
            a = [ i for i in albums if i["ID"] == args.album_id ]

            if not a:
                print("\nUnable to find the album with ID number " +
                    str(args.album_id) + ".")
                print("Please double-check the number.")
                exit(5)

            if len(a) == 1:
                # Just one hit - good
                #albumid = args.album_id
                album = a[0]
                print("\nSelected the following album:")
                list_albums_long(a)
            else:
                # This is probably impossible
                print("\nSearch returned " + str(len(a)) +
                      " albums with that ID!")
                print("Maybe try using --album with the album name from the "
                      "following table?")
                list_album_ids(a)
                exit(6)

    if args.list_photos or \
       args.list_photos_csv or \
       args.list_photo_ids or \
       args.download_photo or \
       args.download_photo_id or \
       args.download_all:

        if not album:
            # Get them all
            print("\nFetching list of all photos in the group...")
            print("(This could take a while.)")
            photos = get_photo_list_group(args.groupname, cookiejar)
        else:
            # Just get one album
            print("\nFetching list of photos in the album...")
            photos = get_photo_list_album(args.groupname, cookiejar, album["id"])

        # Did we get any photos back?
        if not photos:
            # No. Empty list.
            print("Fetching the photo list failed.")
            exit(7)

        print("\nRetrieved details of " + str(len(photos)) + " photos.")

        if args.list_photos:
            list_photos_long(photos)

        if args.list_photos_csv:
            list_photos_csv(photos, args.list_photos_csv)
            print("\nSaved file " + args.list_photos_csv)

        if args.list_photo_ids:
            list_photo_ids(photos)

        if args.download_photo:
            p = [ i for i in photos
                  if i["name"].upper() == args.download_photo.upper() ]

            if not p:
                print("\nUnable to find the photo called '" +
                      args.download_photo + "'.")
                print("Please double-check the name.")
                exit(5)

            if len(p) == 1:
                # Just one hit - good
                print("\nSelected the following photo:")
                list_photos_long(p)

                # Pretend to have clicked through from the album page
                referer = "https://groups.yahoo.com/neo/groups/" + \
                          args.groupname + "/photos/albums/" + str(p["albumID"])

                result = download_photo(p[0], cookiejar, args.filename,
                                        { "Referer": referer })
                if result == 200:
                    print("Downloaded successfully.")
                else:
                    print("Server returned error " + str(result))
            else:
                # More than one hit. This can happen.
                print("\nSearch returned " + str(len(p)) +
                      " photos with that name!")
                print("Please use --download-photo-id with the ID number from "
                      "the following list:")
                list_photos_long(p, True)
                exit(6)

        if args.download_photo_id:
            p = [ i for i in photos if i["ID"] == args.download_photo_id ]

            if not p:
                print("\nUnable to find the photo with ID number " +
                    str(args.download_photo_id) + ".")
                print("Please double-check the number.")
                exit(5)

            if len(p) == 1:
                # Just one hit - good
                print("\nSelected the following photo:")
                list_photos_long(p, True)

                # Pretend to have clicked through from the album page
                referer = "https://groups.yahoo.com/neo/groups/" + \
                          args.groupname + "/photos/albums/" + str(p["albumID"])

                result = download_photo(p[0], cookiejar, args.filename,
                                        { "Referer": referer })
                if result == 200:
                    print("Downloaded successfully.")
                else:
                    print("Server returned error " + str(result))
            else:
                # This is probably impossible
                print("\nSearch returned " + str(len(p)) +
                      " photos with that ID!")
                print("Maybe try using --download-photo with the photo name "
                      "from the following table?")
                list_photo_ids(p)
                exit(6)

    if args.download_all:
        if args.log_csv:
            csvfile = open(args.log_csv, 'w', newline='')
            fields = [ "ID", "albumID", "name", "yahoo_filename", "filetype",
                   "description", "creator", "height", "width", "filesize",
                   "result", "saved_filename" ]

            logger = csv.DictWriter(csvfile,
                                    fieldnames = fields,
                                    extrasaction = "ignore")
            logger.writeheader()

        # Get the current working directory
        cwd = pathlib.Path.cwd()

        # Has the user selected an album?
        if album:
            dirname = str(album["ID"]) + " - " + \
                      sanitise_filename(album["name"])

            print("\nDownloading into directory " + dirname)
            destdir = cwd / dirname
            destdir.mkdir(exist_ok = True)

#        if not albumid:
#            # No - use all of them
#            albumlist = albums
#        else:
#            # Yes - just use the selected one
#            albumlist = [ i for i in albums if i["ID"] == albumid ]

        for photo in photos:
            filename = make_photo_filename(photo)
            print("\nPhoto ID:       " + str(photo["ID"]))
            print(  "Photo name:     " + photo["name"])
            print(  "Description:    " + photo["description"])
            print(  "Filesize:       " + str(photo["filesize"]))

            if not album:
                a = [ i for i in albums if i["ID"] == photo["albumID"] ]

                if a:
                    dirname = str(photo["albumID"]) + " - " + \
                                  sanitise_filename(a[0]["name"])
                else:
                    dirname = str(photo["albumID"])

                print(  "Directory:      " + dirname)
                destdir = cwd / dirname
                destdir.mkdir(exist_ok = True)

            # Pretend to have clicked through from the album page
            referer = "https://groups.yahoo.com/neo/groups/" + \
                      args.groupname + "/photos/albums/" + str(photo["albumID"])

#            if not photos:
#                print("No photos found.")
#            else:
#                print("Downloading photos into directory " + dirname)
#                for photo in photos:

            destfile = destdir / filename

            if destfile.exists():
                print("File '" + filename + "' already exists - "
                        "skipping download.")
            else:
                print("Downloading as: " + filename)

                result = download(photo["url"] + "?download=1",
                                    cookiejar, destfile,
                                    { "Referer": referer })
                if result == 200:
                    print("Downloaded successfully.")
                else:
                    print("Server returned error " + str(result))

                if args.log_csv:
                    loginfo = {}
                    loginfo["yahoo_filename"] = photo["filename"]
                    loginfo["saved_filename"] = str(destfile)
                    loginfo["result"] = result
                    logger.writerow({ **photo, **loginfo })

        if args.log_csv:
            csvfile.close()

main()

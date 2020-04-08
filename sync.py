"""
Commandline Utility to Backup, Convert and Upload files from the remarkable
"""

#!/usr/bin/env python3

### IMPORTS ###
import os
import sys
import shutil
import glob
import json
import time
from argparse import ArgumentParser
from PyPDF2 import PdfFileReader
from rm_tools.rM2svg import rm2svg
# needs imagemagick, pdftk

__prog_name__ = "sync"

# Set Parameters and folders for sync
syncDirectory = "/Users/lisa/Documents/Literature"
remarkableBackupDirectory = "/Users/lisa/Documents/remarkableBackup"
remContent = "/xochitl"
remarkableDirectory = "/home/root/.local/share/remarkable/xochitl"
remarkableUsername = "root"
remarkableIP = "10.11.99.1"
# https://github.com/lschwetlick/maxio/tree/master/tools
# conversionScriptPDF = "/Users/lisa/Documents/Projects/rMTools/maxio/tools/rM2pdf"
# conversionScriptNotes = "/Users/lisa/Documents/Projects/rMTools/maxio/tools/rM2svg"
# https://github.com/reHackable/scripts
pushScript = "/Users/lisa/Documents/Projects/rMTools/scripts/host/repush.sh"
bgPath = "/Users/lisa/Documents/remarkableBackup/templates/"
emptyRm = "/Users/lisa/Documents/remarkableBackup/empty.rm"

def main():
    """
    Parse Commandline Arguments
    """
    parser = ArgumentParser()
    parser.add_argument("-b",
                        "--backup",
                        help="pass when rM is connected, to back up rM data",
                        action="store_true")
    parser.add_argument("-c",
                        "--convert",
                        help="use rM files in backup directory to generate annotated PDFs and save them in your library",
                        action="store_true")
    parser.add_argument("-u",
                        "--upload",
                        help="upload new files in library to rM",
                        action="store_true")
    parser.add_argument("-d",
                        "--dry_upload",
                        help="just print upload commands",
                        action="store_true")
    parser.add_argument("-l",
                        "--makeList",
                        help="get a list of pdf files on rM",
                        action="store_true")
    parser.add_argument("-la",
                        "--listAllFiles",
                        help="get a list of files on rM",
                        action="store_true")
    args = parser.parse_args()
    if args.backup:
        backupRM()
    if args.makeList:
        listFiles()
    if args.convert:
        convertFiles()
    if args.upload:
        print("upload")
        uploadToRM_curl(args.dry_upload)
    if args.listAllFiles:
        printAllFiles()
    print("Done!")

### BACK UP ###
# TODO: catch connection errors
# TODO: only backup changed files (Problem is that rM doesnt run rsync)
def backupRM():
    """
    Backs up all files on the remarkable so we can then convert them. Also its always nice to have a backup.
    Downside is that it kaes a while because rsync doesn't work and we are copying EVERYTHING!
    """
    print("Backing up your remarkable files")
    #Sometimes the remarkable doesnt connect properly. In that case turn off & disconnect -> turn on -> reconnect
    #shutil.rmtree("/Users/lisa/Documents/remarkableBackup" + remContent)
    print("deleted old files")
    backupCommand = "".join(["scp -r ", remarkableUsername, "@", remarkableIP, ":", remarkableDirectory, " ", remarkableBackupDirectory])
    print(backupCommand)
    os.system(backupCommand)
    # os.system("scp -r root@10.11.99.1:/home/root/.local/share/remarkable/xochitl /Users/lisa/Documents/remarkableBackup")

def listFiles():
    """
    Prints a List of all PDFs on the rM
    """
    rmPdfList = glob.glob(remarkableBackupDirectory + remContent + "/*.pdf")
    rmPdfNameList = []
    for f in rmPdfList:
        # refNr = os.path.basename(f[:-4])
        refNrPath = f[:-4]
        meta = json.loads(open(refNrPath + ".metadata").read())
        rmPdfNameList.append(meta["visibleName"])

    print("rmPdfNameList")
    print(rmPdfNameList)
    print("len(rmPdfNameList)")
    print(len(rmPdfNameList))

def printAllFiles():
    """
    Prints a list of all files.
    """
    rmLinesList = glob.glob(remarkableBackupDirectory + remContent + "/*.lines")
    print(rmLinesList)
    print(len(rmLinesList))
    cntr = 0
    for i in range(0, len(rmLinesList)):
        refNrPath = rmLinesList[i][:-6]
        meta = json.loads(open(refNrPath + ".metadata").read())
        print(meta["visibleName"])
        cntr += 1
    print("len ", cntr)

### CONVERT TO PDF ###
def convertFiles():
    """
    Converts Files on rM to PDF versions and saves them the the appropriate folders. Only converts things that have been changed since the last sync.
    """

    #### Get file lists
    files = [x for x in os.listdir(remarkableBackupDirectory+remContent) if "." not in x]

    for i in range(0, len(files)):
        # get file reference number
        refNrPath = remarkableBackupDirectory + remContent + "/" + files[i]
        # get meta Data
        meta = json.loads(open(refNrPath + ".metadata").read())
        fname = meta["visibleName"]
        fname = fname.replace(" ", "_")
        # Does this lines file have an associated pdf?
        AnnotPDF = os.path.isfile(refNrPath + ".pdf")
        # Get list of all rm files i.e. all pages
        npages = len(glob.glob(refNrPath+"/*.rm"))
        if npages != 0:
            if AnnotPDF:
                # deal with annotated pdfs
                syncFilePath = syncDirectory + "/*/" + meta["visibleName"] + ".pdf" if meta["visibleName"][-4:] != ".pdf" else syncDirectory + "/*/" + meta["visibleName"]
                inSyncFolder = True if glob.glob(syncFilePath) != [] else False
                # does the file exist in our system?
                if inSyncFolder:
                    # have we exported this thing before?
                    local_annotExist = True if glob.glob(syncFilePath[:-4] + "_annot.pdf") != [] else False
                    remoteChanged = True
                    if local_annotExist:
                        local_annotPath = glob.glob(syncFilePath[:-4]+"_annot.pdf")[0]
                        local_annot_mod_time = os.path.getmtime(local_annotPath)
                        remote_annot_mod_time = int(meta["lastModified"])/1000 # rm time is in ms
                        # has this version changed since we last exported it?
                        remoteChanged = remote_annot_mod_time > local_annot_mod_time
                    if remoteChanged:
                        origPDF = glob.glob(syncFilePath)[0]
                        #####
                        convertAnnotatedPDF(fname, refNrPath, origPDF)
                        #####
                    else:
                        print(fname + "hasn't been modified")
                else:
                    print(fname + " does not exist in the sync directory")
                    # TODO allow y/n input whether it should be copied there anyway
            else:
                # deal with notes
                # needs imagemagick
                print("exporting Notebook " + fname)
                syncFilePath = syncDirectory + "/Notes/" + fname + ".pdf"
                inSyncFolder = True if glob.glob(syncFilePath) != [] else False
                remoteChanged = True
                # does it exist yet?
                if inSyncFolder:
                    local_annot_mod_time = os.path.getmtime(syncFilePath)
                    remote_annot_mod_time = int(meta['lastModified'])/1000 # rm time is in ms
                    # has this version changed since we last exported it?
                    remoteChanged = remote_annot_mod_time > local_annot_mod_time
                if remoteChanged:
                    #####
                    convertNotebook(fname, refNrPath)
                    #####
                else:
                    print(fname + "has not changed")


### UPLOAD ###
# TODO: Upload to folders (scripts/repush.sh)
def uploadToRM(dry):
    """
    Uploads files to the rM. This should allow us to set a folder. DOESNT WORK YET!
    """
    # list of files in Library
    syncFilesList = glob.glob(syncDirectory + "/*/*.pdf")
    # list of files on the rM (hashed)
    rmPdfList = glob.glob(remarkableBackupDirectory + remContent + "/*.pdf")
    # make list of actual names (not hashed)
    pdfNamesOnRm = []
    for i in range(0, len(rmPdfList)):
        refNrPath = rmPdfList[i][:-4]
        # get meta Data
        meta = json.loads(open(refNrPath + ".metadata").read())
        # Make record of pdf files already on device
        rmPdfName = meta["visibleName"] + ".pdf" if meta["visibleName"][-4:] != ".pdf" else meta["visibleName"]
        pdfNamesOnRm.append(rmPdfName)

    # remove files in the Notes directory from the list (those dont need to be re-uploaded)
    syncFilesList = [x for x in syncFilesList if "/Notes/" not in x]
    # find absolute path
    syncNames = [os.path.basename(f) for f in syncFilesList]
    # remove annotated pdf files from the list (those dont need to be re-uploaded)
    syncNames = [x for x in syncNames if "annot" not in x]

    # find files that are not already on the rM
    # this gets elements that are in the sync list but not on the rM
    uploadList = [x for x in syncNames if x not in pdfNamesOnRm]
    # print("uploadList:")
    # print(uploadList)

    uploadPathList = [glob.glob(syncDirectory + "/*/" + x)[0] for x in uploadList]
    # print("uploadPathList:")
    # print(uploadPathList)
    # do in batches of the folders
    folderList = [os.path.dirname(x).split("/")[-1] for x in uploadPathList]
    # print(folderList)
    batches = list(set(folderList))

    # print(batches)

    for folder in batches:
        filesInFolder = [f for f in uploadPathList if folder == os.path.dirname(f).split("/")[-1]]
        print("upload " + " ".join(filesInFolder) + " to " + folder)

        folderpath = os.path.dirname(filesInFolder[0])
        if folderpath != syncDirectory:
            uploadCmd = "".join(["bash ", pushScript, " -o /", folder, " ", " ".join(filesInFolder)])
        else:
            uploadCmd = "".join(["bash ", pushScript, " ".join(filesInFolder)])

        if dry:
            print("uploadCmd: ")
            print(uploadCmd)
        else:
            os.system(uploadCmd)
            #Sleep to allow restart
            print("sleeping while rM restarts")
            time.sleep(15)




def uploadToRM_curl(dry):
    """
    Uploads files to the rM. They will land just in the home folder for manual sorting.
    filenames cant have "-" in them!
    """
    # list of files in Library
    syncFilesList = glob.glob(syncDirectory + "/*/*.pdf")
    # list of files on the rM (hashed)
    rmPdfList = glob.glob(remarkableBackupDirectory + remContent + "/*.pdf")
    # make list of actual names (not hashed)
    pdfNamesOnRm = []
    for i in range(0, len(rmPdfList)):
        refNrPath = rmPdfList[i][:-4]
        # get meta Data
        meta = json.loads(open(refNrPath + ".metadata").read())
        # Make record of pdf files already on device
        rmPdfName = meta["visibleName"] + ".pdf" if meta["visibleName"][-4:] != ".pdf" else meta["visibleName"]
        pdfNamesOnRm.append(rmPdfName)
    # remove files in the Notes directory from the list (those dont need to be re-uploaded)
    syncFilesList = [x for x in syncFilesList if "/Notes/" not in x]
    # find absolute path
    syncNames = [os.path.basename(f) for f in syncFilesList]
    # remove annotated pdf files from the list (those dont need to be re-uploaded)
    syncNames = [x for x in syncNames if "annot" not in x]

    # find files that are not already on the rM
    # this gets elements that are in the sync list but not on the rM
    uploadList = [x for x in syncNames if x not in pdfNamesOnRm]
    for upl in uploadList:
        # get full path for the file to be uploaded
        filePath = glob.glob(syncDirectory + "/*/" + upl)[0]
        # chop the ending if necessary to get file name
        fileName = upl if upl[-4:0] != "pdf" else upl[:-4]

        print("upload "+ fileName +" from "+filePath)

        # # CURL version (can't copy directly to folders)
        # #http://remarkablewiki.com/index.php?title=Methods_of_access
        # #chronos@localhost ~/Downloads $ curl 'http://10.11.99.1/upload' -H 'Origin: http://10.11.99.1' -H 'Accept: */*' -H 'Referer: http://10.11.99.1/' -H 'Connection: keep-alive' -F "file=@Get_started_with_reMarkable.pdf;filename=Get_started_with_reMarkable.pdf;type=application/pdf"
        #                                  curl 'http://10.11.99.1/upload' -H 'Origin: http://10.11.99.1' -H 'Accept: */*' -H 'Referer: http://10.11.99.1/' -H 'Connection: keep-alive' -F "file=@bla.pdf;filename=bla.pdf;type=application/pdf" 
        #uploadCmd = "".join(["curl 'http://10.11.99.1/upload' -H 'Origin: http://10.11.99.1' -H 'Accept: */*' -H 'Referer: http://10.11.99.1/' -H 'Connection: keep-alive' -F 'file=@", filePath, ";filename=", fileName, ";type=application/pdf'"])
        uploadCmd = "".join(["curl 'http://",remarkableIP,"/upload' -H 'Origin: http://",remarkableIP,"' -H 'Accept: */*' -H 'Referer: http://",remarkableIP,"' -H 'Connection: keep-alive' -F 'file=@", filePath, ";filename=", fileName, ";type=application/pdf'"])
        #print(uploadCmd)
        # os.system(uploadCmd)
        # folderpath=os.path.dirname(filePath)
        # if folderpath != syncDirectory:
        #     foldername=folderpath.split('/')[-1]
        #     uploadCmd="".join(["bash ", pushScript, " -o /", foldername," ",filePath])
        # else:
        #     uploadCmd="".join(["bash ", pushScript, filePath])

        if dry:
            print("uploadCmd: ")
            print(uploadCmd)
        else:
            os.system(uploadCmd)
            # time.sleep(10)

## CONVERT UNITS ##
def convertNotebook(fname, refNrPath):
    """
    Converts Notebook to a PDF by taking the annotations and the template background for that notebook.
    """
    try:
        os.mkdir('tempDir')
    except:
        pass
    with open(refNrPath+".pagedata") as file:
        backgrounds = [line.strip() for line in file]

    bg_pg = 0
    bglist = []
    for bg in backgrounds:
        convertSvg2PdfCmd = "".join(["rsvg-convert -f pdf -o ", "tempDir/bg_" + str(bg_pg) + ".pdf ", str(bgPath) + bg.replace(" ", "\ ") + ".svg"])
        os.system(convertSvg2PdfCmd)
        bglist.append("tempDir/bg_"+str(bg_pg)+".pdf ")
        bg_pg += 1
    merged_bg = "tempDir/merged_bg.pdf"
    os.system("convert " + (" ").join(bglist) + " " + merged_bg)
    input1 = PdfFileReader(open(merged_bg, 'rb'))
    pdfsize = input1.getPage(0).mediaBox
    content = json.loads(open(refNrPath + ".content").read())

    pdflist = []
    for pg, pg_hash in enumerate(content['pages']):
        rmpath = refNrPath + "/" + pg_hash + ".rm"
        print("page",rmpath)
        # skip page if it doesnt extist anymore. This is fine in notebooks because nobody cares about the rM numbering.
        try:
            rm2svg(rmpath, "tempDir/temprm"+str(pg)+".svg", coloured_annotations=True)
            convertSvg2PdfCmd = "".join(["rsvg-convert -f pdf -o ", "tempDir/temppdf" + str(pg), ".pdf ", "tempDir/temprm" + str(pg) + ".svg"])
            os.system(convertSvg2PdfCmd)
            pdflist.append("tempDir/temppdf"+str(pg)+".pdf")
        except FileNotFoundError:
            continue

    merged_rm = "tempDir/merged_rm.pdf"
    os.system("convert " + (" ").join(pdflist) + " " + merged_rm)
    stampCmd = "".join(["pdftk ", merged_bg, " multistamp ", merged_rm, " output " + syncDirectory + "/Notes/" + fname + ".pdf"])
    os.system(stampCmd)
    # Delete temp directory
    shutil.rmtree("tempDir", ignore_errors=False, onerror=None)
    return True

def convertAnnotatedPDF(fname, refNrPath, origPDF):
    """
    Converts a PDF and it's annotations into one PDF.
    """
    try:
        os.mkdir("tempDir")
    except:
        pass
    # only then fo we export
    print(fname+" is being exported.")
    # subFolder = os.path.basename(os.path.dirname(origPDF))
    # get info on origin pdf
    input1 = PdfFileReader(open(origPDF, "rb"))
    npages = input1.getNumPages()
    pdfsize = input1.getPage(0).mediaBox
    pdfx = int(pdfsize[2])
    pdfy = int(pdfsize[3])
    # rM will not create a file when the page is empty so this is a placeholde empty file to use.
    rm2svg(emptyRm, "tempDir/emptyrm.svg", coloured_annotations=True, x_width=pdfx, y_width=pdfy)

    content = json.loads(open(refNrPath + ".content").read())
    # export
    pdflist = []
    for pg, pg_hash in enumerate(content['pages']):
        # print(pg)
        rmpath = refNrPath + "/" + pg_hash + ".rm"
        if os.path.isfile(rmpath):
            rm2svg(rmpath, "tempDir/temprm" + str(pg) + ".svg", coloured_annotations=False, x_width=pdfx, y_width=pdfy)
            svg_path = "tempDir/temprm" + str(pg) + ".svg"
        else:
            svg_path = "tempDir/emptyrm.svg"
        convertSvg2PdfCmd = "".join(["rsvg-convert -f pdf -o ", "tempDir/temppdf" + str(pg), ".pdf ", svg_path])
        os.system(convertSvg2PdfCmd)
        pdflist.append("tempDir/temppdf"+str(pg)+".pdf")
    #pdflist = glob.glob("tempDir/*.pdf")
    merged_rm = "tempDir/merged_rm.pdf"
    os.system("convert "+ (" ").join(pdflist)+" "+merged_rm)
    # could also use empty pdf on remarkable, but computer side annotations are lost. this way if something has been annotated lots fo times it may stat to suck in quality
    # stamp extracted lines onto original with pdftk
    stampCmd = "".join(["pdftk ", origPDF, " multistamp ", merged_rm, " output ", origPDF[:-4], "_annot.pdf"])
    os.system(stampCmd)
    # Remove temporary files
    shutil.rmtree("tempDir", ignore_errors=False, onerror=None)
    return True


if __name__ == "__main__":
    print("main")
    main()

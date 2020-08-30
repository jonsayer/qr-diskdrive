
#!/usr/bin/env python
################################################################################
 # qr-drive can encode and decode files into a QR codes in the manner of storing 
 # data to a disk drive
 #
 # LICENSE: GNU GENERAL PUBLIC LICENSE Version 3
 #
 # @author      Jon Sayer
 # @copyright   Copyright (c) 2020
 # @license     http://www.gnu.org/licenses/gpl.html GPLv3
 # @version     1
 # @link        
 ###############################################################################

import qrcode
import cv2
import sys
import argparse
import time
import math
from pyzbar import pyzbar
from base64     import b64encode, b64decode
from os         import path,mkdir,rmdir,remove
from binaryornot.check import is_binary
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import inch
from reportlab.lib import utils as rl_utils

################################################################################################################
                                        # Pre-set default variables
################################################################################################################

# paper sizes for output PDFs
from reportlab.lib.pagesizes import LETTER 
PLAYING_CARD = (2.5 * inch, 3.5 * inch)
INDEX_CARD = (3 * inch, 5 * inch)

#max capacity of a QR code in binary is 2953. 
CHUNK_SIZE = 2900 #2928     set to 1kb
#pixel width of a bit of saved QR code
DEFAULT_PIXEL_DENSITY = 10
#color of a 'black' pickel
DEFAULT_FILL_COLOR = 'black'
# color of a 'white' pixel
DEFAULT_BACK_COLOR = 'white'
# default error detection. H for security, L for capacity. Also M and Q but why even?
DEBUG_LEVEL  = qrcode.constants.ERROR_CORRECT_L
#default folder that generated files are stored in, default is the same as the script
DIRECTORY = ''

# class definition used in QR reading functions to 
class qrCodeOutput:
    def __init__(self, isBinaryFile, outFileName, finalOutputString):
        self.isBinaryFile = isBinaryFile
        self.outFileName = outFileName
        self.finalOutputString = finalOutputString

################################################################################################################
                                        # COMMAND AND CONTROL FUNCTIONS
################################################################################################################

def main():
    print(welcomeGraphic())
    
    parser = argparse.ArgumentParser(description='## WRITE A DESCRIPTION')
    parser.add_argument("-s","--save", type=str, help="Save specified file to QR code", action="store")
    parser.add_argument("-l","--load",  type=str, help="Load a file from a QR code or series of codes in specified image file(s) using the filename '[filename].[0-9].png' ", action="store")
    parser.add_argument("-c","--camera", help="Load a file from a QR code/series of codes from a webcam", action="store_true")
    parser.add_argument("-d","--directory",  type=str, help="Directory in which to save the output files", action="store")
    parser.add_argument("-n","--name", type=str, help="Output file name overriding default behavior (for save, default uses filename in, for load default uses name encoded in QR code, or file name). Setting this will not override the file type (eg. png, zip, etc)", action="store")
    #parser.add_argument("-cid","--cameraId", help="Select the webcam to use as the input camera. Default = 0", type=int, action="store")
    parser.add_argument("-o","--outputType", type=str, help="Output Type: PNG (Default), letter, index_card, playing_card, zip. Ignored when loading data.", action="store")
    parser.add_argument("-b","--bytesize", type=int, help="Maximum size of each QR code, in bytes (max 2953, default 2900)", action="store")
    parser.add_argument("-px","--pixeldensity", type=int, help="Width in pixels of a bit of saved QR code.", action="store")
    parser.add_argument("-f","--fillcolor", type=str, help="FILL COLOR, ie the dark color in the QR code. Use a basic color name eg. \'red\' or a hex code eg. #FFAABB.  Default: black", action="store")
    parser.add_argument("-w","--whitebackgroundcolor", type=str, help="BACK COLOR, ie the light color in the QR code.  \n Default: white", action="store")
    parser.add_argument("-e","--errorcorrection", type=str, help="Error correction level in QR codes. Can use L, M or H  \n Default: L", action="store")
    
    args = parser.parse_args()
    setDefaults(args)
    if args.name is not None:
        outFileName = args.name
    else: 
        outFileName = None
    if args.save is not None:
        filename = args.save
        if args.outputType is not None:
            if args.outputType.lower() == 'png':
                saveMode(filename,False,LETTER,outFileName)
            elif args.outputType.lower() == 'letter':
                saveMode(filename,True,LETTER,outFileName)
            elif args.outputType.lower() == 'index':
                saveMode(filename,True,INDEX_CARD,outFileName)
            elif args.outputType.lower() == 'playing_card':
                saveMode(filename,True,PLAYING_CARD,outFileName)
            elif args.outputType.lower() == 'zip':
                print('I aint done that yet')
                sys.exit()
            else:
                print('invalid output type')
                parser.print_help()
                sys.exit()
        else:
            saveMode(filename,False,LETTER,outFileName)
    elif args.load is not None:
        readFromPNG(args.load,outFileName)
    elif args.camera:
        readFromCamera(outFileName)
    else:
        mode = input("\nSave or read? \n (1) Save \n (2) Read \n: ")
        if(mode != '1' and mode != '2' ):
            print("Error: Invalid mode. Type 1 to save file or 2 to read QR codes")
            sys.exit()
        if(mode == '1'):
            filename = input('Filename to encode: ')
            mode = input('\nOutput to \n(1) PNG file(s) \n(2) Letter-size PDF \n(3) Index Card-size PDF \n(4) Playing Card-size PDF \n(5) Custom \n: ')
            if(mode == '1'):
                saveMode(filename,False,LETTER,outFileName)
            elif(mode == '2'):
                saveMode(filename,True,LETTER,outFileName)
            elif(mode == '3'):
                saveMode(filename,True,INDEX_CARD,outFileName)
            elif(mode == '4'):
                saveMode(filename,True,PLAYING_CARD,outFileName)
            elif(mode == '5'):
                customize(filename,outFileName)
            else:
                print('Invalid selection')
                sys.exit()
        elif(mode == '2'):
            mode = input('Read from \n(1) Camera \n(2) Local PNG Files \n: ')
            if(mode == '1'):
                readFromCamera(outFileName)
            elif(mode == '2'):
                readFromPNG(None,outFileName)
            else:
                print('Invalid selection')
                sys.exit()

def setDefaults(args):
    global DEBUG_LEVEL
    global CHUNK_SIZE
    global DIRECTORY
    global DEFAULT_PIXEL_DENSITY
    global DEFAULT_FILL_COLOR
    global DEFAULT_BACK_COLOR
    global CHUNK_SIZE
    if args.directory is not None:
        DIRECTORY = args.directory
    if args.pixeldensity is not None:
        DEFAULT_PIXEL_DENSITY = args.pixeldensity
    if args.fillcolor is not None:
        DEFAULT_FILL_COLOR = args.fillcolor
    if args.whitebackgroundcolor is not None:
        DEFAULT_BACK_COLOR = args.whitebackgroundcolor
    if args.bytesize is not None:
        CHUNK_SIZE = args.bytesize
    if args.errorcorrection is not None:
        if args.errorcorrection == 'M':
            DEBUG_LEVEL  = qrcode.constants.ERROR_CORRECT_M
            if CHUNK_SIZE > 2331:
                CHUNK_SIZE = 2331
                print('Setting bytesize to 2331 due to selecting error correction level M')
        if args.errorcorrection == 'H':
            DEBUG_LEVEL  = qrcode.constants.ERROR_CORRECT_H
            if CHUNK_SIZE > 1273:
                CHUNK_SIZE = 1273
                print('Setting bytesize to 1273 due to selecting error correction level H')

def customize(filename,outFileName):
    print('\n\nHit enter to use the default value on all options')
    global CHUNK_SIZE
    global DEFAULT_PIXEL_DENSITY
    global DEFAULT_BACK_COLOR
    global DEFAULT_FILL_COLOR
    global DEBUG_LEVEL
    global DIRECTORY
    NEW_CHUNK_SIZE = int(input('\nCHUNK SIZE, ie max amount of data in each QR code, in bytes \n Default: 2900. Max: 2953 \n: ') or str(0))
    if bool(NEW_CHUNK_SIZE):
        CHUNK_SIZE = NEW_CHUNK_SIZE
        if CHUNK_SIZE > 2953:
            CHUNK_SIZE = 2953
    NEW_PIXEL_DENSITY = int(input('\nPIXEL DENSITY, ie width of each \'bit\' of data, in pixels \n Default: 10 \n: ') or str(0))
    if bool(NEW_PIXEL_DENSITY):
        DEFAULT_PIXEL_DENSITY = NEW_PIXEL_DENSITY
    NEW_FILL_COLOR = input('\nFILL COLOR, ie the dark color in the QR code. Use a basic color name eg. \'red\' or a hex code eg. #FFAABB \n Default: black \n: ')
    if NEW_FILL_COLOR != '':
        DEFAULT_FILL_COLOR = NEW_FILL_COLOR
    NEW_BACK_COLOR = input('\nBACK COLOR, ie the light color in the QR code.  \n Default: white \n ')
    if NEW_BACK_COLOR:
        DEFAULT_BACK_COLOR = NEW_BACK_COLOR
    NEW_DEBUG_LEVEL  = input('\nERROR CORRECTION LEVEL: A higher level of correction will make your codes more resilient to damage, but at a cost of data capacity per code. **This may reduce your Chunk Size if you select a higher level** \n (1) Low (default)\n (2) Medium \n (3) High \n: ')
    if NEW_DEBUG_LEVEL == '2':
        DEBUG_LEVEL  = qrcode.constants.ERROR_CORRECT_M
        if CHUNK_SIZE > 2331:
            CHUNK_SIZE = 2331
    if NEW_DEBUG_LEVEL == '3':
        DEBUG_LEVEL  = qrcode.constants.ERROR_CORRECT_H
        if CHUNK_SIZE > 1273:
            CHUNK_SIZE = 1273
    NEW_DIRECTORY = input('\nDIRECTORY, ie folder to save files to.  \n Default: same as this script \n ')
    if NEW_DIRECTORY is not None:
        DIRECTORY = NEW_DIRECTORY

    mode = input('\nOutput to \n(1) PNG file(s) \n(2) Letter-size PDF \n(3) Index Card-size PDF \n(4) Playing Card-size PDF \n: ')
    if(mode == '1'):
        saveMode(filename,False,LETTER,outFileName)
    if(mode == '2'):
        saveMode(filename,True,LETTER,outFileName)
    if(mode == '3'):
        saveMode(filename,True,INDEX_CARD,outFileName)
    if(mode == '4'):
        saveMode(filename,True,PLAYING_CARD,outFileName)

################################################################################################################
                                        # SAVING FUNCTIONS
################################################################################################################

# MAIN FUNCTION that reads the file and saves file
def saveMode(filename,pdfMode,pagesize,preset_outFileName):
    global DIRECTORY
    global CHUNK_SIZE
    if pdfMode:
        # On playing-card size QR codes we are limited to the width of that medium showing proper density
        # 2 inch square x 72 dpi, max 144 pixel box
        # so I am restricting that format to version 30 QR codes, 137x137, which is pretty low capacity
        # with future testing, may restrict higher!
        if pagesize == PLAYING_CARD:
            if CHUNK_SIZE > 1732 and DEBUG_LEVEL == qrcode.constants.ERROR_CORRECT_L:
                CHUNK_SIZE = 1732
            elif CHUNK_SIZE > 1370 and DEBUG_LEVEL == qrcode.constants.ERROR_CORRECT_M:
                CHUNK_SIZE = 1370
            elif CHUNK_SIZE > 742 and DEBUG_LEVEL == qrcode.constants.ERROR_CORRECT_H: 
                CHUNK_SIZE = 742
        

    if preset_outFileName == '' or preset_outFileName is None:
        preset_outFileName = path.basename(filename)
    else:
        preset_outFileName = preset_outFileName + getextension( path.basename(filename) )
    file = getAndSplitFile(filename,CHUNK_SIZE,preset_outFileName)
    filesizefull = len(file)*( CHUNK_SIZE - len(filename) )
    outputCount = len(file)
    continuing = input( '\nThat file would save as '+str(outputCount)+' QR code(s). Continue? Y/N  : ' )
    if(continuing != 'Y'):
        sys.exit("\nQuitting...")
    current = 0
    directory = ''
    if pdfMode:
        directory = 'TEMP_QR_HOLD'
        mkdir(directory)
        directory = directory + '/'
    elif DIRECTORY != '':
        directory = DIRECTORY
        if not path.exists(directory):
            mkdir(directory)
        directory = directory+'/'
    for blob in file:
        outFileName = generateFileName(directory+preset_outFileName,current,outputCount)
        data = blob
        saveQRcode(outFileName,data,len(data),DEFAULT_FILL_COLOR,DEFAULT_BACK_COLOR,DEFAULT_PIXEL_DENSITY,DEBUG_LEVEL)
        current = current + 1
    if pdfMode:
        generateQRpdf(directory,preset_outFileName,pagesize,outputCount)
        index = 0
        while index < outputCount:
            if path.exists(generateFileName(directory+preset_outFileName,index,outputCount)):
                remove(generateFileName(directory+preset_outFileName,index,outputCount))
            index += 1
        rmdir(directory[:len(directory)-1 ])

def getAndSplitFile(filename,chunkSize,preset_outFileName):
    if not path.exists( filename ):
        show_usage()
        exit( 1 )
    if is_binary( filename ):
        print('\nThis is a binary file. It\'s contents will be encoded in Base64 as ascii text in the QR code. \n')
        BASE64ENCODE = True
        readMethod = 'rb'
    else:
        print('\nThis is a text file and will be encoded directly into the QR code \n')
        BASE64ENCODE = False
        readMethod = 'r'
    
    blobList = []

    with open(filename,readMethod) as f:
        buffer = ''
        if readMethod == 'r':
            fullFile = f.read()
        else:
            binaryData = f.read()
            fullFile = b64encode(binaryData)
            fullFile = fullFile.decode('utf-8')
            buffer = 'b64:'
        if preset_outFileName == '' or preset_outFileName is None:
            preset_outFileName = filename
        buffer = buffer + '::f::' + path.basename(preset_outFileName) + '::/f::'
        codeCount = math.ceil((len(buffer)+len(fullFile))/chunkSize)
        buffer = buffer + '::c0::'
        byte = fullFile[0]
        index = 0
        while len( byte ):
            buffer += byte
            if len( buffer ) == chunkSize:
                blobList.append( buffer )
                index += 1
                buffer = '::c'+str(index)+'::'
            fullFile = fullFile[1:len(fullFile)]
            if len(fullFile):
                byte = fullFile[0]
            else:
                byte = ''

        if len( buffer ):
            blobList.append( buffer )
    return blobList

# Main function for saving a QR code file
def saveQRcode(saveName,data,chunkSize,fillColor,backColor,pixelDensity,debugLevel):
    qr = qrcode.QRCode(
        version=getVersionFromChunk(chunkSize),
        error_correction=debugLevel,
        box_size=pixelDensity,
        border=4,
    )
    qr.add_data(data)
    img = qr.make_image(fill_color=fillColor, back_color=backColor)
    img.save(saveName)

def generateQRpdf(foldername,filename,pagesize,codecount):
    # must alert user that 858 is recommended max chunk size for playing card

    stopThePresses = False
    codesPerPage = 1
    topMargin = 0.25 * inch
    leftMargin = 0.25 * inch
    imageWidth = 2 * inch #default on this is for a playing card
    if pagesize == LETTER:
        codesPerPage = 4
        topMargin = 0.5 * inch
        leftMargin = 0.5 * inch
        imageWidth = 3.5 * inch
    elif pagesize == INDEX_CARD:
        imageWidth = 2.5 * inch
        topMargin = 0.5 * inch
    WIDTH = pagesize[0]
    HEIGHT = pagesize[1]
    if HEIGHT < 5 * inch: #index or playing card
        topMargin = 0.25 * inch
        leftMargin = 0.25 * inch
    currentRow = topMargin
    currentColumn = leftMargin
    index = 0
    pageIndex = 0
    saveDir = ''
    if DIRECTORY != '':
        saveDir = DIRECTORY+'/'
    canvas = Canvas(saveDir+filename+'.QR.pdf',pagesize=pagesize)
    #print headline
    canvas.setFont("Courier-Bold", 18)
    canvas.drawCentredString( WIDTH/2 , HEIGHT-topMargin-9, filename)
    currentRow = topMargin+18+topMargin
    while index < codecount:
        thisFile = foldername+filename+'.'+str(index)+'.png'
        if path.exists( thisFile ):
            #print label for image
            canvas.setFont("Courier", 12)
            canvas.drawString(currentColumn, HEIGHT - currentRow-6 , str(index+1) +'/'+str(codecount))
            # set current row below label
            currentRow = currentRow
            # draw the QR code
            canvas.drawImage(thisFile,currentColumn,HEIGHT - currentRow - imageWidth - 12,imageWidth,imageWidth)
            # position our cursor for next position, to the right of this one
            currentColumn = currentColumn + imageWidth + leftMargin
            #increment page index and check to see if we need a new page
            pageIndex +=1 
            index += 1
            if pageIndex >= codesPerPage and index < codecount:
                #create a new page and redraw the headline, reset margins
                pageIndex = 0
                canvas.showPage()
                currentRow = topMargin
                currentColumn = leftMargin
                canvas.setFont("Courier-Bold", 18)
                canvas.drawCentredString( WIDTH/2 , HEIGHT-topMargin-9, filename)
                currentRow = topMargin+18+topMargin
            #check to see if we've drawn the second QR code on this row, 
            # and if so move to next row
            elif pageIndex == 2:
                currentColumn = leftMargin
                currentRow = currentRow + topMargin + imageWidth
        else:
            print('\n\nSTOP THE PRESSES! Couldn\'t find file with index '+str(index))
            stopThePresses = True
            index = codecount
    if stopThePresses == False:
        canvas.save()

# saves QR code as a PNG
def writeOutputFile(out):
    if out.isBinaryFile:
        readMethod = 'wb'
        output = b64decode(out.finalOutputString)
    else:
        readMethod = 'w'
        output = out.finalOutputString
    if out.outFileName == '':
        out.outFileName = 'unknownfile.txt'
    with open( out.outFileName, readMethod ) as f:
        f.write( output )

################################################################################################################
                                        # LOADING FUNCTIONS
################################################################################################################

# reads a series of QR codes from camera shots
def readFromCamera(outFileName):
    print('\nPlace first QR code in front of the camera. Be sure to cover or keep off frame any other QR codes\n')
    cap = cv2.VideoCapture(0)
    font = cv2.FONT_HERSHEY_PLAIN
    isAnotherFile = True
    out = qrCodeOutput(False,outFileName,'')
    index = 0
    while isAnotherFile:
        print( '\nScanning for image '+str(index) )
        found = False
        time.sleep(1)
        outWithNew = None
        lastQr = ''
        frameC = 0
        while found == False:
            _, frame = cap.read()
            decodedObjects = pyzbar.decode(frame)
            frameC += 1
            for qr in decodedObjects:
                print("\a")
                cv2.putText(frame, str(qr.data), (50, 50), font, 2,
                        (255, 0, 0), 3)
                if len(str(qr.data)) and frameC > 200:
                    outWithNew = decodeQRandAppend(qr,out,index,True)
                    found = True
                    frameC = 0
            cv2.imshow("Frame", frame)

            key = cv2.waitKey(1)
            if key == 27:
                found = True
        if outWithNew.finalOutputString is not None:
            out = outWithNew
            more = ''
            while more != 'Y' and more != 'N':
                more = input('\nQR code '+str(index)+' found. Scan another? Y/N  : ')
            if more == 'Y':
                isAnotherFile = True
                index += 1
            if more == 'N':
                isAnotherFile = False
        else:
            print('Redoing scan')
            isAnotherFile = True
    writeOutputFile(out)

# reads a series of QR code png files
def readFromPNG(fileName,outFileName):
    if fileName == None :
        fileName = input('\nFile to read: ')
    isAnotherFile = True
    index = 0
    out = qrCodeOutput(False,outFileName,'')
    while isAnotherFile:
        if path.exists( fileName+'.'+str(index)+'.png' ):
            firstFile = cv2.imread(fileName+'.'+str(index)+'.png')
            decoded = pyzbar.decode(firstFile)
            for qr in decoded:
                out = decodeQRandAppend(qr,out,index,False)
        else:
            if index == 0:
                print('\nFile "{}" does not exist'.format(fileName) )
                show_usage()
                exit( 1 )
            isAnotherFile = False
        index += 1
    writeOutputFile(out)

#decodes a provided QR code and appends it to the existing "out" object
#also figures out the filename and binary/text status if provided in the first QR code
def decodeQRandAppend(qr,out,index,fromCamera):
    if out.finalOutputString is None:
        out.finalOutputString = ''
    print('Decoding QR code '+str(index))
    data = qr.data.decode("utf-8")
    count = 0
    if index == 0 and data[0 : len( 'b64:' ) ] == 'b64:':
        print('Outputting a binary file')
        out.isBinaryFile = True
        data = data[ len( 'b64:' ) : ]
    if index == 0:
        if data[0 : len( '::f::' ) ] == '::f::':
            data = data[ len( '::f::' ) : ]
            extractedFileName = data[ 0 : data.index('::/f::') ]
            if out.outFileName is None or out.outFileName == '':
                out.outFileName = extractedFileName
                print('Using filename "'+extractedFileName+'"')
            else:
                ext = getextension(extractedFileName)
                out.outFileName = out.outFileName + ext
            data = data[len(extractedFileName) : ]
            data = data[ len( '::/f::' ) : ]
    countMatch = True
    noCount = False
    if data[0 : len( '::c' ) ] == '::c':
        data = data[len('::c') : ]
        count = int(data[0 : data.index('::') ])
        print('Found count '+str(count))
        if count != index:
            countMatch = False
        data = data[ len( str(count) )+len('::') : ]
    else:
        noCount = True
        print('No count found')
    if (countMatch == False or noCount == True) and fromCamera:
        accept = ''
        while accept != 'A' and accept != 'R':
            if countMatch == False:
                print('The index of this QR code ('+str(count)+')does not match the current index ('+str(index)+').')
            if noCount == True:
                print('The scanned QR code does not contain an index, so we can\'t be sure you scanned them in order.')
            accept = input('Would you like to (A)ccept this code or (R)escan QR code'+str(index)+'? \n A/R : ')
        if accept == 'R':
            out.finalOutputString = None
            return out
    out.finalOutputString = out.finalOutputString + data
    return out

################################################################################################################
                                        # UTILITY FUNCTIONS
################################################################################################################

    
# this returns the version number of the QR code protocol that is needed given the 
# size of the data being saved
def getVersionFromChunk(chunk):
    if DEBUG_LEVEL == qrcode.constants.ERROR_CORRECT_H:
        modifier = 0.4
    elif DEBUG_LEVEL == qrcode.constants.ERROR_CORRECT_M:
        modifier = 0.75
    else:
        modifier = 1
    if(chunk <= 106*modifier):
        return 5
    if(chunk <= 271*modifier):
        return 10
    if(chunk <= 520*modifier):
        return 15
    elif(chunk <= 858*modifier):
        return 20
    if(chunk <= 1273*modifier):
        return 25
    elif(chunk <= 1732*modifier):
        return 30
    elif(chunk <= 2303*modifier):
        return 35
    else:
        return 40

def generateFileName(filename,current,outputCount):
    out = filename + '.'+str(current)
    return out+'.png'    

def getextension(filename):
    name, file_extension = path.splitext(filename)
    return file_extension

def show_usage():
    print('you did it wrong')

def welcomeGraphic():
    out = '''

 #####  ######     ######                     ######                         
#     # #     #    #     # #  ####  #    #    #     # #####  # #    # ###### 
#     # #     #    #     # # #      #   #     #     # #    # # #    # #      
#     # ######     #     # #  ####  ####      #     # #    # # #    # #####  
#   # # #   #      #     # #      # #  #      #     # #####  # #    # #      
#    #  #    #     #     # # #    # #   #     #     # #   #  #  #  #  #      
 #### # #     #    ######  #  ####  #    #    ######  #    # #   ##   ###### 


         ▄▄▄▄▄▄▄   ▄▄▄ ▄▄▄▄▄▄▄         ____________________
         █ ▄▄▄ █ ▀▀█▄█ █ ▄▄▄ █        | |""""""""""""""""| |
         █ ███ █ ▀█  █ █ ███ █        |.|________________|H|
         █▄▄▄▄▄█ █ ▄▀▄ █▄▄▄▄▄█        | |________________| |
         ▄▄▄▄▄ ▄▄▄▀ ▄ ▄ ▄ ▄ ▄         | |________________| |
         ▄▄▄█▀▄▀▀█▄▀██ ▀▀ ▀█▀    >>   | |________________| |
         ▄▄  ▀▄▄▄▀ █▀█ ▄▀▀ ▀▀    >>   |    ____________    |
         ▄▄▄▄▄▄▄ █▄▄▄▀▀█ ▀█▄█▀   >>   |   |   |  _     |   |
         █ ▄▄▄ █ ▄▀▀▄ █▄▄▄▀▀▀█        |   |   | | |    |   |
         █ ███ █ █ ▄ █  ▀▀▀█          |   |   | |_|    | V |
         █▄▄▄▄▄█ ██▀▀▀█▄█▀█▀▄         |___|___|________|___|
         
         '''
    return out

if __name__ == "__main__":
    main()

#!/usr/bin/env python
################################################################################
 # qr-drive can encode and decode files into a QR codes in the manner of storing 
 # data to a disk drive
 #
 # LICENSE: GNU GENERAL PUBLIC LICENSE Version 3
 #
 # @author      Jon Sayer
 # @copyright   Copyright (c) 2023
 # @license     http://www.gnu.org/licenses/gpl.html GPLv3
 # @version     1.1
 # @link        https://github.com/jonsayer/qr-diskdrive
 ###############################################################################

import qrcode
import cv2
import sys
import argparse
import time
import math
import shutil
import io
from pyzbar import pyzbar
from base64     import b64encode, b64decode
from os         import path,mkdir,rmdir,remove
from binaryornot.check import is_binary
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import inch
from reportlab.lib import utils as rl_utils
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import ParagraphStyle

################################################################################################################
                                        # Pre-set default variables
################################################################################################################

# paper sizes for output PDFs
from reportlab.lib.pagesizes import LETTER 

PLAYING_CARD = (2.5 * inch, 3.5 * inch)
INDEX_CARD = (3 * inch, 5 * inch)
HALF_LETTER = (5.5 * inch, 8.5 * inch)

#max capacity of a QR code in binary is 2953. 
CHUNK_SIZE = 2928 #2928     set to 1kb
# if true, this variable will prevent the system from overriding the user-set chunk size. 
CHUNK_SAFETY_OVERRIDE = False
#pixel width of a bit of saved QR code
DEFAULT_PIXEL_DENSITY = 10
#color of a 'black' pickel
DEFAULT_FILL_COLOR = 'black'
# color of a 'white' pixel
DEFAULT_BACK_COLOR = 'white'
# width in blocks of the border around the QR code
BORDER = 1
# default error detection. H for security, L for capacity. Also M and Q but why even?
DEBUG_LEVEL  = qrcode.constants.ERROR_CORRECT_L
#default folder that generated files are stored in, default is the same as the script
DIRECTORY = ''
# if true, the file is zipped before being encoded
ZIP_FIRST = False
# Set during decoding when the flag :z: is found on the first QR code. It means that the QR codes contain an archive and must be unzipped after being decoded. 
ZIP_DECODE = False
# number of codes per page on a pdf. 0 means to use defaults
CODES_PER_PAGE = 0
# number of rows and columns per page on a pdf.
COLUMNS = 0
ROWS = 0
# width in inches of a QR code on a PDF page. 0 means it will use the default for that page type
CODE_WIDTH = 0
# margins used on PDF pages, in inches. 0 means to use the defaults
MARGIN_TOP = 0
MARGIN_BOTTOM = 0
MARGIN_LEFT = 0
MARGIN_RIGHT = 0
MARGIN_INTERIOR = 0
# font details for PDFs
PDF_HEADER_FONT = 'Courier-Bold'
PDF_HEADER_FONT_SIZE = 18
PDF_BODY_FONT = 'Courier'
PDF_BODY_FONT_SIZE = 12
# how to align the pdf code within its column, if the horizontal space available is wider than the code. 
PDF_CODE_ALIGN = 'left'
# Assumed dots per inch of the printer, used when printing a PDF
PRINTER_DPI = 72 # We are assuming a **shitty** printer with 72 dpi
# if the user wants to include the ascii text of the QR code on the page for some reason, we can also save .txt files to the directory for use that way. 
PDF_INCLUDE_TXT = ''

# set the text style for the PDF
PARAGRAPH_STYLE = ParagraphStyle(
    "text_output_style",
    fontName="Times-Roman",  
    fontSize=7,  
    textColor='black'
)

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
    
    parser = argparse.ArgumentParser(description='This is a tool for saving files as QR codes, in the manner of saving files to an old-fashioned data format such as tape or punch cards. ')
    parser.add_argument("-l","--load",  type=str, help="Load a file from a QR code or series of codes in specified image file(s) using the filename '[filename].[0-9].png'. ", action="store")
    parser.add_argument("-c","--camera", help="Load a file from a QR code/series of codes from a webcam. Allows for the scanning of multiple QR codes in sequence for larger files. Will use your primary webcam by default.", action="store_true")
    parser.add_argument("-n","--name", type=str, help="Output file name, overriding default behavior (for save, default uses the name of file being encoded, for load default uses name encoded within the QR code). Setting this will not override the file type which is encoded in the QR code or the original file(eg. png, zip, etc).", action="store")

    parser.add_argument("-s","--save", type=str, help="Save specified file to QR code.", action="store")
    parser.add_argument("-d","--directory",  type=str, help="Directory in which to save the output files from a save action.", action="store")
    parser.add_argument("-z","--zipfirst", action='store_const',const=True, help="Flag to Zip the file first before encoding it into QR codes (as a compressed file needs fewer codes). When the file is decoded, it will be automatically unzipped. NOTE: This does't relate to the output type of 'zip'.")

    #parser.add_argument("-cid","--cameraId", help="Select the webcam to use as the input camera. Default = 0", type=int, action="store")
    parser.add_argument("-o","--outputType", type=str, help="Output Type: Method for outputting QR codes. Options: PNG (Default), letter, half_letter, index_card, playing_card, zip. Ignored when loading data.", action="store")
    parser.add_argument("-b","--bytesize", type=int, help="Maximum size of each QR code, in bytes (max and default: 2953). Use one of the following for maximum capacity and scannability: 2953, 2303, 1732, 1273, 858, 520, 271, 106 ", action="store")
    parser.add_argument("-bd","--border", type=int, help="Width of the border around the generated QR code image, in the background color, measured in blocks.", action="store")
    parser.add_argument("-e","--errorcorrection", type=str, help="Error correction level in QR codes. Can use L, M or H  \n Default: L", action="store")
    parser.add_argument("-x","--pixeldensity", type=int, help="Width in pixels of a bit of saved QR code in a PNG. Default: 10", action="store")
    parser.add_argument("-f","--fillcolor", type=str, help="FILL COLOR, ie the dark color in the QR code. Use a basic color name eg. \'red\' or a hex code eg. #FFAABB.  Default: black", action="store")
    parser.add_argument("-w","--whitebackgroundcolor", type=str, help="BACK COLOR, ie the light color in the QR code.  \n Default: white", action="store")
    #parser.add_argument("-p","--codesperpage", type=str, help="When outputing to a PDF, defines how many QR codes to put on a page. Default for index_card and playing_card is 1, default for letter is 4 (2 columns and 2 rows), and the default for half-letter is 2 (1 column and 2 rows).", action="store")
    parser.add_argument("-a","--codealign", type=str, help="On a PDF, how to align the qr code within its column, if the horizontal space available is wider than the code. Options: left, right, center. Default: left", action="store")
    parser.add_argument("-mt","--margintop", type=float, help="Top Margin, when outputing to a PDF. Default: 0.5 inch on letter, 0.25 inch on all others.", action="store")
    parser.add_argument("-mr","--marginright", type=float, help="Right Margin, when outputing to a PDF. Default: 0.5 inch on letter, 0.25 inch on all others.", action="store")
    parser.add_argument("-mb","--marginbottom", type=float, help="Bottom Margin, when outputing to a PDF. Default: 0.5 inch on letter, 0.25 inch on all others.", action="store")
    parser.add_argument("-ml","--marginleft", type=float, help="Left Margin, when outputing to a PDF. Default: 0.5 inch on letter, 0.25 inch on all others.", action="store")
    parser.add_argument("-mi","--margininterior", type=float, help="Margin between columns, when outputing to a PDF with multiple columns. Default: 0.5 inch on letter, 0.25 inch on all others.", action="store")
    parser.add_argument("-col","--columns", type=int, help="On a PDF, the number of columns of QR codes. Default: 1, except on letter, which is 2.", action="store")
    parser.add_argument("-r","--rows", type=int, help="On a PDF, the number of rows of QR codes. Default: 1, except on letter and half_letter, which is 2.", action="store")
    parser.add_argument("-t","--includeText", action='store',type=str, help="When outputting to a PDF, include this to include the text contained in the QR on the same page as it. Options: left, right, above, below. \n NOTE: You must include a -r/--rows or -col/columns parameter above 1 for this to work, as it will render the text in one of the spots for a QR code. \n NOTE: For text that includes a lot of new lines, the tool might not work very well because text will always take up more space than a QR code.")
    parser.add_argument("-y","--overridebytesizelimits", action='store_const',const=True, help="By default, when outputting to PDF, the system will try to figure out a minimum bytesize given the size of the QR codes that will be on the page to ensure they aren't too small to be read. This may override a bytesize you set explicitly. Include this flag to override the override, and use the bytesize you explicitly set.")
    

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
                saveMode(filename,False,False,LETTER,outFileName)
            elif args.outputType.lower() == 'letter':
                saveMode(filename,True,False,LETTER,outFileName)
            elif args.outputType.lower() == 'index_card':
                saveMode(filename,True,False,INDEX_CARD,outFileName)
            elif args.outputType.lower() == 'playing_card':
                saveMode(filename,True,False,PLAYING_CARD,outFileName)
            elif args.outputType.lower() == 'half_letter':
                saveMode(filename,True,False,HALF_LETTER,outFileName)
            elif args.outputType.lower() == 'zip':
                saveMode(filename,False,True,LETTER,outFileName)
                sys.exit()
            else:
                print('invalid output type')
                parser.print_help()
                sys.exit()
        else:
            saveMode(filename,False,False,LETTER,outFileName)
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
            mode = input('\nOutput to \n(1) PNG file(s) \n(2) Letter-size PDF \n(3) Index Card-size PDF \n(4) Playing Card-size PDF \n(5) Half letter PDF \n (6) Custom: ')
            if(mode == '1'):
                saveMode(filename,False,False,LETTER,outFileName)
            elif(mode == '2'):
                saveMode(filename,True,False,LETTER,outFileName)
            elif(mode == '3'):
                saveMode(filename,True,False,INDEX_CARD,outFileName)
            elif(mode == '4'):
                saveMode(filename,True,False,PLAYING_CARD,outFileName)
            elif(mode == '5'):
                saveMode(filename,True,False,HALF_LETTER,outFileName)
            elif(mode == '6'):
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
    global CODES_PER_PAGE
    global MARGIN_TOP
    global MARGIN_BOTTOM
    global MARGIN_LEFT 
    global MARGIN_RIGHT 
    global MARGIN_INTERIOR
    global COLUMNS
    global ROWS
    global CHUNK_SAFETY_OVERRIDE
    global PDF_INCLUDE_TXT
    global BORDER
    global ZIP_FIRST
    global PDF_CODE_ALIGN

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
    if args.bytesize is not None:
        CHUNK_SIZE = args.bytesize
    #if args.codesperpage is not None:
    #    CODES_PER_PAGE = args.codesperpage
    if args.border is not None:
        BORDER = args.border
    if args.margintop is not None:
        MARGIN_TOP = args.margintop
    if args.marginbottom is not None:
        MARGIN_BOTTOM = args.marginbottom
    if args.marginleft is not None:
        MARGIN_LEFT = args.marginleft
    if args.marginright is not None:
        MARGIN_RIGHT = args.marginright
    if args.margininterior is not None:
        MARGIN_INTERIOR = args.margininterior
    if args.codealign is not None:
        PDF_CODE_ALIGN = args.codealign
    if args.columns is not None:
        COLUMNS = args.columns
    if args.rows is not None:
        ROWS = args.rows
    if args.overridebytesizelimits is not None:
        CHUNK_SAFETY_OVERRIDE = True
    if args.zipfirst is not None:
        ZIP_FIRST = True
    if args.includeText is not None:
        PDF_INCLUDE_TXT = args.includeText
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

    mode = input('\nOutput to \n(1) PNG file(s) \n(2) Letter-size PDF \n(3) Index Card-size PDF \n(4) Playing Card-size PDF \n (5) Half-letter PDF : ')
    if(mode == '1'):
        saveMode(filename,False,False,LETTER,outFileName)
    if(mode == '2'):
        saveMode(filename,True,False,LETTER,outFileName)
    if(mode == '3'):
        saveMode(filename,True,False,INDEX_CARD,outFileName)
    if(mode == '4'):
        saveMode(filename,True,False,PLAYING_CARD,outFileName)
    if(mode == '5'):
        saveMode(filename,True,False,HALF_LETTER,outFileName)

################################################################################################################
                                        # SAVING FUNCTIONS
################################################################################################################

# MAIN FUNCTION that reads the file and saves the output file(s)
def saveMode(filename,pdfMode,zipMode,pagesize,preset_outFileName):
    global DIRECTORY
    global CHUNK_SIZE
    
    validateUserInput()

    if pdfMode:
        #set the size parameters of the PDF and check if we need to reduce the chunk size
        setPDFpageDimensionVars(pagesize)

    if preset_outFileName == '' or preset_outFileName is None:
        preset_outFileName = path.basename(filename)
    else:
        preset_outFileName = preset_outFileName + getextension( path.basename(filename) )
    # file is an array containing manageable chunks of the original file stored as text. 
    file = getAndSplitFile(filename,CHUNK_SIZE,preset_outFileName)
    outputCount = len(file)
    continuing = input( '\nThat file would save as '+str(outputCount)+' QR code(s). Continue? Y/N  : ' )
    if(continuing != 'Y'):
        sys.exit("\nQuitting...")
    current = 0
    directory = ''
    # PDF and Zipped QR codes will be stored in a temporary directory that we will delete at the end of the process
    # Otherwise, output to the directory defined by the user
    if pdfMode:
        directory = 'TEMP_QR_HOLD'
        if not path.exists(directory):
            mkdir(directory)
        directory = directory + '/'
    elif zipMode:
        directory = 'QR_'+preset_outFileName
        if not path.exists(directory):
            mkdir(directory)
        directory = directory + '/'
    elif DIRECTORY != '':
        directory = DIRECTORY
        if not path.exists(directory):
            mkdir(directory)
        directory = directory+'/'
    # Loop through the file array and make a QR code for each chunk of the file.
    for blob in file:
        outFileName = generateFileName(directory+preset_outFileName,current,outputCount)
        data = blob
        saveQRcode(outFileName,data,len(data),DEFAULT_FILL_COLOR,DEFAULT_BACK_COLOR,DEFAULT_PIXEL_DENSITY,DEBUG_LEVEL)
        if pdfMode and PDF_INCLUDE_TXT:
            # the user wants to include the ascii text of the QR code on the page of the PDF, so we will also cache that
            saveDataAsTXT(preset_outFileName+'.'+str(current),data)
        current = current + 1
    # if generating a PDF, take the QR codes created and make it, then delete the cached QR codes
    if pdfMode:
        generateQRpdf(directory,preset_outFileName,pagesize,outputCount)
    # if generating a zip file, take the QR codes created and zip them, then delete the cached QR codes
    # as written, you can't zip the pdf
    elif zipMode:
        saveDir = ''
        if DIRECTORY != '':
            saveDir = DIRECTORY+'/'
        shutil.make_archive(saveDir+preset_outFileName, 'zip', directory[:-1])
    # delete the cached QR code PNG files used in the pdf or zip creation process
    if pdfMode or zipMode:
        index = 0
        while index < outputCount:
            if path.exists(generateFileName(directory+preset_outFileName,index,outputCount)):
                remove(generateFileName(directory+preset_outFileName,index,outputCount))
            index += 1
        rmdir(directory[:len(directory)-1 ])


# This function figures out what the CODE_WIDTH of the QR codes should be if output to a PDF, ie. the width in inches
# Also, it will reduce the CHUNK_SIZE if the user's settings will result in QR codes that are illegible. 
def setPDFpageDimensionVars(pagesize):
    global CODES_PER_PAGE
    global MARGIN_TOP
    global MARGIN_BOTTOM
    global MARGIN_LEFT 
    global MARGIN_RIGHT 
    global MARGIN_INTERIOR
    global COLUMNS
    global ROWS
    global CODE_WIDTH
    global CHUNK_SIZE
    global DEBUG_LEVEL
    global PRINTER_DPI
    global PDF_HEADER_FONT_SIZE

    # figure out what all those parameters should be, given what they entered
    if MARGIN_TOP == 0 and (pagesize == LETTER or pagesize == INDEX_CARD or pagesize == HALF_LETTER):
        MARGIN_TOP = 0.5
    elif MARGIN_TOP == 0 :
        MARGIN_TOP = 0.25

    if MARGIN_RIGHT == 0 and (pagesize == LETTER or pagesize == HALF_LETTER):
        MARGIN_RIGHT = 0.5
    elif MARGIN_RIGHT == 0:
        MARGIN_RIGHT = 0.25

    if MARGIN_BOTTOM == 0 and (pagesize == LETTER or pagesize == INDEX_CARD or pagesize == HALF_LETTER):
        MARGIN_BOTTOM = 0.5
    elif MARGIN_BOTTOM == 0:
        MARGIN_BOTTOM = 0.25
        
    if MARGIN_LEFT == 0 and (pagesize == LETTER or pagesize == HALF_LETTER):
        MARGIN_LEFT = 0.5
    elif MARGIN_LEFT == 0:
        MARGIN_LEFT = 0.25
    
    if MARGIN_INTERIOR == 0 and (pagesize == LETTER ):
        MARGIN_INTERIOR = 0.5

    if COLUMNS == 0 and pagesize == LETTER:
        COLUMNS = 2
    elif COLUMNS == 0:
        COLUMNS = 1

    if ROWS == 0 and (pagesize == LETTER or pagesize == HALF_LETTER):
        ROWS = 2
    elif ROWS == 0:
        ROWS = 1

    CODES_PER_PAGE = COLUMNS * ROWS
    print('Margin Top: '+str(MARGIN_TOP)+' Right:'+str(MARGIN_RIGHT)+' Bottom:'+str(MARGIN_BOTTOM)+' Left:'+str(MARGIN_LEFT)+' Inside:'+str(MARGIN_INTERIOR))
    print('Page Dimensions:'+str(pagesize[0])+', '+str(pagesize[1] ))
    print('Columns: '+str(COLUMNS)+' Rows:'+str(ROWS)+' Codes per page:'+str(CODES_PER_PAGE))

    maxWidth = getImageWidth(pagesize[0]/inch,CODES_PER_PAGE,(MARGIN_LEFT+MARGIN_RIGHT),MARGIN_INTERIOR,COLUMNS)
    maxHeight = getImageWidth(pagesize[1]/inch,CODES_PER_PAGE,((2*MARGIN_TOP)+MARGIN_BOTTOM)+(PDF_HEADER_FONT_SIZE/ inch),MARGIN_INTERIOR,ROWS) # to do: the height of the heading on the page
    #print(maxWidth)
    #print(maxHeight)
    if maxWidth > maxHeight:
        CODE_WIDTH = maxHeight
    else:
        CODE_WIDTH = maxWidth
    print('Code Width:'+str(CODE_WIDTH) )

    # We need to ensure that these QR codes are legible
    dpi = PRINTER_DPI
    # what is the minimum dots a QR code module can be and still be legible? This parameter will need to be set in testing and is camera dependent
    # At 72 dpi 1/16th of an inch is 4.5 dots. 1/32nd is 2.25
    minModuleDotWidth = 2
    # 2 inch square x 72 dpi, with at least 2 dots per module, max 72 module (1 module is 1 square) box. This is an imperfect estimate of the max capacity of the QR code
    moduleWidth = CODE_WIDTH * dpi / minModuleDotWidth
    #The largest QR code is 177 modules to a side, so we can stop if we are already larger
    chunkOriginal = CHUNK_SIZE
    # this doesn't work and is temporarily disabled
    if(moduleWidth < 177):
        # there are some sizes of QR code too small for the box we are in
        # a QR codes version number starts at 1, 21 dts per side and goes up to 40. Each additional version is 4 more dots per side
        maxQRversion = (moduleWidth-21)/4
        # get the QR code version our chunk would use
        chunkQRversion = getVersionFromChunk(CHUNK_SIZE)
        while chunkQRversion > maxQRversion or CHUNK_SIZE < 107: # the second parameter stops us from entering a forever loop if we reach the smallest size
            # if we are in this position, it means that our chunk size is too big for the size of QR code we are outputting
            # we need to reduce it
            CHUNK_SIZE = reduceChunkSize(CHUNK_SIZE)
            chunkQRversion = getVersionFromChunk(CHUNK_SIZE)
        print('WARNING: Had to reduce the capacity of each QR code from '+str(chunkOriginal)+' to '+str(CHUNK_SIZE) +' because we are printing a smaller-sized QR code based on settings.')
        #if chunk size is changed, but the override flag is set, reset it back to what the user set it to originally
        if CHUNK_SAFETY_OVERRIDE == True:
            CHUNK_SIZE = chunkOriginal
            print('QR code capacity overridden because -y was set. Reset back to '+str(str(chunkOriginal)) +'. YOU HAVE BEEN WARNED!')

# This gets the file and splits it into smaller chunks that the QR code maker can handle
def getAndSplitFile(filename,chunkSize,preset_outFileName):
    if not path.exists( filename ):
        print('File does not exist: '+filename)
        exit( 1 )

    if ZIP_FIRST:
        # User wants to compress the file before splitting it up
        # Get the full path of the file
        target_path = path.dirname(path.abspath(filename))
        fileBasename = path.basename(filename)
        print('Zipping file '+filename+' because -z flag was set...')
        print('File path: '+target_path)
        print('File name: '+fileBasename)
        # Archive the file
        shutil.make_archive(target_path+'\\'+preset_outFileName, 'zip', target_path, fileBasename)
        filename = filename+'.zip'
        print('File compressed to zip.')
    
    if is_binary( filename ):
        print('This is a binary file. It\'s contents will be encoded in Base64 as ascii text in the QR code.')
        BASE64ENCODE = True
        readMethod = 'rb'
    else:
        with open(filename,'r') as f:
            fullFile = f.read()
            if(isAscii(fullFile)):
                print('This is a text file and will be encoded directly into the QR code.')
                BASE64ENCODE = False
                readMethod = 'r'
            else:
                print('Text file contains non-ascii chararacters, so it will be encoded as binary data.')
                BASE64ENCODE = True
                readMethod = 'rb'
        
    
    #blobList will be an array of strings, each being the size we need for our QR codes. It will be returned.
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
            if ZIP_FIRST:
                #this flag will alert the decoder that this is a zip file and will need to be decompressed
                buffer = buffer + ':z:'
        if preset_outFileName == '' or preset_outFileName is None:
            preset_outFileName = filename
        buffer = buffer + '::f::' + path.basename(preset_outFileName) + '::/f::'
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
    if ZIP_FIRST:
        #remove the temporary zip file
        remove(filename)
    return blobList

# Main function for generating a QR code and saving it as a PNG file
def saveQRcode(saveName,data,chunkSize,fillColor,backColor,pixelDensity,debugLevel):
    theVersion=getVersionFromChunk(chunkSize)
    if theVersion > 40:
        theVersion = 40
    qr = qrcode.QRCode(
        version=theVersion,
        error_correction=debugLevel,
        box_size=pixelDensity,
        border=BORDER,
    )
    
    #print('version: '+str(qr.version))
    qr.add_data(data, optimize=0)
    #f = io.StringIO()
    #qr.print_ascii(out=f)
    #f.seek(0)
    #print('qr code length: '+str(len(f.read())))
    img = qr.make_image(fill_color=fillColor, back_color=backColor)
    img.save(saveName)

# On a PDF, estimates the width in inches that a QR code can be based on the required empty space around it
def getImageWidth(pageWidth,perPage,totalOuterMargin,innerMargin,columns):
    width = pageWidth - totalOuterMargin
    if(perPage > 1 and columns > 1):
        width = (width - (innerMargin*(columns-1)))/columns
    return width

# function that takes the QR codes generated and cached in a temporary folder and makes a PDF 
def generateQRpdf(foldername,filename,pagesize,codecount):
    def writeTextBlock(filename,index,drawX,drawY):
        textFileName = filename + '.'+str(index)
        #print(textFileName)
        textValue = ''
        fullfilename = 'TXT_CACHE_TEMP/'+textFileName+'.txt'
        with open(fullfilename, "r") as t:
            textValue = t.read()
        # CLEAN THE TEXT
        # replace new lines with <br> tags
        textValue = textValue.replace("\n", "<br/>")
        # remove the metadata tags
        if textValue[0 : len( 'b64:' ) ] == 'b64:':
            textValue = textValue[ len( 'b64:' ) : ]
        if textValue[0 : len( ':z:' ) ] == ':z:':
            textValue = textValue[ len( ':z:' ) : ]
        if textValue[0 : len( '::f::' ) ] == '::f::':
            textValue = textValue[ textValue.index('::/f::') : ]
            textValue = textValue[ len( '::/f::' ) : ]
        if textValue[0 : len( '::c' ) ] == '::c':
            textValue = textValue[ len( '::c' ) : ]
            textValue = textValue[ textValue.index('::') : ]
            textValue = textValue[ len( '::' ) : ]
        #style = ParagraphStyle(name='normal')
        p = Paragraph(textValue, style=PARAGRAPH_STYLE)
        textwidth = imageWidth
        if COLUMNS == 1:
            # in a single-column environment, we can make the text width the full width of the page
            textwidth = canvas._pagesize[0] - leftMargin - (MARGIN_RIGHT*inch)
        # get the height of the rendered paragraph for easy positioning
        paragraphHeight = p.wrap(textwidth,100000)[1]
        paraY = HEIGHT - drawY - paragraphHeight
        #print(HEIGHT)
        #print(drawY)
        #print(paragraphHeight)
        #print(paraY)
        if PDF_INCLUDE_TXT == 'bottom' and ROWS == 2:
            if paraY < 0 :
                paraY = MARGIN_BOTTOM*inch
        if PDF_INCLUDE_TXT == 'top' and ROWS == 2:
            # what we want is for the text to start at the origin point right under the code
            #paraY = HEIGHT - paragraphHeight + internalMargin - PDF_BODY_FONT_SIZE
            if paraY > HEIGHT:
                paraY = HEIGHT - (topMargin*2*inch)
        #print(paraY)
        
        p.wrapOn(canvas, textwidth, imageWidth)
        # Draw the text block at the specified coordinates
        p.drawOn(canvas, drawX, paraY)
        nonlocal pageIndex
        pageIndex +=1 
        remove(fullfilename)

    def drawQR():
        additional = 0
        usableWidth = WIDTH - (leftMargin + (MARGIN_RIGHT*inch))-((COLUMNS-1)*internalMargin )
        if PDF_CODE_ALIGN == 'center':
            additional = (usableWidth - (COLUMNS*imageWidth))/2/COLUMNS
        if PDF_CODE_ALIGN == 'right':
            additional = (usableWidth/COLUMNS)-imageWidth

        canvas.drawImage(thisFile,currentDrawX+additional,HEIGHT - currentDrawY - imageWidth - PDF_BODY_FONT_SIZE,imageWidth,imageWidth)
        nonlocal pageIndex
        pageIndex +=1  
        nonlocal index
        index += 1
        
    def incrementColumn():
        # position our cursor for next position, to the right of this one
        nonlocal currentDrawX
        currentDrawX = currentDrawX + imageWidth + internalMargin
        nonlocal columnIndex
        columnIndex += 1

    def incrementRow():
        nonlocal currentDrawY
        currentDrawY = currentDrawY + internalMargin + imageWidth
        nonlocal columnIndex
        columnIndex = 0
        nonlocal currentDrawX
        currentDrawX = leftMargin

    stopThePresses = False
    codesPerPage = CODES_PER_PAGE
    topMargin = MARGIN_TOP * inch
    leftMargin = MARGIN_LEFT * inch
    imageWidth = CODE_WIDTH * inch
    internalMargin = MARGIN_INTERIOR * inch
    
    WIDTH = pagesize[0]
    HEIGHT = pagesize[1]

    currentDrawY = topMargin
    currentDrawX = leftMargin
    index = 0
    pageIndex = 0
    # column index is the current column we are in on a row
    columnIndex = 0
    saveDir = ''
    if DIRECTORY != '':
        saveDir = DIRECTORY+'/'
    canvas = Canvas(saveDir+filename+'.QR.pdf',pagesize=pagesize)
    print('Start Page 1')
    #print headline
    canvas.setFont(PDF_HEADER_FONT, PDF_HEADER_FONT_SIZE)
    canvas.drawString( leftMargin , HEIGHT-topMargin-(PDF_HEADER_FONT_SIZE/2), filename)
    #Start drawing the QR codes below the headline
    currentDrawY = topMargin+PDF_HEADER_FONT_SIZE+topMargin
    pageCount = 1
    while index < codecount:
        thisFile = foldername+filename+'.'+str(index)+'.png'
        if path.exists( thisFile ):
            print('Adding to PDF: '+thisFile)
            #print label for image
            canvas.setFont(PDF_BODY_FONT,PDF_BODY_FONT_SIZE)
            # draw the index label for this QR code
            canvas.drawString(currentDrawX, HEIGHT - currentDrawY+(PDF_BODY_FONT_SIZE/4) , str(index+1) +'/'+str(codecount))
            # set current row below label
            currentDrawY = currentDrawY
            # are we drawing text or a QR code?
            if PDF_INCLUDE_TXT == '' or PDF_INCLUDE_TXT == None:
                # draw the QR code
                drawQR()
            elif PDF_INCLUDE_TXT == 'left':
                # draw the text and increment the columnIndex and currentDrawX, then draw the QR code
                writeTextBlock(filename,index,currentDrawX,currentDrawY + PDF_BODY_FONT_SIZE)
                incrementColumn()
                drawQR()
            elif PDF_INCLUDE_TXT == 'right':
                # draw the QR code, and increment the columnIndex and currentDrawX, then draw the text
                drawQR()
                incrementColumn()
                writeTextBlock(filename,index-1,currentDrawX,currentDrawY + PDF_BODY_FONT_SIZE)
            elif PDF_INCLUDE_TXT == 'top':
                writeTextBlock(filename,index,currentDrawX,currentDrawY + PDF_BODY_FONT_SIZE)
                tempY = currentDrawY
                currentDrawY = currentDrawY + internalMargin + imageWidth
                drawQR()
                currentDrawY = tempY
            elif PDF_INCLUDE_TXT == 'bottom':
                drawQR()
                tempY = currentDrawY
                currentDrawY = currentDrawY + internalMargin + imageWidth
                writeTextBlock(filename,index-1,currentDrawX,currentDrawY)
                currentDrawY = tempY
            incrementColumn()
            if pageIndex >= codesPerPage and index < codecount:
                #create a new page and redraw the headline, reset margins
                pageCount += 1
                print('Starting page '+str(pageCount) )
                pageIndex = 0
                columnIndex = 0
                canvas.showPage()
                currentDrawY = topMargin
                currentDrawX = leftMargin
                canvas.setFont(PDF_HEADER_FONT, PDF_HEADER_FONT_SIZE)
                canvas.drawCentredString( WIDTH/2 , HEIGHT-topMargin-(PDF_HEADER_FONT_SIZE/2), filename)
                currentDrawY = topMargin+PDF_HEADER_FONT_SIZE+topMargin
            #check to see if we've drawn the second QR code on this row, 
            # and if so move to next row
            elif columnIndex >= COLUMNS:
                incrementRow()
        else:
            print('\nSTOP THE PRESSES! Couldn\'t find file with index '+str(index))
            stopThePresses = True
            index = codecount
    if PDF_INCLUDE_TXT:
        rmdir('TXT_CACHE_TEMP')
    if stopThePresses == False:
        canvas.save()
        

# takes a text blob and saves a .txt file. Used to cache for pdfs that render text alongside the QR code
def saveDataAsTXT(outFileName,data):
    #print('saving...'+outFileName)
    if not path.exists('TXT_CACHE_TEMP'):
        mkdir('TXT_CACHE_TEMP')
    if "\\" in outFileName:
        outFileName.split("\\")[-1]
    if "/" in outFileName:
        outFileName.split("/")[-1]
    #print('writing.... TXT_CACHE_TEMP/'+outFileName+'.txt')
    with open('TXT_CACHE_TEMP/'+outFileName+'.txt', "x") as t:
        print(data,file=t)
        t.close()


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
                exit( 1 )
            isAnotherFile = False
        index += 1
    writeOutputFile(out)

#decodes a provided QR code and appends it to the existing "out" object
#also figures out the filename and binary/text status if provided in the first QR code
def decodeQRandAppend(qr,out,index,fromCamera):
    global ZIP_DECODE

    if out.finalOutputString is None:
        out.finalOutputString = ''
    print('Decoding QR code '+str(index))
    data = qr.data.decode("utf-8")
    count = 0
    if index == 0 and data[0 : len( 'b64:' ) ] == 'b64:':
        print('Outputting a binary file')
        out.isBinaryFile = True
        data = data[ len( 'b64:' ) : ]
    if index == 0 and data[0 : len( ':z:' ) ] == ':z:':
        print('QR code series contains Zip archive to unzip.')
        data = data[ len( ':z:' ) : ]
        ZIP_DECODE = True
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

# saves the file retrieved from the QR codes to the computer
def writeOutputFile(out):
    global ZIP_DECODE

    if out.isBinaryFile:
        readMethod = 'wb'
        output = b64decode(out.finalOutputString)
    else:
        readMethod = 'w'
        output = out.finalOutputString
    if out.outFileName == '':
        out.outFileName = 'unknownfile.txt'
    if ZIP_DECODE:
        out.outFileName = out.outFileName + '.zip'
    with open( out.outFileName, readMethod ) as f:
        f.write( output )
    if ZIP_DECODE:
        shutil.unpack_archive(out.outFileName)
        remove(out.outFileName)


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

# detects if the input file, which is text, contains non-ascii characters
def isAscii(input_string):
    for char in input_string:
        if ord(char) > 127:
            return False
    return True

# lowers the chunk size to the next lowest level
def reduceChunkSize(chunk):
    if chunk >= 2953:
        return 2303
    elif  chunk >= 2303:
        return 1732
    elif  chunk >= 1732:
        return 1273
    elif  chunk >= 1273:
        return 858
    elif  chunk >= 858: 
        return 520
    elif  chunk >= 520:
        return 271
    else: 
        return 106

def generateFileName(filename,current,outputCount):
    out = filename + '.'+str(current)
    return out+'.png'    

def getextension(filename):
    name, file_extension = path.splitext(filename)
    return file_extension

# verifies that the user hasn't put in parameters that make no sense, and kills the program when it makes no sense
def validateUserInput():
    global CHUNK_SIZE 
    if PDF_INCLUDE_TXT != '' and PDF_INCLUDE_TXT != None:
        if COLUMNS * ROWS <= 1:
            print('***Error*** Cannot include text on PDF pages that do not have multiple columns or rows')
            sys.exit()
        if (PDF_INCLUDE_TXT == 'left' or PDF_INCLUDE_TXT == 'right') and COLUMNS < 2:
            print('***Error*** Cannot include text to the '+PDF_INCLUDE_TXT+' when there aren\'t at least 2 columns')
            sys.exit()
        if (PDF_INCLUDE_TXT == 'top' or PDF_INCLUDE_TXT == 'bottom') and ROWS < 2:
            print('***Error*** Cannot include text to the '+PDF_INCLUDE_TXT+' when there aren\'t at least 2 rows')
            sys.exit()
    if DEBUG_LEVEL == qrcode.constants.ERROR_CORRECT_H:
        if(CHUNK_SIZE > 1273):
            CHUNK_SIZE = 1273
    if DEBUG_LEVEL == qrcode.constants.ERROR_CORRECT_M:
        if(CHUNK_SIZE > 2331):
            CHUNK_SIZE = 2331
    if(CHUNK_SIZE > 2953):
            CHUNK_SIZE = 2953

        


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
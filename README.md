# qr-diskdrive

```
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
```         

This is a tool for saving files as QR codes, in the manner of saving files to
an old-fashioned data format such as tapes or punch cards. It allows you to encode 
data to QR codes in PNG files or to a number of easily printed PDF formats. 

Use it for archiving data to paper, or just experiencing the absurdity of storing
your files as a QR code. 

## Requirements

The following python libraries are required. A few of these should already be loaded by default in your python install. 

- qrcode
- pil
- cv2
- sys
- argparse
- pyzbar
- base64
- binaryornot
- reportlab

## Try it out

Included in the repository are some example files that you can decode. The following command will decode the PNG files "nevagonnagiveyouup.jpg.*.png". These files represent a small jpg image encoded into 3 QR codes. 

`python3 qr-diskdrive.py -l exampleCodes/nevagonnagiveyouup.jpg`

The file "letUdown.jpg.QR.pdf" is the same file encoded to a PDF that can be easily printed to 3x5 index cards. You can print the cards and scan them individually in order to load the file using this command. 

`python3 qr-diskdrive.py -c`

### Encode your own file

You can select any file of your own to encode using the command below. While there is no file limit, know that large files might encode to a large number of QR codes. Each code is limited to 2953 *bytes* of data. You would need 488 QR codes to encode the contents of a single 1.44 MB floppy disk!

`python3 qr-diskdrive.py -s pathToFileToEncode`

## Usage

You can use the command line arguments below, or simply use the command:

`python3 qr-diskdrive.py`

which will launch a menu that will allow you to configure all the same options. 

### Command line arguments

```
  -h, --help            show this help message and exit
  -s SAVE, --save SAVE  Save specified file to QR code
  -l LOAD, --load LOAD  Load a file from a QR code or series of codes in
                        specified image file(s) using the filename
                        '[filename].[0-9].png'
  -c, --camera          Load a file from a QR code/series of codes from a
                        webcam. Allows for the scanning of multiple QR codes
                        in sequence for larger files. Will use your primary
                        webcam by default.
  -d DIRECTORY, --directory DIRECTORY
                        Directory in which to save the output files
  -n NAME, --name NAME  Output file name, overriding default behavior (for
                        save, default uses the name of file being encoded, for
                        load default uses name encoded within the QR code).
                        Setting this will not override the file type which is
                        encoded in the QR code or the original file(eg. png,
                        zip, etc)
  -o OUTPUTTYPE, --outputType OUTPUTTYPE
                        Output Type: Method for outputting QR codes. Options:
                        PNG (Default), letter, index_card, playing_card, zip.
                        Ignored when loading data.
  -b BYTESIZE, --bytesize BYTESIZE
                        Maximum size of each QR code, in bytes (max and
                        default: 2953). Use one of the following for maximum
                        capacity and scannability: 2953, 2303, 1732, 1273,
                        858, 520, 271, 106
  -px PIXELDENSITY, --pixeldensity PIXELDENSITY
                        Width in pixels of a bit of saved QR code. Default: 10
  -f FILLCOLOR, --fillcolor FILLCOLOR
                        FILL COLOR, ie the dark color in the QR code. Use a
                        basic color name eg. 'red' or a hex code eg. #FFAABB.
                        Default: black
  -w WHITEBACKGROUNDCOLOR, --whitebackgroundcolor WHITEBACKGROUNDCOLOR
                        BACK COLOR, ie the light color in the QR code.
                        Default: white
  -e ERRORCORRECTION, --errorcorrection ERRORCORRECTION
                        Error correction level in QR codes. Can use L, M or H
                        Default: L
```

### More Example commands

Save the file "never-gonna-give-you-up.mp3" to a pdf file on standard 8.5" x 11" paper, in the color red, in the folder "exampleFolder", and changing the name to "yellowSubmarine.mp3" so no one gets suspicious.

`python3 qr-diskdrive.py -s never-gonna-give-you-up.mp3 -o letter -f red -d exampleFolder -n yellowSubmarine`

Save the file "rick-astley.jpg" to a pdf file on playing-card size paper, but restricting each QR code to 271 bytes of data, and renaming the file to "theBeatles.jpg".

`python3 qr-diskdrive.py -s rick-astley.jpg -o playing_card -b 271 -n theBeatles`

## How files are saved across multiple QR codes

In order to save files of any type across multiple QR codes, the data encoded by this program will include the following metadata within the QR code data.

`b64:` On the first QR code only, this flag will start the encoded data if we are dealing with a binary filetype that has been encoded in base64. 

`::f::FILENAME.XXX::/f::` Encodes the filename on the first QR code. 

`::c0::` Encodes which QR code this is in order. When scanning by camera, the scanner checks to make sure you have not accidentally scanned a code out of order. 

So, if a jpg file called "example.jpg" is split between 3 QR codes, the first QR code will start with the flag `b64:` followed by the flag `::f::example.jpg::/f::`, then `::c0::`, after which will be the data of the jpg file encoded in base 64. The second QR code will start with `::c1::` and the third QR code will start with `::c2::`. There is no flag indicating that the file is finished, or that this is the last QR code in a series. 

If your data was not encoded by this program, you should still be able to decode it. You will need to provide an output filename with the flag `-n`, and if scanning by camera accept each scanned image. The scanner will think that maybe you are scanning out of order. 

## Why would you do this?

**Data is a state of matter**. Like liquids, solids, and gases, data is a particular arrangement of matter that has meaning. 

In the modern age, we are used to thinking of data purely in the abstract, as if it exists outside of the physical world. A file downloaded comes as if by magic at incomprehensible speed, and a full hard drive weighs no more than an empty one. If someone stops to actually think of data as something physical, we see it as the magnetic polarity of a microscopic speck of rust on a spinning platter, or the electrical state of a transistor. But data can take any form. Take for example [delay line memory](https://en.wikipedia.org/wiki/Delay_line_memory), where data was stored as a wave propogating through a column of mercury. 

Early in the history of computers, the forms of data storage available to us were *macroscopic*, such as [punched cards](https://en.wikipedia.org/wiki/Punched_card) and [punched tape](https://en.wikipedia.org/wiki/Punched_tape), and so it was clear to the user that data was a physical state of matter. You can see the bits, and if you know what you are looking at you could even read it. 

I wanted a way to physically handle data, something I could see, like a punch card. While there are not a lot of tools out there for decoding and encoding punch cards, QR codes can be created and read by almost any device. They are like a modern punch card, a visible, tangible form of data, ink on a page arranged to have meaning. 

I envision this tool as creating modern punch cards, data made tangible. A gif encoded in a stack of playing cards. A rick roll stored in a shoebox. An mp3 stored in a binder. 

Completely absurd, of course, 

## Future improvements 

In the future I intend to:

- Test and make it all work on Windows. I have only used this on Linux so far. 
- Allow the user to print directly, sending the PDF file to the operating system's printer dialog.
- Recommend maximum QR code data capacities for the PDF formats. This will require lots of printing and testing. 
- Allow the user to select the number of codes per letter-sized PDF page (1 or 4), which would be useful for very large codes that need to be read by low-quality cameras. 
- Print directly to a standard receipt printer, at a reduced capacity per QR code. 
- Allow the user to select a different webcam from their default. Useful if you have one that is not attached to the screen of your laptop. 
    - As it is, that can be changed from the code in the function readFromCamera()
- Allow the user to save their file as a Zip file containing the PNG files. 

## Credit where due

I owe the following sources for inspiration and/or the knowledge I needed to make this. 

- eandriol's [file2qr-qr2file](https://github.com/eandriol/file2qr-qr2file). I believe I stole from them the idea to store binary files in base64, and using the `b64:` prefix. Reading the code helped, but I don't believe I am using any of their code aside from using pyzbar to decode. 
- MattKC stored a game in a qr code [here](https://www.youtube.com/watch?v=ExwqNreocpg)

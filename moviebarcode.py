#!/usr/bin/env python
# -*- coding: utf-8 -*-
# License: © 2020 Achille-Tâm GUILCHARD All Rights Reserved
# Author: Achille-Tâm GUILCHARD

import os
import sys
import math
import time
import datetime
import argparse
import logging
import pprint
import numpy as np
from   functools import wraps
from   collections import Counter
import cv2
from   skimage import io
from   imutils.video import FileVideoStream
import progressbar
from   termcolor import colored
pp   = pprint.PrettyPrinter(indent=4)

# Logging stuff
LOG_FORMAT = "(%(levelname)s) %(asctime)s - %(message)s"
# create and configure logger
logging.basicConfig(level    = logging.DEBUG, 
                    format   = LOG_FORMAT, 
                    filemode = 'w')
logger = logging.getLogger()

# Function profiling
PROF_DATA = {}

def profile(fn):
    @wraps(fn)
    def with_profiling(*args, **kwargs):
        start_time = time.time()
        ret = fn(*args, **kwargs)
        elapsed_time = time.time() - start_time
        if fn.__name__ not in PROF_DATA:
            PROF_DATA[fn.__name__] = [0, []]
        PROF_DATA[fn.__name__][0] += 1
        PROF_DATA[fn.__name__][1].append(elapsed_time)
        return ret
    return with_profiling

def print_prof_data():
    for fname, data in PROF_DATA.items():
        max_time = max(data[1])
        avg_time = sum(data[1]) / len(data[1])
        logger.info('Function {:s} called {:d} times. Execution time max: {:.3f} seconds, average: {:.3f} seconds'.format(fname, data[0], max_time, avg_time))

def clear_prof_data():
    global PROF_DATA
    PROF_DATA = {}

# Functions and main()
def parse_arguments():
    """Parse input args"""                                                                                                                                                                                                                            
    parser = argparse.ArgumentParser(description='')                                                                                                                                                                                                                  
    parser.add_argument('--input',  type=str, default="./", help='Where the entries of the program are stored.')                                                                                                                                                                                                                                   
    parser.add_argument('--output', type=str, default="./", help='Where the outputs of the program are written.')
    return parser.parse_args()                                                                                                                                                                                                                                        

@profile
def frameCounter(video_path):
    frameNumber = 0
    # create a VideoCapture object and read from input file
    fvs = FileVideoStream(video_path).start()
    # loop over frames from the video file stream
    while fvs.more():
        # grab the frame from the threaded video file stream
        frame = fvs.read()
        frameNumber+=1
    fvs.stop()
    return frameNumber

@profile
def getDominantColour(img):
    average            = img.mean(axis=0).mean(axis=0)
    pixels             = np.float32(img.reshape(-1, 3))
    n_colors           = 5
    criteria           = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, .1)
    flags              = cv2.KMEANS_RANDOM_CENTERS
    _, labels, palette = cv2.kmeans(pixels, n_colors, None, criteria, 10, flags)
    _, counts          = np.unique(labels, return_counts=True)
    dominant           = palette[np.argmax(counts)]
    return dominant

@profile
def getBlackBarHeight(img):
    # TODO: what happen if no black bars?
    # height, width, number of channels in image
    height       = img.shape[0]
    width        = img.shape[1]
    channels     = img.shape[2]
    if (height > 0) and (width > 0):    
        start1       = 1
        start2       = int(width/2)
        start3       = width - 1
        pixel_value  = 0
        pixel_value2 = 0
        pixel_value3 = 0
        i            = 0
        tmp1         = 0
        temp2        = 0
        temp3        = 0
        while(pixel_value < 10 and pixel_value2 < 10 and pixel_value3 < 10):
            pixel_value  = img[i,start1,0]
            pixel_value2 = img[i,start2,0]
            pixel_value3 = img[i,start3,0]
            i = i + 1
        return i
    else:
        logger.info("Problem to decode the video frame")
        logger.info("height: {}".format(height))
        logger.info("width: {}".format(width))
        exit(1)

@profile 
def create_frameline(video_path, output_image_path):
    try:
        output_width    = 1280
        output_height   = 480 
        counter         = 0
        columnCounter   = 0
        dominantColours = list()
        BBheight        = 0
        width           = 0
        height          = 0
        frameNumber     = frameCounter(video_path)
        frame_by_column = math.ceil(frameNumber/output_width)
        # Create a VideoCapture object and read from input file
        logger.info("Number of frame for one pixel column: {}".format(frame_by_column))
        cap = cv2.VideoCapture(video_path)
        # Check if camera opened successfully
        if (cap.isOpened() == False):
            logger.info("Error opening video stream or file")
            exit(1)
        with progressbar.ProgressBar(max_value=frameNumber) as bar:
            # Read until video is completed
            while(cap.isOpened()):
                # Capture frame-by-frame
                ret, frame = cap.read()
                if ret == True:
                    counter = counter + 1
                    if counter == frame_by_column - 1:
                        # determine black bar height to remove them
                        height   = frame.shape[0]
                        width    = frame.shape[1]
                        BBheight = getBlackBarHeight(frame)
                        logger.info('Black bar height: {}'.format(BBheight))
                    # process the frame
                    if counter % frame_by_column == 0:
                        # crop to remove black bars
                        frame_cropped  = frame[BBheight:height-BBheight,0:width]
                        dominantColour = getDominantColour(frame_cropped)
                        dominantColours.append(dominantColour)   
                        bar.update(counter)     
                 # Break the loop
                else: 
                    break
        maxFrame    = len(dominantColours)
        if maxFrame > output_width:
            logger.info(colored('There are more pixel columns ({}) than output image width ({})'.format(maxFrame,output_width), 'red'))
            exit(1)
        # blank_image = np.zeros((int(maxFrame/2),maxFrame,3), np.uint8)
        blank_image = np.zeros((output_height,output_width,3), np.uint8)
        counter = 0
        for colour in dominantColours:
            blank_image[:,counter,0] = int(colour[0]) # B
            blank_image[:,counter,1] = int(colour[1]) # G
            blank_image[:,counter,2] = int(colour[2]) # R
            counter = counter + 1
        cv2.imwrite(output_image_path, blank_image)
    except Exception as e:
        logger.info('Something went wrong... Oopsie!')
        logger.info(str(e))
        exit(1)

def main():
    """Where the magic happens"""  
    start_time = time.time()
    args = parse_arguments()
    logger.info(colored('Entry summary:', 'red'))
    logger.info("   > input:  " + colored(args.input, 'green'))
    logger.info("   > output: " + colored(args.output, 'green'))
    create_frameline(args.input, args.output)    
    print_prof_data()
    elapsed_time = time.time() - start_time
    logger.info(colored('Elapsed time: ' + time.strftime("%H:%M:%S", time.gmtime(elapsed_time)), 'red'))

if __name__ == "__main__":
    main()

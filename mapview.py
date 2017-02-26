#    mapview.py
#
#    Copyright 2017 Albert Margolis
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function
from builtins import (bytes, str, open, super, range,
                      zip, round, input, int, pow, object)

import numpy
import cv2
import ConfigParser

# from: http://stackoverflow.com/questions/19987039/inverse-mapped_imective-transformation

class MyImage(object):
    def __init__(self, im, UI=None, SourceImage=None, SourceOffsetY=None):
        self.im = im
        self.ui = UI
        self.height, self.width, self.channel_ct = im.shape
        self.transformationBox = None
        self.sourceImage = SourceImage
        self.sourceOffsetY = SourceOffsetY
        if (SourceImage is not None) and (UI is None):
            self.ui = SourceImage.ui

    def MakeLine(self, center_ratio, width_ratio, height_ratio):
        center = (self.width / 2) + (self.width * center_ratio)
        y = int(self.height - (self.height * height_ratio))
        line_width = self.width * width_ratio
        x1 = int(center - (line_width / 2))
        if x1 < 0:
            x1 = 0
        x2 = int(center + (line_width / 2))
        if x2 > self.width:
            x2 = self.width
        return [(x1, y), (x2, y)]

    def PlaceTransformationBox(self):
        # Save points in sequence in case we ever want to use a more complex polygon
        print("Box Top C/W/H =", (self.ui.top_center_ratio, self.ui.top_width_ratio, self.ui.top_height_ratio),
					"Box Bottom C/W/H =", (self.ui.bottom_center_ratio, self.ui.bottom_width_ratio, self.ui.bottom_height_ratio))
        box = self.MakeLine(self.ui.top_center_ratio, self.ui.top_width_ratio, self.ui.top_height_ratio)
        bottom_line = self.MakeLine(self.ui.bottom_center_ratio, self.ui.bottom_width_ratio, self.ui.bottom_height_ratio)
        box.append(bottom_line[1])
        box.append(bottom_line[0])
        self.transformationBox = box

    def MakeCroppedByBottomRatios(self):
        # Cut away sides
        print("Crop X =", self.ui.crop_x_ratio, "Shift X =", self.ui.shift_x_ratio, "Y =", self.ui.crop_y_ratio)
        x_center = (self.width / 2) + (self.width * self.ui.shift_x_ratio)
        x_keep = self.width * (1 - self.ui.crop_x_ratio)			# how much of image width to keep
        x_keep_side = int(x_keep / 2)			# how much to keep on each side of center
        x_start = int(x_center - x_keep_side)
        if x_start < 0:
          x_start = 0
        x_end = int(x_center + x_keep_side)
        if x_end > self.width:
          x_end = self.width

        # Cut away top
        y_cut = int(self.height * self.ui.crop_y_ratio)
        height_keep = self.height - y_cut
        y_start = int(self.height - height_keep)

        # Crop
        # The crop parameters are slices of height (y) and width (x) we keep.  
        cropped_im = MyImage(self.im[y_start:self.height, x_start:x_end],
				SourceImage=self, SourceOffsetY=y_cut)
        print("Cropped: XxY =", (cropped_im.width, cropped_im.height), "Y-slice =", (y_start, self.height), "X-slice =", (x_start, x_end))
        return cropped_im

    def GetSourcesProjectedTransformationBox(self):
        # Called from a cropped image.
        # Get source's Transformation Box mapped to this cropped image.
        # Assume this is a bottom crop.
        # May need to shift X also.
        # This returns a list that is compatible with numby.array()
        box = []
        for this_point in self.sourceImage.transformationBox:
            box.append([float(this_point[0]), float(this_point[1] - self.sourceOffsetY)])
        return box

    def InversePerspective(self):
        # The size of the inverse perspective image will be bigger.
        # The expansion ratio is proportional to the ratio of the transformation box
        # top and bottom lines multiplied by the distance contained within the box height.
        # That distance is supplied by map_y_ratio.
        print("Map X x Y =", (self.ui.map_x_ratio, self.ui.map_y_ratio))
        box_src = self.GetSourcesProjectedTransformationBox()

        box_bottom_y = box_src[2][1]
        box_bottom_x2 = box_src[2][0]
        box_bottom_x1 = box_src[3][0]
        box_bottom_width = box_bottom_x2 - box_bottom_x1
        box_bottom_center = box_bottom_x1 + (box_bottom_width / 2)
        box_squeezed_width = int(box_bottom_width * self.ui.map_x_ratio)
        box_squeezed_x1 = box_bottom_center - (box_squeezed_width / 2)
        box_squeezed_x2 = box_bottom_center + (box_squeezed_width / 2)

        box_top_y = box_src[1][1]
        box_top_x1 = box_src[0][0]
        box_top_x2 = box_src[1][0]
        box_height = box_bottom_y - box_top_y

        box_stretched_height = int(box_height * (self.ui.map_y_ratio * 10.0))
        box_stretched_top_y = box_bottom_y - box_stretched_height
        if box_stretched_top_y < 0:
            box_stretched_top_y = 0
        box_stretched_top_x1 = box_squeezed_x1
        box_stretched_top_x2 = box_squeezed_x2
        # Fix box top line coordinates
        box_dst = []
        box_dst.append([box_stretched_top_x1, box_stretched_top_y])
        box_dst.append([box_stretched_top_x2, box_stretched_top_y])
        box_dst.append([box_squeezed_x2, box_bottom_y])
        box_dst.append([box_squeezed_x1, box_bottom_y])
 
        pts_src = numpy.array(box_src, dtype="float32")
        pts_dst = numpy.array(box_dst, dtype="float32")

        # Calculate Homography
        print("Points:", pts_src, pts_dst)
        #h, status = cv2.findHomography(pts_src, pts_dst)
        h = cv2.getPerspectiveTransform(pts_src, pts_dst)
        print("Transformation Matrix:", h)
        mapped_width = self.width * 3
        mapped_height = self.height * 3
        mapped_im = cv2.warpPerspective(self.im, h, (mapped_width, mapped_height))
        return MyImage(mapped_im)

    #mapped_im = cv2.remap(cropped_im, pts_src, pts_dst, cv2.INTER_LINEAR)

    def MakeLinedImage(self):
        image_lined = self.im.copy()
        prev_pt = self.transformationBox[0]
        for this_pt in self.transformationBox[1:]:
            cv2.line(image_lined, prev_pt, this_pt, (0, 0, 255), 1)
            prev_pt = this_pt
        cv2.line(image_lined, prev_pt, self.transformationBox[0], (0, 0, 255), 1)
        return MyImage(image_lined)

UI_TRACKBARS = [
    ('top_center_ratio',    50, 50, "Top Line Center"),
    ('top_height_ratio',    20,  0, "Top Line Height"),
    ('top_width_ratio',     20,  0, "Top Line Width"),
    ('bottom_center_ratio', 50, 50, "Bottom Line Center"),
    ('bottom_height_ratio', 10,  0, "Bottom Line Height"),
    ('bottom_width_ratio',  20,  0, "Bottom Line Width"),
    ('map_x_ratio',        100,  0, "Map X"),
    ('map_y_ratio',         10,  0, "Map Y"),
    ('crop_x_ratio',         0,  0, "Crop X"),
    ('shift_x_ratio',       50, 50, "Crop Shift X"),
    ('crop_y_ratio',         0,  0, "Crop Y")
    ]

UI_ATTRIBUTE_NAME_IX = 0
UI_DEFAULT_VALUE_IX = 1
UI_VALUE_OFFSET_IX = 2
UI_CAPTION_IX = 3

INI_TRACKBARS = "Trackbars"
INI_FILE_NAME = "makemap.ini"

class OpenCvUi(object):
    def __init__(self, fn):
        self.original_im = MyImage(cv2.imread(fn), UI=self)
        self.originalWindowName = "Original"
        self.outputWindowName = "Map"
        cv2.namedWindow(self.originalWindowName)
        cv2.namedWindow(self.outputWindowName)
        self.LoadIniFile()			# create trackbars
        self.OnTrackbarChange(0)		# load initail attribute values
        self.InversePerspective()

    def Run(self):
        cv2.waitKey(0) & 0xff
        self.SaveIniFile()
        cv2.destroyWindow(self.originalWindowName)
        cv2.destroyWindow(self.outputWindowName)

    def LoadIniFile(self):
        ini = ConfigParser.RawConfigParser()
        ini.read(INI_FILE_NAME)
        for this_trackbar in UI_TRACKBARS:
            trackbar_attribute_name = this_trackbar[UI_ATTRIBUTE_NAME_IX]
            trackbar_caption = this_trackbar[UI_CAPTION_IX]
            if ini.has_option(INI_TRACKBARS, trackbar_attribute_name):
                trackbar_initial_pct = int(ini.get(INI_TRACKBARS, trackbar_attribute_name))
            else:
                trackbar_initial_pct = this_trackbar[UI_DEFAULT_VALUE_IX]
            cv2.createTrackbar(trackbar_caption, self.originalWindowName,  trackbar_initial_pct, 100, self.OnTrackbarChange)

    def SaveIniFile(self):
        ini = ConfigParser.RawConfigParser()
        ini.add_section(INI_TRACKBARS)
        for this_trackbar in UI_TRACKBARS:
            trackbar_attribute_name = this_trackbar[UI_ATTRIBUTE_NAME_IX]
            trackbar_caption = this_trackbar[UI_CAPTION_IX]
            pos = cv2.getTrackbarPos(trackbar_caption, self.originalWindowName)
            ini.set(INI_TRACKBARS, trackbar_attribute_name, str(pos))
        with open(INI_FILE_NAME, 'wb') as configfile:
            ini.write(configfile)

    def InversePerspective(self):
        print("**********")
        print("**********")
        print("**********")
        self.original_im.PlaceTransformationBox()
        cropped_im = self.original_im.MakeCroppedByBottomRatios()
        mapped_im = cropped_im.InversePerspective()

        image_lined = self.original_im.MakeLinedImage()
        cv2.imshow(self.outputWindowName, mapped_im.im)
        cv2.imshow(self.originalWindowName, image_lined.im)

    def OnTrackbarChange(self, pos):
        for this_trackbar in UI_TRACKBARS:
            # All trackbars have an OpenCV UI range of 0 to 100.
            # They are converted to a ratio here.
            # The offset is used to convert to a range of -50% to 50%
            trackbar_attribute_name = this_trackbar[UI_ATTRIBUTE_NAME_IX]
            trackbar_caption = this_trackbar[UI_CAPTION_IX]
            pct_offset = this_trackbar[UI_VALUE_OFFSET_IX]
            new_pct = cv2.getTrackbarPos(trackbar_caption, self.originalWindowName)
            val_ratio = float(new_pct - pct_offset) / 100.0
            setattr(self, trackbar_attribute_name, val_ratio) 
        self.InversePerspective()


fn = "bot_view.jpg"
app = OpenCvUi(fn)
app.Run()


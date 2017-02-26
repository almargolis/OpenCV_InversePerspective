# OpenCV_InversePerspective
This is a Python program that demonstates the use of cv2.warpPerspective() to convert a robot driver view image to a bird's eye map view.

Launch the program from the command line. 
That will open two GUI windows. One with the original image, a perspective box and a bunch of sliders.
The second contains the map view -- provided that the parameters are correct.
Depending on your screen, the windows may launch in an overlapping position. 
Move them around to get a reasonable working view. 
A large, high resolution screen is helpful.

Play carefully with the sliders until you get a good feel for what they do.
Small changes can cause large distortions that can be challenging to diagnose.

To close, press any key with the GUI in focus.
The program does not modify the image file.
It reads and writes makemap.ini to save and restore the slider values between sessions. 
You can delete makemap.ini to start over with reasonable default values.

OpenCV presents the sliders in an inconsistent order, so check the labels carfully when changing the sliders.
This may be fixed in Python 3.6. The UI is a bit painful to use. This is a "quick and dirty" demo
intended only to help me explore use of this function.

To work with your own image:

* Edit variable fn at the bottom of the source file with the path to your image file.

* Launch the program. You should your image in the window with the sliders.

* Choose an area of the image that has two edges converging on the horizon.
Modify the red perspective box to model that convergence. 
For robotics, that will typically be a trapezoid fitted between lane lines.
As in my example. 

	* Move the bottom line of the trapezoid into position using the "Bottom Center", "Bottom Width" and "Bottom Height" sliders.

	* Move the top line of the trapezoid into position using the "Top Center", "Top Width" and "Top Height" sliders.

	* Stretch the output to a reasonable map view using the "Map Y" and "Map X" sliders.

	* Adjust the perspective box in small increments to finalize the image. 
The best view in my samples is not precisely between the lane lines. 
I am pretty sure that this is because the camera is not aligned perfectly square with the view, 
but this coud be a bug in the code.
Taller boxes seem to produce better results than short boxes.

The "Crop X", "Crop Shift X" and "Crop Y" sliders perform an image cropping before applying the warpPerspective. 
These do crop the image properly but they seem to hinder rather than help the warpPerspective process.
I haven't yet explored whether this is a bug in my code or the nature of the warpPerspective transformation.

This is pre-alpha code with a minimum of error checking and potentially full of bugs. 
I have found it useful for my exploration of this function.
No further assurances are implied.

The demo image was taken with the Pi Camera on the front of my robot. A corresponding ini file is included so the program launches with a reasonable conversion.

This has been tested using Python v2.7 and OpenCV v3.2 on OSX Sierra v10.12.3.

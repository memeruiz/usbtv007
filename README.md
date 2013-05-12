usbtv007
========

Userspace test driver for the easycap usbtv007 (utv007) video capture adapters.

To use this you need to get the v4l2loopback kernel module:

http://github.com/umlaeute/v4l2loopback

Then load it:

modprobe v4l2loopback

Install the usbtv007 userspace driver dependencies (python-libusb1, python-v4l2, etc)

run it:

./utv007_driver.py -d /dev/video0

Use for example mplayer to look at the output:

mplayer tv:// -tv device=/dev/video0

This driver is extremely experimental, code is ugly and full of debugging prints: this code was made to investigate the usb protocol of this device. Hopefully me or somebody else will use this to make a kernel driver.

Python was used to make program. Performance is not the best, I guess it may be possible to improve it. In my computer (Core i5-2500T) it consumes 70% of one of the processor threads (very bad).

Features:

- resolution 720x480
- Composite (CVBS) Video input capture
- Tested with two different adapters

Missing features: (due to missing analysis of usb protocol)

- change resolution (or recognize different input resolution: I only have one analog video source, therefore I can not check different resolutions)
- S-Video input
- Audio capture
- Colorspace transformations (currently uses the same one that comes from the adapter, I don't know if it is possible to tell the adapter to change what it sends, or do it in the driver)
- ...

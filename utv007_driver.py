#!/usr/bin/env python
# Copyright (c) 2013 Federico Ruiz Ugalde
# Author: Federico Ruiz-Ugalde <memeruiz at gmail dot com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

easycap_dev_id='0x1b71:0x3002'
usb_interface=0
from easycap_utv007 import Utv007

from protocol import *
from time import time, sleep
import signal
import sys
import gc

quit_now=False
def signal_handler(signal, frame):
    print 'You pressed Ctrl+C!'
    global quit_now
    quit_now=True

def main():
    with Utv007() as utv:
    #utv=Utv007()
        signal.signal(signal.SIGINT, signal_handler)
        old_t=time()
        for i in xrange(20):
            utv.do_iso2()
        #pass
        while not quit_now:
    #for i in xrange(100):
            t=time()
            delta_t=t-old_t
            old_t=t
        #print "Delta t" , delta_t
        #utv.do_iso2()
            utv.handle_ev()
        print "closing utv"
        utv.stop=True


if __name__=="__main__":
    main()

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

# This is a stand alone application. For now it only captures and displays an image after connecting to the device, then it stops.

easycap_dev_id='0x1b71:0x3002'
interface=0

import usb1 as u
from protocol import p_init, p5
from protocol import *
from time import sleep
from fcntl import ioctl
import v4l2 as v
import os
from time import time, sleep
import weakref
import numpy as n

class Delta_t(object):
    def __init__(self):
        self.old_t=time()

    def update_t(self):
        self.old_t=time()

    def diff_t(self):
        t=time()
        print "Diff t:", t-self.old_t
        self.old_t=t

def variable_for_value(value):
    for n,v in globals().items():
        if v == value:
            return n
    return None

def run_protocol(prot, devh):
    print "TESTST"
    for req_num, req in enumerate(prot):
        print "line", req[0], hex(req[1]), hex(req[2]), hex(req[3]), req[4], req[5],
        if len(req)>6:
            if type(req[6])==list:
                for i,j in req[6]:
                    print hex(i), variable_for_value(j),
            elif type(req[6])==tuple:
                print [hex(i) for i in req[6]],
            else:
                print hex(req[6]),
        #else:
        #    print
        print "req num", req_num
        if req[0][0]=='c':
            if req[0][2:]=='vd':
                print "Control request"
                if req[0][1]=='r':
                    print "Read"
                    reply=devh.controlRead(
                        u.libusb1.LIBUSB_TYPE_VENDOR|u.libusb1.LIBUSB_RECIPIENT_DEVICE,
                        req[1], req[2], req[3], req[5])
                    if len(reply)==1:
                        print "Reply:", hex(ord(reply))
                    else:
                        print "Reply:", [hex(ord(i)) for i in reply]
                        print "Reply char:", reply
                    if type(req[6])==list:
                        print " Multiply options"
                        found_prot=False
                        for resp, next_prot in req[6]:
                            if resp==ord(reply):
                                print "Found response in multiple options, running recursively"
                                print "Jumping to:" , variable_for_value(next_prot)
                                run_protocol(next_prot, devh)
                                found_prot=True
                                break
                        if not found_prot:
                            print "Unknown response!! Exiting!"
                            exit()
                    elif type(req[6])==tuple:
                        print "Long answer"
                        #raw_input()
                        if len(req)==7:
                            if list(req[6])==[ord(i) for i in reply]:
                                print " All fine"
                            else:
                                print " Response incorrect!!! Exiting"
                                exit()
                        elif len(req)==8:
                            print "Some reply may be ignored"
                            for reply, exp_reply, check in zip([ord(i) for i in reply], req[6], req[7]):
                                print "Reply", reply, exp_reply, check
                                if check:
                                    if reply==exp_reply:
                                        print "All fine"
                                    else:
                                        print "Problems with reply!", reply, exp_reply, check
                                        exit()
                                else:
                                    print "Ignored reply"
                            #raw_input()
                    else:
                        if ord(reply)==req[6]:
                            print "All fine!"
                        else:
                            print "Error: Different reply"
                            exit()
                elif req[0][1]=='w':
                    print "Write"
                    reply=devh.controlWrite(
                        u.libusb1.LIBUSB_TYPE_VENDOR|u.libusb1.LIBUSB_RECIPIENT_DEVICE,
                        req[1], req[2], req[3], req[4])
                    print "Reply:", reply
                    if reply==req[5]:
                        print "All fine!"
                    else:
                        print "Error: More data send!"
                        exit()
                else:
                    print "Not supported"


class Utv007(object):
    interface=0
    def __init__(self, device="/dev/video1"):
        self.v4l_device=device
        dev=None
        self.cont=u.USBContext()
        for i in self.cont.getDeviceList():
            print "ID", i.getVendorID(),i.getProductID(), i.getManufacturer(), "Serial: ", i.getSerialNumber(), "Num conf", i.getNumConfigurations()
            if hex(i.getVendorID())+':'+hex(i.getProductID())==easycap_dev_id:
                print "Easycap utv007 found! Dev ID: ", easycap_dev_id
                self.dev=i
                break

        if self.dev:
            print "Openning device"
            self.devh=self.dev.open()
        else:
            print "No easycap utv007 devices found"
            exit()

        while self.devh.kernelDriverActive(self.interface):
            self.devh.detachKernelDriver(self.interface)
            sleep(0.5)
        #if kernel:
        #    print "Kernel driver already using device. Stopping. Kernel:", kernel
        #    exit()

        print "Claiming interface"
        self.devh.claimInterface(self.interface)
        print "Preinit"
        run_protocol(p_preinit, self.devh)
        print "init"
        run_protocol(p_init, self.devh)
        #sleep(1.)
        print
        print "Second part"
        print
        run_protocol(p5, self.devh)
        print "Setting Altsetting to 1"
        self.devh.setInterfaceAltSetting(self.interface,1)
        self.image=[]
        #packet related:
        self.s_packets=''
        #self.s_packets=n.chararray(1, itemsize=960)
        self.expected_toggle=True
        self.expected_n_s_packet=0
        self.expected_n_img=0
        self.start_frame=True
        self.n_packets=0
        self.v4l_init()
        self.stop=False
        self.iso=[]
        self.dt=Delta_t()
        #self.test=' '*960
        #self.iso=self.devh.getTransfer(iso_packets=8)
        #self.iso.setIsochronous(0x81, 0x6000, callback=self.callback2, timeout=1000)
        print "Initialization completed"
        #print "Reading int"
    #a=devh.interruptRead(4,0, timeout=1000)
    #print "Interrupt result" , a

    def __enter__(self):
        print "Enter"
        return(self)

    def __exit__(self, type, value, traceback):
        #for iso in self.iso:
        #    print "STatus", iso.getStatus()
        #del iso
        print "Realeasing interface"
        self.devh.releaseInterface(0)
        print "Closing device handler"
        self.devh.close()
        #sleep(2)
        print "Exiting context"
        self.cont.exit()
        pass

    def __del__(self):
        print "Deleting"

    def do_iso(self):
        self.iso=self.devh.getTransfer(iso_packets=8)
        self.iso.setIsochronous(0x81, 0x6000, callback=self.callback1, timeout=1000)
        self.iso.submit()
        #self.iso.setCallback(callback1)

    def do_iso2(self):
        #print "Submitting another iso"
        iso=self.devh.getTransfer(iso_packets=8)
        iso.setIsochronous(0x81, 0x6000, callback=self.callback2, timeout=1000)
        iso.submit()
        self.iso.append(iso)
        #self.iso.setCallback(callback1)


    def handle_ev(self):
        #print "Event a"
        #sleep(10)
        self.cont.handleEvents()
        #print "Event b"

    def get_useful_data(self, buffer_list, setup_list):
        data=''
        for b, s in zip(buffer_list, setup_list):
            actual_len=s['actual_length']
            print "Actual len" , actual_len
            data+=b[:actual_len]
        return(data)

    def build_images(self, buffer_list, setup_list):
        """ buffer_list is a list that contains around 8 packets inside, each of this packets contains 3 smaller packets inside
        The first four bytes of this s_packets are special:
        1) 0x88 always
        2) frame counter
        3) 8bit: toogle frame bit (for interlacing), 7-0bits packet counter
        4) packet counter
        With frame counter one can know if we are loosing frames
        With the packet counter one can know if we have incomplete frames
        With the toogle frame bit it is possible to generate the correct complete progressive image
        This four bytes must be removed from the image data.
        The last 60 bytes are black filled (for synchronization?) and must be removed
        Each s_packet is 1024 long but once we remove this bytes the data payload is 1024-4-60=960 bytes long.
        If packet starts with 0x00 instead of 0x88, it means it is empty and to be ignored

        In this routine we find the start of first of the two interlaced images, and then we start processing
"""
        packets=[self.buffer_list[i][:int(self.setup_list[i]['actual_length'])] for i in xrange(len(self.buffer_list))]
        #print "n packets", len(packets)
        for packet in packets:
            #print [hex(ord(i)) for i in packet[:4]]
            #print [hex(ord(i)) for i in packet[len(packet)/3:len(packet)/3+4]]
            #print [hex(ord(i)) for i in packet[2*len(packet)/3:2*len(packet)/3+4]]
            #if [hex(ord(i)) for i in packet[:4]]==['0x0', '0x0', '0x0', '0x0'] or [hex(ord(i)) for i in packet[len(packet)/3:len(packet)/3+4]]==['0x0', '0x0', '0x0', '0x0'] or [hex(ord(i)) for i in packet[2*len(packet)/3:2*len(packet)/3+4]]==['0x0', '0x0', '0x0', '0x0']:
                #print "special packet"
            #    pass
            if len(packet)!=0:
                #self.dt.update_t()
                for s_packet in [packet[:len(packet)/3], packet[len(packet)/3:2*len(packet)/3], packet[2*len(packet)/3:len(packet)]]:
                    if ord(s_packet[0])==0x88:
                        #print "Correct packet, adding"
                        n_img=ord(s_packet[1])
                        n_s_packet=((ord(s_packet[2]) & 0x0f)<< 8) | (ord(s_packet[3]))
                        n_toggle=(((ord(s_packet[2]) & 0xf0) >> 7) == 0)
                        #print "packet info", n_img, n_toggle, n_s_packet, self.n_packets
                        self.n_packets+=1
                        if self.expected_toggle==n_toggle and self.expected_n_s_packet==n_s_packet:
                            #print "Expected"
                            #print "packet info", "Image number:", n_img, "Toggle:",  n_toggle, "Pack Number:", n_s_packet, "Total packs:", self.n_packets
                            if self.start_frame:
                                self.start_frame=False
                                self.expected_n_img=n_img
                            #self.dt.update_t()
                            self.s_packets+=s_packet[4:1024-60]
                            #self.s_packets.join(s_packet[4:1024-60])
                            #self.dt.diff_t()
                            #self.s_packets+=self.test
                            self.expected_n_img+=1
                            self.expected_n_s_packet+=1
                            if self.expected_n_s_packet==360:
                                self.expected_n_s_packet=0
                                self.expected_toggle=not self.expected_toggle
                                #print "n packets", self.n_packets, len(self.s_packets)
                                if self.n_packets>360:
                                    print "N Packets", self.n_packets, " losing:" , (self.n_packets/360.)-1., " images"
                                self.n_packets=0
                                if self.expected_toggle==False:
                                    if len(self.s_packets)==720*2*480:
                                        #print "Image complete!"
                                        self.send_v4l()
                                        #raw_input()
                                    self.s_packets=''
                        else:
                            #print "Not expected"
                            self.expected_n_s_packet=0
                            self.s_packets=''
                #self.dt.diff_t()
            #print [hex(ord(i)) for i in packet]

    def callback2(self, transfer):
        #print "Callback"
        self.buffer_list=transfer.getISOBufferList()
        self.setup_list=transfer.getISOSetupList()
        self.status=transfer.getStatus()
        #print "Status" , self.status
        self.build_images(self.buffer_list, self.setup_list)
        #del transfer
        #transfer.close()
        if not self.stop:
            transfer.submit()
        else:
            print "Sending no more submits"
        #self.do_iso2()

    def callback1(self, transfer):
        self.buffer=transfer.getBuffer()
        print " Call back"
        #print " user data" ,transfer.getUserData()
        #print " buffer" , self.buffer
        print " act length" , transfer.getActualLength()
        print " endpoint" , transfer.getEndpoint()
        self.buffer_list=transfer.getISOBufferList()
        #print "Buffer list", self.buffer_list
        #raw_input()
        self.setup_list=transfer.getISOSetupList()
        print "Setup list" , self.setup_list
        print " Status" , transfer.getStatus()
        print " Len buffer" , len(self.buffer)
        #self.image+=self.get_useful_data(self.buffer_list, self.setup_list)
        for i in xrange(len(self.buffer_list)):
            print self.setup_list[i]['actual_length']
        #raw_input()
        self.image+=[self.buffer_list[i][:int(self.setup_list[i]['actual_length'])] for i in xrange(len(self.buffer_list))]

    def v4l_init(self):
        self.d=os.open(self.v4l_device, os.O_RDWR)
        cap=v.v4l2_capability()
        ioctl(self.d, v.VIDIOC_QUERYCAP, cap)
        vid_format=v.v4l2_format()
        #ioctl(d, v.VIDIOC_G_FMT, vid_format)
        vid_format.type=v.V4L2_BUF_TYPE_VIDEO_OUTPUT
        vid_format.fmt.pix.width=720
        vid_format.fmt.pix.sizeimage=1036800
        vid_format.fmt.pix.height=480
        vid_format.fmt.pix.pixelformat=v.V4L2_PIX_FMT_YUYV
        vid_format.fmt.pix.field=v.V4L2_FIELD_NONE
        vid_format.fmt.pix.colorspace=v.V4L2_COLORSPACE_SRGB
        ioctl(self.d, v.VIDIOC_S_FMT, vid_format)
        print "frame size", vid_format.fmt.pix.sizeimage, len(self.s_packets)
        self.old_t=time()

    def send_v4l(self):
        t=time()
        delta_time=t-self.old_t
        #print "Delta", delta_time,
        self.old_t=t
        out=''
        for i in xrange(480/2):
            out+=self.s_packets[i*1440:(i+1)*1440]
            out+=self.s_packets[(i+480/2)*1440:(i+480/2+1)*1440]
        os.write(self.d, out)


def even(num):
    div=num/2
    if div*2==num:
        return(True)
    else:
        return(False)

def clamp(num):
    if num>255:
        return(255)
    elif num<0:
        return(0)
    else:
        return(num)

def yuv2rgb(yuv):
    c=ord(yuv[0])
    d=ord(yuv[1])
    e=ord(yuv[2])
    r=chr(clamp((298*c+409*e+128)>>8))
    g=chr(clamp((298*c+100*d-208*e+128)>>8))
    b=chr(clamp((299*c+516*d+128)>>8))
    return((r,g,b))

from numpy import array , dot
def ypbpr2rgb(data):
    #print data
    return(dot(array([[1., 0., 1.402],[1., -0.344, -0.714], [1., 1.772, 0.]]), data))

def ypbpr2rgb2(data):
    res=ypbpr2rgb(array([ord(data[0]), struct.unpack('b', data[1])[0], struct.unpack('b', data[2])[0]]))
    #print res
    return(chr(clamp(int(res[0]))), chr(clamp(int(res[1]))), chr(clamp(int(res[2]))))

def ycbcr2rgb(data):
    return(dot(array([[1., 0., 0.701],
           [1., -0.886*0.114/0.587, -0.701*0.299/0.587],
           [1., 0.886, 0.]]), data))

def ycbcr2rgb(data):
    return(dot(array([[1., 0., 1.4],
           [1., -0.343, -0.711],
           [1., 1.765, 0.]]), data))

def ycbcr2rgb(data):
    return(dot(array([[1., 0., 1.402],
           [1., -0.34414, -0.71414],
           [1., 1.772, 0.]]), data))

def ycbcr2rgb2(data):
    res=ycbcr2rgb(array([(ord(data[0])-16)*255./(235.-16.), (ord(data[1])-0x80)*255./(240.-16.)/2., (ord(data[2])-0x80)*255./(240.-16.)/2.]))
    #print res
    return(chr(clamp(int(res[0]))), chr(clamp(int(res[1]))), chr(clamp(int(res[2]))))

def mirror(data):
    return(data)

def unpack_images(raw_packets):

    # Getting smaller internal packets
    print "Raw packet"
    small_packets=[]
    for packet in raw_packets:
        #print [hex(ord(i)) for i in packet]
        print [hex(ord(i)) for i in packet[:4]]
        print [hex(ord(i)) for i in packet[len(packet)/3:len(packet)/3+4]]
        print [hex(ord(i)) for i in packet[2*len(packet)/3:2*len(packet)/3+4]]
        if [hex(ord(i)) for i in packet[:4]]==['0x0', '0x0', '0x0', '0x0'] or [hex(ord(i)) for i in packet[len(packet)/3:len(packet)/3+4]]==['0x0', '0x0', '0x0', '0x0'] or [hex(ord(i)) for i in packet[2*len(packet)/3:2*len(packet)/3+4]]==['0x0', '0x0', '0x0', '0x0']:
            print "special packet"
            pass
            #print [hex(ord(i)) for i in packet]
        if len(packet)!=0:
            for small_packet in [packet[:len(packet)/3], packet[len(packet)/3:2*len(packet)/3], packet[2*len(packet)/3:len(packet)]]:
                if ord(small_packet[0])==0x88:
                    print "Correct packet, adding"
                    n_img=ord(small_packet[1])
                    n_packet=((ord(small_packet[2]) & 0x0f)<< 8) | (ord(small_packet[3]))
                    n_toggle=(ord(small_packet[2]) & 0xf0) >> 7
                    small_packets.append((n_img, n_packet, n_toggle, small_packet[4:1024-60]))
    #raw_input()
    #for j in  [[i[:3]]+[len(i[3])] for i in small_packets]:
    #    print j
    #print [hex(ord(i)) for i in small_packets[0][3]]

    # Getting useful images out of the packets
    images=[]
    counter=0
    image=[]
    counter2=0
    for small_packet in small_packets:
        if small_packet[1]==counter:
            print "Adding packet to image", small_packet[0], counter, counter2
            image.append(small_packet)
            counter+=1
            if counter==360:
                counter=0
                images.append(image)
                image=[]
        else:
            print "Counter incorrect, resetting"
            counter=0
        counter2+=1
    print "len images", len(images), len(images[0])

    #raw_input()
    # Joining packets to generate correct rows
    images2=[]
    image2=[]
    for img in images:
        image2=[]
        full_image=''
        n_img=img[0][0]
        n_toggle=img[0][2]
        #print "Image", n_img, n_toggle
        #raw_input()
        for row in img:
            full_image+=row[3]
        #print " 2 *len(full_image)/3" , 2*len(full_image)/3
        #raw_input()
        new_n_cols=(3*len(img[0][3])/2)
        new_n_rows=len(full_image)/new_n_cols
        print "New cols row size", new_n_cols, new_n_cols
        for i in xrange(new_n_rows):
            new_row_big=full_image[i*new_n_cols:(i+1)*new_n_cols]
            image2.append((n_img, 0, n_toggle, new_row_big))
            #print "new row" ,  len(new_row_big)
        images2.append(image2)


    print "interlacing"
    images2a=[]
    image2a=[]
    for n_img, img in enumerate(images2):
        image2a=[]
        if len(images2)>=n_img+2 and img[0][2]==0 and images2[n_img+1][0][2]==1:
            print "First image, followed by a second one"
            for row0, row1 in zip(img, images2[n_img+1]):
                image2a.append((img[0][0], 0, 0, row1[3]))
                image2a.append((img[0][0], 0, 0, row0[3]))
            images2a.append(image2a)

    #raw_input()
    # printing images
    for img in images2a:
        for n, row in enumerate(img):
            #print n, row[:3], [hex(ord(i)) for i in row[3]], len(row[3])
            pass

    for row in images2a[0][len(img[0])/5:(len(img[0])/5)+10]:
        #print "Row", row[:3], [hex(ord(i)) for i in row[3]], len(row[3])
        pass


    #YUV!
    images3=[]
    image3=[]
    for img in images2a:
        image3=[]
        for n_row, row in enumerate(img):
            new_row=''
            for i in xrange(len(row[3])/4):
                y1=row[3][i*4]
                u=row[3][i*4+1]
                y2=row[3][i*4+2]
                v=row[3][i*4+3]
                yuv1=(y1,u,v)
                yuv2=(y2,u,v)
                rgb1=ycbcr2rgb2(yuv1)
                rgb2=ycbcr2rgb2(yuv2)                #rgb1=mirror(yuv1)
                #rgb2=mirror(yuv2)
                new_row+=reduce(lambda x,y: x+y, rgb1)+reduce(lambda x,y: x+y, rgb2)
                if (n_row==80/2 and i==80/2) or (n_row==150/2 and i==300/2) or (n_row==470/2 and i==150/2):
                    pass
                    #azul 11 20 71, verde 43 155 55, negro 9 9 9 
                    #print "N rows" , len(img), "len(row[3])/4", len(row[3])/4
                    #print "Old:" , [hex(ord(k)) for k in row[3][i*4:i*4+4]], [hex(ord(k)) for k in y1+u+y2+v]
                    #print "New row", [hex(ord(k)) for k in reduce(lambda x,y: x+y, rgb1)+reduce(lambda x,y: x+y, rgb2)]
                    #raw_input()
                #raw_input()
            image3.append((0, 0, 0, new_row))
        images3.append(image3)

    # Erasing even dots in images
    #raw_input()
    new_images=[]
    for image in images2:
        new_image=[]
        for row in image:
            new_row=''
            for n, col in enumerate(row[3]):
                if not even(n):
                    new_row+=col
                #else:
                #    new_row+=col
            new_image.append((row[0], row[1], row[2], new_row))
        new_images.append(new_image)
    return(images3)

def create_pil_images(images):
    out_images=[]
    for img in images:
        #print img
        out_image=''
        for row in img:
            #print row
            out_image=row[3]+out_image
        size=(len(img[0][3]), len(img))
        print "size", size
        out_images.append((out_image, size))
        #raw_input()
    return(out_images)

def change_res(images):
    width=640
    new_images=[]
    for img, size in images:
        new_img=''
        for i in xrange(size[1]):
            new_img=img[i*size[0]: i*size[0]+width*3]+new_img
        new_images.append((new_img, (width*3, size[1])))
    return(new_images)

from fcntl import ioctl
import v4l2 as v
import os
from time import time, sleep

def send_loopback(images):
    d=os.open("/dev/video1", os.O_RDWR)
    cap=v.v4l2_capability()
    ioctl(d, v.VIDIOC_QUERYCAP, cap)
    vid_format=v.v4l2_format()
    #ioctl(d, v.VIDIOC_G_FMT, vid_format)
    vid_format.type=v.V4L2_BUF_TYPE_VIDEO_OUTPUT
    vid_format.fmt.pix.width=640
    #vid_format.fmt.pix.sizeimage=1036800
    vid_format.fmt.pix.height=480
    vid_format.fmt.pix.pixelformat=v.V4L2_PIX_FMT_RGB24
    vid_format.fmt.pix.field=v.V4L2_FIELD_NONE
    vid_format.fmt.pix.colorspace=v.V4L2_COLORSPACE_SRGB
    ioctl(d, v.VIDIOC_S_FMT, vid_format)
    print "frame size", vid_format.fmt.pix.sizeimage, len(images[0][0]), images[0][1]
    raw_input()
    counter=0
    old_t=time()
    fps_period=1./29.97
    while True:
        counter+=1
        #print "Image", counter
        for img, size in images:
            t=time()
            delta_time=t-old_t
            print "Delta", delta_time,
            old_t=t
            if delta_time<fps_period:
                print "sleeping a bit"
                sleep(fps_period-delta_time)
            os.write(d, img)

import Image
import struct

def main():
    utv=Utv007()
    for i in xrange(80):
        #raw_input()
        utv.do_iso()
    for i in xrange(80):
        print "Event", i
        utv.handle_ev()
    print " len image", len(utv.image)
    #image=struct.unpack('H'*(len(utv.image)/2), utv.image)
    #print "Image raw"
    #print utv.image
    images=unpack_images(utv.image)
    vis_images_final=create_pil_images(images)
    v4l_images=change_res(vis_images_final)
    send_loopback(v4l_images)

    for i, size in vis_images_final:
        im=Image.frombuffer("RGB", (size[0]/3, size[1]), i)
        im.show()



if __name__=="__main__":
    main()

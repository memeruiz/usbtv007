#!/usr/bin/env python

easycap_dev_id='0x1b71:0x3002'
interface=0

import usb1 as u
from protocol import p_init, p5
from time import sleep

def run_protocol(prot, devh):
    for req in prot:
        print "line", req[0], hex(req[1]), hex(req[2]), hex(req[3]), req[4], req[5],
        if len(req)>6:
            if type(req[6])==list:
                for i,j in req[6]:
                    print hex(i), j
            else:
                print hex(req[6])
        else:
            print
        if req[0][0]=='c':
            if req[0][2:]=='vd':
                print "Control request"
                if req[0][1]=='r':
                    print "Read"
                    reply=devh.controlRead(
                        u.libusb1.LIBUSB_TYPE_VENDOR|u.libusb1.LIBUSB_RECIPIENT_DEVICE,
                        req[1], req[2], req[3], req[5])
                    print "Reply:", hex(ord(reply))
                    if type(req[6])==list:
                        print " Multiply options"
                        found_prot=False
                        for resp, next_prot in req[6]:
                            if resp==ord(reply):
                                print "Found response in multiple options, running recursively" 
                                run_protocol(next_prot, devh)
                                found_prot=True
                                break
                        if not found_prot:
                            print "Unknown response!! Exiting!"
                            exit()
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
    def __init__(self):
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

        if self.devh.kernelDriverActive(self.interface):
            print "Kernel driver already using device. Stopping"
            exit()

        print "Claiming interface"
        self.devh.claimInterface(self.interface)
        run_protocol(p_init, self.devh)
        #sleep(1.)
        print
        print "Second part"
        print
        run_protocol(p5, self.devh)
        print "Setting Altsetting to 1" 
        self.devh.setInterfaceAltSetting(self.interface,1)
        self.image=[]
        #print "Reading int"
    #a=devh.interruptRead(4,0, timeout=1000)
    #print "Interrupt result" , a

    def __del__(self):
        print "Realeasing interface"
        self.devh.releaseInterface(0)
        print "Closing device handler"
        self.devh.close()
        #sleep(2)
        print "Exiting context"
        self.cont.exit()

    def do_iso(self):
        self.iso=self.devh.getTransfer(iso_packets=8)
        self.iso.setIsochronous(0x81, 0x6000, callback=self.callback1, timeout=1000)
        self.iso.submit()
        #self.iso.setCallback(callback1)

    def handle_ev(self):
        self.cont.handleEvents()

    def get_useful_data(self, buffer_list, setup_list):
        data=''
        for b, s in zip(buffer_list, setup_list):
            actual_len=s['actual_length']
            print "Actual len" , actual_len
            data+=b[:actual_len]
        return(data)

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
    for small_packet in small_packets:
        if small_packet[1]==counter:
            print "Adding packet to image", small_packet[0]
            image.append(small_packet)
            counter+=1
            if counter==360:
                counter=0
                images.append(image)
                image=[]
        else:
            print "Counter incorrect, resetting"
            counter=0
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
                image2a.append((img[0][0], 0, 0, row0[3]))
                image2a.append((img[0][0], 0, 0, row1[3]))
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


    #raw_input()
    print small_packets
    #raw_input()
    state="lost"
    n_zeros=0
    out_data=[]
    for i in raw_data:
        if state=="lost":
            print "looking for zeros"
            if ord(i)==0x00:
                print "first zero found"
                state="zeros"
                n_zeros+=1
        elif state=="zeros":
            if ord(i)==0x00:
                n_zeros+=1
                if n_zeros==60:
                    print "All zeros found"
                    state="88"
                    n_zeros=0
                elif n_zeros>60:
                    print " Error more zeros than 60"
                    exit()
        elif state=="88":
            if ord(i)==0x88:
                print "88 found"
                state=="record_packet"
                out=''
            else:
                print "Error 88 expected"
                exit()
        elif state=="record_packet":
            print "recording data"
            if ord(i)==0x00:
                n_zeros+=1
                if n_zeros==60:
                    print "All zeros found"
            elif ord(i)==0x88:
                if n_zeros>=60:
                    print "Found 60 or more zeros and 88, new line found!"
                    n_zeros=0
                    new_line=True
            else:
                n_zeros=0
            if new_line:
                out_data.append(out)
                out=i
                new_line=False
            else:
                out+=i


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

import Image
import struct

def main():
    utv=Utv007()
    for i in xrange(80):
        #raw_input()
        utv.do_iso()
    for i in xrange(80):
        utv.handle_ev()
    print " len image", len(utv.image)
    #image=struct.unpack('H'*(len(utv.image)/2), utv.image)
    #print "Image raw"
    #print utv.image
    images=unpack_images(utv.image)
    vis_images_final=create_pil_images(images)

    for i, size in vis_images_final:
        im=Image.frombuffer("RGB", (size[0]/3, size[1]), i)
        im.show()



if __name__=="__main__":
    main()

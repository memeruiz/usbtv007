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

    raw_input()
    # Joining packets to generate correct rows
    images2=[]
    image2=[]
    for img in images:
        image2=[]
        full_image=''
        for row in img:
            full_image+=row[3]
        print " 2 *len(full_image)/3" , 2*len(full_image)/3
        raw_input()
        new_n_cols=(3*len(img[0][3])/2)
        new_n_rows=len(full_image)/new_n_cols
        print "New cols row size", new_n_cols, new_n_cols
        for i in xrange(new_n_rows):
            new_row_big=full_image[i*new_n_cols:(i+1)*new_n_cols]
            image2.append((0, 0, 0, new_row_big))
            print "new row" ,  len(new_row_big)
        images2.append(image2)

    raw_input()
    # printing images
    for img in images2:
        for row in img:
            print row[:3], [hex(ord(i)) for i in row[3]], len(row[3])

    # Erasing even dots in images
    #raw_input()
    new_images=[]
    for image in images2:
        new_image=[]
        for row in image:
            new_row=''
            for n, col in enumerate(row[3]):
                if even(n):
                    new_row+=col
            new_image.append((row[0], row[1], row[2], new_row))
        new_images.append(new_image)
    return(new_images)


    raw_input()
    print small_packets
    raw_input()
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
    for i in xrange(40):
        #raw_input()
        utv.do_iso()
    for i in xrange(40):
        utv.handle_ev()
    print " len image", len(utv.image)
    #image=struct.unpack('H'*(len(utv.image)/2), utv.image)
    #print "Image raw"
    #print utv.image
    images=unpack_images(utv.image)
    vis_images_final=create_pil_images(images)

    for i, size in vis_images_final:
        im=Image.frombuffer("L", size, i)
        im.show()



    #for i in utv.image:
    #    print hex(ord(i)),
    #    pass
    #print "Image" ,image
    n_zeros=0
    n_lines=0
    cols=0
    new_image=[]
    images=[]
    line=''
    for n,i in enumerate(utv.image):
        if i==chr(0x00):
            n_zeros+=1
            max_zeros=0
            max_cols=cols
        else:
            max_zeros=n_zeros
            n_zeros=0
            cols+=1
            line+=i
        if max_zeros>=50:
            n_lines+=1
            #print " Cols" , max_cols, " max zeros" , max_zeros, "First number" , hex(ord(i)), hex(ord(utv.image[n+1])), hex(ord(utv.image[n+2])), hex(ord(utv.image[n+3])), struct.unpack('H', utv.image[n+3]+utv.image[n+2])
            cols=0
            #print " New line", n_lines
            #max_zeros=0
        if max_zeros>=1084:
            #print " Lines" , n_lines
            #n_lines=0
            pass
        if max_zeros>=2100:
            print " New image" , max_zeros
            print " Lines" , n_lines
            n_lines=0
            #max_zeros=0
        if max_zeros>=50:
            #print "new line added", [hex(ord(i)) for i in line]
            new_image.append(line)
            line=''
        if max_zeros>=2100:
            images.append(list(new_image))
            new_image=[]
            print "new image added", len(images)
    print " Captured", len(images), " Images"

    vis_images=[]
    vis_image=''
    for i, img in enumerate(images):
        #print "Image" , i, "Lines", len(img), "First line cols" , len(img[0])
        if len(img)==360:
            n_lines=0
            for line in img:
                if len(line)>=960:
                    n_lines+=1
                    print " Line" ,
                    #print [hex(ord(line[k])) for k in xrange(len(line))],
                    print [hex(ord(line[k])) for k in xrange(4)],
                    print [hex(ord(line[-4:][k])) for k in xrange(4)],
                    print "len" , len(line)
                    vis_image+=line[:960]
            vis_images.append((vis_image,(960, n_lines)))
            vis_image=''

    print "Useful images" , len(vis_images)
    for i in vis_images:
        print "length image", len(i[0]), i[1][0]*i[1][1], 360*960
    raw_input()


    #remove vert line
    vis_images2=[]
    for i, size in vis_images:
        new_image=''
        for row in xrange(size[1]):
            line=i[row*size[0]:(row+1)*size[0]]
            new_line=''
            for col, j in enumerate(line):
                if not even(col):
                    new_line+=j
            #print " Line" , [hex(ord(k)) for k in new_line]
            new_image+=new_line
        vis_images2.append((new_image, (size[0]/2, size[1])))


    # # resync
    # vis_image3=[]
    # for img, size in vis_images:
    #     new_image=''
    #     for i in img:
    #         if ord(i)==0x01:
    #             print " Sync"


    #flip
    vis_images_final=[]
    for i, size in vis_images2:
        new_image=''
        for row in xrange(size[1]):
            line=i[row*size[0]:(row+1)*size[0]]
            new_image=line+new_image
            #print " Line" , [hex(ord(k)) for k in line]
        vis_images_final.append((new_image, size))

    #image=''
    #for i in utv.image:
    #    if i!=chr(0x00):
    #        image+=i
    #image2=''
    #counter=0
    #for i in xrange(640*525):
    #    image2+=chr((ord(image[i*4]) & 0xff))+chr((ord(image[i*4+1]) & 0xff))+chr((ord(image[i*4+2]) & 0xff))+chr((ord(image[i*4+3]) & 0xff))
    #print "len image2" ,len(image2)
    for i, size in vis_images_final:
        im=Image.frombuffer("L", size, i)
        #im.show()
    #raw_input()

if __name__=="__main__":
    main()

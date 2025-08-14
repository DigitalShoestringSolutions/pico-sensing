# Using the https://github.com/peterhinch/micropython-fourier/ repo for discrete FTs. 
# Combining necessary files into this one. Imports have been adapted accordingly.

"""
The MIT License (MIT)

Copyright (c) 2015 Peter Hinch

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


# dftclass.py Python interface for FFT assembler code
# Author: Peter Hinch

import array
import math
from uctypes import addressof
import utime

# Control: on entry r1 should hold one of these values to determine the direction and scaling
# of the transform. Only bit 0 now used by fft()
REVERSE = const(0)      # Inverse transform (frequency to time domain)
FORWARD = const(1)      # Forward transform
POLAR   = const(3)      # bit 2: Polar conversion
DB      = const(7)      # bit 3: Polar with dB conversion

# Instantiating the class creates the real, imaginary and control arrays, populates real and imaginary
# with zero. Populates the control array with these values:
# ctrl[0] = length of data array
# ctrl[1] = no. of bits to represent the length
# ctrl[2] = Address of real data array
# ctrl[3] = Address of imaginary data array
# ctrl[4] = Byte Offset into entry 0 of complex roots of unity
# ctrl[5] = Address of scratchpad for use by fft code
# After this is an array of seven complex nos followed by one for the roots of unity.
# The first complex no. is initialised to the initial u value. The rest make up a scratchpad used by fft()
# see ctrlmap.ods for more detail.

class DFT(object):
    def __init__(self, length, popfunc=None, winfunc=None):
        bits = round(math.log(length)/math.log(2))
        assert 2**bits == length, "Length must be an integer power of two"
        self.dboffset = 0               # Offset for dB calculation
        self._length = length
        self.popfunc = popfunc          # Function to acquire data
        self.re = array.array('f', (0 for x in range(self._length)))
        self.im = array.array('f', (0 for x in range(self._length)))
        if winfunc is not None:  # If a window function is provided, create and populate the array
            self.windata = array.array('f', (0 for x in range(self._length))) # of window coefficients
            for x in range(0, length):
                self.windata[x] = winfunc(x, length)
        else:
            self.windata = None
        COMPLEX_NOS = 7                       # Size of complex buffer area before roots of unity
        ROOTSOFFSET = COMPLEX_NOS*2           # Word offset into complex array of roots of unity
        bits = round(math.log(self._length)/math.log(2)) # havent we already done this? Can't have changed since line 58
        self.ctrl = array.array('i', [0]*6)
        self.cmplx = array.array('f', [0.0]*((bits +1 +COMPLEX_NOS)*2))
        self.ctrl[0] = self._length
        self.ctrl[1] = bits
        self.ctrl[2] = addressof(self.re)
        self.ctrl[3] = addressof(self.im)
        self.ctrl[4] = COMPLEX_NOS*8          # Byte offset into complex array of roots of unity
        self.ctrl[5] = addressof(self.cmplx)  # Base address

        self.cmplx[0] = 1.0                   # Initial value of u = [1 +j0]
        self.cmplx[1] = 0.0                   # Intermediate values are used by fft() and not initialised
        self.cmplx[12] = 1.0/self._length     # Default scaling multiply by 1/length
        self.cmplx[13] = 0.0                  # ignored
        i = ROOTSOFFSET
        creal = -1
        cimag =  0
        self.cmplx[i] = creal                 # Complex roots of unity
        self.cmplx[i +1] = cimag
        i += 2
        for x in range(bits):
            cimag = math.sqrt((1.0 - creal) / 2.0)  # Imaginary part
            self.cmplx[i +1] = cimag
            creal = math.sqrt((1.0 + creal) / 2.0)  # Real part
            self.cmplx[i] = creal
            i += 2

    @property
    def scale(self):
        return self.cmplx[12]

    @scale.setter
    def scale(self, value):                    # Allow user to override default
        self.cmplx[12] = value

    @property
    def length(self):
        return self._length                    # Read only

    def run(self, conversion):                 # Uses assembler for speed
        
        if self.popfunc is not None:
            self.popfunc(self)                 # Populate the data (for fwd transfers, just the real data)
        
        if conversion != REVERSE:              # Forward transform: real data assumed
            setarray(self.im, 0, self._length) # Fast zero imaginary data
            if self.windata is not None:       # Fast apply the window function
                winapply(self.re, self.windata, self._length)
        
        start = utime.ticks_us()
        fft(self.ctrl, conversion)
        delta = utime.ticks_diff(utime.ticks_us(), start)

        if (conversion & POLAR) == POLAR:      # Ignore complex conjugates, convert 1st half of arrays
            topolar(self.re, self.im, self._length//2) # Fast

            if conversion == DB:               # Ignore conjugates: convert 1st half only
                for idx, val in enumerate(self.re[0:self._length//2]):
                    self.re[idx] = -80.0 if val <= 0.0 else 20*math.log10(val) - self.dboffset

        return delta


# Here's a tiny wrapper I added
def simpledft(data:Iterable[float]) -> array:
    """Take some real data and get the magnitude of the frequency components"""
    mydft = DFT(len(data))       # includes assertion that length is a power of 2
    for n, v in enumerate(data): # preserves array form, rather than just mydft.re = data which replaces it with a list
            mydft.re[n] = v

    fft_execution_time = mydft.run(POLAR)
    #print(fft_execution_time)
    return mydft.re[:len(mydft.re)//2] # After polar conversion, re contains magnitudes. But only the first half contains meaningful data







# window.py Window function
# Author: Peter Hinch
# 20th April 2015
# Now uses FPU mnemonics. Tests complete.
# Floating point version
# Applies a window function to an array of real samples before performing a DFT.
# removes the DC (zero frequency) component by averaging the sample set and
# subtracting from each sample, before multiplying the sample by the corrsponding
# coefficient and storing the result in the sample array.
# The coefficient array is unchanged.

#import array, math # already imported above

# Multiply each element in array 0 by the corresponding one in array 1, returning the
# result in array 0.
# r0: array 0 real data
# r1: array 1 window coefficients
# r2: length of arrays

@micropython.asm_thumb
def winapply(r0, r1, r2):
    push({r0, r2})
    mov(r3, 0)
    vmov(s14, r3)
    vcvt_f32_s32(s15, s14)  # s15 holds value to set
    label(LOOP1)
    vldr(s14, [r0, 0])
    vadd(s15, s14, s15)
    add(r0, 4)
    sub(r2, 1)
    bgt(LOOP1)
    pop({r0, r2})
    vmov(s14, r2)
    vcvt_f32_s32(s14, s14)  # convert array length to float
    vdiv(s13, s15, s14)     # avg. in s13
    label(LOOP)
    vldr(s14, [r0, 0])
    vsub(s15, s14, s13)
    vldr(s14, [r1, 0])
    vmul(s15, s14, s15)
    vstr(s15, [r0, 0])
    add(r0, 4)
    add(r1, 4)
    sub(r2, 1)
    bgt(LOOP)

# Set all elements of a float array to an integer value
# r0: the array
# r1: value
# r2: length of array
@micropython.asm_thumb
def setarray(r0, r1, r2):
    vmov(s14, r1)
    vcvt_f32_s32(s15, s14)  # Value in s15
    label(LOOP)
    vstr(s15, [r0, 0])
    add(r0, 4)
    sub(r2, 1)
    bgt(LOOP)


# Copy elements of an integer array to a float array, converting
# r0: integer array
# r1: float array
# r2: length
@micropython.asm_thumb
def icopy(r0, r1, r2):
    label(LOOP)
    vldr(s14, [r0, 0])
    vcvt_f32_s32(s15, s14)
    vstr (s15, [r1, 0])
    add(r0, 4)
    add(r1, 4)
    sub(r2, 1)
    bgt(LOOP)












# polar.py Fast floating point cartesian to polar coordinate conversion
# Author: Peter Hinch
# 31st Oct 2015 Updated to match latest firmware
# 21st April 2015
# Now uses recently implemented FPU mnemonics
# Arctan is based on the following approximation applicable to octant zero where q = x/y :
# arctan(q) = q*pi/4- q*(q - 1)*(0.2447 + 0.0663*q)
# Arctan approximation: max error about 0.085 deg in my tests.

from math import pi
from array import array
consts = array('f', [0.0, 0.0, 1.0, pi, pi/2, -pi/2, pi/4, 0.2447, 0.0663])

# Entry:
# r0: array of real (x) values
# r1: array of imaginary (y) values
# r2: array element 0 = length of arrays following are constants
# ARM CPU register usage
# r3: Array length (integer)
# r4: Negate flag
# r5, r6: Temporary storage
# Returns:
# The real array holds magnitude values, the imaginary ones phase.
# Phase is in radians compatible with cPython's math.atan2()

@micropython.asm_thumb
def polar(r0, r1, r2):    # Array length in r3: convert to integer
    vldr(s15, [r2, 0])
    vcvt_s32_f32(s15, s15)
    vmov(r3, s15)
# Load constants
    vldr(s0, [r2, 4])       # 0
    vldr(s1, [r2, 8])       # 1
    vldr(s2, [r2, 12])      # Pi
    vldr(s3, [r2, 16])      # Pi/2
    vldr(s4, [r2, 20])      # -Pi/2
    vldr(s5, [r2, 24])      # Pi/4
    vldr(s6, [r2, 28])      # 0.2447
    vldr(s7, [r2, 32])      # 0.0663
    b(START)

    label(DOCALC)
    vldr(s8, [r2, 4])       # c = 0.0
    vldr(s14, [r0, 0])      # x
    vldr(s15, [r1, 0])      # y
# Calculate magnitude
    vmul(s10, s14, s14)
    vmul(s9, s15, s15)
    vadd(s10, s10, s9)
    vsqrt(s10, s10)
    vstr(s10, [r0, 0])      # real = hypot

# Start of arctan calculation
    mov(r4, 0)              # Negate flag
    vcmp(s14, s0)
    vmrs(APSR_nzcv, FPSCR)  # transfer status to ARM status registers
    bne(QUADCHECK)          # Skip if not x == 0

    vcmp(s15, s0)
    vmrs(APSR_nzcv, FPSCR)  # transfer status to ARM status registers
    bne(P01)
    vstr(s0, [r1,0])        # result = 0
    b(Q0DONE)

    label(P01)
    vcmp(s15, s0)
    vmrs(APSR_nzcv, FPSCR)  # transfer status to ARM status registers
    ite(ge)
    vstr(s3, [r1,0])        # result = pi/2
    vstr(s4, [r1,0])        # result = -pi/2
    b(Q0DONE)

    label(QUADCHECK)
    vcmp(s15, s0)           # compare y with 0
    vmrs(APSR_nzcv, FPSCR)
    bge(P02)
    vneg(s15, s15)          # y = -y
    mov(r4, 1)              # set negate flag
    label(P02)              # y now > 0
    vcmp(s14, s0)           # comp x with 0
    vmrs(APSR_nzcv, FPSCR)
    bge(P04)
                            # x < 0
    vneg(s14, s14)          # x = -x
    vcmp(s14, s15)          # comp x with y
    vmrs(APSR_nzcv, FPSCR)
    bgt(P03)
    vmov(r5, s14)           # swap x and y CONVOLUTED: need to implement vmov(Sd, Sm)
    vmov(r6, s15)
    vmov(s15, r5)
    vmov(s14, r6)
    vmov(r5, s3)
    vmov(s8, r5)            # c = pi/2
    b(OCTZERO)

    label(P03)              # y < x
    cmp(r4, 0)
    ite(eq)
    mov(r4, 1)
    mov(r4, 0)              # neg = not neg
    vmov(r5, s2)            # c = pi
    vmov(s8, r5)
    vneg(s8, s8)            # c = -pi
    b(OCTZERO)

    label(P04)              # x > 0
    vcmp(s14, s15)          # comp x with y
    vmrs(APSR_nzcv, FPSCR)
    bge(OCTZERO)
    vmov(r5, s14)           # swap x and y
    vmov(r6, s15)
    vmov(s15, r5)
    vmov(s14, r6)
    vmov(r5, s4)            # c = -pi/2
    vmov(s8, r5)
    cmp(r4, 0)
    ite(eq)
    mov(r4, 1)
    mov(r4, 0)              # neg = not neg
# Octant zero
    label(OCTZERO)          # calculate r = x*pi/4 - x*(x - 1)*(0.2447 + 0.0663*x)
    vdiv(s14, s15, s14)     #  x = y/x
    vmul(s15, s7, s14)      #  s15 = 0.0663x
    vadd(s15, s6, s15)      # s15 = 0.2447 + 0.0663*x
    vsub(s13, s14, s1)      # s1 = x -1
    vmul(s15, s15, s13)     # s15 = (x - 1)*(0.2447 + 0.0663*x)
    vmul(s15, s14, s15)     # s15 = x*(x - 1)*(0.2447 + 0.0663*x)
    vmul(s13, s14, s5)      # s5 = x*pi/4
    vsub(s15, s13, s15)

    vadd(s15, s15, s8)      # s15 += c
    cmp(r4, 0)
    it(ne)
    vneg(s15, s15)
    vstr(s15, [r1, 0])      # imag = angle
    label(Q0DONE)
    bx(lr)                  # ! DOCALC

    label(START)            # r0-> real r1-> imag r3 = length
    bl(DOCALC) 
    add(r0, 4)
    add(r1, 4)
    sub(r3, 1)
    bne(START)

def topolar(re, im, length):
    consts[0] = length
    polar(re, im, consts)











# dft.py DFT code
# Author: Peter Hinch
# 31st Oct 2015 Updated to match latest firmware
# 20th April 2015
# Uses FPU: now uses newly implemented FPU assembler mnemonics.
# Timing: 256 points 2.5mS vs 115mS for Python (90mS with native code emitter)
# 1024 points:12mS vs 8.98mS on Cray 1 :-)
# Now supports dB conversion
# Implemented DFT class
# Workrounds for beq() problem now removed as problem fixed.
# Separate scaling factors for roots of unity and for t1
# Maths scaling is now controlled by caller
# Test moved out to dfttest.py
# Now produces plausible results with 16384 scaling
# Note: weird results always arise from overflow. Try reducing amplitude.

# Source: ARM v7-M Architecture Reference Manual
import array
import math

# Complex primitives
# CADD, CSUB, CMUL add, subtract, multiply
# These operate on a scratchpad array with data stored as real, imag in consecutive locations
# On entry:
# r0 is address of complex scratchpad
# r1 is byte offset of destination
# r2 is byte offset of op1
# r3 is byte offset of op2
# r4 (in case of CMUL) bits to right-shift the result
# dest := operand1 <operator> operand2
# CGET gets a complex number from real, imag arrays and stores in the scratchpad
# CPUT stores a complex from the scratchpad into the real, imag arrays
# CMUL computes the product of two complex nos. and shifts the result right by N bits
# CCOPY copies a complex from one scratchpad location to another
# CONJUGATE replaces a complex with its conjugate
# Routines preserve all registers

# ********* DFT FUNCTION ENTRY POINT ********* 
# On entry r0 holds adress of scratchpad
# r1: 
# bit 0 if set specifies a Forward transform otherwise a Reverse transform

@micropython.asm_thumb
def fft(r0, r1):        # r0 adress of scratchpad, r1 = Control: see above
    b(ENTRY)            # Skip internal functions
# Reverse an array in place
    label(ARRAY_REVERSE)
    mov(r2, r0)         # Scratch array
    ldr(r0, [r2, 8])    # Real data array
    ldr(r1, [r2, 12])   # Imaginary data array
    ldr(r4, [r2, 0])
    sub(r4, 1)          # limit of source offset into data arrays length -1
    mov(r3, 2)
    lsl(r4, r3)         # r4 is max byte offset into arrays
    ldr(r3, [r2, 4])    # bits in address
    mov(r5, 28)         # word length - 4 to produce a byte offset
                        # when a source byte offset is bit reversed
    sub(r3, r5, r3)     # r3 is no. of bits to shift reversed address.
    mov(r6, 0)          # r6 is source offset into data arrays

    label(LOOP1)
    rbit(r7, r6)
    lsr(r7, r3)         # r7 bit reversed array offset as a byte address
    cmp(r7, r6)
    ble(PASS)           # Skip if source and dest are the same or if already done (dest < source)
    push({r3, r4, r6})

    push({r6})          # Process r0 array
    mov(r3, 0)          # r3 = Source address
    add(r3, r0, r6)     # array + source offset
    mov(r6, 0)          # r6 = destination address
    add(r6, r0, r7)     # array + reversed offset
    ldr(r4, [r6, 0])    # Swap source and destination
    ldr(r5, [r3, 0])
    str(r5, [r6, 0])
    str(r4, [r3, 0])

    pop({r6})           # Repeat for r1 array
    mov(r3, 0)          # r3 = Source address
    add(r3, r1, r6)
    mov(r6, 0)          # r6 = destination address
    add(r6, r1, r7)
    ldr(r4, [r6, 0])
    ldr(r5, [r3, 0])
    str(r5, [r6, 0])
    str(r4, [r3, 0])

    pop({r3, r4, r6})
    label(PASS)
    add(r6, 4)
    cmp(r6, r4)
    ble(LOOP1)
    bx(lr)              # ! ARRAY_REVERSE

# Multiply r5 = r3*r5
    label(FSCALE)
    vmov(s14, r3)
    vmov(s15, r5)
    vmul(s15, s14, s15)
    vmov(r5, s15)
    bx(lr)                  # ! FSCALE

# Complex primitives:
    label(CADD)             # add
    push({r1, r7})
    add(r7, r0, r2)         # op1 address
    vldr(s12, [r7, 0])      # op1.real
    vldr(s13, [r7, 4])      # op1.imag
    add(r7, r0, r3)         # op2 address
    vldr(s14, [r7, 0])      # op2.real
    vldr(s15, [r7, 4])      # op2.imag
    vadd(s10, s12, s14)
    vadd(s11, s13, s15)
    add(r1, r0, r1)         # Destination offset
    vstr(s10, [r1, 0])
    vstr(s11, [r1, 4])
    pop({r1, r7})
    bx(lr)                  # ! CADD

    label(CSUB)             # subtract
    push({r1, r7})
    add(r7, r0, r2)         # op1 address
    vldr(s12, [r7, 0])      # op1.real
    vldr(s13, [r7, 4])      # op1.imag
    add(r7, r0, r3)         # op2 address
    vldr(s14, [r7, 0])      # op2.real
    vldr(s15, [r7, 4])      # op2.imag
    vsub(s10, s12, s14)
    vsub(s11, s13, s15)
    add(r1, r0, r1)         # Destination offset
    vstr(s10, [r1, 0])
    vstr(s11, [r1, 4])
    pop({r1, r7})
    bx(lr)                  # ! CSUB

# r1 = dest offset
# r2 = op1 offset
# r3 = op2 offset
    label(CMUL)             # multiply
    push({r1, r7})
    add(r7, r0, r2)         # op1 address
    vldr(s12, [r7, 0])      # op1.real
    vldr(s13, [r7, 4])      # op1.imag
    add(r7, r0, r3)         # op2 address
    vldr(s14, [r7, 0])      # op2.real
    vldr(s15, [r7, 4])      # op2.imag

    vmul(s10, s12, s14)     # s10 = ax
    vmul(s9, s13, s15)      # s9  = by
    vsub(s10, s10, s9)      #  s10 = ax - by
    vmul(s11, s13, s14)     # s11 = ay
    vmul(s9,  s12, s15)     # s9  = bx
    vadd(s11, s11, s9)      # s11 = ay + bx

    add(r1, r0, r1)         # Destination offset
    vstr(s10, [r1, 0])
    vstr(s11, [r1, 4])
    pop({r1, r7})
    bx(lr)                  # ! CMUL

# Get a complex pair from source arrays
# r0 = scratchpad base address
# r1 = real base address
# r2 = imag base address
# r3 = source offset
# r4 = dest scratchpad offset
    label(CGET)
    push({r1, r2, r3, r4})
    add(r4, r0, r4)     # R4: dest addr
    add(r1, r1, r3)     # R1: source real addr
    add(r2, r2, r3)     # R2: source imag addr
    ldr(r1, [r1, 0])
    str(r1, [r4, 0])
    ldr(r1, [r2, 0])
    str(r1, [r4, 4])
    pop({r1, r2, r3, r4})
    bx(lr)              # ! CGET
    
# Store a complex pair into original arrays
# r0 = scratchpad base address
# r1 = real base address
# r2 = imag base address
# r3 = source scratchpad  offset
# r4 = dest offset into arrays
    label(CPUT)
    push({r1, r2, r3, r4})
    add(r1, r1, r4)     # R1: real dest addr
    add(r2, r2, r4)     # R2: imag dest addr
    add(r3, r0, r3)     # R3: scratchpad operand addr
    ldr(r4, [r3, 0])
    str(r4, [r1, 0])
    ldr(r4, [r3, 4])
    str(r4, [r2, 0])
    pop({r1, r2, r3, r4})
    bx(lr)              # ! CPUT

# Copy a complex, e.g. from roots to scratchpad
# r0 dest base address
# r1 source base address
# r2 dest offset
# r3 source offset
    label(CCOPY)
    push({r1, r2, r3})
    add(r2, r0, r2)     # R2: dest addr
    add(r3, r1, r3)     # R3: source addr
    ldr(r1, [r3, 0])
    str(r1, [r2, 0])
    ldr(r1, [r3, 4])
    str(r1, [r2, 4])
    pop({r1, r2, r3})
    bx(lr)              # ! CCOPY

# Convert a complex to its conjugate
# r0 base addr
# r1 offset
    label(CONJUGATE)
    push({r2, r3})
    add(r2, r0, r1)     # Operand address
    vldr(s15, [r2, 4])  # op.imag
    vneg(s15, s15)
    vstr(s15, [r2, 4])
    pop({r2, r3})
    bx(lr)              # ! CONJUGATE

# Main calculation enter with r2 = i r5 = l1

    label(DOMATHS)
    push({lr, r1, r2, r3, r4})

    add(r7, r2, r5)     #                       ** i1 = i+l1
    add(r7, r7, r7)     # Convert to byte offsets into source data arrays
    add(r7, r7, r7)     # r7 = i1(bytes)
    mov(r6, r2)
    add(r6, r6, r6)
    add(r6, r6, r6)     # r6 = i(bytes)
                        # Get real and imag from source and put in complex scratchpad
    mov(r0, r8)         # &scratch
    ldr(r1, [r0, 8])    # &real
    ldr(r2, [r0,12])    # &imag
    mov(r3, r6)         # i(bytes)
    mov(r4, 32)         # nums[i]
    ldr(r0, [r0, 20])   # &complex_scratchpad
    bl(CGET)
    mov(r3, r7)         # i1(bytes)
    mov(r4, 40)
    bl(CGET)            # nums[i1]
                        #                       ** t1 = u*nums[i1]
    mov(r1, 24)         # t1
    mov(r2, 8)          # u
    mov(r3, 40)         # nums[i1]
    bl(CMUL)


                        #                       ** nums[i1] = nums[i] - t1
    mov(r1, 40)         # nums[i1]
    mov(r2, 32)         # nums[i]
    mov(r3, 24)         # t1
    bl(CSUB)
                        #                       ** nums[i] += t1
    mov(r1, 32)         # nums[i]
    mov(r2, r1)
    mov(r3, 24)
    bl(CADD)

# put back into source arrays
    mov(r0, r8)         # &scratch
    ldr(r1, [r0, 8])    # &real
    ldr(r2, [r0,12])    # &imag
    mov(r4, r6)         # i(bytes)
    mov(r3, 32)         # nums[i]
    ldr(r0, [r0, 20])   # &complex_scratchpad
    bl(CPUT)
    mov(r4, r7)         # i1(bytes)
    mov(r3, 40)
    bl(CPUT)            # nums[i1]
    pop({lr, r1, r2, r3, r4})
    bx(lr)              # ! DOMATHS

# **************** FFT MAIN CODE ****************
# Entry: r0 adress of scratchpad, r1 = control (see above)
# Register usage
# r0 free for all
# r1 loop limit value [pushed on entry, popped before test]
# r2 loop counter [pushed on entry, popped before increment]
# Innermost loop: increment is l2 stored in r9
# Variables
# r3
# r4 l2
# r5 l1
# r6 i as byte offset
# r7 i1 as byte offset
# r8  &scratch
# r9  l2
# r10 control
# r11 Unused
# r12 Unused
# COMPLEX SCRATCHPAD
# Index ByteOffset  Contents
#  0        0       u initial value
#  1        8       u current
#  2       16       c current
#  3       24       t1
#  4       32       nums[i]
#  5       40       nums[i1]
    label(ENTRY)
    push({r8, r9, r10})
    mov(r8, r0)         # r8 address of scratch
    mov(r10, r1)        # control (forward = 1)
    bl(ARRAY_REVERSE)   # Reverse data arrays

    mov(r0, r8)
    ldr(r1, [r0, 4])    # r1 = m                ** m = int(math.log(n)/math.log(2))

    mov(r2, 0)          # r2 = l
    mov(r4, 1)
    mov(r9, r4)         # r9 = l2               ** l2 = 1
    label(OUTER)        #                       ** for l in range(m)
    push({r1, r2})
    mov(r4, r9)
    mov(r5, r4)         # r5 = l1               ** l1 = l2
    add(r4, r4, r4)     #                       ** l2 <<= 1
    mov(r9, r4)         # Save l2
    push({r2})
                        #                       ** u = 0j+1 copy initial value to variable
    mov(r0, r8)         # &scratch
    ldr(r0, [r0, 20])   # &complex_scratchpad
    mov(r1, r0)
    mov(r2, 8)
    mov(r3, 0)
    bl(CCOPY)           #                       ** u = 0j+1
                        #                       ** c = roots[l]
    pop({r2})           # r2 = l
    mov(r3, 3)
    lsl(r2, r3)         # r2 = l as byte offset
                        # r0 = &complex_scratchpad (dest addr)
    mov(r3, r8)         # &scratch
    ldr(r3, [r3, 16])   # Byte offset from start of scratchpad into start of roots
    add(r1, r3, r0)     # r1 = &roots (source addr)
    mov(r3, r2)         # Byte offset of l
    mov(r2, 16)         # Byte offset into c
    bl(CCOPY)           #                       ** c = roots[l]
    mov(r1, r2)         # Byte offset into c for conjugate
    mov(r2, r10)        # Control
    mov(r6, 1)
    and_(r2, r6)        #                       ** if Control == Forward: c.imag = -c.imag
    cmp(r2, 1)
    it(eq)
    bl(CONJUGATE)       # Conjugate C if forward

    mov(r2, 0)          # r2 = j
    mov(r1, r5)         # r5 = l1
    label(INNER1)       #                       ** for j in range(l1)
    push({r1, r2})      # Preserve r2 until DOMATHS

    mov(r0, r8)
    ldr(r1, [r0, 0])    # r1 = length, r2 (i) = j
    label(INNER2)       #                       ** for i in range(j, length, l2)

    bl(DOMATHS)         # The core of the DFT
                        # r2 = i
    mov(r0, r9)
    add(r2, r2, r0)
    cmp(r2, r1)
    blt(INNER2)         # ! for i in range(j, length, l2)

                        #                       ** u = (u*c)/2**BITSCALE   
    mov(r0, r8)         # &scratch
    ldr(r0, [r0, 20])   # &complex_scratchpad
    mov(r1, 8)          # u
    mov(r2, r1)
    mov(r3, 16)         # c
    bl(CMUL)            # ! u = (u*c)
    pop({r1, r2})
    add(r2, 1)
    cmp(r2, r1)
    blt(INNER1)         # ! for j in range(l1)
    
    pop({r1, r2})
    add(r2, 1)
    cmp(r2, r1)
    blt(OUTER)          # !for i in range(m)
# scale if forward
    mov(r2, r10)        # Control
    mov(r1, 1)          # bit 0: forward transform
    tst(r2, r1)
    beq(DFTDONE)        # Reverse transform
# scaling
    mov(r0, r8)         # &scratch
    ldr(r4, [r0, 0])    # Length
    ldr(r1, [r0, 8])    # &real
    ldr(r2, [r0,12])    # &imag
    ldr(r3, [r0,20])    # &cmplx
    ldr(r3, [r3,48])    # Multiplier
    mov(r6, r1)         # Save &real
                        #                       ** for i in range(n):
    label(SCALE01)
    ldr(r5, [r1, 0])    # Real                  ** nums[i] /= n
    bl(FSCALE)          # r5 = r5*r3
    str(r5, [r1, 0])
    ldr(r5, [r2, 0])    # Imag
    bl(FSCALE)          # r5 = r5*r3
    str(r5, [r2, 0])
    add(r1, 4)
    add(r2, 4)
    sub(r4, 1)
    cmp(r4, 0)
    bge(SCALE01)        #                       ** ! for i in range(n):
    label(DFTDONE)
    pop({r8, r9, r10})



if __name__ == '__main__':

    length = 2048 # size of synthetic dataset
    cycles = 30 # complete cycles in sampling window -> freq bin in output
    mydata = [math.sin(cycles*2*pi*x/length) for x in range(length)] # create some data

    #print(mydata)
    result = simpledft(mydata) 
    print(result)

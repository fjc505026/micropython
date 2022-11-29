#===============================================================#
#   HMAC SHA1 ALGORITHM IMPLEMENTAION FOR INEOS
#===============================================================#
import struct
import gc



class sha1:

    def __init__(self):
        
        # Init hash values (these init values are pre-defined for sha1)
        self.h0 = 0x67452301
        self.h1 = 0xEFCDAB89
        self.h2 = 0x98BADCFE
        self.h3 = 0x10325476
        self.h4 = 0xC3D2E1F0

        self.msg_length = 0
        self.bit_length = 0

    def __left_shift(self, n, b):
        return ((n << b) | (n >> (32 - b))) & 0xffffffff  #S^n(X) = (X << n) OR (X >> 32-n). Circular left shift

    def sha1_calculation(self, message):

        self.h0 = 0x67452301
        self.h1 = 0xEFCDAB89
        self.h2 = 0x98BADCFE
        self.h3 = 0x10325476
        self.h4 = 0xC3D2E1F0
        self.msg_length = len(message)
        self.bit_length = self.msg_length * 8

        # Add '1' at the end of the message
        message += b'\x80'

        # Pad with zeros so that length will be 56 bytes ( reserve 2 word length to append length. (64byte - 8byte = 56 bytes))
        message += b'\x00' * ((56 - (self.msg_length + 1) % 64) % 64)

        # Append 2 word representation of the input message length to right end of the message
        message += struct.pack(b'>Q', self.bit_length)

        # break message into 512-bit chunks
        for i in range(0, len(message), 64):
            w = [0] * 80
            # break chunk into sixteen 32-bit big-endian words w[i]
            for j in range(16):
                w[j] = struct.unpack(b'>I', message[i + j*4:i + j*4 + 4])[0]
            # Extend the sixteen 32-bit words into eighty 32-bit words:
            for j in range(16, 80):
                w[j] = self.__left_shift(w[j-3] ^ w[j-8] ^ w[j-14] ^ w[j-16], 1)
        
            # Initialize hash value for this chunk:
            a = self.h0
            b = self.h1
            c = self.h2
            d = self.h3
            e = self.h4

            for i in range(80):
                if 0 <= i <= 19:            
                    f = d ^ (b & (c ^ d))   # Use alternative 1 for f from FIPS PB 180-1 to avoid ~
                    k = 0x5A827999          
                elif 20 <= i <= 39:         
                    f = b ^ c ^ d
                    k = 0x6ED9EBA1
                elif 40 <= i <= 59:         
                    f = (b & c) | (b & d) | (c & d) 
                    k = 0x8F1BBCDC
                elif 60 <= i <= 79:         
                    f = b ^ c ^ d
                    k = 0xCA62C1D6
        
                a, b, c, d, e = ((self.__left_shift(a, 5) + f + e + k + w[i]) & 0xffffffff, 
                                a, self.__left_shift(b, 30), c, d)
        
            # sAdd this chunk's hash to result so far:
            self.h0 = (self.h0 + a) & 0xffffffff
            self.h1 = (self.h1 + b) & 0xffffffff 
            self.h2 = (self.h2 + c) & 0xffffffff
            self.h3 = (self.h3 + d) & 0xffffffff
            self.h4 = (self.h4 + e) & 0xffffffff
            del w
        
        
        #print("calling gc")
        gc.collect()
        # Produce the final hash value (big-endian):
        return '%08x%08x%08x%08x%08x' % (self.h0, self.h1, self.h2, self.h3, self.h4)

sha1_key = sha1()

    







    


    



#Title:
# CAN700 Diagnostic tool 
#revision A

#Description
# Check the Can communication on P bus
# Bypassing the ECU and turning the Bull Bar lights directly

#Hardware:
# MicroPython Jr Rev 2

from array import *
from UDS_UNLOCK import calculate_key_sha1
from pyb import CAN
from UDS_TL import *
import UDS_TL
#import hashlib
from binascii import hexlify


fileList=["S467_TLCMC_FLSDRV.hex","S467_TLCMC_C002.hex","S467_FP.hex" ,"S467_EOL.hex"]

checksomFileName= "checksom.txt"

CRClist=[ 0xB8213B35, 0x8D182239, 0x25ECB728, 0x25ECB728]

StartAdd= [0x5000, 0xFC00, 0xFE00, 0xFE00]

ADDBYTES = 4
CHECKSOMSIZE = 4

ProgSize= [0xAC00,0x200,0x200,0x200]


fileStatus= [False,False,False,False]

PADDING = 0xFF



arrayTemp = [0xFF for i in range(514)]
seedArray = [0 for i in range(18)]
keyArray  = [0 for i in range(18)]

#CAN ID's:
DiagResponseId    = 0x63B       #INEOS
DiagReqId         = 0x6BB       #INEOS

#Definitions

sysEN = 1
printMessage = 0        #print processed message 



SelectOption = True
userDiagOption = 0
option = 0
x = 0
lastTimePr2=0
lastTimePr1=0

lasttimepressed1 = 0
lasttimepressed2 = 0

DIAGINEOSECU    =  1  
FLASHINEOSECU   =  2

MAXDIAGOPTIONS =   2

NOMOFFILES = 2

HexFileCheckDone = 1

MAXPACKETSIZE = 512
OK = 1
ERROR = -1

#Setup Tester:

CAN1toComm = 0
CAN2toComm = 1


# Variables
SeedToSend = 0


#states
Idle = 0
reqSeed  = 1
sendKey  = 2
resetECU = 3
eraseMem = 4
reqDL    = 5
transferData = 6
reqTrExit= 7
checkCksm= 8
resetFinal=9
programmSession = 10 
DisNorComm = 11 
ExtSession=12
finish = 13
PrFgrPrint= 14
chkpgmDependency = 21
toCANalyzer = 22
submitSignature = 23
verifyApplication = 24


IOByID = 14

errorState=19
waitingForRep=20
WDTforReflCECU = 0 
WDTforDiagEng = 0

#Flags
EngDiagEnable = 0
EnginDiagState=Idle

diagEnable    = 0
ReflashEnable = 0
InBootL= 0

PROG = 0
ERASE= 1

APPSTART=1
BLSTART= 0

startFrom = 0

UnlockDest = PROG


BootLoaderState = Idle
nextState = Idle

filesSent = 0       

PRINTLOG = 0
printError=0 

TestReza = 0


timerTick_1ms    = 0
timerTick_10ms   = 0
timerTick_100ms  = 0
timerTick_1000ms = 0

timerTick_Seconds = 0

CYCLE_TIME = 1000
timerTick_100mSeconds= 0
timerTick_msec= 0



# LED Setup
grnLED = pyb.LED(1)
redLED = pyb.LED(2)
bluLED = pyb.LED(3)
BleLEDToggle100ms = 0

CAN1 = pyb.CAN(2)
CAN2 = pyb.CAN(1)

udsTl2 = UDS_TL.UDS_TransportLayer( CAN2, DiagReqId, DiagResponseId )

# CAN1 Setup
if(CAN1toComm ==1):    
    CAN1.init( pyb.CAN.NORMAL, extframe = False, prescaler = 4, sjw = 1, bs1 = 14, bs2 = 6 )
    CAN1.setfilter( 0, CAN.LIST16, 0, ( 0, DiagReqId, DiagResponseId, 0) )
    
    
if(CAN2toComm ==1):     
     CAN2.init( pyb.CAN.NORMAL, extframe = False, prescaler = 4, sjw = 1, bs1 = 14, bs2 = 6 )
     CAN2.setfilter( 0, CAN.LIST16, 0, ( 0, 0, DiagResponseId, 0))
     CANSTB2 = pyb.Pin( 'CANSTB1', pyb.Pin.OUT_PP )
     CANSTB2.low()
    

# Input Switches
SW_1 = pyb.Pin('SWITCH1', pyb.Pin.IN, pyb.Pin.PULL_UP)
SW_2 = pyb.Pin('SWITCH2', pyb.Pin.IN, pyb.Pin.PULL_UP)

# Timer Setup
def timerCallback( timer ):
    global timerTick_1ms    
    if( sysEN == 1 ):
        timerTick_1ms += 1

timer = pyb.Timer( 1, freq = 1000 )
timer.callback( timerCallback )

# Button One Setup
def buttonCallback1( button1 ):
        
    global timerTick_100mSeconds
    global lastTimePr1
    
    if timerTick_100mSeconds > lastTimePr1 +2 :     #200 ms debounce time
        lastTimePr2 = timerTick_100mSeconds
        
        global userDiagOption            
        global x

        if userDiagOption == 0 and x != 0:
            # print("Select button has been pressed, selected option is : ", x , "\n\n")  
            userDiagOption = x  
            # print(SW_1.value())         
    

button1 = pyb.ExtInt( SW_1, pyb.ExtInt.IRQ_FALLING, pyb.Pin.PULL_UP, buttonCallback1 )

# Button Two Setup
def buttonCallback2( button2 ):  
       
    global option
    global timerTick_100mSeconds
    global lastTimePr2
    global x
    global userDiagOption

    if timerTick_100mSeconds > lastTimePr2 +2 :     #200 ms debounce time
        lastTimePr2 = timerTick_100mSeconds
        
        if userDiagOption == 0 : 
            option =1
            if x>= MAXDIAGOPTIONS :
                x = 1 
            else:
                x += 1
    

button2 = pyb.ExtInt( SW_2, pyb.ExtInt.IRQ_RISING, pyb.Pin.PULL_DOWN, buttonCallback2 )


# Timer2 Setup
def timerCallback( timer2 ):
    global timerTick_100mSeconds 
    timerTick_100mSeconds +=1

    if  BleLEDToggle100ms == 1:
        bluLED.toggle()
    
timer2 = pyb.Timer( 2, freq = 10 )
timer2.callback( timerCallback )


def transferToECU(block, blNumber):
    resReceived = 0
    global arrayTemp 
    global BleLEDToggle100ms
    global timerTick_100mSeconds

    BleLEDToggle100ms = 0
    arrayTemp[0] = 0x36     #transfer data command
    arrayTemp[1] = blNumber
    ll = len(block)

    if ll <512 :        #Non Max size packet
        
        lastblock = [0xFF for i in range(ll +2)]
        lastblock[0] = 0x36     #transfer data command
        lastblock[1] = blNumber
        for i in range(ll):
            lastblock[2+i] = block[i]

        response = Tx_CAN(lastblock)

    else:
        for i in range (512):
            arrayTemp[2 +i] = block[i]    
        
        response = Tx_CAN(arrayTemp)

    if response != None :
        
        if (response[0] == 0x76 and response[1] == blNumber):
            resReceived = 1            
            return blNumber
    tstamp = timerTick_100mSeconds
    while (resReceived == 0 and tstamp > timerTick_100mSeconds -100) : #10 sec WDT
        if( CAN2.any(0)):
            response = CAN2.recv(0)
            # print(response[3])
            if (response[0] == DiagResponseId and response[3][1] == 0x76 and response[3][2] == blNumber):
                resReceived = 1
        pyb.delay(1)

    BleLEDToggle100ms = 0
    bluLED.off()
        

    if(resReceived ==1):
        print("packet sent successfully, PNUM: " , blNumber)
        return blNumber
    else:
        print("Timeout receiving response for packet number: " , blNumber)
        return ERROR
    

#------------------------------------------------------------------#
#---- CAN2 Transmit and wait for response
#------------------------------------------------------------------#
def Tx_CAN( frame ):
    try:
        global BleLEDToggle100ms
        BleLEDToggle100ms = 1
        frameTryCount = 5
        while( frameTryCount > 0 ):
            udsTl2.WriteMessage( frame )
            for i in range(0,200):
                udsTl2.Run()
                pyb.delay(1)

            responseFrame = udsTl2.ReadMessage()
            
            if( responseFrame == None ):
                print( "Frame receive error try: ", frameTryCount - 4 )
                frameTryCount = frameTryCount - 1
            else:
                frameTryCount = 0
        

        if( responseFrame != None ):
            
            if( responseFrame[ 0 ] == 0x7F and responseFrame[ 2 ] != 0x78 and printError == 1):
                foundNRC = 0
                for NRCIndex in range( len( UDS_NRC_DEFINES ) ):
                    if( responseFrame[ 2 ] == UDS_NRC_DEFINES[ NRCIndex ][ 0 ] ):
                        print( "\nError, negative response received: " )
                        print( UDS_NRC_DEFINES[ NRCIndex ][ 1 ] )
                        foundNRC = 1
                if( foundNRC == 0 ):
                    print( "\nError, unknown negative response received" )
        else:
            print( "\nError receiving data, no data received ")

        BleLEDToggle100ms = 0
        bluLED.off()

        return responseFrame
    except OSError as er:
        print ("[ERR] CAN ",er)
        pass

# Send CAN Message
def sendCANMessage( msgID, message, CANtosend ):
    try:
        CANtosend.send( message, msgID)
    except OSError as er:
        print( " *** CAN MSG FAILED TO SEND *** " )
        redLED.on()

def ProcessCANmes(dataRecv): 
    global BootLoaderState
    global InBootL
    global SeedToSend
    global EnginDiagState
    global UnlockDest
    global startFrom
    try:
        ReadID = dataRecv[0]
        IDinHex = hex(ReadID)
        data = dataRecv[3]
        dlc = len(data)
                            
        
        if(ReadID == DiagResponseId ):
                                    
            if(data[1]== 0x50 and data[2]==0x03): 
                #print("PRGPRGPRGPRGPRGPRGPRG----Extended Session----PRGPRGPRGPRGPRGPRGPRG\n\n") 
                if InBootL == 0:
                    BootLoaderState = DisNorComm
                elif startFrom == BLSTART:
                    BootLoaderState = programmSession

                else:
                    BootLoaderState = reqSeed
                    

            elif(data[1]== 0x68 and data[2]==0x01):
                #print("SSSSSSSSSSSSSSSS^^^^^^^^----SEED received----^^^^^^^^SSSSSSSSSSSSSSSS")                                
                BootLoaderState = programmSession                
            
            #Go to Programming session
            elif data[1]== 0x67 and data[2]==0x08 :

                print("UUUUUUUUUUUU----ECU unlocked----UUUUUUUUUUU\n\n") 
                
                # if InBootL == 0:                    
                #     BootLoaderState = programmSession
                
                # else:                       
                BootLoaderState = eraseMem                
                                          

            #Rest ECU
            elif(data[1]== 0x50 and data[2]==0x02): 
                #print("PRGPRGPRGPRGPRGPRGPRG----Programming Session----PRGPRGPRGPRGPRGPRGPRG\n\n") 
                if InBootL == 0:
                    InBootL = 1
                    BootLoaderState = programmSession

                BootLoaderState = reqSeed               
                

            elif(data[1]== 0x51 and data[2]==0x01): 
                print("^^^^^^^^^^^^^^^^^^^^ECU RESET^^^^^^^^^^^^^^^^^^^^\n\n") 
                pyb.delay(100)
                if InBootL == 0:
                    InBootL = 1
                else:
                    InBootL = 0               
                    BootLoaderState = finish
                
            elif(data[1] == 0x6E and data[2]== 0xF1 and data[3]== 0x07):      #positive response fingerprint
                print ("posive resp from print finger print")
                BootLoaderState = eraseMem
                
            #memory erased
            elif(data[1]== 0x71 ): 
                #check progg pre condition
                if(data[2]== 0x01  and data[3]== 0xFF  and data[4]== 0x01 ):
                    print("TBD")
                #Ckeck Memory
                elif(data[2]== 0x01  and data[3]== 0x02  and data[4]== 0x02 ):
                    if data[5]== 0x00 :
                        BootLoaderState = resetFinal

                    elif data[5]== 0x01:
                        print("\n\n---- CRC doesn't match---\n\n")
                        BootLoaderState = errorState
                
                #Erase Memory
                elif (data[2]== 0x01  and data[3]== 0xFF  and data[4]== 0x00 ):
                    
                    #print("---- requesting Download ----\n\n")
                    BootLoaderState = reqDL


            elif(data[1]== 0x74 and data[2]==0x20):
                
                #print("Requesting Transfer data accepted\n\n")
                BootLoaderState = transferData

            #transfer exit positive resp
            elif data[1]== 0x76 :
                print("---- transfer  done,  ----\n\n")
                BootLoaderState = reqTrExit

            #transfer exit positive resp
            elif data[1]== 0x77 :
                #print("---- transfer Exit done, checking checksom ----\n\n")
                BootLoaderState = checkCksm

            elif data[1]== 0x7F and data[3]!= 0x78:
                print("---- Negative response: ----\n\n")

        
                        
      
    except OSError as er:
        print("Error 456")
        redLED.on()

def ReflashECU():
    global BootLoaderState
    global nextState
    global HexFileCheckDone
    global ReflashEnable
    global filesSent
    global WDTforReflCECU
    global InBootL
    global Seedtosend
    global CRClist
    global ProgSize
    global startFrom
    # global keyArray
    # global seedArray

        
    if HexFileCheckDone == 0:
        result = fileCheck()
        if result != OK:
            print("Hex File Error, Reflashing stoped")
            redLED.on()
            ReflashEnable = 0
            return ERROR
        else:
            HexFileCheckDone = 1
            result = checksmRead()
            if result != OK:
                print("Checksom File Error, Reflashing stoped")
                redLED.on()
                ReflashEnable = 0
                return ERROR

    
    if (BootLoaderState == Idle):
        print("------- Send Default Session ------")
        msg = array('B',[2, 0x10, 0x01, 0 ,0 ,0 ,0 ,0 ])
        #wake up
        sendCANMessage(DiagReqId, msg , CAN2)
        pyb.delay(50)

        #wake up
        sendCANMessage(DiagReqId, msg , CAN2)
        pyb.delay(50)

        #wake up
        sendCANMessage(DiagReqId, msg , CAN2)
        pyb.delay(50)

        chck = RDBID_check(DiagReqId, DiagResponseId)
        if(chck == ERROR):
            for i in range (10):
                redLED.toggle()
                pyb.delay(100)
            print("The Cabin ECU is not Responding\n\n")
            BootLoaderState = errorState
            redLED.on()
            return
        
        print(startFrom)     
        BootLoaderState = ExtSession

            
    elif(BootLoaderState == ExtSession):
        #print("DISDIS-----dISABLING NORMA COMMUNICATIONS--------DISDISDIS")
        print("\n------------- Send Extended Session  ---------------\n")
        msg = array('B',[2 ,0x10, 0x03 , 0 , 0, 0, 0, 0])
        sendCANMessage(DiagReqId, msg , CAN2)
        pyb.delay(1)
        BootLoaderState = waitingForRep
        WDTforReflCECU = timerTick_100mSeconds
                

    elif(BootLoaderState == DisNorComm):
        #print("DISDIS-----dISABLING NORMA COMMUNICATIONS--------DISDISDIS")

        print("\n-----------Send Preprogramming Check----------\n")
        msg = array('B',[2 ,0x3E, 0x80 , 0 , 0, 0, 0, 0])
        sendCANMessage(DiagReqId, msg , CAN2)
        pyb.delay(150)
        
        # Check programming pre-conditions
        msg = [0x31, 0x01 , 0x02 , 0x03]
        pgm_precondition_resp = Tx_CAN(msg)
        
        if pgm_precondition_resp[0] == 0x71:
            if pgm_precondition_resp[4] == 1:
                print(" Error - Precondition check failed!!")
                print("Error code 01 - Engine speed is not zero")
            elif pgm_precondition_resp[5] == 2:
                print(" Error - Precondition check failed!!")
                print("Error code 02 - Vehicle speed is >3km/hr")
            elif pgm_precondition_resp[6] == 3:
                print(" Error - Precondition check failed!!")
                print("Error code 03 - IGN is start position")
            elif pgm_precondition_resp[7] == 4:
                print(" Error - Precondition check failed!!")
                print("Error code 04 - Under/Above programming voltage (11.5V- 16V)")
            else:
                print("No Failure recorded for pre-programming checks.")
        pyb.delay(150)
        
        msg = array('B',[2 ,0x85, 0x82 , 0 , 0, 0, 0, 0])
        sendCANMessage(DiagReqId, msg , CAN2)
        pyb.delay(500)
        
        print("-----------Send Enable Rx and Tx----------")
        msg = array('B',[3 ,0x28, 0x01 , 3 , 0, 0, 0, 0])       #check INEOS BL for 28 81 3 or 28 81 1
        sendCANMessage(DiagReqId, msg , CAN2)
        pyb.delay(1)
        BootLoaderState = waitingForRep
        WDTforReflCECU = timerTick_100mSeconds
            
    elif(BootLoaderState == reqSeed):

        print("\n-----Send Turn On Debug Command--------\n")

        msg = [0x31, 0x01 , 0x06, 0x66, 0x1]
        response = Tx_CAN(msg) 

        pyb.delay(10)

        print("------------Send Programming Request Seed ------------------")
        #print("RQSRQS-----start sending Request seed command--------RQSRQS")
        msg = [0x27 , 7]
        seedArray = Tx_CAN(msg) 
        print("\nseed response array is: ",seedArray)
        
        # KeyL4 = [0xF1,0xFF,0x85,0xD2,0xAC,0x5F,0x27,0x2B,0xE6,0xFA,0x2F,0xED,0x3B,0xE9,0x77,0xEE] 
        # keyBin= array('B', KeyL4)  
         
        seed = seedArray[2:]  
        key =calculate_key_sha1(seed)
        print(key)
        for i in range(16):
            Hexvalue =  key[2*i : (2*i +2)]       
            keyArray[i+2] = int(Hexvalue,16 )     #TBD key generation must be replaced
        keyArray[0] = 0x27
        keyArray[1] = 0x08              # key subfunction
        
        
        # seedBin = array('B', seed)
        
        # hash = hashlib.sha256(keyBin)
        # print("step1\n")        
        # # m= hashlib.sha1("it is a test again")
        # # print("step1\n")       
        # #hash.update(KeyL4)
        
        # hash.update(seedBin)
        # print("step2\n")
        
        # key = hexlify(hash.digest())
        # print("step3\n")
        
        
        # print("\nkey is: ",key) 
        # for i in range(16):
        #     keyArray[i+2] = key[i]      #TBD key generation must be replaced
        # keyArray[0] = 0x27
        # keyArray[1] = 0x08              # key subfunction
         
        #computeKey(seedArray,keyArray)
                       
        msg = Tx_CAN(keyArray)
        
        if (msg[0] == 0x67 and msg[1]== 0x08):      #positive response
            BootLoaderState = PrFgrPrint
                        
        else:            
            BootLoaderState = errorState
            print("negative response 0x27, Invalid or bad key \n")        
                
        pyb.delay(1)
          
    elif(BootLoaderState == PrFgrPrint):
        
        fgPrnt = [0 for i in range(33)]
        fgPrnt[0] = 0X2E
        fgPrnt[1] = 0xF1
        fgPrnt[2] = 0x07
        
        fgPrnt[3] = 0x22
        fgPrnt[4] = 0x06
        fgPrnt[5] = 0x21
        
        msg = Tx_CAN(fgPrnt)
         
        if (msg[0] == 0x7F and msg[1]== 0x2E and msg[2]== 0x78):      #pending
            print("fingerprint reply pending")
            BootLoaderState = waitingForRep
            WDTforReflCECU = timerTick_100mSeconds  
        
        elif (msg[0] == 0x6E and msg[1]== 0xF1 and msg[2]== 0x07):      #positive response
                BootLoaderState = eraseMem    
        else:            
            BootLoaderState = errorState
            print("negative response 0x2E \n")        
       

    elif(BootLoaderState == programmSession):
        print("\n-----Sending Programming session command----\n")
        msg = array('B',[2, 0x10, 0x02, 0 ,0 ,0 ,0 ,0 ])
        print(msg)
        sendCANMessage(DiagReqId, msg , CAN2)
        pyb.delay(50)
        BootLoaderState = waitingForRep
        WDTforReflCECU = timerTick_100mSeconds
        
                

    elif(BootLoaderState == eraseMem):        
        print("Erase ECU Memory File number : " , filesSent+1 )
        AddressErase = StartAdd[filesSent]
        print("address to erase is :" , hex(AddressErase))

        EraseLen = ProgSize[filesSent]
        print("Size of block to erase is :" , hex(EraseLen))
        
        ersMsg  = [0 for i in range(13)]  
        ersMsg[0] = 0x31
        ersMsg[1] = 0x01
        ersMsg[2] = 0xFF
        ersMsg[3] = 0x00
        ersMsg[4] = 0x44                      
        
        for i in range(ADDBYTES):
            print("\n",i)
            ersMsg[5+i] = ((AddressErase >> (ADDBYTES-i-1)*8 ) & 0xFF)
            ersMsg[9+i] = ((EraseLen >> (ADDBYTES-i-1)*8 ) & 0xFF)
            
        msg = Tx_CAN(ersMsg) 
        if (msg[0] == 0x71 and msg[1] == 0x01 and msg[2] == 0xFF and msg[3] == 0x00 and msg[4] == 0x00 ) :      #positive response or pending
            BootLoaderState = reqDL 
        elif (msg[0] == 0x7F and msg[2] == 0x78):
            BootLoaderState = waitingForRep
            WDTforReflCECU = timerTick_100mSeconds           
        else:
           print("Error in erasing memory, negative response" ,msg)
           BootLoaderState = errorState
           

    elif(BootLoaderState == reqDL):        
        #print("Requesting Download")
        print("Reflash File number : " , filesSent+1)
        AddressErase = StartAdd[filesSent]
        print("address to flash is :" , hex(AddressErase))

        EraseLen = ProgSize[filesSent]
        print("Size of block to flash is :" , hex(EraseLen))
        
        frame=[0x34, 0x00, 0x44, 0x00, 0x00, 0x00 , 0x00, 0x00, 0x00, 0x00 ,0x00]  
        for i in range(ADDBYTES):
            frame[3+i] =(AddressErase >>(ADDBYTES-i-1)*8 ) & 0xFF
            frame[7+i] =(EraseLen >> (ADDBYTES-i-1)*8 ) & 0xFF         
              
        response = Tx_CAN( frame )
        if (response[0]== 0x74):        
            BootLoaderState = transferData 
        else:
            BootLoaderState = errorState   

    elif(BootLoaderState == transferData):
                              
        result = writeFW(fileList[filesSent])            
        if(result != ERROR):            
            print("Transfer done\n\n")        
        else:
            print("Error Transfering data") 
            BootLoaderState =  errorState
        #BootLoaderState = waitingForRep
        pyb.delay(100)      #in case of receiving 0x7F 0x36 0x78 which is not actually negative response
        BootLoaderState = reqTrExit

    elif(BootLoaderState == reqTrExit): 
        print("PPPP-----Requesting Transfer Exit----PPPPP\n\n\n")
        msg = array('B',[1, 0x37, 0, 0 ,0 ,0 ,0 ,0 ])
        
        sendCANMessage(DiagReqId, msg , CAN2)
        pyb.delay(50)
        BootLoaderState = waitingForRep
        WDTforReflCECU = timerTick_100mSeconds

        
    elif(BootLoaderState == checkCksm): 
        print("CHCCHCHC-----Checksum check----CHCCHCHC\n\n\n")
        
        frame=[0x31, 0x01, 0x02, 0x02, 0x00, 0x00, 0x00 ,0x00] 
        checksome = CRClist[filesSent]
        for i in range(CHECKSOMSIZE):
            frame[4+i] = ((checksome >> (CHECKSOMSIZE-i-1)*8 ) & 0xFF)
            
        data = Tx_CAN( frame ) 

        if(data[0]== 0x71 and data[1]== 0x01  and data[2]== 0x02  and data[3]== 0x02 ):
                    if data[4]== 0x01 :
                        BootLoaderState = errorState
                        print("\n\n---- CRC doesn't match---\n\n")
                    elif data[4]== 0x00:                    
                        
                        print("CRC match Reflash File " , filesSent+1 , " done\n\n")
                        filesSent += 1
                        if(filesSent < NOMOFFILES):
                            BootLoaderState = eraseMem
                        else:
                            BootLoaderState = toCANalyzer
        else:
            BootLoaderState = errorState
            print("negative response 0x31 \n")

    elif (BootLoaderState == toCANalyzer):
        print(" !!!! Attention !!!!!")
        print("\nProgramming dependency check finished.")
        print("\nProceed the rest of teh steps from CANalyzer now....")

        while 1:
            print("Tester Present")
            frame = [0x10, 0x03]
            msg = Tx_CAN( frame )
            pyb.delay(500)

        BootLoaderState = finish

    elif(BootLoaderState == chkpgmDependency):
        print("Check Programming Dependency")
        frame = [0x31, 0x01, 0xFF, 0x01]
        data = Tx_CAN(frame)
        if data[0] == 0x71 and data[1]== 0x01  and data[2]== 0xFF  and data[3]== 0x01:
            if data[4] == 0x01:
                BootLoaderState = errorState
                print("\n-----Programming Dependency check failed-----\n")
            elif data[4] == 0x0:
                print("Programming dependency check passed. ")
                BootLoaderState = toCANalyzer
        else:
            BootLoaderState = errorState
            print("negative response 0x31 \n")
    

    elif (BootLoaderState == toCANalyzer):
        print(" !!!! Attention !!!!!")
        print("\nProgramming dependency check finished.")
        print("\nProceed the rest of teh steps from CANalyzer now....")

        while 1:
            print("Tester Present")
            frame = [0x10, 0x03]
            msg = Tx_CAN( frame )
            pyb.delay(500)

        BootLoaderState = finish

    elif(BootLoaderState == resetFinal):
        #Reset ECU
        print("Reset ECU")
        frame = [0x11 , 0x01]
        msg = Tx_CAN( frame )
        
        if(msg[0]== 0x51):
            frame= [0x10, 0x03]
            msg = Tx_CAN( frame )
            
            if(msg[0]== 0x50 and msg[1]== 0x03):
                frame = [0x28,0x80,0x03]        #check INEOS for 0x01 or 0x03  TBD           
                pyb.delay(50) 
                msg = Tx_CAN( frame )
                
                pyb.delay(50)
                frame= [0x10, 0x01]
                msg = Tx_CAN( frame )
                
        
        pyb.delay(50) 

        BootLoaderState = finish
      

    elif(BootLoaderState == waitingForRep):
        if timerTick_100mSeconds > WDTforReflCECU + 100 :       #10 second WDT
            WDTforReflCECU = 0
            BootLoaderState = errorState
            print(" Timeout getting resonse from ECU \n\n")

     

    elif(BootLoaderState == finish):
        #Reflash finished
                
        grnLED.on()
        print("----------------------------------------------------\n")
        print("----------- INEOS ECU REFLASHED SUCCESSFULLY--------\n")
        print("----------------------------------------------------\n\n\n")
        ReflashEnable = 0

        #version_check()
        return

    if(BootLoaderState == errorState):
        print("Error in Reflashing")
        for i in range(10):
            redLED.toggle()
            pyb.delay(100)
        print("Reset ECU")
        frame = [0x11 , 0x01]
        msg = Tx_CAN( frame )
        redLED.on()
        ReflashEnable = 0
        InBootL = 0
        
# Get the debug info as an array and convert it to string
def decodeVersion(data):
    data = data[3:]
    version = "".join(chr(entry) for entry in data)
    return version

# Check the SW & bootloader version on the ECU
def version_check():
    frame = [0x10, 0x01]
    data = Tx_CAN(frame)

    frame = [0x22, 0xF1, 0x94 ]   
    data = Tx_CAN(frame)
    if data[0] == 0x62:
        print("SW version on ECU: ", decodeVersion(data))
    
    pyb.delay(100)
    frame = [0x22, 0xFD, 0x1D]
    data = Tx_CAN(frame)
    if data[0] == 0x62:
        print("Bootloader version on ECU: ", decodeVersion(data))
        print("\n")

    

def RDBID_check(id, respID):
    
    global InBootL
    global startFrom

    counter = 0

    msg = array('B',[2, 0x10, 0x001, 0x00, 0 ,0 ,0 ,0 ])
    sendCANMessage(id, msg , CAN2)
    pyb.delay(500)
    msg = array('B',[2, 0x10, 0x01, 0x00, 0 ,0 ,0 ,0 ])
    sendCANMessage(id, msg , CAN2)
    pyb.delay(500)

    erroeCOde = ERROR

    while CAN2.any(0) :
        message = CAN2.recv(0)
        
        if( message[0] == respID ) and (message[3][1] == 0x50) and (message[3][2] == 0x01):
            erroeCOde = OK
 
    if erroeCOde == OK:
        msg = array('B',[3, 0x22, 0xF1, 0x86, 0 ,0 ,0 ,0 ])
        sendCANMessage(id, msg , CAN2)
        pyb.delay(500)
    
        
        while( CAN2.any(0)):
            message = CAN2.recv(0)
            if message[0] == respID :
                counter += 1
                if (message[3][1] == 0x7F) and (message[3][2] == 0x22):
                    InBootL = 1
                    startFrom = BLSTART
                    return BLSTART
                    
                     
    pyb.delay(50)
    if counter != 0:    
        return erroeCOde
    else:
        return ERROR
    

def selectDiag():
    global x
    global userDiagOption

    bluLED.off()
    grnLED.off()
    redLED.off()

    x = 1
       
    while userDiagOption == 0 :
        bluLED.on()
        pyb.delay(2000)
        bluLED.off()
        pyb.delay(200)
        i = x
        while (userDiagOption == 0 and i> 1)  :
            bluLED.on()
            pyb.delay(200)
            bluLED.off()
            pyb.delay(200)
            i -= 1
                   
    x = 0
    option = 0
    return

                
def diag(sel):
    global userDiagOption
    global ReflashEnable    
    global HexFileCheckDone 
    global BootLoaderState 
    global filesSent
    global option
    global BleLEDToggle100ms
    global EngDiagEnable

    
    print("\n The Diag option " , sel , "has been selected by user \n\n") 
    
    for i in range(sel) :
            grnLED.on()
            pyb.delay(500)
            grnLED.off()
            pyb.delay(500)

    bluLED.off()
    grnLED.off()
    pyb.delay(1000)

    if sel == DIAGINEOSECU:

        print("----------------------------------------------------\n")
        print("------------- Checking INEOS ECU Comm---------------\n")
        print("----------------------------------------------------\n")
        BleLEDToggle100ms = 1
        pyb.delay(4000)

        resp = RDBID_check(DiagReqId, DiagResponseId)

        BleLEDToggle100ms = 0
        bluLED.off()

        if(resp != ERROR):
            grnLED.on()
            print("----------------------------------------------------\n")
            print("--------------- INEOS ECU comm is OK----------------\n")
            print("----------------------------------------------------\n")
        else:
            for i in range (10):
                redLED.toggle()
                pyb.delay(100)
            redLED.on()
            
        
    elif sel == FLASHINEOSECU:

        ReflashEnable = 1
        HexFileCheckDone = 0
        BootLoaderState = Idle
        filesSent = 0  
        print("----------------------------------------------------\n")
        print("-------------- Reflashing INEOS TRM ECU -------------\n")
        print("----------------------------------------------------\n")  

        for i in range (40):   
            redLED.toggle()
            bluLED.toggle()
            grnLED.toggle()
            pyb.delay(100)

        redLED.off()
        bluLED.off()
        grnLED.off()

        pyb.delay(1000)

    else: 
        print("Option number not supported")

    userDiagOption = 0
    option = 0
    BleLEDToggle100ms = 0
    bluLED.off()
    return


def UDSlightDrive():

    global EnginDiagState
    global SeedToSend
    global InBootL
    global EngDiagEnable
    global timerTick_100mSeconds
    global WDTforDiagEng
    global BleLEDToggle100ms

    BleLEDToggle100ms =  1
    if(EnginDiagState == Idle):
        msg = array('B',[2, 0x10, 0x01, 0 ,0 ,0 ,0 ,0 ])
        #wake up
        sendCANMessage(EngDiagID, msg , CAN2)
        pyb.delay(500)

        #wake up
        print("Tester Present")
        msg = array('B',[2, 0x10, 0x03, 0 ,0 ,0 ,0 ,0 ])
        sendCANMessage(EngDiagID, msg , CAN2)
        pyb.delay(500)

        #wake up
        msg = array('B',[2, 0x10, 0x01, 0 ,0 ,0 ,0 ,0 ])
        sendCANMessage(EngDiagID, msg , CAN2)
        pyb.delay(500)

        
        print("EEEEEEEEEEEE-----start sending Extended session command--------EEEEEEEEEEE")
        #extended session
        msg = array('B',[2, 0x10, 0x03, 0 ,0 ,0 ,0 ,0 ])
        sendCANMessage(EngDiagID, msg , CAN2)
        pyb.delay(50)
        
        EnginDiagState = waitingForRep
        WDTforDiagEng = timerTick_100mSeconds
        nextState = reqSeed

    elif(EnginDiagState == ExtSession):
        #print("DISDISDISDIS---------dISABLING NORMA COMMUNICATIONS-----------DISDISDISDIS")
        print("--------------Send Extended Session ------------")
        msg = array('B',[2 ,0x10, 0x03 , 0 , 0, 0, 0, 0])
        sendCANMessage(EngDiagID, msg , CAN2)
        pyb.delay(1)
        EnginDiagState = waitingForRep
        WDTforDiagEng = timerTick_100mSeconds
        nextState = reqSeed
        

    elif(EnginDiagState == DisNorComm):
        print("DISDISDISDIS---------dISABLING NORMA COMMUNICATIONS-----------DISDISDISDIS")
        msg = array('B',[3 ,0x28, 0x81 , 1 , 0, 0, 0, 0])
        sendCANMessage(EngDiagID, msg , CAN2)
        pyb.delay(1)
        EnginDiagState = waitingForRep
        WDTforDiagEng = timerTick_100mSeconds
        nextState = reqSeed
    
    elif(EnginDiagState == reqSeed):

        print("-----start Turn On Debug Command--------")

        msg = array('B',[5 ,0x31, 0x01 , 0x06, 0x66, 0x1, 0, 0])
        sendCANMessage(EngDiagID, msg , CAN2)

        pyb.delay(1000)

        print("-----start sending Request seed command--------")
        if(InBootL == 0):
            msg = array('B',[2 ,0x27, 0x71 , 0 , 0, 0, 0, 0])
        else:
            msg = array('B',[2 ,0x27, 0x01 , 0 , 0, 0, 0, 0])
        sendCANMessage(EngDiagID, msg , CAN2)
        pyb.delay(1)
        EnginDiagState = waitingForRep
        WDTforDiagEng = timerTick_100mSeconds
        nextState = sendKey

    elif(EnginDiagState == sendKey):
        key = ((SeedToSend >> 5) & 0xFFFFFFFF)  | ((SeedToSend << 23) & 0xFFFFFFFF)
        key *= 7
        key ^= ( 0x53343432 & 0xFFFFFFFF )
        
        if(InBootL == 0):
            keyMsg = array('B',[6 ,0x27, 0x72 , ( key >> 24 ) & 0xFF ,  ( key >> 16 ) & 0xFF, ( key >> 8  ) & 0xFF, ( key       ) & 0xFF])
        else:
            keyMsg = array('B',[6 ,0x27, 0x02 , ( key >> 24 ) & 0xFF ,  ( key >> 16 ) & 0xFF, ( key >> 8  ) & 0xFF, ( key       ) & 0xFF])
                        
        sendCANMessage(EngDiagID, keyMsg , CAN2)
        pyb.delay(1)
        #print("key is: ", hex(keyMsg[0]) ,hex(keyMsg[1]) ,hex(keyMsg[2]) , hex(keyMsg[3]) , hex(keyMsg[4]) , hex(keyMsg[5]) , hex(keyMsg[6]))

        EnginDiagState = waitingForRep
        WDTforDiagEng = timerTick_100mSeconds

    elif (EnginDiagState == IOByID): 
           
        seq=[2,4,6,3,5,7,8]     #first left bullbar second right bullbar and then DR
        #for i in range(2,10):
        for i in seq:
            X16 = 0x0003
            X16 |= (1   << i)   & 0xFFFF            
            X4  =  X16         & 0xFF
            X5  = (X16 >> 8)   & 0xFF

            frame1=array('B',[0x10 , 0x08 , 0x2F, 0x05 , 0x00, 0x03 , X4, X5  ]) 
            frame2=array('B',[0x21 , 0xFF ,0xFF])
                      
            sendCANMessage(EngDiagID, frame1 , CAN2)
            pyb.delay(100)
            sendCANMessage(EngDiagID, frame2 , CAN2)
            #print("-----The bit number ", i , " has been selected\n\n")

            pyb.delay(4000)

        
        frame1=array('B',[0x04 , 0x2F, 0x05, 0x00, 0x00]) 
                      
        sendCANMessage(EngDiagID, frame1 , CAN2)
        pyb.delay(100)


        EnginDiagState = finish


    elif(EnginDiagState == waitingForRep):
        if timerTick_100mSeconds > WDTforDiagEng + 100 :       #10 second WDT
            WDTforDiagEng = 0
            EnginDiagState = errorState
            print(" Timeout getting reply from ECU \n\n")   

    elif(EnginDiagState == finish):
    #UDS driving lights has been finished
            
        grnLED.on()
        print("----------------------------------------------------\n")
        print("-------------- Diag number 3 finished --------------\n")
        print("----------------------------------------------------\n")
        EngDiagEnable = 0
        BleLEDToggle100ms = 0
        bluLED.off()
        EnginDiagState = Idle
        return

    if(EnginDiagState == errorState):
        print("Error in Diag Engine ECU")
        for i in range(10):
            redLED.toggle()
            pyb.delay(100)
        redLED.on()
        EnginDiagState = Idle
        EngDiagEnable = 0
        bluLED.off()
        BleLEDToggle100ms = 0
        InBootL =0
            

def diagFunction():

    bluLED.off()
    grnLED.off()

    for i in range (6):
        bluLED.toggle()
        pyb.delay(500)
    bluLED.off()
    print("Sending session request..")
    resp = RDBID_check(DiagReqId, DiagResponseId)
    print("Response is : ", resp)
    if(resp != ERROR):
        bluLED.on()
    else:
        for i in range (10):
            redLED.toggle()
            pyb.delay(200)
        redLED.off()
        pyb.delay(1000)

    for i in range (6):
        grnLED.toggle()
        pyb.delay(500)
    grnLED.off()
    resp = RDBID_check(EngDiagID, EngDiagResID)
    if(resp != ERROR):
        grnLED.on()
    else:
        for i in range (10):
            redLED.toggle()
            pyb.delay(200)
        redLED.off()
        pyb.delay(1000)        

                   
def fileTest(fname):
    try:
        with open(fname , 'r') as f1:          
            for line in f1:
                if PRINTLOG == 1 :
                    print(line)                
                bluLED.toggle()

    except OSError as er:
        ErrFlag = True
        redLED.on()
        print("Error reading line") 
        return 


def fileCheck():    
    ErrorCode = OK
    global BleLEDToggle100ms 
    global ProgSize
    global StartAdd
            
    try:
        for i in range (NOMOFFILES):
            LineNumber = 0
            address = 0 
            baseAddress = 0           
            numOfBytes = 0
            NumOfJumpAdd = 0
            nextaddress = 0            
            lastLine = False
            fileStatus[i] = True
            with open(fileList[i] , 'r') as f1: 
                BleLEDToggle100ms = 1                     
                for line in f1:
                    LineNumber += 1
                    if PRINTLOG == 1 :  
                        print(line)
                    lineStruct = hexFileParser(line)                    
                    if(lineStruct != None):                        
                        if PRINTLOG == 1 :
                            print(lineStruct)
                        #End of file received
                        if(lineStruct['linetype'] == 1):
                            lastLine = True
                            break            
                        #offset
                        elif(lineStruct['linetype'] == 2):
                            baseAddress = ((lineStruct['data'][0] <<8) | lineStruct['data'][1] )<<4
                            print (hex(baseAddress))
                            
                        #segment
                        elif(lineStruct['linetype'] == 4):
                            baseAddress = (((lineStruct['data'][0] <<8) | (lineStruct['data'][1] )) << 16)
                            print (hex(baseAddress))  
                            
                        #data record
                        elif(lineStruct['linetype'] == 0):
                            address = lineStruct['dataAddress'] + baseAddress
                            #first line of data                            
                            if(numOfBytes == 0):
                                nextaddress = address
                                startaddress = address
                            if address < nextaddress :
                                print(" Address Error, address less than previous address")
                                fileStatus[i] = False
                                break
                            elif nextaddress == address :                                
                                numOfBytes += lineStruct['lengOfData']      #counting data bytes
                                nextaddress = address + lineStruct['lengOfData']   #next address
                            else:       #there is gap in address
                                NumOfJumpAdd += 1
                                gapSize = address - nextaddress
                                numOfBytes += (gapSize + lineStruct['lengOfData'] )     #counting data bytes + gap
                                nextaddress = address + lineStruct['lengOfData']   #next address
            BleLEDToggle100ms = 0
            bluLED.off()

            print(" The Hex file number ", i+1 ," checked and result is:" , fileStatus[i],"\n\n")
            pyb.delay(1000)
            if (fileStatus[i] == True):
                print("The check of file -------" + fileList[i] +"  -------has been completed")
                print("\nTotal number of lines in file:  " , LineNumber ," Lines")
                print("\nTotal number of data bytes in file: " , numOfBytes)
                print("\nTotal number of gap in addresses in file: " , NumOfJumpAdd , "gaps \n\n\n\n")

                
                ProgSize[i] = numOfBytes
                StartAdd[i] = startaddress

                                
            else:
                print("\nError in Hex file " + fileList[i])
                ErrorCode = ERROR
                redLED.on()
                return ErrorCode  

    except OSError as er:
        ErrFlag = True
        redLED.on()
        print("Error reading Files") 
        ErrorCode = ERROR
        return ErrorCode 

     
    return ErrorCode
def checksmRead():

    lineNum = 0         
    try:
        with open(checksomFileName , 'r') as file1:            
            for line in file1:
                
                cksm = ""
                
                if(len(line) < 10):
                    print("The Checksom line length could not be less than 10")                    
                    return ERROR
                for c in range(2,10):
                    cksm += line[c]
                                               
                chksmHex = int(cksm,16)
                
                CRClist[lineNum] = chksmHex
                lineNum +=1
                if lineNum> 2:
                    break
        return OK
    except OSError as er:
        return ERROR


def writeFW(fname): 

    global BleLEDToggle100ms
    ErrFlag = False
    lastLine = False 
    record = [0xFF for i in range(512)]    
    
    index = 0
    totalByteSent = 0
    address = 0
    nextaddress = 0
    ReadyToSend = 0
    blockNumber = 0 

    print("---------------starting programming process-------------\n\n")
    with open(fname , 'r') as f1:
        BleLEDToggle100ms = 1          
        while(lastLine == False):           
            try:
                #line = f1.readline() 
                for line in f1:                                   
                    hexline = hexFileParser(line)
                    if(hexline != None):
                        
                        lineType = hexline['linetype']
                                                    
                        #data record
                        if(lineType == 0):
                            address = hexline['dataAddress']
                            
                            lineLen = hexline['lengOfData']
                            
                            lineData = hexline['data']
                            

                            if(totalByteSent == 0):     #first Data record
                                nextaddress = address                            
                                index = 0                            

                            if(nextaddress != address ):
                                
                                gapInAdd = address-nextaddress
                                #print("Gap in Address is :" , gapInAdd)
                                while   gapInAdd>0 :
                                    if (index + gapInAdd) >= MAXPACKETSIZE :
                                        remainingSpace = MAXPACKETSIZE - index 
                                        #print("Filling Padding\n\n\n") 
                                        for i in range(remainingSpace):
                                            record[i + index] = PADDING
                                        

                                        #print("sending block to ECU\n\n\n")
                                        blockNumber += 1
                                        result = transferToECU(record, blockNumber)
                                        if result == ERROR:
                                            return ERROR
                                        totalByteSent += remainingSpace
                                        index= 0 
                                        gapInAdd -= remainingSpace

                                    else:
                                        
                                        for j in range(gapInAdd):
                                            record[index + j] = PADDING
                                        
                                        index +=  gapInAdd                                 
                                        totalByteSent += gapInAdd
                                        gapInAdd = 0
                                nextaddress = address
                                #lastLine = True

                                

                            nextaddress = address + lineLen   #next address

                            if(index + lineLen >= MAXPACKETSIZE):    #existing Block will get full with this line   
                                #print("\n\n--------Block ready to send---------n: " ,blockNumber +1 ,"\n\n" , )
                                remainingSpace = MAXPACKETSIZE - index  
                                for j in range(remainingSpace):
                                    record[j + index] = lineData[j]
                                    
                                    
                                lineLen -= remainingSpace
                                #transfer block
                                blockNumber += 1
                                result = transferToECU(record, blockNumber)
                                if result == ERROR:
                                            return ERROR
                                print ( result)
                                totalByteSent += remainingSpace
                                if (lineLen> 0):
                                    for j in range (lineLen):
                                        lineData[j] = lineData[j + remainingSpace]

                                index= 0 

                            if(lineLen != 0 ):
                                #record.append(hexline['data'])
                                #print("Feeling block, total number of byte is: ", totalByteSent )
                                for i in range(lineLen) :
                                    record[i + index] = lineData[i] 
                                
                                index += lineLen                    
                                totalByteSent += lineLen  
                                        
                        #End of file received
                        elif(lineType == 1):
                            lastLine = True
                            print("Reaching End of line\n\n")
                            if(index != 0):
                                blockNumber +=1
                                
                                lastblock = [0xFF for i in range(index)]
                                for jj in range (index):
                                    lastblock[jj] = record[jj]
                                result = transferToECU(lastblock,blockNumber)
                                        
                                if result == ERROR:
                                            return ERROR
                            
                    else:                
                        print("Error parsing Hex file line")
                        return ERROR

            except OSError as er:
                ErrFlag = True
                redLED.on()
                print("Error reading line") 
                return ERROR

    BleLEDToggle100ms = 0
    bluLED.off()
    if(lastLine == True):
        return totalByteSent
    else:
        return ERROR
                       
        
    

def hexFileParser (line):
    if(len(line) < 10):
        print("The Hex file line length could not be less than 10")
        print(line)
        return

    lineType =""
    lineAdd = ""
    lineLen="" 
    lineCRC ="" 
    dataTxt=""

    lineToP= {
       'linetype' : 0 ,
       'lengOfData' : 0,
       'dataAddress': 0,
       'LineCRC' : 0,
       'data' : []
    }

    #getting the line type
    lineType += line[7] +line[8] 
    if PRINTLOG == 1 : 
        print(lineType)
    try:          
        typeHex = int(lineType,16)
    except OSError as er:        
        redLED.on() 
        return -1    
    
    #getting the data length 
    lineLen +=  line[1] +line[2]
    try:
        lenHex = int(lineLen , 16) 
    except OSError as er:        
        redLED.on()
        return -1
    
    #getting the data address
    lineAdd +=  line[3] +line[4] +line[5] +line[6]
    try:
        addHex = int(lineAdd , 16) 
    except OSError as er:        
        redLED.on()
        return -1

    #getting the data CRC
    lineCRC +=  line[9+ 2*lenHex] +line[10+ 2*lenHex]
    try:
        CRCHex = int(lineCRC , 16)     
    except OSError as er:       
        redLED.on()
        return -1
    
    lineData=[]
    for indx in range(lenHex):
        datatxt= ""
        datatxt += line[9 + 2*indx] +line[10 + 2*indx]
        dataHex = int(datatxt , 16) & 0xFF
        lineData.append(dataHex)

    lineToP["linetype"] = typeHex
    lineToP["lengOfData"] = lenHex
    lineToP["dataAddress"] = addHex
    lineToP["LineCRC"] = CRCHex
    lineToP["data"] = lineData
    
    return lineToP
   
def mainMenue():    

    print('\033[2J')
    print('\033[H')
    print("----------------------------------- ----------------------------------------")
    print("----------------------------------- ----------------------------------------")
    print("-------------------INEOS TRM ECU Diag and Reflashing Tool-------------------")
    print("------------------------------LUMEN Australia-------------------------------")
    print("----------------------------------- ----------------------------------------")
    print("----------------------------------- ----------------------------------------\n\n\n\n")




    print("---------PRESS MIDDLE BUTTON TO CHANGE THE OPTIONS.\n\n")
    
    print("---------1- CHECK THE INEOS ECU COMM.\n")    
    print("---------2-  REFLASH THE INEOS TRM ECU.\n\n")

    print("---------PRESS RIGHT BUTTON TO RESET THE DEVICE.\n\n")
    

mainMenue()


while True:
    if( sysEN == 1 ):
        # Receive all CAN1 data 
        if(CAN1toComm ==1):
            if( CAN1.any(0) ):
                message = CAN1.recv(0)
                ProcessCANmes(message)

                
        # Receive all CAN2 data 
        if(CAN2toComm ==1):
            if( CAN2.any(0)):
                message = CAN2.recv(0)
                ProcessCANmes(message)

        if(ReflashEnable == 1):
            ReflashECU()

        if(diagEnable == 1 and ReflashEnable != 1): 
            diagEnable = 0    
            diagFunction()

        if option == 1 :
            selectDiag()
            if  userDiagOption != 0:
                diag(userDiagOption)

        if EngDiagEnable == 1 :
            UDSlightDrive()
                     
                    

        
        # 1mS Tick
        if( timerTick_1ms >= 1000 ):
            timerTick_1ms = 0
            

        if( timerTick_1ms % 10 == 0 ):    
            timerTick_10ms += 1
            

        # 10mS Tick
        if( timerTick_10ms >= 10 ):
            timerTick_10ms = 0
            timerTick_100ms += 1
            


        # 100mS Tick
        if( timerTick_100ms >= 10 ):
            timerTick_100ms = 0
            timerTick_1000ms += 1
                   
                          
        
        # 1000mS Tick
        if( timerTick_1000ms >= 10 ):
            timerTick_1000ms = 0
            #UnlockECU()

            timerTick_Seconds += 1
            
            if( timerTick_Seconds >= CYCLE_TIME ):
                timerTick_Seconds = 0 
                
    
import pyb
from pyb import CAN

from UDS_TL import *
from uds import UDSClass
service_IDs={   "DiagSessCtrl":0x10,
                "ECU_reset":0x11,
                "ClearDiagInfo":0x14,
                "ReadDTC":0x19,
                "ReadByID":0x22,
                "SecurityAcess":0x27,
                "CommusCtrl":0x28,
                "WriteByID":0x2E, 
                "RoutineCtrl":0X31, 
                "RqstDownload":0x34,
                "TestPreset":0x3E,
                "TransferData":0x36,
                "RqstTransferExit":0x37, 
                "WriteMemByAddr":0x3D, 
                "CtrlDTC":0x85,
                "IOCtrlByID":0x2F }

postive_res_offset=0x40

Postive_Response_ID = {    "DiagSessCtrl":0x50,
                            "ECU_reset":0x51,
                            "ClearDiagInfo":0x54,
                            "ReadDTC":0x59,
                            "ReadByID":0x62,
                            "SecurityAcess":0x67,
                            "CommusCtrl":0x68,
                            "WriteByID":0x6E, 
                            "RoutineCtrl":0X71, 
                            "RqstDownload":0x74,
                            "TestPreset":0x7E,
                            "TransferData":0x76,
                            "RqstTransferExit":0x77, 
                            "WriteMemByAddr":0x7D, 
                            "CtrlDTC":0xC5,
                            "IOCtrlByID":0x6F }

session_IDs = { "defualt":1,
                "programming":2,
                "extended":3,
                "Lumen":4
            }

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

class EcuTest:
    def __init__(self):
        mainMenue()
        self.CANs=[
            {'enable':False, 'req_id':0, 'res_id':0},  #CAN1
            {'enable':False, 'req_id':0, 'res_id':0}   #CAN2
        ]

        self.can_idx_list=[1,2]
      

    def get_can_attribute(self,can_index):
        '''
        return the attributes assocaited to CAN  
        '''
        if can_index in self.can_idx_list:
            return self.CANs[can_index-1].key()
   
    def _enable_can(self,can_index):
        if can_index in self.can_idx_list:
            self.CANs[can_index-1]['enable']=True

    def _disable_can(self,can_index):
        if can_index in self.can_idx_list:
            self.CANs[can_index-1]['enable']=False 

    def _can_is_enabled(self,can_index):
        if can_index in self.can_idx_list:
            return self.CANs[can_index-1]['enable']

    def _set_can_request_id(self,can_index, req_id):
         if can_index in self.can_idx_list:
            self.CANs[can_index-1]['req_id']=req_id

    def _get_can_request_id(self,can_index):
         if can_index in self.can_idx_list:
            return self.CANs[can_index-1]['req_id']       

    def _set_can_response_id(self,can_index, res_id):
         if can_index in self.can_idx_list:
            self.CANs[can_index-1]['res_id']=res_id

    def _get_can_response_id(self,can_index):
         if can_index in self.can_idx_list:
            return self.CANs[can_index-1]['res_id']                                
           

    def init_can1(self, RequestID = 0x6BB, ResponseID= 0x63B):
        self.can1 = pyb.CAN(2)
        self.can1.init( pyb.CAN.NORMAL, extframe = False, prescaler = 4, sjw = 1, bs1 = 14, bs2 = 6 )
        self.can1.setfilter( 0, CAN.LIST16, 0, ( 0, RequestID, ResponseID, 0) )
        self._set_can_request_id(1,RequestID)
        self._set_can_response_id(1,ResponseID)
        self._enable_can(1)
        

    def init_can2(self, RequestID = 0x6BB, ResponseID= 0x63B):
        self.can2 = pyb.CAN(1)
        self.can2.init( pyb.CAN.NORMAL, extframe = False, prescaler = 4, sjw = 1, bs1 = 14, bs2 = 6 )
        self.can2.setfilter( 0, CAN.LIST16, 0, ( 0, 0, ResponseID, 0))
        CANSTB2 = pyb.Pin( 'CANSTB1', pyb.Pin.OUT_PP )
        CANSTB2.low()
        self._set_can_request_id(2,RequestID)
        self._set_can_response_id(2,ResponseID)
        self._enable_can(2)

    def main_loop(self):
        while True:
            for can_index in self.can_idx_list:
                if self._can_is_enabled(can_index) and self.can1.any(0):
                    message = self.can1.recv(0)
                    self.ProcessCANmes(message,can_index)

    


    def ReflashECU():
        pass     

    def diagFunction():
        pass   

    def UDSlightDrive():
        pass 


    def ProcessCANmes(self, data, can_index):
        try:
            ReadID = dataRecv[0]
            IDinHex = hex(ReadID)
            data = dataRecv[3]
            dlc = len(data)
                                
            
            if(data[0] == self._get_can_response_id(can_index) ):
                                        
                if(data[1]== UDSClass('DiagSessCtrl').PosResId() and data[2]==UDSClass('DiagSessCtrl').getSessionIdByName('extended')): 
                    #print("PRGPRGPRGPRGPRGPRGPRG----Extended Session----PRGPRGPRGPRGPRGPRGPRG\n\n") 
                    if InBootL == 0:
                        BootLoaderState = DisNorComm
                    elif startFrom == BLSTART:
                        BootLoaderState = programmSession

                    else:
                        BootLoaderState = reqSeed
                        

                elif(data[1]== Postive_Response_ID('CommusCtrl') and data[2]==0x01):
                    #print("SSSSSSSSSSSSSSSS^^^^^^^^----SEED received----^^^^^^^^SSSSSSSSSSSSSSSS")                                
                    BootLoaderState = programmSession                
                
                #Go to Programming session
                elif data[1]== Postive_Response_ID('SecurityAcess')  and data[2]==0x08 :

                    print("UUUUUUUUUUUU----ECU unlocked----UUUUUUUUUUU\n\n") 
                    
                    # if InBootL == 0:                    
                    #     BootLoaderState = programmSession
                    
                    # else:                       
                    BootLoaderState = eraseMem                
                                            

                #Rest ECU
                elif(data[1]== Postive_Response_ID('DiagSessCtrl') and data[2]==session_IDs('programming')): 
                    #print("PRGPRGPRGPRGPRGPRGPRG----Programming Session----PRGPRGPRGPRGPRGPRGPRG\n\n") 
                    if InBootL == 0:
                        InBootL = 1
                        BootLoaderState = programmSession

                    BootLoaderState = reqSeed               
                    

                elif(data[1]== Postive_Response_ID('ECU_reset') and data[2]==0x01): 
                    print("^^^^^^^^^^^^^^^^^^^^ECU RESET^^^^^^^^^^^^^^^^^^^^\n\n") 
                    pyb.delay(100)
                    if InBootL == 0:
                        InBootL = 1
                    else:
                        InBootL = 0               
                        BootLoaderState = finish
                    
                elif(data[1]== Postive_Response_ID('WriteByID') and data[2]== 0xF1 and data[3]== 0x07):      #positive response fingerprint
                    print ("posive resp from print finger print")
                    BootLoaderState = eraseMem
                    
                #memory erased
                elif(data[1]== Postive_Response_ID('RoutineCtrl') ): 
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


                elif(data[1]== Postive_Response_ID('RqstDownload') and data[2]==0x20):
                    
                    #print("Requesting Transfer data accepted\n\n")
                    BootLoaderState = transferData

                #transfer exit positive resp
                elif data[1]== Postive_Response_ID('TransferData') :
                    print("---- transfer  done,  ----\n\n")
                    BootLoaderState = reqTrExit

                #transfer exit positive resp
                elif data[1]== Postive_Response_ID('RqstTransferExit') :
                    #print("---- transfer Exit done, checking checksom ----\n\n")
                    BootLoaderState = checkCksm

                elif data[1]== 0x7F and data[3]!= 0x78:
                    print("---- Negative response: ----\n\n")

            
                            
        
        except OSError as er:
            print("Error 456")
            redLED.on()






            




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
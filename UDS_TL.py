from array import *

PCI_SF = const(0)
PCI_FF = const(1)
PCI_CF = const(2)
PCI_FC = const(3)

CAN_FIFO_CHN_0 		= const(0)
CAN_TX_TIMEOUT_MS	= const(50)

UDS_REQ_ID = const(0x600)
UDS_RESP_ID = const(0x601)

FF_PAYLOAD_SIZE = const(6)
CF_PAYLOAD_SIZE = const(7)

TX_SEPERATION_TIME_MS = const(1)
TX_BLOCK_SIZE_MAX = const(514)      #REZA

UDS_TL_BlOCK_SIZE = const(10)
UDS_TL_SEPERATION_TIME_MIN = const(20)
UDS_TL_FC_FRAME_TIMEOUT = const(1000)

ERR_TX_BUSY = -1
ERR_TX_MSG_TOO_LARGE = -2

class UDS_TransportLayer():
    mhCan = None
    mTxFsmState = 0
    mRxFsmState = 0
    mCurrentTxMsg = None
    
    mTxCurrentIdx = 0
    mTxFcWaitCounter = 0
    mTxNumOfFrame = 0
    mTxRemainingByte = 0
    mTxCurrentPos = 0
    mTxSeqNumber = 0
    mTxCfFrameRecived = False
    mTxSeperationTimerCount = 0

    mRxMessage = None
    mRxMessageSize = 0
    mRxMessagePos = 0
    mRxCfCount = 0
    mRxFlowCtrlStatus = 0
    mRxMessageReceived = False

    mFlowCtrlStatus = 0
    mBlockSize = 0
    mSeperationTimeMin = 0

    mReqId = UDS_REQ_ID
    mRespId = UDS_RESP_ID

    mVerbose = False
    
    #-----------------------------------------------------------------------
	# Initialise function
	#-----------------------------------------------------------------------
    def __init__(self, hCan, reqId, respId):
        self.mhCan = hCan
        self.mReqId = reqId
        self.mRespId = respId
    
    def SetVerbose( self, bValue ):
        self.mVerbose = bValue

    def TxFsm(self):
        if( self.mTxFsmState == 0 ):
            # idle            
            if self.mCurrentTxMsg != None:
                if len(self.mCurrentTxMsg) <= 7:
                    self.mTxFsmState = 1
                else:
                    self.mTxFsmState = 2
        elif( self.mTxFsmState == 1 ):
            # send SF
            headerByte = ((PCI_SF << 4) | len(self.mCurrentTxMsg) ) & 0xFF
            txData = array('B',[headerByte])
            txData.extend(self.mCurrentTxMsg)            
            
            try:
                self.mhCan.send( txData, self.mReqId, timeout=CAN_TX_TIMEOUT_MS )                
                self.mTxFsmState = 5
            except OSError as er:
                self.mTxFsmState = 6

        elif( self.mTxFsmState == 2 ):
            # send FF
            self.mTxNumOfFrame = ( len(self.mCurrentTxMsg) - FF_PAYLOAD_SIZE ) // CF_PAYLOAD_SIZE
            self.mTxRemainingByte = ( len(self.mCurrentTxMsg) - FF_PAYLOAD_SIZE ) % CF_PAYLOAD_SIZE
            
            headerByte = ((PCI_FF << 4) | ( len(self.mCurrentTxMsg) >> 8 ) & 0x0F ) & 0xFF
            dlByte = len(self.mCurrentTxMsg) & 0xFF

            txData = array('B',[ headerByte, dlByte ])
            txData.extend(self.mCurrentTxMsg[self.mTxCurrentPos : self.mTxCurrentPos + FF_PAYLOAD_SIZE])
            

            try:
                self.mhCan.send( txData, self.mReqId, timeout=CAN_TX_TIMEOUT_MS ) 
                self.mTxCurrentPos += FF_PAYLOAD_SIZE 
                self.mTxSeqNumber = 0
                self.mTxCurrentIdx = 0

                self.mTxFsmState = 4
                self.mTxFcWaitCounter = UDS_TL_FC_FRAME_TIMEOUT
                self.mTxCfFrameRecived = False

            except OSError as er:
                self.mTxFsmState = 6

        elif( self.mTxFsmState == 3 ):
            self.mTxSeperationTimerCount -= 1
            if ( self.mTxSeperationTimerCount == 0 ):
                self.mTxSeperationTimerCount = self.mSeperationTimeMin + TX_SEPERATION_TIME_MS
                
                if ( self.mTxCurrentIdx < self.mTxNumOfFrame ) :
                    self.mTxCurrentIdx += 1
                    self.mTxSeqNumber += 1
                    # send data
                    self.SendCf( self.mTxSeqNumber, self.mCurrentTxMsg[self.mTxCurrentPos : self.mTxCurrentPos + CF_PAYLOAD_SIZE] )
                    self.mTxCurrentPos += CF_PAYLOAD_SIZE
                else:
                    if  self.mTxRemainingByte > 0:
                        self.mTxSeqNumber += 1
                        # send data
                        self.SendCf( self.mTxSeqNumber, self.mCurrentTxMsg[self.mTxCurrentPos : self.mTxCurrentPos + self.mTxRemainingByte] )
                        self.mTxCurrentPos += self.mTxRemainingByte
            
                # send CF
                if self.mBlockSize > 0:
                    if ( self.mTxCurrentIdx % self.mBlockSize == 0 ):
                        self.mTxFsmState = 4
                        self.mTxFcWaitCounter = UDS_TL_FC_FRAME_TIMEOUT
                        self.mTxCfFrameRecived = False

                if ( self.mTxCurrentPos == len(self.mCurrentTxMsg) ):
                    self.mTxFsmState = 5
        elif( self.mTxFsmState == 4 ):
            # wait for FC
            if( self.mTxCfFrameRecived == True ):
                self.mTxCfFrameRecived = False
                self.mTxFsmState = 3
                self.mTxSeperationTimerCount = self.mSeperationTimeMin + TX_SEPERATION_TIME_MS

            self.mTxFcWaitCounter = self.mTxFcWaitCounter - 1
            #print(self.mTxFcWaitCounter)
            # check for timeout
            if self.mTxFcWaitCounter == 0 :
                #print("[ERR] Control frame timeout")
                self.mTxFsmState = 6

        elif( self.mTxFsmState == 5 ):
            # Tx Complete
            #print("Tx Complete")
            self.mTxFsmState = 0
            self.mTxCurrentPos = 0
            self.mCurrentTxMsg = None
        elif( self.mTxFsmState == 6 ):
            # Tx Error
            self.mTxFsmState = 0
            self.mCurrentTxMsg = None
            print("Error in TxFsm")

    def RxFsm(self, data):
        pciType = ( data[0] >> 4 ) & 0x0F         
        if( pciType == PCI_SF ):
            # Sf
            #print("[INFO] First Frame")
            size = data[0] & 0x0F
            self.mRxMessage = array('B',data[ 1: 1 + size])
            self.mRxMessageReceived = True
            
        elif( pciType == PCI_FF ):
            # Ff
            self.mRxMessageReceived = False
            self.mRxMessageSize = (( data[0] & 0x0F ) << 8 ) | data[1]

            if( self.mVerbose == True):
                print("Message Size = {0:d}".format(self.mRxMessageSize))

            self.mRxMessagePos = 0
            self.mRxCfCount = 0

            self.mRxMessage = array('B',data[ 2 : 2 + FF_PAYLOAD_SIZE])
            self.mRxMessagePos += FF_PAYLOAD_SIZE

            # Send CF frame
            self.SendFcFrame()
            
        elif( pciType == PCI_CF ):
            # Cf
            if ( ( self.mRxMessageSize - self.mRxMessagePos ) >= CF_PAYLOAD_SIZE ):
                self.mRxMessagePos += CF_PAYLOAD_SIZE
                self.mRxMessage.extend(data[ 1 : 1 + CF_PAYLOAD_SIZE])
            else:
                remainingBytes = (self.mRxMessageSize - self.mRxMessagePos)
                self.mRxMessagePos += remainingBytes
                self.mRxMessage.extend(data[ 1 : 1 + remainingBytes])
            
            if( self.mVerbose == True):
                print("Current Message Pos = {0:d}".format(self.mRxMessagePos))

            self.mRxCfCount += 1
            
            if( self.mRxMessagePos == self.mRxMessageSize ):
                if( self.mVerbose == True ):
                    print("[INFO] Rx Complete")
                self.mRxMessageReceived = True
                self.mRxMessagePos = 0
            else:
                if ( UDS_TL_BlOCK_SIZE > 0 ):
                    if ( self.mRxCfCount % UDS_TL_BlOCK_SIZE == 0 ):
                        self.SendFcFrame()

        elif( pciType == PCI_FC ):
            # Fc
            self.mFlowCtrlStatus = data[0] & 0x0F
            self.mBlockSize = data[1]
            self.mSeperationTimeMin = data[2]
            self.mTxCfFrameRecived = True
        else:
            nop

    def SendCf(self, seqNum, data):
        headerByte = ((PCI_CF << 4) | ( seqNum & 0x0F )) & 0xFF
        txData = array('B',[ headerByte ])
        if len(data) == 7:
            txData.extend(data)
        else:
            txData.extend(data)
            padding = 7-len(data)
            for y in range(0 , padding):
                txData.append(0)

        try:
            self.mhCan.send( txData, self.mReqId, timeout=CAN_TX_TIMEOUT_MS )         
            
            return
        except OSError as er:
            pass
        

    def SendFcFrame(self):
        headerByte = ((PCI_FC << 4) | (self.mRxFlowCtrlStatus & 0x0F )) & 0xFF
        txData = array('B',[ headerByte, UDS_TL_BlOCK_SIZE, UDS_TL_SEPERATION_TIME_MIN ])
        
        try:
            self.mhCan.send( txData, self.mReqId, timeout=CAN_TX_TIMEOUT_MS )            
            return
        except OSError as er:
            pass

    def WriteMessage(self,data):
        retCode = 0
        if( self.mTxFsmState == 0 ):            
            if( len(data) <= TX_BLOCK_SIZE_MAX ):
                self.mCurrentTxMsg = array('B',data)
            else:
                retCode = ERR_TX_MSG_TOO_LARGE
        else:
            retCode = ERR_TX_BUSY
        return retCode

    def AnyMsgReceived(self):
        return self.mRxMessageReceived

    def ReadMessage(self):
        self.mRxMessageReceived = False
        return self.mRxMessage

    def Run(self):
        # Run Tx State machine
        self.TxFsm()
        # check can fifo
        if self.mhCan.any(CAN_FIFO_CHN_0) == True :
            respMsg = self.mhCan.recv(CAN_FIFO_CHN_0)
            # Run Rx State machine
            if(self.mVerbose == True):
                print(respMsg)

            self.RxFsm(respMsg[3])



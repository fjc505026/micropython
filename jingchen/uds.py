



PostiveResOffset=0x40





class UdsGenericService:
    def __init__(self, name, id):
        self.Name = name
        self.Id= id
        self.PosResid = id+ PostiveResOffset

    def Name(self):
        return self.Name
        
    def Id(self):
        return self.Id   

    def PosResId(self):
        return self.PosResid        



class DiagSessCtrl(UdsGenericService):
    def __init__(self):
        super().__init__('DiagSessCtrl', 0x10)
        self.sessionDict={  "defualt":1,
                            "programming":2,
                            "extended":3,
                            "Lumen":4}

    def getSessionNameById(self, sessionId):
        for key, value in  self.sessionDict.items():
            if  sessionId == value:
                return key
        return -1  

    def getSessionIdByName(self, sessionName):
        for key, value in  self.sessionDict.items():
            if  sessionName.upper() == key.upper():
                return value
        return -1 

     

class EcuReset(UdsGenericService):
    def __init__(self):
        super().__init__('ECU_reset', 0x11) 



class ClearDiagInfo(UdsGenericService):
    def __init__(self):
        super().__init__('ClearDiagInfo', 0x14)   


class ReadDTC(UdsGenericService):
    def __init__(self):
        super().__init__('ReadDTC', 0x19)   


class ReadByID(UdsGenericService):
    def __init__(self):
        super().__init__('ReadByID', 0x22)   


class SecurityAcess(UdsGenericService):
    def __init__(self):
        super().__init__('SecurityAcess', 0x27)   

class CommusCtrl(UdsGenericService):
    def __init__(self):
        super().__init__('CommusCtrl', 0x28)   

class WriteByID(UdsGenericService):
    def __init__(self):
        super().__init__('WriteByID', 0x2E)   


class RoutineCtrl(UdsGenericService):
    def __init__(self):
        super().__init__('RoutineCtrl', 0X31)                                                                

class RqstDownload(UdsGenericService):
    def __init__(self):
        super().__init__('RqstDownload', 0x34)  

class TestPreset(UdsGenericService):
    def __init__(self):
        super().__init__('RoutineCtrl', 0x3E) 


class TransferData(UdsGenericService):
    def __init__(self):
        super().__init__('TransferData', 0x36)  

class RqstTransferExit(UdsGenericService):
    def __init__(self):
        super().__init__('RqstTransferExit', 0x37)  

class WriteMemByAddr(UdsGenericService):
    def __init__(self):
        super().__init__('RoutineCtrl', 0x3D)  

class CtrlDTC(UdsGenericService):
    def __init__(self):
        super().__init__('CtrlDTC', 0x85)  

class IOCtrlByID(UdsGenericService):
    def __init__(self):
        super().__init__('RoutineCtrl', 0x2F)                  



UDSClass={      "DiagSessCtrl":DiagSessCtrl,
                "ECU_reset":EcuReset,
                "ClearDiagInfo":ClearDiagInfo,
                "ReadDTC":ReadDTC,
                "ReadByID":ReadByID,
                "SecurityAcess":SecurityAcess,
                "CommusCtrl":CommusCtrl,
                "WriteByID":WriteByID, 
                "RoutineCtrl":RoutineCtrl, 
                "RqstDownload":RqstDownload,
                "TestPreset":TestPreset,
                "TransferData":TransferData,
                "RqstTransferExit":RqstTransferExit, 
                "WriteMemByAddr":WriteMemByAddr, 
                "CtrlDTC":CtrlDTC,
                "IOCtrlByID":IOCtrlByID }
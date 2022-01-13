'''
Created on 11.05.2018

@author: Entrance04
'''

import inspect, os, sys
from datetime import datetime, date

class ENService ():
    
    session = None
        
    class logger:
        """ nested class """
        
        #declare const Log Leves
        LOGLEVEL_DEBUG  = "DEBUG"
        LOGLEVEL_INFO  = "INFO"
        LOGLEVEL_WARNING = "WARNING"
        LOGLEVEL_ERROR = "ERROR"
        LOGLEVEL_CRITICAL = "CRITICAL"
        LOGLEVEL_ALERT = "ALERT"
        LOGLEVEL_FEEDBACK = "FEEDBACK"
        
        def __init__ (self, contextObj):
            self.logfilename =""
            self.session = contextObj.session 
            self.contextObjName= contextObj.getServiceName()
            
            
            #preparing logfile, create path if necessary
            try:
                directory = "/home/nao/.local/entrance"
                if not os.path.exists(directory):
                    os.makedirs(directory)
                directory = "/home/nao/.local/entrance/log"
                if not os.path.exists(directory):
                    os.makedirs(directory)

                    
            except Exception as e:
                print e
                
            #setLogfilename for today
            self.logfilename = "/home/nao/.local/entrance/log/log_"+datetime.now().strftime("%Y_%m_%d")+".log"
            
            
        def log(self,level,message):
            message = message.encode("UTF-8")            
            context = self.contextObjName
            with open (self.logfilename,"a") as File:
                File.write(level+":("+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+")|"+context+"| "+message+"\n")

        #shortcuts f. Log
        def debug(self,message):
            
            self.log(ENService.logger.LOGLEVEL_DEBUG, message)
            
        def info(self,message):
                        
            self.log(ENService.logger.LOGLEVEL_INFO, message)
        
        def error(self,message):
                        
            self.log(ENService.logger.LOGLEVEL_ERROR, message)
    
        def critical(self,message):
                        
            self.log(ENService.logger.LOGLEVEL_CRITICAL, message)
        
        def warning(self,message):
                        
            self.log(ENService.logger.LOGLEVEL_WARNING, message)
        
        def alert(self,message):
                        
            self.log(ENService.logger.LOGLEVEL_ALERT, message)
            try:
                mem = self.session.service("ALMemory")
                mem.raiseEvent("Entrance/Logger/adminMail",message)
            except Exception as e:
                self.critical("raise Event failed with e="+str(e))
                
        def feedback(self,message):
            
            self.log(ENService.logger.LOGLEVEL_FEEDBACK, message)
            try:
                mem = self.session.service("ALMemory")
                mem.raiseEvent("Entrance/Logger/feedback",message)
            except Exception as e:
                self.critical("raise Event failed with e="+str(e))
                

    
    # -------------------- end logger nested class -------------------------


    def __init__ (self, session=None):
        
        self.session = session
        self.memory = None
        self.logger = ENService.logger(self)
        self.requirements = []
        self.subs = []
        
        if self.session:
            self.memory = self.session.service("ALMemory")
            
        #preparing conf dir, if missing
        try:
            directory = "/home/nao/.local/entrance/config/"
            if not os.path.exists(directory):
                os.makedirs(directory)
                
        except Exception as e:
            print e 
            
    def getLogger(self):
        '''@technical '''
        
        return self.logger
        
            
    def checkRequirements (self):   
        '''@technical '''
        
        _missing = []
        
        if self.requirements and len(self.requirements) > 0 and self.session:
            
            _missing = list(self.requirements)
            _services = self.session.services()


            while len(_missing) > 0 and len(_services) > 0:
                
                _temp = _services[0]
                if "name" in _temp.keys():
                    if _temp["name"] in _missing:
                        _missing.remove(_temp["name"])
                        
                _services.remove(_temp)
                
            
        else:
            self.logger.info("no requirements, pass")
            
        return _missing
            
    def getMethodInfo (self, methodname):
        '''@technical Returns for the method specified in @methodname a python dict that contains the name, params and doc for this method '''
        
        _method = getattr(self,methodname)
        _return = {}
        if callable(_method):
            _args = list(_method.__code__.co_varnames)[0:_method.__code__.co_argcount]
            
            _return["methodname"]=methodname
            _return["params"]= _args#[1:]
            _return["doc"] = str(_method.__doc__)
            
            
        else:
            _return = {"error":"not a callable object"}
            
        return _return 
        
    def methodsByTag (self, doctag):
        """@private """
        
        _retList = []
        
        if not doctag or len(doctag) < 1:
            return _retList
        
        
        _list = [attr for attr in dir(self) if inspect.ismethod(getattr(self, attr))]
        for _methodname in _list:
            
            _method = getattr(self, _methodname)
            if _method.__doc__ and _method.__doc__.startswith(doctag):
                _retList.append(_methodname)

        
        return _retList
    
    def getServiceName (self):
        
        return self.__class__.__name__
        
    def getPublicInterface (self):
        """@public """
        
        return self.methodsByTag("@public")
    
    def getTechnicalInterface (self):
        """@technical """
        
        _v = self.methodsByTag("@public")
        _w = self.methodsByTag("@technical")
        _v.extend(_w)
        return _v
    
    def subscribeToEvent(self, eventname, callback):
        """@private """
        if not self.session:
            self.logger.error("subscribe to Event failed, session = None")
            return
        
        mem = self.session.service("ALMemory")
        try:
            sub = mem.subscriber(eventname)
            sub.signal.connect(callback)
            self.subs.append(sub)
            self.logger.info("subscribe to "+str(eventname)+" done")
            
        except Exception as e:
            self.logger.error("signal connection failed with error, e="+str(e))
        
    
    def stopService(self):
        
        if not self.session:
            self.logger.error("stopService called, but no session")
            return
        
        service_name = self.getServiceName()
        for info in self.session.services():
                try:
                    if info['name'] == service_name:
                        self.session.unregisterService(info['serviceId'])
                        self.logger.info("Unregistered {} as {}".format(service_name, info['serviceId']))
                        self.session.close()
                        break
                except (KeyError, IndexError):
                    pass
    
    def registerAsService(self, session):
        """@private """ 
        
        service_name = self.getServiceName()
        try:
            session.registerService(service_name, self)
            self.logger.info('Successfully registered service: {}'.format(service_name))
        except RuntimeError:
            self.logger.info('{} already registered, attempt re-register'.format(service_name))
            for info in session.services():
                try:
                    if info['name'] == service_name:
                        session.unregisterService(info['serviceId'])
                        self.logger.info("Unregistered {} as {}".format(service_name, info['serviceId']))
                        break
                except (KeyError, IndexError):
                    pass
            session.registerService(service_name,self)
            self.logger.info('Successfully registered service: {}'.format(service_name))


#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys

python_path = os.path.dirname(__file__)  # os.path.join(self.behaviorAbsolutePath(), 'lib')
if python_path not in sys.path:
    sys.path.append(python_path)

#import qi
import qi.path
import qi.logging
from naoqi import *

import time
import logging

import json
import threading
import numpy as np
import almath

REMOTEPEPPER = False

### Variables for Motion thread ###
c = threading.Condition()
actualPose = almath.Pose2D(0.0, 0.0, 0.0)
positionConfidence = 1.0
timeSinceLastMoved = 0.0  # in ms
resetConfidence = False
confidenceThreshold = 0.2
updateRate = 25  # in Hz
moveError = []

### Variables for Motion thread ###

def normalTrans():
    return np.random.normal(0.0, 0.01, 1)[0]

def normalRotation():
    return np.random.normal(0.0, 0.03, 1)[0]

### Parameter Dictionary ###
paramsDictionary = {}
paramsDictionary["orthogonalSecurityDistance"] = 0.15
paramsDictionary["tangentialSecurityDistance"] = 0.15
paramsDictionary["odometryMultiplicatorXPos"] = 1.0
paramsDictionary["odometryMultiplicatorXNeg"] = 1.0
paramsDictionary["odometryMultiplicatorYPos"] = 1.0
paramsDictionary["odometryMultiplicatorYNeg"] = 1.0
paramsDictionary["odometryMultiplicatorTheta"] = 1.0
paramsDictionary["confidenceLossTranslation"] = normalTrans
paramsDictionary["confidenceLossRotation"] = normalRotation
paramsDictionary["epsilonTranslation"] = 0.005
paramsDictionary["epsilonRotation"] = 0.005
paramsDictionary["timeOutToNotify"] = 3000  # ms
paramsDictionary["timeOutToStop"] = 35000  # ms
##############
### Moving ###
##############
# Name                                                           Default Minimum Maximum     Settable
# MaxVelXY       maximum planar velocity(meters / second)        0.35    0.1     0.55        yes
# MaxVelTheta    maximum angular velocity(radians / second)      1.0     0.2     2.00        yes
# MaxAccXY       maximum planar acceleration(meters / second^2)   0.3     0.1     0.55        yes
# MaxAccTheta    maximum angular acceleration(radians / second^2) 0.75    0.1     3.00        yes
# MaxJerkXY      maximum planar jerk(meters / second^3)           1.0     0.2     5.00        yes
# MaxJerkTheta   maximum angular jerk(radians / second^3)         2.0     0.2     50.00       yes
paramsDictionary["speed"] = [["MaxVelXY", 0.35],
                             ["MaxVelTheta", 1.5],
                             ["MaxAccXY", 0.35],
                             ["MaxAccTheta", 0.7],
                             ["MaxJerkXY", 1.0],
                             ["MaxJerkTheta", 1.0]]  # CHANGE: Speed of pepper according to the table above

class loggerClass():
    def __init__(self, name, filename, stream=True, shouldLog=True):
        self.shouldLog = shouldLog
        ### Remove old log file if it exists ###
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            pass

        ### Create Logger ###
        self.logger = logging.getLogger(str(name))

        ### File Handler ###
        fileHandler = logging.FileHandler(str(filename))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fileHandler.setFormatter(formatter)
        self.logger.addHandler(fileHandler)

        ### Stream Handler ###
        if stream:
            streamHandler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            streamHandler.setFormatter(formatter)
            self.logger.addHandler(streamHandler)

        self.logger.setLevel(logging.DEBUG)

    def info(self, mes):
        if self.shouldLog:
            self.logger.info(mes)
            self.logger.handlers[0].flush()

    def warning(self, mes):
        if self.shouldLog:
            self.logger.warning(mes)
            self.logger.handlers[0].flush()

    def error(self, mes):
        if self.shouldLog:
            self.logger.error(mes)
            self.logger.handlers[0].flush()

class motionThread(threading.Thread):
    LOGFILENAME = "motionThread.log"
    global REMOTEPEPPER
    if REMOTEPEPPER:
        LOG_FILE = os.path.join(os.path.dirname(__file__), LOGFILENAME)
    else:
        LOG_FILE = "/home/nao/.local/" + LOGFILENAME

    def __init__(self, name, session):
        threading.Thread.__init__(self)
        self.name = name
        self.motion_service = session.service("ALMotion")
        self.memory = session.service("ALMemory")
        self.tts = session.service("ALTextToSpeech")
        self.motion_service.moveInit()
        self.lastMoveError = []
        self.lastMove = 0
        self.exitMotionThread = False
        self.logger = loggerClass("motionThread", self.LOG_FILE, False, True)
        self.logger.info("Motion Thread Started!!!")

    def _current_milli_time(self):
        return int(round(time.time() * 1000))

    def stop(self):
        self.exitMotionThread = True
        self.logger.info("Motion Thread Finished!!!")

    def resetTime(self):
        global timeSinceLastMoved
        c.acquire()
        self.lastMove = self._current_milli_time()
        timeSinceLastMoved = 0
        c.notify_all()
        c.release()

    def checkMoveError(self):
        global moveError
        moveError = self.memory.getData("ALMotion/MoveFailed")
        # if (not self.lastMoveError and moveError) or self.lastMoveError[0] != moveError[0]:
        #    key = moveError[0]
        #    value = moveError[1]
        #    message = moveError[2]
        #    self.logger.info("[MoveError] " + str(key) + " | " + str(value) + " | " + str(message))
        #    if key == "Internal stop":
        #       self.tts.say("Ich glaube meine Bremse ist noch an, könnte die bitte jemand lösen?")
        #    else:
        #        self.tts.say("Entschuldigung, könnten Sie mir bitte den Weg frei machen!")
        # self.lastMoveError = moveError

    def run(self):
        initialized = False
        global actualPose
        global positionConfidence
        global timeSinceLastMoved
        global paramsDictionary
        global updateRate
        lastPose = actualPose
        self.lastMove = self._current_milli_time()
        epsilonTranslation = paramsDictionary["epsilonTranslation"]
        epsilonRotation = paramsDictionary["epsilonRotation"]
        while True:
            shouldBreak = False
            c.acquire()
            try:
                if self.exitMotionThread:
                    shouldBreak = True
                self.checkMoveError()
                x, y, theta = self.motion_service.getRobotPosition(True)
                actualPose = almath.Pose2D(x, y, theta)
                if not initialized:
                    lastPose = actualPose
                    initialized = True

                deltaX = actualPose.x - lastPose.x
                deltaY = actualPose.y - lastPose.y
                deltaTheta = actualPose.theta - lastPose.theta
                if abs(deltaX) < epsilonTranslation \
                        and abs(deltaY) < epsilonTranslation \
                        and abs(deltaTheta) < epsilonRotation:
                    ### Update TimeOut ###
                    timeSinceLastMoved = self._current_milli_time() - self.lastMove
                else:
                    ### Update Confidence ###
                    translation = np.sqrt((actualPose.x - lastPose.x) ** 2 + (actualPose.y - lastPose.y) ** 2)
                    rotation = almath.modulo2PI(actualPose.theta - lastPose.theta)
                    nT = paramsDictionary["confidenceLossTranslation"]()
                    nR = paramsDictionary["confidenceLossRotation"]()
                    positionConfidence = positionConfidence - abs(translation * nT) - abs(rotation * nR)

                    ### Reset TimeOut ###
                    timeSinceLastMoved = 0.0
                    self.lastMove = self._current_milli_time()
                self.logger.info(
                    "actualPose: (" + str(actualPose.x) + " | " + str(actualPose.y) + " | " + str(actualPose.theta) + ") timeSinceLastMoved:" + str(timeSinceLastMoved) + " confidence: " + str(
                        positionConfidence))
                lastPose = actualPose

            except Exception as e:
                self.logger.error("motionThread: " + str(e))

            c.notify_all()
            c.release()
            if shouldBreak:
                break
            time.sleep(1.0 / updateRate)
        self.logger.info("Motion Thread Run finished!")

def degToRad(deg):
    return deg * (np.pi / 180.0)

class movingService(ALModule):
    LOGFILENAME = "movingService.log"
    global REMOTEPEPPER
    if REMOTEPEPPER:
        LOG_FILE = os.path.join(os.path.dirname(__file__), LOGFILENAME)
    else:
        LOG_FILE = "/home/nao/.local/" + LOGFILENAME

    __location__ = os.path.realpath(
            os.path.join(os.getcwd(), os.path.dirname(__file__)))

    def __init__(self, application):
        self.session = application.session
        self.application = application
        self.serviceName = self.__class__.__name__

        self._startLogger()

        self.logger.info("Initializing Proxies...")
        self.memory = self.session.service("ALMemory")
        self.tts = self.session.service("ALTextToSpeech")
        self.motion_service = self.session.service("ALMotion")
        self.posture_service = self.session.service("ALRobotPosture")
        self.tracker = self.session.service("ALTracker")
        self.session.service('ALBasicAwareness').setTrackingMode("Head")
        self.logger.info("Starting ...")

        if REMOTEPEPPER:
            self.logger.info("Initialize...")
            self.initialize()
            self.logger.info("Initializing done!")
            time.sleep(20)
            self.tts.say("Starte Testpfad!")
            self.moveGivenPath("path1")
            time.sleep(20)
            self.tts.say("Fahre zurück!")
            self.moveGivenPath("path1")

    def _startLogger(self):
        # logger
        self.logger = loggerClass("movingService", self.LOG_FILE)

        # subsribe to itself to put log in file
        self.logManager = self.session.service("LogManager")
        self.listener = self.logManager.createListener()
        self.listener.clearFilters()
        self.listener.addFilter("*", qi.logging.SILENT)
        self.listener.addFilter(self.serviceName, qi.logging.INFO)
        self.listener.addFilter("behavior.*", qi.logging.INFO)

        # connect Log messages to Logfile
        self.listener.onLogMessage.connect(self._onLogMessage)

    def initialize(self):
        global positionConfidence
        positionConfidence = 1.0
        self._wakeup()
        self._initVariable()
        self._initializeStartPosition()
        self._turnOnAutonomousLife()
        self.loadPathFromFile("path1.json", "path1")
        self.loadPathFromFile("path2.json", "path2")
        self.loadPathFromFile("path3.json", "path3")
        self.loadPathFromFile("path4.json", "path4")

    def reinitialize(self):
        global positionConfidence
        positionConfidence = 1.0
        self._wakeup()
        self._turnOffAutonomousLife()
        self._initializeStartPosition()
        self._turnOnAutonomousLife()

    def _initializeStartPosition(self):
        x, y, theta = self.motion_service.getRobotPosition(True)
        self.startPosition = almath.Pose2D(x, y, theta)

    def correctDeltaRotation(self):
        deltaPose = self.getDeltaPosition()
        theta = almath.modulo2PI(deltaPose.theta)

        self.motionThread = motionThread("motionThread", self.session)
        self.motionThread.start()
        self.moveRelative(theta, 0)
        self.motionThread.stop()
        self.motionThread.join()
        self.startPosition = None
        #self.motion_service.moveTo(0, 0, -theta)

    def correctDeltaPosition(self):
        deltaPose = self.getDeltaPosition()
        self.motion_service.moveTo(-deltaPose.x, -deltaPose.y, 0)

    def getDeltaPosition(self):
        x, y, theta = self.motion_service.getRobotPosition(True)
        robotPose = almath.Pose2D(x, y, theta)
        deltaPose = self.startPosition.diff(robotPose)
        return deltaPose

    def _wakeup(self):
        try:
            self.motion_service.wakeUp()
            self.posture_service.goToPosture("StandInit", 0.5)
            self.logger.info("Woke up pepper!")
        except Exception as e:
            self.logger.error("wakeup: " + str(e))

    def _initVariable(self):
        ### Dictionary for Params ###
        global paramsDictionary
        self.paramsDictionary = paramsDictionary

        ### Dictionary for the Path ###
        self.pathDict = {}

        ### Dictionary for the Directions given in Strings ###
        self.directionDict = {}
        self.directionDict["F"] = degToRad(0.0)
        self.directionDict["FR"] = degToRad(45.0)
        self.directionDict["R"] = degToRad(90.0)
        self.directionDict["BR"] = degToRad(135.0)
        self.directionDict["B"] = degToRad(180.0)
        self.directionDict["BL"] = degToRad(-135.0)
        self.directionDict["L"] = degToRad(-90.0)
        self.directionDict["FL"] = degToRad(-45.0)
        self.startPosition = None

        # Security distances #
        self.motion_service.setOrthogonalSecurityDistance(self.paramsDictionary["orthogonalSecurityDistance"])
        self.motion_service.setTangentialSecurityDistance(self.paramsDictionary["tangentialSecurityDistance"])
        self.logger.info("Initialized Variables")

    def _turnOffAutonomousLife(self):
        try:
            awareness = self.session.service('ALBasicAwareness')
            autolife = self.session.service("ALAutonomousLife")
            autolife.setAutonomousAbilityEnabled("BackgroundMovement", False)
            autolife.setAutonomousAbilityEnabled("BasicAwareness", False)
            # awareness.pauseAwareness()
            # awareness.setEnabled(False)
            awareness.setTrackingMode("BodyRotation")
            self.motion_service.setExternalCollisionProtectionEnabled("Arms", False)
            autolife.setAutonomousAbilityEnabled("SpeakingMovement", False)
            autolife.setAutonomousAbilityEnabled("AutonomousBlinking", False)
            autolife.setAutonomousAbilityEnabled("ListeningMovement", False)
            self.logger.info("Turned Off AutonomousLife ...")
        except Exception as e:
            self.logger.error("_turnOffAutonomousLife: " + str(e))

    def _turnOnAutonomousLife(self):
        try:
            awareness = self.session.service('ALBasicAwareness')
            autolife = self.session.service("ALAutonomousLife")
            autolife.setAutonomousAbilityEnabled("BackgroundMovement", True)
            autolife.setAutonomousAbilityEnabled("BasicAwareness", True)
            # awareness.pauseAwareness()
            # awareness.setEnabled(False)
            awareness.setTrackingMode("BodyRotation")
            self.motion_service.setExternalCollisionProtectionEnabled("Arms", True)
            autolife.setAutonomousAbilityEnabled("SpeakingMovement", True)
            autolife.setAutonomousAbilityEnabled("AutonomousBlinking", True)
            autolife.setAutonomousAbilityEnabled("ListeningMovement", True)
            self.logger.info("Turned On AutonomousLife ...")
        except Exception as e:
            self.logger.error("_turnOnAutonomousLife: " + str(e))

    def loadPathFromFile(self, filename, pathname):
        self.logger.info("Load " + str(filename) + " into path " + str(pathname))
        try:
            with open(os.path.join(self.__location__, filename)) as path_file:
                self.pathDict[pathname] = json.load(path_file)
            self.logger.info("Loaded " + str(filename) + " into path " + str(pathname))
        except Exception as e:
            self.logger.error("_loadPathFromFile: " + str(e))

    def waitForReset(self):
        global timeSinceLastMoved
        # try:
        #    self.motion_service.setExternalCollisionProtectionEnabled("All", False)
        #    self.motion_service.setFallManagerEnabled(False)
        #    self.motion_service.setPushRecoveryEnabled(False)
        # except Exception as e:
        #    self.tts.say("Deaktivieren der Sicherheitsmaßnahmen fehlgeschlagen")
        wasOpen = False
        while True:
            bb = self.memory.getData("BackBumperPressed")
            hatch = self.memory.getData("Device/SubDeviceList/Platform/ILS/Sensor/Value")
            if hatch == 1:
                wasOpen = True
            if wasOpen and hatch == 0:
                self._turnOffAutonomousLife()
                wasOpen = False
            if bb:
                break

        # try:
        #    self.motion_service.setExternalCollisionProtectionEnabled("All", True)
        #    self.motion_service.setFallManagerEnabled(True)
        #    self.motion_service.setPushRecoveryEnabled(True)
        # except Exception as e:
        #    self.tts.say("Aktivieren der Sicherheitsmaßnahmen fehlgeschlagen")
        if self.tts.getLanguage() == "English":
            self.tts.say("Thanks, then I will move on. I hope you have closed my back hatch!")
        else:
            self.tts.say("Danke, dann fahre ich jetzt mal weiter. Ich hoffe du hast meine Klappe hinten wieder geschlossen!")

    def moveGivenPath(self, pathname):
        self.logger.info("moveGivenPath: " + pathname)
        if self.startPosition:
            self.logger.info("correct delta rotation")
            self.correctDeltaRotation()
        global positionConfidence, confidenceThreshold
        self.motionThread = motionThread("motionThread", self.session)
        self.motionThread.start()
        self._turnOffAutonomousLife()

        c.acquire()
        posConf = positionConfidence
        confThres = confidenceThreshold
        c.release()

        if posConf < confThres:
            if self.tts.getLanguage() == "English":
                self.tts.say("Sorry, I am not sure where i am. Could you please open my brake and drive me to my desired position? When you have done it, pleas press on my back bumper!")
            else:
                self.tts.say("Tut mir leid, aber ich bin mir leider sehr unsicher wo ich gerade bin, Kann jemand bitte meine Bremse öffnen und mich bitte auf meine Soll-Position schieben? Wenn du fertig bist drück einfach meinen Bäck Bamper!")
            self.waitForReset()

        try:
            givenPath = self.pathDict[pathname]
            if givenPath:
                for section in givenPath["sections"]:
                    while True:
                        self.tracker.lookAt([1.0, 0.0, 0.5], 0, 0.6, False)
                        flag = self.moveRelative(self.directionDict[section["direction"]], section["length"])
                        if flag == False:
                            self.waitForReset()
                            self.motion_service.killAll()
                            self.motion_service.moveInit()
                        else:
                            break
            else:
                self.logger.error("moveGivenPath: no path named " + str(pathname))
        except Exception as e:
            self.logger.error("moveGivenPath: " + str(e))

        self.motionThread.stop()
        self.motionThread.join()
        self._initializeStartPosition()
        self._turnOnAutonomousLife()
        #Call DestinationReached()
        self.memory.raiseEvent("ENMove/DestinationReached",1);

    def moveRelative(self, direction, length):
        try:
            # self.motion_service.killAll()
            self.motion_service.moveToward(0.0, 0.0, 0.0)
            ### Turn around Theta ###
            angle = -direction
            normalizedTurnTheta = almath.modulo2PI(angle)
            succes = self.moveTo(0.0, 0.0, normalizedTurnTheta)
            if not succes:
                return False

            ### Translate ###
            x = length * np.cos(normalizedTurnTheta)
            y = length * np.sin(normalizedTurnTheta)
            succes = self.moveTo(length, 0.0, 0.0)
            if not succes:
                return False
            else:
                return True

        except Exception as e:
            self.logger.error("moveRelative: " + str(e))
            return False

    def moveTo(self, x, y, theta):
        ### Get Parameter ###
        speed = paramsDictionary["speed"]
        epsilonTranslation = paramsDictionary["epsilonTranslation"]
        epsilonRotation = paramsDictionary["epsilonRotation"]

        global actualPose
        global updateRate
        global moveError
        global timeSinceLastMoved

        c.acquire()
        desiredPose = almath.Pose2D(actualPose.x, actualPose.y, actualPose.theta)
        c.release()

        desired = np.array([
            [x],
            [y]
        ])
        rot = np.matrix([
            [np.cos(desiredPose.theta), -np.sin(desiredPose.theta)],
            [np.sin(desiredPose.theta), np.cos(desiredPose.theta)]
        ])
        desiredTrans = rot * desired
        desiredPose.x += float(desiredTrans[0])
        desiredPose.y += float(desiredTrans[1])
        desiredPose.theta += theta

        sayed1 = False
        self.motionThread.resetTime()
        self.memory.insertData("ALMotion/MoveFailed", -421)
        while True:
            shouldReturn = False
            returnValue = False

            c.acquire()
            self.timeSinceLastMoved = timeSinceLastMoved
            self.actualPose = almath.Pose2D(actualPose.x, actualPose.y, actualPose.theta)
            self.moveError = moveError
            self.updateRate = updateRate
            c.release()

            if self.timeSinceLastMoved > paramsDictionary["timeOutToStop"]:
                if self.tts.getLanguage() == "English":
                    self.tts.say("Sorry, i dont get any further. Could you please drive me to my last start position, release my brakes and notify me by pressing my back bumper?")
                else:
                    self.tts.say("Tut mir leid, ich komme hier wirklich nicht mehr weiter. Kann mich bitte jemand auf meine letzte Startposition fahren, dann meine Bremse lösen und mir das durch einen druck auf den Bäck Bamper mitteilen!")
                return False
            if self.timeSinceLastMoved > paramsDictionary["timeOutToNotify"] and not sayed1 and not self.moveError[0] == "Internal stop":
                self.motion_service.moveToward(0.0, 0.0, 0.0)
                self.motion_service.killAll()
                if self.tts.getLanguage() == "English":
                    self.tts.say("Sorry, could you please go out of my way?")
                else:
                    self.tts.say("Entschuldigung, können Sie mir bitte den Weg frei machen!")
                sayed1 = True
            if self.timeSinceLastMoved > 1500:
                self._doAPossibleShift()
            if self.timeSinceLastMoved < 100:
                sayed1 = False

            delta = np.array([
                [(desiredPose.x - self.actualPose.x)],
                [(desiredPose.y - self.actualPose.y)]
            ])
            rot = np.matrix([
                [np.cos(self.actualPose.theta), np.sin(self.actualPose.theta)],
                [-np.sin(self.actualPose.theta), np.cos(self.actualPose.theta)]
            ])
            deltaTrans = rot * delta
            deltaX = float(deltaTrans[0])
            deltaY = float(deltaTrans[1])
            deltaTheta = almath.modulo2PI(desiredPose.theta - self.actualPose.theta)

            if abs(deltaX) < epsilonTranslation and abs(deltaY) < epsilonTranslation and abs(deltaTheta) < epsilonRotation:
                self.motion_service.moveToward(0.0, 0.0, 0.0)
                return True
            else:
                self.motion_service.moveTo(self.odometryCorrection(deltaX, deltaY, deltaTheta), speed, _async=True)
                time.sleep(1.0 / self.updateRate)

    def _doAPossibleShift(self):
        SensorL = self.memory.getData("Device/SubDeviceList/Platform/InfraredSpot/Left/Sensor/Value")
        SensorR = self.memory.getData("Device/SubDeviceList/Platform/InfraredSpot/Right/Sensor/Value")

        LaserL = int((self.memory.getData("Device/SubDeviceList/Platform/LaserSensor/Front/Vertical/Left/Seg01/X/Sensor/Value")*100))
        LaserR = int((self.memory.getData("Device/SubDeviceList/Platform/LaserSensor/Front/Vertical/Right/Seg01/X/Sensor/Value")*100))

        if(SensorL == 0.0 and SensorR == 1.0):
            if(LaserR < 180):
                self.motion_service.moveTo(0.0, 0.05, 0.0)
        elif(SensorL == 1.0 and SensorR == 0.0):
            if(LaserL < 180):
                self.motion_service.moveTo(0.0, -0.05, 0.0)

    def reset(self):
        pass

    def odometryCorrection(self, x, y, theta):
        if x > 0:
            x = x / paramsDictionary["odometryMultiplicatorXPos"]
        else:
            x = x / paramsDictionary["odometryMultiplicatorXNeg"]
        if y > 0:
            y = y / paramsDictionary["odometryMultiplicatorYPos"]
        else:
            y = y / paramsDictionary["odometryMultiplicatorYNeg"]

        theta = theta / paramsDictionary["odometryMultiplicatorTheta"]
        return (x, y, theta)

    def _current_milli_time(self):
        return int(round(time.time() * 1000))

    def _onLogMessage(self, log):
        try:
            self.logger.debug("%s - %s" % (log["category"], log["message"]))
        except Exception:
            print "Fehler LogMessage!!!"

def register_as_service(service_instance, session):
    """
    Registers a service in naoqi
    """
    service_name = service_instance.__class__.__name__
    try:
        session.registerService(service_name, service_instance)
        print 'Successfully registered service: {}'.format(service_name)
    except RuntimeError:
        print '{} already registered, attempt re-register'.format(service_name)
        for info in session.services():
            try:
                if info['name'] == service_name:
                    session.unregisterService(info['serviceId'])
                    print "Unregistered {} as {}".format(service_name, info['serviceId'])
                    break
            except (KeyError, IndexError):
                pass
        session.registerService(service_name, service_instance)
        print 'Successfully registered service: {}'.format(service_name)
        return service_instance

if __name__ == "__main__":
    if REMOTEPEPPER:
        url = "tcp://192.168.30.41:9559"
        # url = "tcp://127.0.0.1:14071"
        app = qi.Application(url=url)
    else:
        app = qi.Application(sys.argv)
    app.start()
    app.session.waitForService("ALMemory")
    app.session.waitForService("ALMotion")
    app.session.waitForService("ALRobotPosture")
    app.session.waitForService("ALTextToSpeech")
    app.session.waitForService("ALTracker")

    movingService = movingService(app)
    id = register_as_service(movingService, app.session)
    app.run()
    app.stop()
    app.session.unregisterService(id)

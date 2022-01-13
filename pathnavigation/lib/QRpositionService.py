import os, sys

python_path = os.path.dirname(__file__)  # os.path.join(self.behaviorAbsolutePath(), 'lib')
if python_path not in sys.path:
    sys.path.append(python_path)

import qi
from naoqi import *

import time
import numpy as np
import almath
import almathswig
from math import sqrt,cos,acos,sin,asin,tan,atan,atan2,exp


class QRpositionService():


    def __init__(self, application):

        self.session = application.session
        self.application = application
        self.module_name = self.__class__.__name__
        # import qicore
        mod = qi.module("qicore")
        # Get LogManager service
        logmanager = application.session.service("LogManager")
        # Create a provider
        provider = mod.createObject("LogProvider", logmanager)
        # Register LogProvider to LogManager
        providerId = logmanager.addProvider(provider)
        self.logger = qi.Logger(self.module_name)

        self.logger.info(".: Starting {} :.".format(self.module_name))
        self.is_looking_qr = False
        self.reset_count= 0

        self.code = "QrReset"
        self.standartMarkSize = 0.195

        self.motion_service = self.session.service("ALMotion")
        self.memory_service = self.session.service("ALMemory")
        self.barcode_service = self.session.service("ALBarcodeReader")
        self.barcode_service.setResolution(4)
        self.barcode_subscriber = self.memory_service.subscriber("BarcodeReader/BarcodeDetected")
        self.barcode_subscriber.signal.connect(self.on_barcode_detected)
        self.video_service = self.session.service("ALVideoDevice")

    def SetMarkSize(self,size):
        self.standartMarkSize = size

    def GetMarkSize(self):
        return  self.standartMarkSize

    def SetQRcode(self,code):
        self.code = code

    def GetQRcode(self):
        return self.code


    def _LookAtQR(self,CodeData):
        """
        Turn the robot in the direction of the QR-code
        """
        try:
            positions = CodeData[0][1]
            positions = self.PixelsToRadian(positions)
            Frame_rob_camera = self.motion_service.getPosition("CameraTop", 2 , True)

            fractionMaxSpeed = 0.1
            names = ["HeadPitch","HeadYaw"]
            Wy = -(positions[0][1] +positions[1][1] +positions[2][1] +positions[3][1])/4. + Frame_rob_camera[4]
            Wz = -(positions[0][0] +positions[1][0] +positions[2][0] +positions[3][0])/4. + Frame_rob_camera[5]

            self.logger.info("Test _LookAtQR")

            if self.is_looking_qr == False:

                Frame_rob_camera = self.motion_service.getPosition("CameraTop", 2 , True)
                self.motion_service.setAngles(names, [0,0], fractionMaxSpeed, _async=False)
                self.motion_service.moveTo(0,0,Wz)
        except Exception, e:
            self.logger.warning("Error while trying to look at the QR-code: " + str(e))

    def on_barcode_detected(self, value):
        """
        Callback for event BarcodeReader/BarcodeDetected
        """
        i = 0
        for i in range(0,len(value)):
            if  value[i][0].find(self.code)>= 0:
                self.barcode_service.unsubscribe("test_barcode")
                if self.is_looking_qr == False:
                    self.barcode_service.subscribe("test_barcode")
                else:
                    if self._Is_in_position(value) == True or self.reset_count >2:
                        try:
                            self.logger.info("Landmark in front")
                            self.reset_count = 0
                            self._turnOnAutonomousLife()
                            self.memory_service.raiseEvent("Position_corrected", "finish")

                        except Exception, e:
                            self.logger.error("Barcode detection: " + str(e))
                    else:
                        if self.reset_count > 0 and self.reset_count <3:
                            self.reset_count += 1
                            self.logger.info("position number: " + str(self.reset_count))
                            self.is_looking_qr = False
                            self._GlobalSearch()
                return

    def _GlobalSearch(self):
        """
        Search for a QR-code and look at it
        """
        self.is_looking_qr = False
        dist = -1
        i = 0
        Qr_found = False
        Pos_head = [0,-2.0, -1.5, -1.0, -0.5,0.0, 0.5, 1.0, 1.5, 2.0,0]
        Pos_head_back = [ -1.5, -1.0, -0.5,0.0, 0.5, 1.0, 1.5, 0]
        try:

            data = self.memory_service.getData("BarcodeReader/BarcodeDetected")
            self.barcode_service.subscribe("test_barcode")

            for i in range(0,len(Pos_head)):
                if Qr_found:
                    return
                else:
                    self.motion_service.setAngles("HeadYaw", Pos_head[i], 0.2, _async=False)

                for range_counter in range(5):
                    if range_counter == 0:
                        time.sleep(0.6)
                    Newdata = self.memory_service.getData("BarcodeReader/BarcodeDetected")
                    if Newdata and isinstance(data, list) and Newdata != data  :
                        Qr_found = True
                        self._LookAtQR(Newdata)
                        self.is_looking_qr = True
                        self.logger.info("QR-code seen")
                        return
                    else:
                        time.sleep(0.6)

            self.motion_service.moveTo(0,0,np.pi)

            for i in range(0,len(Pos_head_back)):
                if Qr_found:
                    return
                else:
                    self.motion_service.setAngles("HeadYaw", Pos_head_back[i], 0.2, _async=False)

                for range_counter in range(5):
                    Newdata = self.memory_service.getData("BarcodeReader/BarcodeDetected")
                    if Newdata and isinstance(data, list) and Newdata != data :
                        Qr_found = True
                        self._LookAtQR(Newdata)
                        self.is_looking_qr = True
                        self.logger.info("QR-code seen")
                        return
                    else:
                        time.sleep(0.3)

            if Qr_found == False:
                self.barcode_service.unsubscribe("test_barcode")

        except Exception, e:
            self.logger.error("Error while searching qr codes: " + str(e))

    def Start_positioning(self):
        """
        Start the position correction process
        """
        self.reset_count = 1
        self.is_looking_qr = False
        self._turnOffAutonomousLife()
        fractionMaxSpeed = 0.2

        self.motion_service.setAngles(["HeadYaw", "HeadPitch"], [0,0], fractionMaxSpeed, _async=False)
        self._GlobalSearch()

    def _Is_in_position(self, CodeData):
        """
        Search if the robot is correctly placed, if not,calculates and moves the robot at the good position
        """

        self.logger.warning("_Is_in_position")
        positions = CodeData[0][1]
        positions = self.PixelsToRadian(positions)
        Frame_rob_camera = self.motion_service.getPosition("CameraTop", 2 , True)

        try:

            a = self.standartMarkSize
            a1 = [positions[0][0]-positions[1][0], positions[0][1] - positions[1][1]]
            a3 = [positions[2][0]-positions[3][0], positions[2][1] - positions[3][1]]
            norme_a1 = sqrt(a1[0]**2 + a1[1]**2)
            dist1 = a /norme_a1
            norme_a3 = sqrt(a3[0]**2 + a3[1]**2)
            dist3 = a /norme_a3
            norme_moy = (norme_a1 + norme_a3)/2.
            dist = a /norme_moy


            #Y3 = a
            #Y0 = 0
            Ya = (dist1**2 - dist3**2 + a**2)/(2*a) #Ya = (dist1**2 - dist3**2 + Y3**2 - Y0**2)/(2*(Y3-Y0))
            Xa = dist3**2 - (a - Ya)**2  #Xa = dist3**2 - (Y3 - Ya)**2
            Tau3 = atan2((Ya - a),Xa )   #Tau3 = atan2((Ya - Y3),Xa )
            Tau1 = atan2(Ya,Xa )   #Tau1 = atan2((Ya - Y0),Xa )


            if abs(norme_a1-norme_a3) < 0.0015 and dist < 1.5:
                return True
            else:

                #print(dist)
                gamma = (Tau3 + Tau1)/2
                Angle_Qrcode = (a1[0]-a3[0])/2


                gamma = gamma*exp(0.35*dist)
                Angle_Qrcode = Angle_Qrcode*exp(0.35*dist)


                direction = - (Angle_Qrcode + gamma + Frame_rob_camera[5])

                if  norme_a3 < norme_a1:
                    AngleMvt = (-(np.pi + gamma)/2  + Angle_Qrcode)%(2*np.pi)

                else:
                    AngleMvt = ((np.pi - gamma)/2  + Angle_Qrcode)%(2*np.pi)
                distMvt = abs(cos((np.pi - gamma)/2)*2*dist)

            self.motion_service.moveTo(distMvt*cos(AngleMvt) + (dist-1)*cos(direction) ,distMvt*sin(AngleMvt) + (dist-1)*sin(direction),direction)
            #self.MovingService.moveTo(dist-1,0, 0)
            #time.sleep(0.2)

            return False
        except Exception, e:
            self.logger.error("Positionning: " + str(e))
            return False

    def PixelsToRadian(self,positions):
        """
        Convert a set of pixels coordinates in radiqn coordinates for a camera of 2560*1920 pixels
        """
        NewPositions = [[0,0],[0,0],[0,0],[0,0]]
        try:
            Ymax,Zmax = self.video_service.getAngularPositionFromImagePosition(2,[0,1])
            for i in range(0,4):
                NewPositions[i][0] = 2.*Ymax*(positions[i][0]/2560. - 1/2.)
                NewPositions[i][1] = 2.*Zmax*(1./2. -  positions[i][1]/1920.)
            return NewPositions
        except Exception, e:
            self.logger.error("PixelsToRadian : " + str(e))
            return (0,0,0,0,0,0,0,0)

    def _turnOffAutonomousLife(self):
        try:
            awareness = self.session.service('ALBasicAwareness')
            autolife = self.session.service("ALAutonomousLife")
            autolife.setAutonomousAbilityEnabled("BackgroundMovement", False)
            autolife.setAutonomousAbilityEnabled("BasicAwareness", False)
            # awareness.pauseAwareness()
            # awareness.setEnabled(False)
            awareness.setTrackingMode("Head")
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
            awareness.setTrackingMode("Head")
            self.motion_service.setExternalCollisionProtectionEnabled("Arms", True)
            autolife.setAutonomousAbilityEnabled("SpeakingMovement", True)
            autolife.setAutonomousAbilityEnabled("AutonomousBlinking", True)
            autolife.setAutonomousAbilityEnabled("ListeningMovement", True)
            self.logger.info("Turned On AutonomousLife ...")
        except Exception as e:
            self.logger.error("_turnOnAutonomousLife: " + str(e))


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

    url = "tcp://127.0.0.1:9559"

    app = qi.Application(url=url)
    app.start()
    instance = QRpositionService(app)
    register_as_service(instance, app.session)
    app.session.waitForService("ALMemory")
    app.session.waitForService("ALMotion")
    app.session.waitForService("ALRobotPosture")
    app.session.waitForService("ALTextToSpeech")
    app.session.waitForService("ALTracker")
    app.session.waitForService("ALBarcodeReader")
    app.run()



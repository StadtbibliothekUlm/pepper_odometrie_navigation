'''
 Created on 22.01.2021 14:45

@author Entrance

-->comment here

'''

import sys, qi, ENService, os, time, json


class ENPositioningService (ENService.ENService):

	#Constructor
	def __init__ (self, session=None):

		ENService.ENService.__init__(self,session)

		#checking requirements, please edit
		self.requirements = []
		_missing = self.checkRequirements()


		self.almotion = self.session.service("ALMotion")
		self.enlandmark = self.session.service("ENLandMarkDetection")

		self.running=False
		
		self.lastRotate=0.0


		self.lastTimestamp =0

		if len(_missing)>0:
			self.logger.error("Requirements not met, missing: "+str(_missing))

	#Methods here
	
	def lockHead (self):
		
		
		if self.session:
			
			_auto = self.session.service("ALAutonomousLife")
			_alb = self.session.service("ALBasicAwareness")
			
			abilities = ["AutonomousBlinking","BackgroundMovement","ListeningMovement","SpeakingMovement","AutonomousBlinking"]
			
			for ability in abilities:
				
				_auto.setAutonomousAbilityEnabled(ability,False)
				

			if _alb.isEnabled() == True:
				_alb.setEnabled(False)
			
					
		actors = ["HeadPitch","HeadYaw"]
		angles = [-0.2,-0.0]
		times = [0.5,0.5]
		
		self.almotion.angleInterpolation(actors,angles,times,True)
		time.sleep(1)
	
	
	def positionZero(self):
		'''@TAG_here - DOCUMENTATION here'''
		
		
		if(self.running):
			return -1,-1
		
		self.running=True
		
		
		cooldown =5
		minRot =0.1
		while(self.running):
			
			leds = self.session.service("ALLeds")
			

			self.enlandmark.extractData()
			
			x,y = self.enlandmark.getAngles()
			
			t = self.enlandmark.getTimeStamp()
			
			if(cooldown ==0):
				cooldown =3
				if (x ==0):
					x=10
				else:
					x=-x
				minRot =1.0
				leds.fadeRGB("FaceLeds","white",0.2)
				
			elif t==0:
				
				minRot = 0.1
				x = 10
				leds.fadeRGB("FaceLeds","white",0.2)
				
				
			elif (t == self.lastTimestamp):
				
				cooldown = cooldown -1
				#self.almotion.moveToward(0.0,0.0,0.0)
				time.sleep(0.5)
				leds.fadeRGB("FaceLeds","yellow",0.2)
				continue
			else:
				minRot=0.1
				leds.fadeRGB("FaceLeds","magenta",0.2)
			
			self.lastTimestamp = t
			
			#iterations checking, revert last move if robot gets lost
			
			if (x > 9.99):
				self.almotion.moveToward(0.0,0.0,-0.2)
				
			
			elif (x > 6.0):
				 self.almotion.moveToward(0.0,0.0,-0.1)
				
				
			elif x > 4.0:
				self.almotion.moveToward(0.0,0.0,-0.075)
				
			elif x < -9.99:
				self.almotion.moveToward(0.0,0.0,0.2)
				
			elif x < -6.0:
				self.almotion.moveToward(0.0,0.0,0.1)
				
			elif (x < -4.0):
				self.almotion.moveToward(0.0,0.0,0.075)
			else:
				self.running=False
				self.almotion.moveToward(0.0,0.0,0.0)
				
			time.sleep(minRot)
				
		return x,y
		

	def correctHeading(self):
		'''@TAG_here - DOCUMENTATION here'''
		
		if(self.running):
			return -1,-1
		
		self.running=True
		
		t = self.enlandmark.getTimeStamp()
		iteration =0
		
		while(self.running):
			
			self.enlandmark.extractData()
			t = self.enlandmark.getTimeStamp()
			x = self.enlandmark.getHeading()
			
			
			if (t == self.lastTimestamp):
				
				self.almotion.moveToward(0.0,0.0,0.0)
				time.sleep(0.4)
				iteration=iteration+1
				if(iteration > 20):
					self.running=False
					
				continue
			
			self.lastTimestamp = t
			iteration =0
			
			if (x > 0):
				
				self.almotion.moveToward(0.0,0.1,0.0)
				
			elif (x<0):
				self.almotion.moveToward(0.0,-0.1,0.0)
				
			else:
				self.almotion.moveToward(0.0,0.0,0.0)
				self.running=False	
				
				
		return x
		

	def moveLR(self,dist):
		'''@TAG_here - DOCUMENTATION here'''

		if(self.almotion):
			
			self.almotion.moveTo(0.0,dist,0.0,1)

	def moveFB(self,dist):
		'''@TAG_here - DOCUMENTATION here'''

		if(self.almotion):
			
			self.almotion.moveTo(dist,0.0,0.0,1)
			
			
	def stopAll(self):
		
		self.running=False;
		
	def version(self):
		
		return "0.15"
	
	def nextMove (self):
		
		self.enlandmark.extractData()
		
		x,y = self.enlandmark.getAngles()
		
		timest = self.enlandmark.getTimeStamp()
		
		if timest ==0 :
			return "poszero"
		
		if x < -2.5 or x > 2.5:
			return "poszero"
		
		t = self.enlandmark.getHeading()
		
		if t!=0:
			
			return "heading"
		
		return "ok"
	
	
	def processPositioning (self):
		
		
		processing=True
		self.lockHead()
		
		while processing:
			
			step = self.nextMove()
			
			if step == "poszero":
				
				self.positionZero()
				
			elif step == "heading":
				
				self.correctHeading()
			
			elif step == "ok":
				
				processing = False
				
			else:
				
				processing = False
				return "error, step was "+step
				
				
		return "done"	 


def main():
	app = qi.Application(sys.argv)
	app.start()
	instance = ENPositioningService(app.session)
	instance.registerAsService(app.session)
	app.run()


if __name__ == "__main__":
	main()
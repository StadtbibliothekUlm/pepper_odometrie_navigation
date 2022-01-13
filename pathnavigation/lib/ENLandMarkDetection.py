'''
 Created on 19.01.2021 10:33

@author Entrance

-->comment here

'''

import sys, qi, ENService, os, time, json, math

class ENLandMarkDetection (ENService.ENService):

	#Constructor
	def __init__ (self, session=None):

		ENService.ENService.__init__(self,session)

		#checking requirements, please edit
		self.requirements = []
		_missing = self.checkRequirements()
		
		if self.session:
			self.ALLandMarks = self.session.service("ALLandMarkDetection")

		if len(_missing)>0:
			self.logger.error("Requirements not met, missing: "+str(_missing))
			
			
		
		self.registerDetection(500)	
		self.subscribeToEvent("LandmarkDetected", self.triggerUpdate)
		
		
		
		self.width=0
		self.height=0
		self.defaultSizeX=0
		self.defaultSizeY=0
		
		self.angleAlpha=0.0
		self.angleBeta=0.0
		self.heading=0
		
		self.landMark=None
		
	
		
		
		self.timeStamp=0
		self.iteration=0

	#Methods here
	
	def registerDetection(self,period):
			
		if (self.ALLandMarks):
			
			self.ALLandMarks.subscribe(self.getServiceName(),period,0.0);
			
	
	def prepareDefaults(self,x,y):
		
		self.defaultSizeX=x
		self.defaultSizeY=y
		

	def readData(self):
		'''@TAG_here - DOCUMENTATION here'''

	
		
		if (self.landMark):
			
			print self.landMark
			return self.landMark

		else:
			print "No landmark detected"
			return "No Landmark"

	def getDistance(self):
		'''@TAG_here - DOCUMENTATION here'''

		

	def getLandMarkID(self):
		'''@TAG_here - DOCUMENTATION here'''

		if self.landMark:
			
			try:
				
				return self.landMark["MarkID"]
				
			except Exception as e:
				
				print e
			
			
			return 0
					
	
	def triggerUpdate (self,value):
		
		try:
			
			self.landMark = value
			
			
				 
		except Exception as e:
			
			self.newData=False
			print e
			


	def extractData (self):
		
		x = self.readData()
		
		if x:
			
			if (isinstance(x,str)):
				
				pass
			
			else:
				self.timeStamp = time.time()
				try:
					
					arr = x
					
					self.angleAlpha=math.degrees(arr[1][0][0][1])
					self.angleBeta=math.degrees(arr[1][0][0][2])
					
					self.width= arr[1][0][0][3]
					self.height= arr[1][0][0][4]
					
					self.heading = arr[1][0][0][5]
					

				except:

					print "Exception"
					
					
	def getAngles (self):
		
		return self.angleAlpha,self.angleBeta
	
	def getDimensions (self):
		
		return self.width,self.height
		
	def getHeading(self):
		
		return self.heading
	
	def getTimeStamp (self):
		
		return self.timeStamp
		

def main():
	app = qi.Application(sys.argv)
	app.start()
	instance = ENLandMarkDetection(app.session)
	instance.registerAsService(app.session)
	app.run()


if __name__ == "__main__":
	main()
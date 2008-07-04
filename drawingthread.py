#!/usr/bin/env python

#import PyQt4.QtGui as qtgui
import PyQt4.QtCore as qtcore

from beetypes import *
from Queue import Queue

from beeutil import *

class DrawingThread(qtcore.QThread):
	def __init__(self,queue,window,type=ThreadTypes.user):
		qtcore.QThread.__init__(self)
		self.queue=queue
		self.window=window
		self.type=type

		# this will be keyed on a layer key, value will be the tool
		# object so it retains information throughout the stroke
		self.inprocesstools={}

	def addExitEventToQueue(self):
		self.queue.put((DrawingCommandTypes.quit,))

	def run(self):
		while 1:
			command=self.queue.get()

			type=command[0]

			if type==DrawingCommandTypes.quit:
				return

			elif type==DrawingCommandTypes.nonlayer:
				self.processNonLayerCommand(command)

			elif type==DrawingCommandTypes.layer:
				self.processLayerCommand(command)

			elif type==DrawingCommandTypes.alllayer:
				# these commands need to be requested from the server
				# if part of a network session and sent locally
				if self.type==ThreadTypes.user and self.window.type==WindowTypes.network:
					self.requestAllLayerCommand(command)
				else:
					self.processAllLayerCommand(command)

	def processNonLayerCommand(self,command):
		subtype=command[1]
		if subtype==NonLayerCommandTypes.startlog:
			pass
		elif subtype==NonLayerCommandTypes.endlog:
			pass
		elif subtype==NonLayerCommandTypes.undo:
			self.window.undo(subtype[2])
			if self.type==ThreadTypes.user and self.window.type==WindowTypes.network:
				self.sendToServer(command)
		elif subtype==NonLayerCommandTypes.redo:
			self.window.redo(subtype[2])
			if self.type==ThreadTypes.user and self.window.type==WindowTypes.network:
				self.sendToServer(command)
		else:
			print "unknown processNonLayerCommand subtype:", subtype

	def processLayerCommand(self,command):
		subtype=command[1]
		if subtype==LayerCommandTypes.alpha:
			layer=self.window.getLayerForKey(command[2])
			if layer:
				layer.setOptions(opacity=command[3])

		elif subtype==LayerCommandTypes.mode:
			layer=self.window.getLayerForKey(command[2])
			if layer:
				layer.setOptions(compmode=command[3])

		elif subtype==LayerCommandTypes.pendown:
			#print "Pen down event:", command
			layer=self.window.getLayerForKey(command[2])
			x=command[3]
			y=command[4]
			pressure=command[5]
			tool=command[6]
			if layer:
				self.inprocesstools[int(command[2])]=tool
				tool.penDown(x,y,pressure)
			else:
				print "WARNING: no layer selected"

		elif subtype==LayerCommandTypes.penmotion:
			if command[2]==None:
				return
			#print "Pen motion event:", command
			x=command[3]
			y=command[4]
			pressure=command[5]
			if self.inprocesstools.has_key(int(command[2])):
				tool=self.inprocesstools[int(command[2])]
				tool.penMotion(x,y,pressure)

		elif subtype==LayerCommandTypes.penup:
			if command[2]==None:
				return
			#print "Pen up event:", command
			x=command[3]
			y=command[4]
			if self.inprocesstools.has_key(int(command[2])):
				tool=self.inprocesstools[int(command[2])]
				tool.penUp(x,y)
				# send to server if needed
				if self.type==ThreadTypes.user and self.window.type==WindowTypes.network:
					sendToServer((DrawingCommandTypes.layer,LayerCommandTypes.tool,tool))
				del self.inprocesstools[int(command[2])]

		elif subtype==LayerCommandTypes.rawevent:
			layer=self.window.getLayerForKey(command[2])
			image=command[3]
			x=command[4]
			y=command[5]
			path=command[6]
			compmode=qtgui.QPainter.CompositionMode_Source
			layer.compositeFromCorner(image,x,y,compmode,path)
		else:
			print "unknown processLayerCommand subtype:", subtype

	def processAllLayerCommand(self,command):
		subtype=command[1]
		if subtype==AllLayerCommandTypes.resize:
			self.window.adjustCanvasSize(command[2],command[3],command[4],command[5])

		elif subtype==AllLayerCommandTypes.scale:
			pass

		elif subtype==AllLayerCommandTypes.layerup:
			self.window.layerUp(command[2])

		elif subtype==AllLayerCommandTypes.layerdown:
			self.window.layerDown(command[2])

		elif subtype==AllLayerCommandTypes.deletelayer:
			self.window.removeLayerByKey(command[2])

		elif subtype==AllLayerCommandTypes.insertlayer:
			key = command[2]
			index = command[3]
			owner = command[4]
			if self.window.ownedByMe(owner):
				self.window.insertLayer(key,index)
			else:
				self.window.insertLayer(key,index,LayerTypes.network)

	def requestAllLayerCommand(self,command):
		self.sendToServer(command)

	def sendToServer(self,command):
		self.window.remoteoutputqueue.put(command)

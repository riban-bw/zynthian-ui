#!/usr/bin/python3
# -*- coding: utf-8 -*-
#******************************************************************************
# ZYNTHIAN PROJECT: Zynthian GUI
# 
# Zynthian GUI Step-Sequencer Class
# 
# Copyright (C) 2015-2020 Fernando Moyano <jofemodo@zynthian.org>
# Copyright (C) 2015-2020 Brian Walton <brian@riban.co.uk>
#
#******************************************************************************
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the LICENSE.txt file.
# 
#******************************************************************************

import inspect
import tkinter
import logging
import tkinter.font as tkFont
from math import sqrt
from PIL import Image, ImageTk

# Zynthian specific modules
from . import zynthian_gui_config
from zyncoder import *

SELECT_BORDER		= zynthian_gui_config.color_on


#------------------------------------------------------------------------------
# Zynthian Step-Sequencer Sequence / Pad Trigger GUI Class
#------------------------------------------------------------------------------

# Class implements step sequencer
class zynthian_gui_seqtrigger():

	# Function to initialise class
	def __init__(self, parent):
		self.parent = parent

		self.zyngui = zynthian_gui_config.zyngui # Zynthian GUI configuration

		self.columns = 4
		self.rows = 4
		self.selectedPad = 1 # Index of last selected pad - used to edit config
		self.song = 1 # Index of song used to configure pads

		self.playModes = ['Disabled', 'Oneshot', 'Loop', 'Oneshot all', 'Loop all']
		self.padColourDisabled = 'grey'
		self.padColourStarting = 'orange'
		self.padColourPlaying = 'green'
		self.padColourStopping = 'red'
		self.padColourStoppedEven = 'purple'
		self.padColourStoppedOdd = 'blue'

		# Geometry vars
		self.width=zynthian_gui_config.display_width
		self.height=zynthian_gui_config.display_height - zynthian_gui_config.topbar_height
		self.selectThickness = 1 + int(self.width / 500) # Scale thickness of select border based on screen
		self.colWidth = self.width / self.columns
		self.rowHeight = self.height / self.rows

		# Main Frame
		self.main_frame = tkinter.Frame(self.parent.main_frame)
		self.main_frame = tkinter.Frame(self.parent.main_frame)
		self.main_frame.grid(row=1, column=0, sticky="nsew")

		# Pad grid
		self.gridCanvas = tkinter.Canvas(self.main_frame,
			width=self.width, 
			height=self.height,
			bd=0,
			highlightthickness=0,
			relief='flat',
			bg = zynthian_gui_config.color_bg)
		self.gridCanvas.grid(row=0, column=0)

		# Icons
		self.icon = [tkinter.PhotoImage(),tkinter.PhotoImage(),tkinter.PhotoImage(),tkinter.PhotoImage(),tkinter.PhotoImage()]

		self.imgSingleshot = tkinter.PhotoImage(file="/zynthian/zynthian-ui/icons/singleshot.png")
		self.imgLoop = tkinter.PhotoImage(file="/zynthian/zynthian-ui/icons/loop.png")

		# Selection highlight
		self.selection = self.gridCanvas.create_rectangle(0, 0, self.width / self.columns, self.height / self.rows, fill="", outline=SELECT_BORDER, width=self.selectThickness, tags="selection")

	#Function to set values of encoders
	#	note: Call after other routine uses one or more encoders
	def setupEncoders(self):
		pass

	# Function to show GUI
	def show(self):
		self.parent.addMenu({'Pad mode':{'method':self.parent.showParamEditor, 'params':{'min':0, 'max':len(self.playModes)-1, 'value':0, 'getValue':self.getSelectedPadMode, 'onChange':self.onMenuChange}}})
		self.parent.addMenu({'MIDI channel':{'method':self.parent.showParamEditor, 'params':{'min':1, 'max':16, 'value':1, 'getValue':self.getSelectedPadChannel, 'onChange':self.onMenuChange}}})
		self.parent.addMenu({'Song':{'method':self.parent.showParamEditor, 'params':{'min':1, 'max':999, 'value':1, 'getValue':self.getSong, 'onChange':self.onMenuChange}}})
		self.loadSong(self.song)
		self.main_frame.tkraise()
		self.setupEncoders()
		self.parent.setTitle("ZynPad (%d)"%(self.song))

	# Function to hide GUI
	def hide(self):
		pass

	# Function to get the mode of the currently selected pad
	#	returns: Mode of selected pad
	def getSelectedPadMode(self):
		return self.parent.libseq.getPlayMode(self.getSequence(self.selectedPad))

	# Function to get the MIDI channel of the currently selected pad
	#	returns: MIDI channel of selected pad
	def getSelectedPadChannel(self):
		return self.parent.libseq.getChannel(self.getSequence(self.selectedPad))

	# Function to get zynpad song
	def getSong(self):
		return self.song

	# Function to get pad sequence
	#	pad: Pad index
	#	returns: Index of sequence associated with pad
	def getSequence(self, pad):
		return self.parent.libseq.getSequence(self.song, pad)

	# Function to handle menu editor change
	#	params: Menu item's parameters
	#	returns: String to populate menu editor label
	#	note: params is a dictionary with required fields: min, max, value
	def onMenuChange(self, params):
		menuItem = self.parent.paramEditorItem
		value = params['value']
		if value < params['min']:
			value = params['min']
		if value > params['max']:
			value = params['max']
		if menuItem == 'Tempo':
			#TODO: Consider how this works with tempo map (song master channel)
			self.zyngui.zyntransport.set_tempo(value)
		prefix = "%s%d" % (chr(int((self.selectedPad - 1) / self.rows) + 65), (self.selectedPad - 1) % self.rows + 1)
		if menuItem == 'Pad mode':
			self.parent.libseq.setPlayMode(self.getSequence(self.selectedPad), value)
			self.parent.setParam(menuItem, 'value', value)
			self.drawPad(self.selectedPad)
			return "%s: %s" % (prefix, self.playModes[value])
		elif menuItem == 'MIDI channel':
			self.parent.libseq.setChannel(self.parent.libseq.getSequence(self.song, self.selectedPad), value - 1)
			self.parent.setParam(menuItem, 'value', value)
			return "%s: MIDI channel: %d" % (prefix, value)
		elif menuItem == 'Song':
			self.loadSong(value)
		return "%s: %d" % (menuItem, value)

	# Function to load song
	#	song: Index of song to load
	def loadSong(self, song):
		self.song = song
		tracks = self.parent.libseq.getTracks(self.song)
		if tracks < 1:
			self.columns = 1
		else:
			self.columns = int(sqrt(int(tracks - 1))+1)
		self.rows = self.columns
		imgWidth = int(self.width / self.columns / 4)
		iconsize = (imgWidth, imgWidth)
		img = (Image.open("/zynthian/zynthian-ui/icons/endnoline.png").resize(iconsize))
		self.icon[1] = ImageTk.PhotoImage(img)
		img = (Image.open("/zynthian/zynthian-ui/icons/loop.png").resize(iconsize))
		self.icon[2] = ImageTk.PhotoImage(img)
		img = (Image.open("/zynthian/zynthian-ui/icons/end.png").resize(iconsize))
		self.icon[3] = ImageTk.PhotoImage(img)
		img = (Image.open("/zynthian/zynthian-ui/icons/loopstop.png").resize(iconsize))
		self.icon[4] = ImageTk.PhotoImage(img)
		self.drawGrid(True)

	# Function to draw grid
	def drawGrid(self, clear = False):
		if clear:
			self.gridCanvas.delete(tkinter.ALL)
		for col in range(self.columns):
			self.drawColumn(col, clear)

	# Function to draw grid column
	#	col: Column index
	def drawColumn(self, col, clear = False):
		for row in range(self.rows):
			self.drawCell(col, row, clear)

	# Function to draw grid cell (pad)
	#	col: Column index
	#	row: Row index
	def drawCell(self, col, row, clear = False):
		pad = row + col * self.rows
		sequence = self.getSequence(pad)
		group = self.parent.libseq.getGroup(sequence)
		if col < 0 or col >= self.columns or row < 0 or row >= self.rows:
			return
		padX = col * self.width / self.columns
		padY = row * self.height / self.rows
		padWidth = self.width / self.columns - 2 #TODO: Calculate pad size once
		padHeight = self.height / self.rows - 2
		cell = self.gridCanvas.find_withtag("pad:%d"%(pad))
		if cell:
			if not sequence or self.parent.libseq.getPlayMode(sequence) == zynthian_gui_config.SEQ_DISABLED or self.parent.libseq.getSequenceLength(sequence) == 0:
				fill = self.padColourDisabled
			elif self.parent.libseq.getPlayState(sequence) == zynthian_gui_config.SEQ_STOPPED:
				if group % 2:
					fill = self.padColourStoppedOdd
				else:
					fill = self.padColourStoppedEven
			elif self.parent.libseq.getPlayState(sequence) == zynthian_gui_config.SEQ_STARTING:
				fill = self.padColourStarting
			elif self.parent.libseq.getPlayState(sequence) == zynthian_gui_config.SEQ_STOPPING:
				fill = self.padColourStopping
			else:
				fill = self.padColourPlaying
			self.gridCanvas.itemconfig(cell, fill=fill)
			self.gridCanvas.coords(cell, padX, padY, padX + padWidth, padY + padHeight)
			mode = self.parent.libseq.getPlayMode(sequence)
			self.gridCanvas.itemconfig("mode:%d"%pad, image=self.icon[mode], state='normal')
		else:
			cell = self.gridCanvas.create_rectangle(padX, padY, padX + padWidth, padY + padHeight,
				fill='grey', width=0, tags=("pad:%d"%(pad), "gridcell"))
			self.gridCanvas.create_text(padX + padWidth / 2, padY + padHeight / 2,
				font=tkFont.Font(family=zynthian_gui_config.font_topbar[0],
				size=int(padHeight * 0.3)),
				fill=zynthian_gui_config.color_panel_tx,
				tags="lbl_pad:%d"%(pad),
				text="%s%d" % (chr(65 + group), pad))
			self.gridCanvas.create_image(padX + padWidth - 1, padY + padHeight - 1, image=self.imgSingleshot, tags=("mode:%d"%(pad)), anchor="se")
			self.gridCanvas.tag_bind("pad:%d"%(pad), '<Button-1>', self.onPadPress)
			self.gridCanvas.tag_bind("lbl_pad:%d"%(pad), '<Button-1>', self.onPadPress)
			self.gridCanvas.tag_bind("mode:%d"%(pad), '<Button-1>', self.onPadPress)
			self.gridCanvas.tag_bind("pad:%d"%(pad), '<ButtonRelease-1>', self.onPadRelease)
			self.gridCanvas.tag_bind("lbl_pad:%d"%(pad), '<ButtonRelease-1>', self.onPadRelease)
			self.gridCanvas.tag_bind("mode:%d"%(pad), '<ButtonRelease-1>', self.onPadRelease)

	# Function to draw pad
	#	pad: Pad index
	#	returns: Pad sequence play state
	def drawPad(self, pad):
		pads = self.rows * self.columns
		if pads < 1 or pad < 0 or pad >= pads:
			return 0
		col = int(pad / self.rows)
		row = pad % self.rows
		self.drawCell(col, row)
		if self.selectedPad == pad:
			if self.parent.paramEditorItem:
				self.gridCanvas.coords(self.selection, (col * self.colWidth, row * self.rowHeight, (1 + col) * self.colWidth, (1 + row) * self.rowHeight))
				self.gridCanvas.tag_raise(self.selection)
				self.gridCanvas.itemconfig(self.selection, state="normal")
			else:
				self.gridCanvas.itemconfig(self.selection, state="hidden")
		return self.parent.libseq.getPlayState(self.parent.libseq.getSequence(self.song, pad))

	# Function to handle pad press
	def onPadPress(self, event):
		if self.parent.lstMenu.winfo_viewable():
			self.parent.hideMenu()
			return
		tags = self.gridCanvas.gettags(self.gridCanvas.find_withtag(tkinter.CURRENT))
		pad = int(tags[0].split(':')[1])
		self.selectedPad = pad
		sequence = self.getSequence(pad)
		print("Pressed pad %d, sequence %d, playmode %d, channel %d, length %d"%(pad, sequence, self.parent.libseq.getPlayMode(sequence), self.parent.libseq.getChannel(sequence), self.parent.libseq.getSequenceLength(sequence)))
		menuItem = self.parent.paramEditorItem
		if menuItem == 'Pad mode':
			self.parent.setParam('Pad mode', 'value', self.parent.libseq.getPlayMode(sequence))
			self.parent.refreshParamEditor()
		elif menuItem == 'MIDI channel':
			self.parent.setParam('MIDI channel', 'value', self.parent.libseq.getChannel(sequence) + 1)
			self.parent.refreshParamEditor()
		if sequence == 0:
			return;
		if self.parent.libseq.getPlayState(sequence) == zynthian_gui_config.SEQ_PLAYING:
			self.parent.libseq.setPlayState(sequence, zynthian_gui_config.SEQ_STOPPING)
		elif self.parent.libseq.getPlayMode(sequence) != zynthian_gui_config.SEQ_DISABLED:
			self.parent.libseq.setPlayPosition(sequence, 0)
			self.parent.libseq.setPlayState(sequence, zynthian_gui_config.SEQ_STARTING)
		playing = self.drawPad(pad)
		if playing and not self.zyngui.zyntransport.get_state():
			self.parent.libseq.resetSync()
			self.parent.libseq.setPlayState(sequence, zynthian_gui_config.SEQ_PLAYING)
			self.zyngui.zyntransport.transport_play()

	# Function to handle pad release
	def onPadRelease(self, event):
		pass

	# Function called when new file loaded from disk
	def onLoad(self):
		pass

	# Function to refresh status
	def refresh_status(self):
		playing = 0
		for pad in range(0, self.rows * self.columns):
			playing = playing + self.drawPad(pad)

	def refresh_loading(self):
		pass

	# Function to handle zyncoder value change
	#	encoder: Zyncoder index [0..4]
	#	value: Current value of zyncoder
	def onZyncoder(self, encoder, value):
		pass

	# Function to handle switch press
	#	switch: Switch index [0=Layer, 1=Back, 2=Snapshot, 3=Select]
	#	type: Press type ["S"=Short, "B"=Bold, "L"=Long]
	#	returns True if action fully handled or False if parent action should be triggered
	def switch(self, switch, type):
		if type == "L":
			return False # Don't handle any long presses
		return True # Tell parent that we handled all short and bold key presses
#------------------------------------------------------------------------------
# -*- coding: utf-8 -*-
"""
This Plugin was created  and is shipped under the copyright of the author:
  Sven H
"""
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChannelSelection import ChannelSelection
from Screens.InfoBar import InfoBar
from ServiceReference import ServiceReference
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry, ConfigSelection, ConfigYesNo, ConfigInteger, ConfigText
from Components.config import KEY_LEFT, KEY_RIGHT
from Components.Sources.StaticText import StaticText
from Components.AVSwitch import AVSwitch
from enigma import eLabel, eSize, eServiceReference, RT_VALIGN_TOP, RT_VALIGN_CENTER, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_WRAP, gFont, eListbox, eServiceCenter, eListboxPythonMultiContent, eListboxServiceContent, eEPGCache, getDesktop, gPixmapPtr, iServiceInformation, ePicLoad
from skin import parseColor, parseFont, TemplatedColors, componentSizes, TemplatedListFonts
from Components.GUIComponent import GUIComponent
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN, SCOPE_LANGUAGE, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE, fileExists
from Tools.Log import Log
from Tools.BoundFunction import boundFunction
from Components.ServiceList import ServiceList, PiconLoader
from Components.Language import language
from RecordTimer import parseEvent
from time import time, localtime, mktime
from datetime import datetime, timedelta
from os import environ as os_environ, path as os_path
import sys, gettext

try:
	from Plugins.Extensions.EventDataManager.plugin import getEventImageName, getExistEventImageName, downloadEventImage, downloadContentImage
	EventDataManager_installed = True
except:
	EventDataManager_installed = False

sz_w = getDesktop(0).size().width()

VERSION = "0.1.0-r4"

#language-support
lang = language.getLanguage()
os_environ["LANGUAGE"] = lang[:2]
gettext.bindtextdomain("enigma2", resolveFilename(SCOPE_LANGUAGE))
gettext.textdomain("enigma2")
gettext.bindtextdomain("enigma2-plugins", resolveFilename(SCOPE_LANGUAGE))
gettext.bindtextdomain("ChannelSelectionPlus", "%s%s" % (resolveFilename(SCOPE_PLUGINS), "Extensions/ChannelSelectionPlus/locale"))

def _(txt):
	t = gettext.dgettext("ChannelSelectionPlus", txt)
	if t == txt:
		t = gettext.gettext(txt)
	if t == txt:
		t = gettext.dgettext("enigma2-plugins", txt)
	return t

#new config for channelselection
config.usage.configselection_listnumbersposition = ConfigSelection(default = "0", choices = [("0",_("ahead")),("1",_("together with servicename"))])
config.usage.configselection_listnumberformat = ConfigSelection(default = "%d", choices = [("%d",_("only number")),("%d.",_("number with dot"))])
config.usage.configselection_showeventnameunderservicename = ConfigYesNo(default=False)
config.usage.configselection_servicenamecolwidth_percent = ConfigInteger(40, limits =(0,100))
config.usage.configselection_ok_key = ConfigSelection(default = "normal", choices = [("normal",_("normal (zap+close)")),("zaponly",_("1. zap, 2. close"))])
config.usage.configselection_info_key = ConfigSelection(default = "simpleepg", choices = [("simpleepg",_("Single EPG") + " (" + _("default") + ")"),("eventview",_("EventView"))])
config.usage.configselection_style = ConfigText(default = "default", fixed_size = False)
config.usage.configselection_select_last_service = ConfigYesNo(default=False)
config.usage.configselection_showdvbicons = ConfigYesNo(default=False)

#check for Merlin-Image
global isMerlin 
isMerlin = False

try:
	from Components.Merlin import MerlinImage
	isMerlin = True
except: pass

if os_path.exists("/usr/lib/enigma2/python/Plugins/Extensions/EPGSearch/EPGSearch.py"):
	from Plugins.Extensions.EPGSearch.EPGSearch import EPGSearch
	
	# overwrite EPGSelection __init__ for audio-key
	from Screens.EpgSelection import EPGSelection
	baseEPGSelection__init__ = None
	baseEPGSelection__init__ = EPGSelection.__init__

	def EPGSelection__init__(self, session, service, zapFunc=None, eventid=None, bouquetChangeCB=None, serviceChangeCB=None):
		#print("[CSP] EPGSelection_ori__init__", baseEPGSelection__init__.__module__)
		baseEPGSelection__init__(self, session, service, zapFunc, eventid, bouquetChangeCB, serviceChangeCB)

		def bluePressed():
			cur = self["list"].getCurrent()
			if cur[0] is not None:
				name = cur[0].getEventName()
			else:
				name = ''
			self.session.open(EPGSearch, name)

		self["epgsearch_epgselection"] = ActionMap(["InfobarAudioSelectionActions"],
				{
					"audioSelection": bluePressed,
				})
	
	#print("[CSP] overwrite EPGSelection.__init__")
	EPGSelection.__init__ = EPGSelection__init__

	# Overwrite EventViewBase.__init__ 
	from Screens.EventView import EventViewBase
	baseEventViewBase__init__ = EventViewBase.__init__
	def EventViewBase__init__(self, Event, Ref, callback=None, similarEPGCB=None):
		baseEventViewBase__init__(self, Event, Ref, callback, similarEPGCB)

		def searchEPG():
			eventName = self.event.getEventName()
			self.session.open(EPGSearch, eventName)

		self["epgsearch_eventview"] = HelpableActionMap(self, "InfobarAudioSelectionActions",
				{
					"audioSelection":  (searchEPG, _("Search EPG with Message")),
			})
	EventViewBase.__init__ = EventViewBase__init__

#change style on ChannelSelection_execBegin if style changed for example in ValisEPG-Plugin
ChannelSelection_execBegin_ori = None
from Screens.ChannelSelection import ChannelSelection
ChannelSelection_execBegin_ori = ChannelSelection._ChannelSelection__execBegin

def ChannelSelection_execBegin(self):
	ChannelSelection_execBegin_ori(self)
	print("[CSP] own ChannelSelection_execBegin style: %s, %s" % (self.servicelist.active_style, config.usage.configselection_style.value))
	if self.servicelist.active_style != config.usage.configselection_style.value:
		print("[CSP] own ChannelSelection_execBegin change_style")
		self.servicelist.setServiceListTemplate(self.servicelist.root)
		self.servicelist.setList(self.servicelist._list)
	self.servicelist.setDVBIcons()

ChannelSelection._ChannelSelection__execBegin = ChannelSelection_execBegin

ChannelSelectionEPG_showEPGList_ori = None
from Screens.ChannelSelection import ChannelSelectionEPG
ChannelSelectionEPG_showEPGList_ori = ChannelSelectionEPG.showEPGList

def ChannelSelectionEPG_showEPGList(self):
	if config.usage.configselection_info_key.value == "simpleepg" or not "ServiceEvent" in self:
		ChannelSelectionEPG_showEPGList_ori(self)
	else:
		ref=self.getCurrentSelection()
		event = self["ServiceEvent"].getCurrentEvent()
		service = self["ServiceEvent"].getCurrentService()
		if ref and event:

			def openSingleServiceEPG():
				self.session.openWithCallback(self.SingleServiceEPGClosed, EPGSelection, ref, serviceChangeCB = self.changeServiceCB)

			self.savedService = ref
			from Screens.EventView import EventViewEPGSelect
			self.session.open(EventViewEPGSelect, event, ServiceReference(ref), None, openSingleServiceEPG, InfoBar.instance.openMultiServiceEPG, InfoBar.instance.openSimilarList)

ChannelSelectionEPG.showEPGList = ChannelSelectionEPG_showEPGList

ChannelSelectionBase_ori = None
from Screens.ChannelSelection import ChannelSelectionBase
ChannelSelectionBase_ori = ChannelSelectionBase.__init__

#overwrite ChannelSelectionBase from ChannelSelection
def ChannelSelectionBase__init__(self, session):
		print("[CSP] ChannelSelectionPlus ChannelSelectionBase__init__ Screen: %s" % self.__class__.__name__)
		ChannelSelectionBase_ori(self, session)

		#don't use Templates in SimpleChannelSelection or Radio-Screens, which use ChannelSelectionBase
		if self.__class__.__name__ in ("ChannelSelection", "ValisEPG", "CSP_ChannelSelectionPreview", "CSP_ValisEPGPreview"):
			self["list"] = ServiceListOwn(session)
			self.servicelist = self["list"]
			self["template_channelbase_action"] = HelpableActionMap(self, "MediaPlayerSeekActions",
				{
					"seekFwd":  (boundFunction(ChannelSelectionBase_nextTemplate,self), _("Change to next Template")),
					"seekBack":  (boundFunction(ChannelSelectionBase_previousTemplate,self), _("Change to previous Template")),
				},-2)
			ChannelSelectionBase_createConfigSelection_style(self)
		else:
			self["list"] = ServiceListOwn(session, useTemplates=False)
			self.servicelist = self["list"]
			self.servicelist.setDVBIcons()
		
		#set Audio-Key to search with EPGSearch
		if os_path.exists("/usr/lib/enigma2/python/Plugins/Extensions/EPGSearch/EPGSearch.py"):
			
			def searchEPG():
				eventName = getEventName(cur = self.servicelist.getCurrent())
				self.session.open(EPGSearch, eventName)
			
			def getEventName(cur):
				serviceref = cur
				refstr = serviceref.toString()
				event = None
				try:
					epg = eEPGCache.getInstance()
					event = epg.lookupEventTime(serviceref, -1, 0)
					if event is None:
						info = eServiceCenter.getInstance().info(serviceref) 
						event = info.getEvent(0)
				except:
					pass
				if event is not None:
					return event.getEventName()
				else:
					return ""
		
			self["epgsearch_channelbase_action"] = HelpableActionMap(self, "InfobarAudioSelectionActions",
				{
					"audioSelection":  (searchEPG, _("Search EPG with Message")),
			})

ChannelSelectionBase.__init__ = ChannelSelectionBase__init__

def ChannelSelectionBase_nextTemplate(self):
	#print("[CSP] ChannelSelectionBase_nextTemplate")
	ChannelSelectionBase_handleKey(self, KEY_RIGHT)
	pass
	
def ChannelSelectionBase_previousTemplate(self):
	#print("[CSP] ChannelSelectionBase_previousTemplate")
	ChannelSelectionBase_handleKey(self, KEY_LEFT)
	pass

def ChannelSelectionBase_handleKey(self, KEY_VALUE):
	config.usage.configselection_style.handleKey(KEY_VALUE)
	self.servicelist.setServiceListTemplate(self.servicelist.root)
	self.servicelist.setList(self.servicelist._list)

def ChannelSelectionBase_createConfigSelection_style(self):
	#print("[CSP] ChannelSelectionBase_createConfigSelection_style")
	if isinstance(config.usage.configselection_style,ConfigText):
		#load template-config-options from templates
		templates = ChannelSelectionBase_getServiceListTemplates(self)
		templates.sort()
		template_options = []
		option_txt = _("default") + " " + _("style")
		template_options.append(("default", option_txt))
		for template in templates:
			if template.startswith("MODE_FAVOURITES"):
				if template == "MODE_FAVOURITES":
					option_txt = _("default") + " " + _("template")
					template_options.append(("MODE_FAVOURITES", option_txt))
				else:
					template_options.append((template,template[16:] + " " + _("template")))
		cur_value = config.usage.configselection_style.value
		config.usage.configselection_style = ConfigSelection(default = "default", choices = template_options)
		config.usage.configselection_style.value = cur_value
		config.usage.configselection_style.saved_value = cur_value
	
def ChannelSelectionBase_getServiceListTemplates(self):
	from enigma import gFont, RT_HALIGN_LEFT, RT_HALIGN_CENTER, RT_HALIGN_RIGHT, RT_VALIGN_TOP, RT_VALIGN_CENTER, RT_VALIGN_BOTTOM, RT_WRAP, SCALE_NONE, SCALE_CENTER, SCALE_ASPECT, SCALE_WIDTH, SCALE_HEIGHT, SCALE_STRETCH, SCALE_FILL
	from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmap, MultiContentEntryPixmapAlphaTest, MultiContentEntryPixmapAlphaBlend, MultiContentTemplateColor, MultiContentEntryProgress, MultiContentEntryProgressPixmap
	return eval(self.servicelist._template).get('templates', {}).keys()

#overwrite changeBouquet from ChannelSelectionBase
ChannelSelectionBase_changeBouquet_ori = ChannelSelectionBase.changeBouquet
def ChannelSelectionBase_changeBouquet(self, direction):
	#print("[CSP] own ChannelSelectionBase_changeBouquet")
	ChannelSelectionBase_changeBouquet_ori(self, direction)
	
	#don't use in SimpleChannelSelection or Radio-Screens, which use ChannelSelectionBase
	if self.__class__.__name__ not in ("ChannelSelection", "ValisEPG"):
		return
	
	if len(self.servicePath) > 1 and config.usage.configselection_select_last_service.value:
		#select last history-service on change bouquet
		from Screens.InfoBar import InfoBar
		servicelist = InfoBar.instance.getBouquetServices(self.servicePath[1])
		curr_service = self.session.nav.getCurrentlyPlayingServiceReference()
		history = self.history[:]
		history.reverse()
		#from ServiceReference import ServiceReference
		breaking = False
		for history_entry in history:
			#print("[CSP] history", history_entry[2].toString(), ServiceReference(history_entry[2]).getServiceName())
			if len(history_entry)>2:
				for service in servicelist:
					#print("[CSP] history", history_entry)
					#print("[CSP] service, history, equal", service.ref, history_entry[2], service.ref == history_entry[2])
					if service.ref == history_entry[2]:
						self.setCurrentSelection(history_entry[2])
						breaking = True
						break
			if breaking:
				break

ChannelSelectionBase.changeBouquet = ChannelSelectionBase_changeBouquet

#overwrite channelSelected from ChannelSelection
def ChannelSelection_channelSelected(self):
	#print "[CSP] close ChannelSelection"
	#print("[CSP] ChannelSelection_channelSelected")
	sel_serviceref = self.getCurrentSelection() #self.servicelist.getCurrent()
	sel_refstr = sel_serviceref.toString()
	
	cur_serviceref = self.session.nav.getCurrentlyPlayingServiceReference()
	cur_refstr = ""
	if cur_serviceref:
		cur_refstr = cur_serviceref.toString()
	
	OFF = 0
	EDIT_ALTERNATIVES = 2

	ref = self.getCurrentSelection()
	if self.movemode:
		self.toggleMoveMarked()
	elif (ref.flags & 7) == 7:
		self.enterPath(ref)
	elif self.bouquet_mark_edit != OFF:
		if not (self.bouquet_mark_edit == EDIT_ALTERNATIVES and ref.flags & eServiceReference.isGroup):
			self.doMark()
	elif not (ref.flags & eServiceReference.isMarker): # no marker
		root = self.getRoot()
		if not root or not (root.flags & eServiceReference.isGroup):
			if isMerlin:
				# Dr.Best
				if not config.merlin2.minitv.value:
					self.zap()
				if sel_refstr == cur_refstr or config.usage.configselection_ok_key.value == "normal":
					self.close(ref)
				if config.merlin2.minitv.value:
					self.zap()
			else:
				self.zap()
				if sel_refstr == cur_refstr or config.usage.configselection_ok_key.value == "normal":
					self.close(ref)
		
		# from Merlin-Image
		# Shaderman
		# Enable zapping for alternative services
		elif isMerlin and not (ref.flags & (eServiceReference.isMarker|eServiceReference.isDirectory)): # should be a playable service, zap!
			self.close(ref)
			self.zap()
			self.saveRoot()

class ChannelSelectionDisplaySettings(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("ChannelSelection Display Settings") + " (CSP " + VERSION + ")")
		self.createConfig()

		self["actions"] = ActionMap(["SetupActions", "ColorActions","EPGSelectActions"],
		{
			"green": self.keySave,
			"info": self.keyInfo,
			"red": self.keyCancel,
			"cancel": self.keyCancel,
			"left": self.keyLeft,
			"right": self.keyRight,
		}, -2)
		self["key_blue"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = session)
		self.createSetup("config")
		
		#save org value to compare on save
		self.liststyle_org = config.usage.configselection_style.value

	def keyCancel(self):
		config.usage.configselection_bigpicons.cancel()
		config.usage.configselection_secondlineinfo.cancel()
		config.usage.configselection_style.saved_value = self.liststyle_org
		ConfigListScreen.cancelConfirm(self, True)
		#todo use own cancelConfirm to avoid changing the saved_value of style-setting on cancel

	def keySave(self):
		reloadServiceList = self.liststyle.value != self.liststyle_org
		
		for x in self["config"].list:
			x[1].save()
		config.usage.configselection_bigpicons.save()
		config.usage.configselection_secondlineinfo.save()
		self.showeventnameunderservicename.save()
		
		if reloadServiceList:
			#print("[CSP] set setServiceListTemplate after save")
			from Screens.InfoBar import InfoBar
			InfoBar.instance.servicelist.servicelist.setServiceListTemplate(InfoBar.instance.servicelist.servicelist.root)
		self.close()

	def newConfig(self):
		cur = self["config"].getCurrent()
		if cur and cur in (self.additionEventInfoEntry, self.columnStyleEntry, self.showEventProgressEntry, self.showServiceNameEntry, self.showlistnumbersEntry, self.showEventnameUnderServicenameEntry, self.ListStyleEntry):
			self.createSetup("config")
		if cur and cur in (self.piconPathEntry, self.showPiconsEntry):
			if self.showpicons.value:
				if self.piconpath.value.endswith("/picon/"):
					config.usage.configselection_bigpicons.value = True
				else:
					config.usage.configselection_bigpicons.value = False
			self.createSetup("config")
		# logical dependence between settings for showservicename and showeventnameunderservicename
		if cur and cur == self.showServiceNameEntry and not self.showservicename.value:
			self.showeventnameunderservicename.value = self.showservicename.value
		if cur and cur == self.showEventnameUnderServicenameEntry and self.showeventnameunderservicename.value:
			self.showservicename.value = self.showeventnameunderservicename.value
		#for Merlin-Image
		if isMerlin and cur and cur[1] == config.usage.configselection_listnumbersposition:
			self.createSetup("config")

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()
	
	def keyInfo(self):
		self.last_liststyle = config.usage.configselection_style.value
		if os_path.exists("/usr/lib/enigma2/python/Plugins/Extensions/ValisEPG/plugin.py") and config.valisepg.channellist.value == "valis":
			from Plugins.Extensions.ValisEPG.plugin import ValisEPG
			class CSP_ValisEPGPreview(ValisEPG):
				IS_DIALOG = True
				def __init__(self, session):
					ValisEPG.__init__(self, session)
					self.skinName = "ValisEPG"
					self.setTitle( "== " + _("Channel Selection") + " " + _("Preview") + " ==" )
					#delete all actions
					for key in self.keys():
						if isinstance(self[key],ActionMap):
							del self[key]
					self["actions"] = ActionMap(["OkCancelActions","DirectionActions"],
						{
							"cancel": self.close,
							"ok": self.close,
							"leftRepeated": self.pageUp0,
							"up": self.moveUp0,
							"upRepeated": self.moveUp0,
							"down": self.moveDown0,
							"downRepeated": self.moveDown0,
							"left": self.keyLeft,
							"right": self.keyRight,
						}, -1)
				
				def handleKey(self, KEY_VALUE):
					config.usage.configselection_style.handleKey(KEY_VALUE)
					self.servicelist.setServiceListTemplate(self.servicelist.root)
					self.servicelist.setList(self.servicelist._list)
					title = _("Preview") +  ": " + config.usage.configselection_style.value.replace("MODE_FAVOURITES_","").replace("MODE_FAVOURITES",_("default") + " " + _("template")).replace("default", _("default") + " " + _("style"))
					ChannelSelection.setTitle(self, title)
			
				def keyLeft(self):
					self.handleKey(KEY_LEFT)
	
				def keyRight(self):
					self.handleKey(KEY_RIGHT)
	
				def setTitle(self, title):
					title = "== " + _("Channel Selection") + " " + _("Preview") + " - " + _("close with exit") + " =="
					ValisEPG.setTitle(self, title)
			
			self.session.openWithCallback(self.openCSP_Callback, CSP_ValisEPGPreview)
		else:
			self.session.openWithCallback(self.openCSP_Callback, CSP_ChannelSelectionPreview)

	def openCSP_Callback(self):
		#self["config"].instance.invalidate()
		if self.last_liststyle != config.usage.configselection_style.value:
			self.createSetup("config")
		
	def createConfig(self):
		#set new choices with "nothing" instead "off"
		config.usage.configselection_showadditionaltimedisplay.choices.choices = [("0", _("nothing")), ("1", _("Percent")), ("2", _("Remain")),("3", _("Remain / duration")), ("4", _("Elapsed")), ("5", _("Elapsed / duration")), ("6", _("Elapsed / remain / duration")),("7", _("Time"))]
		self.additionEventInfo = config.usage.configselection_showadditionaltimedisplay
		self.columnStyle = config.usage.configselection_columnstyle
		self.showlistnumbers = config.usage.configselection_showlistnumbers
		self.listnumberposition = config.usage.configselection_listnumbersposition
		self.listnumerformat = config.usage.configselection_listnumberformat
		self.progressbarposition = config.usage.configselection_progressbarposition
		self.showeventprogress = config.usage.show_event_progress_in_servicelist
		self.showpicons = config.usage.configselection_showpicons
		self.showservicename = config.usage.configselection_showservicename
		self.showbigpicons = config.usage.configselection_bigpicons
		self.piconpath = config.usage.configselection_piconspath
		self.showeventnameunderservicename = config.usage.configselection_showeventnameunderservicename
		self.liststyle = config.usage.configselection_style

	def createSetup(self, widget):
		self.list = []
		self.columnStyleEntry = getConfigListEntry(_("Column style"), self.columnStyle)
		self.list.append(self.columnStyleEntry)
		# self.list.append(getConfigListEntry(_("Show settings in channel context menu"), config.usage.configselection_showsettingsincontextmenu))
		self.list.append(getConfigListEntry(_("Show recordings"), config.usage.configselection_showrecordings))
		if self.columnStyle.value:
			self.showServiceNameEntry = getConfigListEntry(_("Show service name"), self.showservicename)
			self.list.append(self.showServiceNameEntry)
			self.showEventnameUnderServicenameEntry = getConfigListEntry(_("Show eventname below servicename"), self.showeventnameunderservicename)
			if self.showservicename.value:
				self.list.append(self.showEventnameUnderServicenameEntry)
		else:
			self.showServiceNameEntry = None
			self.showEventnameUnderServicenameEntry = getConfigListEntry(_("Show eventname below servicename"), self.showeventnameunderservicename)
			self.list.append(self.showEventnameUnderServicenameEntry)
		#if isMerlin:
		self.list.append(getConfigListEntry(_("Show DVB-icons"), config.usage.configselection_showdvbicons))
		self.showlistnumbersEntry = getConfigListEntry(_("Show service numbers"), self.showlistnumbers)
		self.list.append(self.showlistnumbersEntry)
		if self.showlistnumbers.value:
			self.list.append(getConfigListEntry(_("service number position"), config.usage.configselection_listnumbersposition))
			self.list.append(getConfigListEntry(_("service number format"), config.usage.configselection_listnumberformat))
			if isMerlin and config.usage.configselection_listnumbersposition.value == "0":
				self.list.append(getConfigListEntry(_("Service number alignment"), config.usage.configselection_listnumbersalignment))
		self.showPiconsEntry = getConfigListEntry(_("Show Picons"), self.showpicons)
		self.list.append(self.showPiconsEntry)
		if self.showpicons.value:
			self.piconPathEntry = getConfigListEntry(_("Picons path"), self.piconpath)
			self.list.append(self.piconPathEntry)
		else:
			config.usage.configselection_bigpicons.value = False
			self.piconPathEntry = None
		if self.columnStyle.value:
			self.list.append(getConfigListEntry(_("2nd line info"), config.usage.configselection_secondlineinfo))
		else:
			config.usage.configselection_secondlineinfo.value = "0"
		if self.columnStyle.value:
			self.list.append(getConfigListEntry(_("Servicename column width in %"), config.usage.configselection_servicenamecolwidth_percent))
		self.showEventProgressEntry = getConfigListEntry(_("Show event-progress"), self.showeventprogress)
		self.list.append(self.showEventProgressEntry)
		if self.columnStyle.value and self.showservicename.value and not self.showeventnameunderservicename.value:
			self.progressbarposition.setChoices([("0",_("After service number")),("1",_("After service name")), ("2",_("After event description"))])
		else:
			self.progressbarposition.setChoices([("0",_("After service number")), ("2",_("After event description"))])
		if self.showeventprogress.value:
			self.list.append(getConfigListEntry(_("Event-progessbar position"), self.progressbarposition))
		self.additionEventInfoEntry = getConfigListEntry(_("Additional event-time info"), self.additionEventInfo)
		self.list.append(self.additionEventInfoEntry)
		if self.additionEventInfo.value != "0":
			self.list.append(getConfigListEntry(_("Additional event-time position"), config.usage.configselection_additionaltimedisplayposition))
		if isMerlin:
			self.list.append(getConfigListEntry(_("Tag bouquet services"), config.usage.configselection_tagBouquetServices))

		self.ListStyleEntry = getConfigListEntry(_("servicelist style (Preview = Info)"), self.liststyle)
		if self.liststyle.value == "default":
			self.list.insert(0,self.ListStyleEntry)
		else:
			self.list = []
			self.list.append(self.ListStyleEntry)
			self.list.append(self.showlistnumbersEntry)
			if self.showlistnumbers.value:
				self.list.append(getConfigListEntry(_("service number format"), config.usage.configselection_listnumberformat))
		
		self.list.append(getConfigListEntry(_("select last history-service on bouquet-change"), config.usage.configselection_select_last_service))
		self.list.append(getConfigListEntry(_("behavior of the ok button"), config.usage.configselection_ok_key))
		self.list.append(getConfigListEntry(_("behavior of the info button (tv mode)"), config.usage.configselection_info_key))

		self[widget].list = self.list
		self[widget].l.setList(self.list)


from Components.TemplatedMultiContentComponent import TemplatedMultiContentComponent
from enigma import RT_HALIGN_LEFT, RT_WRAP, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_HALIGN_RIGHT, gFont, eListbox, getDesktop

class ProviderPiconLoader():
	def __init__(self):
		self.nameCache = { }
		config.usage.configselection_piconspath.addNotifier(self.piconPathChanged)

	def getPicon(self, provider):
		pngname = self.getPngName(provider)
		if fileExists(pngname):
			return LoadPixmap(cached = True, path = pngname)
		else:
			return None

	def getPngName(self, provider):
		pngname = self.nameCache.get(provider, "")
		if pngname == "":
			pngname = self.findPicon(provider)
			if pngname != "":
				self.nameCache[provider] = pngname
			if pngname == "":
				pngname = self.nameCache.get("default", "")
				if pngname == "":
					pngname = self.findPicon("picon_default")
					if pngname == "":
						tmp = resolveFilename(SCOPE_CURRENT_SKIN, "picon_default_provider.png")
						if fileExists(tmp):
							pngname = tmp
						else:
							pngname = resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/picon_default.png")
					self.nameCache["default"] = pngname
		return pngname

	def findPicon(self, provider):
		pngname = "%sPiconProvider/%s.png" % (config.usage.configselection_piconspath.value, provider)
		if not fileExists(pngname):
			pngname = ""
		return pngname

	def piconPathChanged(self, configElement = None):
		self.nameCache.clear()

	def finish(self):
		config.usage.configselection_piconspath.removeNotifier(self.piconPathChanged)


class ServiceListOwn(ServiceList,TemplatedMultiContentComponent):
	COMPONENT_ID = "ServiceList"
	if sz_w == 1920:
		default_template = """{"templates":
			{
				"default": (48, [ # needed dummy-template - not used
					MultiContentEntryPixmapAlphaTest(pos=(0,1), size=(30,30), png=3),
					MultiContentEntryText(pos=(40,1), size=(1260,48), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=1, text=1),
				]),
				"MODE_FAVOURITES": (48, [ # template for channel-entries
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(1260,48), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(1,5), size=(60,40), png=4),
					# ServiceName
					MultiContentEntryText(pos=(80,3), size=(300,45), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# EventName
					MultiContentEntryText(pos=(390,3), size=(860,45), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progress
					MultiContentEntryProgress(pos=(80,38),size=(1170,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
					# Marker_Icon + Marker_Text
					MultiContentEntryPixmapAlphaTest(pos=(1,5), size=(60,40), png=27),
					MultiContentEntryText(pos=(65,1), size=(1190,47), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=2, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_FAVOURITES_PERCENT": (48, [ # alternative template for channel-entries
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(1260,48), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(1,5), size=(60,40), png=4),
					# ServiceName
					MultiContentEntryText(pos=(80,3), size=(300,45), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# EventName
					MultiContentEntryText(pos=(390,3), size=(760,45), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# PercentText
					MultiContentEntryText(pos=(1160,3), size=(80,45), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=1, text=23, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progress
					MultiContentEntryProgress(pos=(80,38),size=(1170,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
					# Marker_Icon + Marker_Text
					MultiContentEntryPixmapAlphaTest(pos=(1,5), size=(60,40), png=27),
					MultiContentEntryText(pos=(65,1), size=(1190,47), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=2, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_FAVOURITES_PERCENT_1": (48, [ # alternative template for channel-entries
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(1260,48), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(1,5), size=(60,40), png=4),
					# EventName
					MultiContentEntryText(pos=(80,3), size=(1060,45), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# PercentText
					MultiContentEntryText(pos=(1160,3), size=(80,45), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=1, text=23, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progress
					MultiContentEntryProgress(pos=(80,38),size=(1170,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
					# Marker_Icon + Marker_Text
					MultiContentEntryPixmapAlphaTest(pos=(1,5), size=(60,40), png=27),
					MultiContentEntryText(pos=(65,1), size=(1190,48), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=2, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_FAVOURITES_Remaining": (48, [ # alternative template for channel-entries
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(1260,48), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(1,5), size=(60,40), png=4),
					# EventName
					MultiContentEntryText(pos=(80,3), size=(1060,45), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Remainig Text
					MultiContentEntryText(pos=(1110,3), size=(130,45), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=1, text=22, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progress
					MultiContentEntryProgress(pos=(80,38),size=(1170,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
					# Marker_Icon + Marker_Text
					MultiContentEntryPixmapAlphaTest(pos=(1,5), size=(60,40), png=27),
					MultiContentEntryText(pos=(65,1), size=(1190,48), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=2, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_FAVOURITES_Big":(162,[
					MultiContentEntryPixmapAlphaTest(pos=(5,5),size=(120,80),png=4),
					MultiContentEntryText(pos=(140,5),size=(1090,35),font=1,text=2, color=MultiContentTemplateColor(14),color_sel=MultiContentTemplateColor(15),backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					MultiContentEntryText(pos=(140,50),size=(1090,70),font=0, flags=RT_WRAP,text=26,color=MultiContentTemplateColor(16),color_sel=MultiContentTemplateColor(16),backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					MultiContentEntryText(pos=(5,90),size=(130,35), flags=RT_HALIGN_CENTER,font=1,text=22,color=MultiContentTemplateColor(14),color_sel=MultiContentTemplateColor(15),backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					MultiContentEntryProgressPixmap(pos=(5,130),size=(1230,10), percent=-5,png=25,borderWidth=1,foreColor=MultiContentTemplateColor(6),backColor=MultiContentTemplateColor(7)),
					MultiContentEntryPixmapAlphaTest(pos=(5,35),size=(130,80),png=27),
					MultiContentEntryText(pos=(120,0),size=(1200,150),flags=RT_VALIGN_CENTER, font=1,text=24,color=MultiContentTemplateColor(10),color_sel=MultiContentTemplateColor(11),backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				],True,None,{"ProgressbarPixmapSize": (790,10)}),
				"MODE_NORMAL": (48, [ # template for folder-entries
					MultiContentEntryText(pos=(0,0), size=(840,48), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					MultiContentEntryPixmapAlphaTest(pos=(1,2), size=(30,30), png=3),
					MultiContentEntryText(pos=(40,0), size=(840,48), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_ALL": (48, [ # alternative template for channel-entries
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(1260,48), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(1,5), size=(60,40), png=4),
					# ServiceName
					MultiContentEntryText(pos=(80,3), size=(300,45), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# EventName
					MultiContentEntryText(pos=(390,3), size=(710,45), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Remainig Text
					MultiContentEntryText(pos=(1110,3), size=(130,45), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=1, text=23, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progress
					MultiContentEntryProgress(pos=(80,38),size=(1170,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
				]),
			},
			"fonts": [gFont("Regular",21),gFont("Regular",30), gFont("Regular", 32), gFont("Regular", 30)]
		}"""

	else:
		default_template = """{"templates":
			{
				"default": (34, [ # needed dummy-template - not used
					MultiContentEntryPixmapAlphaTest(pos=(0,1), size=(30,30), png=3),
					MultiContentEntryText(pos=(40,2), size=(840,30), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=1, text=1),
				]),
				"MODE_FAVOURITES": (34, [ # template for channel-entries
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(840,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(50,30), png=4),
					# ServiceName
					MultiContentEntryText(pos=(65,2), size=(200,35), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# EventName
					MultiContentEntryText(pos=(270,2), size=(560,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progressbar
					MultiContentEntryProgress(pos=(65,27),size=(765,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
					# Marker_Icon + Marker_Text
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(50,30), png=27),
					MultiContentEntryText(pos=(53,1), size=(780,34), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=0, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_FAVOURITES_PERCENT": (34, [ # alternative template for channel-entries
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(840,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(50,30), png=4),
					# ServiceName
					MultiContentEntryText(pos=(65,2), size=(200,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# EventName
					MultiContentEntryText(pos=(270,2), size=(480,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# PercentText
					MultiContentEntryText(pos=(750,2), size=(60,34), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=1, text=23, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progressbar
					MultiContentEntryProgress(pos=(65,27),size=(665,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
					# Marker_Icon + Marker_Text
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(50,30), png=27),
					MultiContentEntryText(pos=(53,1), size=(780,34), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=0, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_FAVOURITES_REMAIN": (34, [ # alternative template for channel-entries
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(840,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(50,30), png=4),
					# ServiceName
					MultiContentEntryText(pos=(65,2), size=(200,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# EventName
					MultiContentEntryText(pos=(270,2), size=(480,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Remaining Time Text
					MultiContentEntryText(pos=(740,2), size=(80,34), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=1, text=22, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progressbar
					MultiContentEntryProgress(pos=(65,27),size=(790,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
					# Marker_Icon + Marker_Text
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(50,30), png=27),
					MultiContentEntryText(pos=(53,1), size=(780,34), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=0, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_FAVOURITES_PERCENT 1": (30, [ # alternative template for channel-entries
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(730,30), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(47,28), png=4),
					# EventName
					MultiContentEntryText(pos=(65,1), size=(590,30), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progress 
					MultiContentEntryProgress(pos=(65,25),size=(790,3), percent=-5, borderWidth=-5, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
					# Percenttext
					MultiContentEntryText(pos=(750,1), size=(60,30), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=1, text=23, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Marker_Icon + Marker_Text
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(47,28), png=27),
					MultiContentEntryText(pos=(50,2), size=(675,30), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=0, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_FAVOURITES_REMAIN (16)": (30, [ # alternative template for channel-entries
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(730,30), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(47,28), png=4),
					# EventName
					MultiContentEntryText(pos=(65,1), size=(640,30), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progress 
					MultiContentEntryProgress(pos=(65,25),size=(790,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
					# Remaining Time Text
					MultiContentEntryText(pos=(730,1), size=(90,30), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=1, text=22, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Marker_Icon + Marker_Text
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(47,28), png=27),
					MultiContentEntryText(pos=(50,2), size=(675,30), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=0, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_FAVOURITES_REMAIN (12)": (40, [ # alternative template for channel-entries
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(730,40), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=4, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(63,38), png=4),
					# EventName
					MultiContentEntryText(pos=(75,1), size=(660,40), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=4, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progress 
					MultiContentEntryProgress(pos=(75,33),size=(780,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
					# Remaining Time Text
					MultiContentEntryText(pos=(705,1), size=(115,40), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=4, text=22, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Marker_Icon + Marker_Text
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(63,38), png=27),
					MultiContentEntryText(pos=(60,2), size=(665,40), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=2, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_FAVOURITES_BIG": (80, [ # alternative template for channel-entries
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(730,80), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(2,2), size=(120,71), png=4),
					# EventName
					MultiContentEntryText(pos=(135,1), size=(505,30), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# ExtDesc
					MultiContentEntryText(pos=(135,25), size=(505,54), flags=RT_HALIGN_LEFT | RT_WRAP | RT_VALIGN_TOP, font=3, text=26, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(16), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Remaining text
					MultiContentEntryText(pos=(640,1), size=(80,30), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=1, text=22, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progress
					MultiContentEntryProgress(pos=(640,40),size=(80,10), percent=-5, borderWidth=1, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
					# Marker_Icon + Marker_Text
					MultiContentEntryPixmapAlphaTest(pos=(2,15), size=(83,50), png=27),
					MultiContentEntryText(pos=(90,1), size=(630,80), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=2, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_NORMAL": (34, [ # template for folder-entries
					MultiContentEntryText(pos=(0,0), size=(840,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					MultiContentEntryPixmapAlphaTest(pos=(1,0), size=(30,30), png=3),
					MultiContentEntryText(pos=(40,0), size=(840,34), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
				]),
				"MODE_ALL": (34, [ # template for channel-entries in satellites, providers and all-list
					# empty line full width to fill empty rects
					MultiContentEntryText(pos=(0,0), size=(840,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Picon
					MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(50,30), png=4),
					# ServiceName
					MultiContentEntryText(pos=(65,2), size=(200,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# EventName
					MultiContentEntryText(pos=(270,2), size=(470,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Remaining Time Text
					MultiContentEntryText(pos=(740,2), size=(70,34), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=1, text=22, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
					# Progressbar
					MultiContentEntryProgress(pos=(65,27),size=(665,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
				]),
			},
			"fonts": [gFont("Regular",21),gFont("Regular",20), gFont("Regular", 32), gFont("Regular", 15), gFont("Regular", 25)]
		}"""
	
	def __init__(self, session = None, useTemplates=True):
		#print("[CSP] ServiceListOwn__init__", useTemplates)
		self.useTemplates = useTemplates
		TemplatedMultiContentComponent.__init__(self)
		ServiceList.__init__(self, session)
		
		self.slist = []
		tlf = TemplatedListFonts()
		self.serviceNumberFont = gFont(tlf.face(TemplatedListFonts.MEDIUM), tlf.size(TemplatedListFonts.MEDIUM))
		config.usage.configselection_showeventnameunderservicename.addNotifier(self.setItemHeight, initial_call = False)
		if not isMerlin:
			config.usage.configselection_showdvbicons.addNotifier(self.setDVBIcons, initial_call = False)
		
		self.showPrimeTime = False  #for valisepg to show primtime in ServiceList
		self.PrimeTime = None       #primetime-value for valisepg to show primtime in ServiceList
		
		#set special default values - use in applyskin for list-widget
		self.styleMode = self.styleModeTemplate = eListbox.layoutVertical
		self.styleScrollbarMode = eListbox.showOnDemand
		self.styleMoreNextEvents = 0
		self.stylePrimetimeEvents = 0
		self.stylePrimeTimeHeading = None
		self.picServiceEventProgressbarPath = None
		
		#save org fonts to use in default style
		self.orgFont0 = gFont(tlf.face(TemplatedListFonts.SMALL), tlf.size(TemplatedListFonts.SMALL))
		self.orgFont1 = gFont(tlf.face(TemplatedListFonts.MEDIUM), tlf.size(TemplatedListFonts.MEDIUM))
		self.orgFont2 = gFont(tlf.face(TemplatedListFonts.BIG), tlf.size(TemplatedListFonts.BIG))
		self.orgFont3 = gFont(tlf.face(TemplatedListFonts.SMALL), tlf.size(TemplatedListFonts.SMALL)) 
		
		if config.usage.configselection_style.value + '"' not in self._template:
			config.usage.configselection_style.value = "default"
		self.setTemplate("default")
		
		self.providerPiconLoader = ProviderPiconLoader()
		self.images_downloader_list = []
		self.picload = ePicLoad()

	def setRoot(self, root, justSet=False):
		#Log.i("[CSP] %s" % justSet)
		ServiceList.setRoot(self, root, justSet)
		if self.useTemplates and config.usage.configselection_style.value != "default":
			self.setServiceListTemplate(root)

	def setServiceListTemplate(self, root):
		#Log.i("[CSP]")
		setModeFavourites = False
		
		#check list-entries
		serviceHandler = eServiceCenter.getInstance()
		list = root and serviceHandler.list(root)
		if list is not None:
			service = list.getNext()
			if not (service.flags & eServiceReference.isMarker) and not (service.flags & eServiceReference.isDirectory) and not (service.flags & eServiceReference.isGroup):
				setModeFavourites = True
		
		if self.mode == self.MODE_FAVOURITES:
			template = config.usage.configselection_style.value # "MODE_FAVOURITES..."
		elif setModeFavourites:
			template = "MODE_ALL"
			if 'MODE_ALL' not in self._template:
				template = config.usage.configselection_style.value # fallback to MODE_FAVOURITES...-Template
		else:
			template = "MODE_NORMAL" # folder-lists
		
		if config.usage.configselection_style.value == "default":
			template = "default"
		
		if template == self.active_style:
			#print("[CSP] setServiceListTemplate - same template - no changes needed")
			return
		
		#set own template-Values from template (like itemWidth, bgPixmap, selPixmap, scrollbarMode ...)
		self.setServiceListTemplateValues(template)
		
		#print("[CSP] template", template)
		#if template == "default":
		if config.usage.configselection_style.value == "default":
			self.l.setTemplate(None)
			self.active_style = "default"
		else:
			self.setTemplate(template)

	def getSkinAttribute(self, attribute):
		retValue = None
		for (attrib, value) in self.skinAttributes:
			if attrib == attribute:
				retValue = value
				break
		return retValue
	
	def setServiceListTemplateValues(self, template=""):
		
		if not hasattr(self, "template") or not template:
			#print("[CSP] no template in self - leave function")
			return
		
		#set own template-Values from template
		templates = self.template.get("templates")
		#print("[CSP] templates", len(templates[template]), template, templates)
		if template != "default":
			self.initContent() #set Templatefonts
			if len(templates[template]) > 4: #use template-options
				scrollbarMode =  templates[template][3]
				tpl = templates[template][4]
			else:
				scrollbarMode = None
				tpl = {}
			if scrollbarMode is None:
				scrollbarMode = self.styleScrollbarMode
			self.styleModeTemplate = tpl.get("mode", self.styleMode)
			itemWidth = tpl.get("itemWidth", self.itemWidth)
			
			pixmapSize = tpl.get("pixmapSize", ())
			if pixmapSize:
				pixmapSize = eSize(pixmapSize[0],pixmapSize[1])
			else:
				pixmapSize = eSize()
			
			useWidgetPixmaps = tpl.get("useWidgetPixmaps", None)
			bgPixmap = tpl.get("bgPixmap", None)
			if useWidgetPixmaps and bgPixmap:
				bgPixmap = self.getSkinAttribute(bgPixmap)
			#print("[CSP] set template bgPixmap", bgPixmap)
			if bgPixmap:
				bgPixmap = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, bgPixmap),size=pixmapSize)
			
			selPixmap = tpl.get("selPixmap", None)
			if useWidgetPixmaps and selPixmap:
				selPixmap = self.getSkinAttribute(selPixmap)
			#print("[CSP] set template selPixmap", selPixmap)
			if selPixmap:
				selPixmap = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, selPixmap), size=pixmapSize)
			
			ProgressbarPixmapSize = tpl.get("ProgressbarPixmapSize", ())
			if self.picServiceEventProgressbarPath and ProgressbarPixmapSize:
				pic = LoadPixmap(self.picServiceEventProgressbarPath,size=eSize(ProgressbarPixmapSize[0],ProgressbarPixmapSize[1]))
				if pic:
					self.picServiceEventProgressbar = pic
			
			self.styleMoreNextEvents = tpl.get("moreNextEvents", 0)
			self.stylePrimetimeEvents = tpl.get("primetimeEvents", 0)
		else:
			itemWidth = self.itemWidth
			self.styleModeTemplate = self.styleMode
			selPixmap = self.selectionPixmapStandard
			if config.usage.configselection_bigpicons.value and self.selectionPixmapBig:
				selPixmap = self.selectionPixmapBig
			bgPixmap = self.getSkinAttribute("backgroundPixmap")
			if bgPixmap:
				bgPixmap = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, bgPixmap))
			scrollbarMode = self.styleScrollbarMode
			self.styleMoreNextEvents = 0
			self.stylePrimetimeEvents = 0
			self.setItemHeight()
			
			#set ProgressBarPixmap if exist in the skin
			if self.picServiceEventProgressbarPath:
				pic = LoadPixmap(self.picServiceEventProgressbarPath)
				if pic:
					self.picServiceEventProgressbar = pic
			
			#set default style fonts
			#print("[CSP] set org fonts")
			tlf = TemplatedListFonts()
			self.l.setFont(0, self.orgFont0) # AdditionalInfoFont
			self.l.setFont(1, self.orgFont1) # ServiceNumberFont
			self.l.setFont(2, self.orgFont2) # ServiceNameFont
			self.l.setFont(3, self.orgFont3) # ServiceInfoFont
		
		#print("[CSP] bgPixmap", bgPixmap)
		if bgPixmap:
			self.instance.setBackgroundPicture(bgPixmap)
		else:
			self.instance.setBackgroundPicture(gPixmapPtr())
		#print("[CSP] selPixmap", selPixmap)
		if selPixmap:
			self.instance.setSelectionPicture(selPixmap)
		else:
			self.instance.setSelectionPicture(gPixmapPtr())
		
		#print("[CSP] scrollbarMode, styleScrollbarMode", scrollbarMode, self.styleScrollbarMode)
		self.instance.setScrollbarMode(scrollbarMode)
		#print("[CSP] set template styleMode:", self.styleModeTemplate)
		self.instance.setMode(self.styleModeTemplate)
		#print("[CSP] set template itemWidth", itemWidth)
		self.instance.setItemWidth(itemWidth)

		self.setDVBIcons()

	def moveUp(self):
		#Log.i("[CSP]")
		#print("[CSP] mode, styleMode", self.mode, self.styleMode)
		if self.styleModeTemplate != eListbox.layoutVertical:
			self.instance.moveSelection(self.instance.moveLeft)
		else:
			self.instance.moveSelection(self.instance.moveUp)

	def moveDown(self):
		#Log.i("[CSP]")
		if self.styleModeTemplate != eListbox.layoutVertical:
			self.instance.moveSelection(self.instance.moveRight)
		else:
			self.instance.moveSelection(self.instance.moveDown)

	def setItemHeight(self, configElement = None):
		if self.useTemplates and config.usage.configselection_style.value != "default":
			#print("[CSP] ServiceListOwn setItemHeight ignore on useTemplates")
			return
		if (config.usage.configselection_bigpicons.value or config.usage.configselection_secondlineinfo.value != "0" or config.usage.configselection_showeventnameunderservicename.value) and self.mode == self.MODE_FAVOURITES:
			self.l.setItemHeight(self.itemHeightHigh)
			#print("[CSP] ServiceListOwn setItemHeightBig",self.itemHeightHigh)
			if self.instance is not None and self.selectionPixmapBig:
				self.instance.setSelectionPicture(self.selectionPixmapBig)
		else:
			self.l.setItemHeight(self.itemHeight)
			#print("[CSP] ServiceListOwn setItemHeight",self.itemHeight)
			if self.instance is not None and self.selectionPixmapStandard:
				self.instance.setSelectionPicture(self.selectionPixmapStandard)

	def setDVBIcons(self, ConfigElement=None):
		if (config.usage.configselection_showdvbicons.value and (config.usage.configselection_style.value == "default" or not self.useTemplates)) or (config.usage.configselection_style.value != "default" and self.useTemplates):
			print("[CSP] set DVBIcons on - style: %s, useTemplate: %s, config: %s" % (config.usage.configselection_style.value, self.useTemplates, config.usage.configselection_showdvbicons.value))
			self.picDVB_S = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "ico_dvb_s-fs8.png"))
			self.picDVB_C = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "ico_dvb_c-fs8.png"))
			self.picDVB_T = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "ico_dvb_t-fs8.png"))
			self.picStreaming = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "ico_streaming-fs8.png"))
		else:
			print("[CSP] set DVBIcons off - style: %s, useTemplate: %s, config: %s" % (config.usage.configselection_style.value, self.useTemplates, config.usage.configselection_showdvbicons.value))
			self.picDVB_S = None
			self.picDVB_C = None
			self.picDVB_T = None
			self.picStreaming = None

	def _buildOptionEntryProgressBar(self, event, xoffset, width, height):
		#Log.i("[CSP]")
		percent = 0
		progressW = self._progressBarWidth()
		progressH = self._componentSizes.get(self.KEY_PROGRESS_BAR_HEIGHT, 8)
		if event and event.getDuration():
			now = int(time())
			percent = 100 * (now - event.getBeginTime()) / event.getDuration()
		top = int((height - progressH) / 2)
		showeventnameunderservicename = config.usage.configselection_showeventnameunderservicename.value
		progressbarPosition = config.usage.configselection_progressbarposition.value
		if showeventnameunderservicename and self.mode != self.MODE_NORMAL and progressbarPosition != "0":
			top = int((height - self.serviceInfoHeight - progressH) / 2)
		if self.picServiceEventProgressbar is None:
			return(eListboxPythonMultiContent.TYPE_PROGRESS, xoffset, top, progressW, progressH, percent, 1, self.serviceEventProgressbarColor, self.serviceEventProgressbarColorSelected, self.serviceEventProgressbarBackColor, self.serviceEventProgressbarBackColorSelected)
		else:
			return(eListboxPythonMultiContent.TYPE_PROGRESS_PIXMAP, xoffset, top, progressW, progressH, percent, self.picServiceEventProgressbar, 1, self.serviceEventProgressbarBorderColor, self.serviceEventProgressbarBorderColorSelected, self.serviceEventProgressbarBackColor, self.serviceEventProgressbarBackColorSelected)

	def _buildOptionEntryServicePixmap(self, service):
		pixmap = None
		if service.flags & eServiceReference.isMarker:
			pixmap = self.picMarker
		elif service.flags & eServiceReference.isGroup:
			pixmap = self.picServiceGroup
		elif service.flags & eServiceReference.isDirectory:
			pixmap = self.picFolder
		else:
			if service.getPath():
				pixmap = self.picStreaming
			else:
				orbpos = service.getUnsignedData(4) >> 16;
				if orbpos == 0xFFFF:
					pixmap = self.picDVB_C
				elif orbpos == 0xEEEE:
					pixmap = self.picDVB_T
				else:
					pixmap = self.picDVB_S
		return pixmap

	#own function for valisepg to show primtime
	def getEventFromService(self, service):
		info = self.service_center.info(service)
		event = info and info.getEvent(service)
		return event

	#own function for valisepg to show primtime
	def getEventNameFromEvent(self, event):
		return event.getEventName()

	#own function for valisepg to show timersymbol on primetime-eventlist
	def getPrimeTimeClockPixmap(self, refstr, beginTime, endTime, eventId): 
		pre_clock = 1
		post_clock = 2
		clock_type = 0
		for x in self.session.nav.RecordTimer.timer_list:
			if x.service_ref.ref.toString() == refstr:
				#print "[CSP] timer", x.name, x.service_ref.ref.toString(), x.eit, eventId
				if x.eit == eventId:
					if x.begin > int(time()): #timer in future
						return 5, LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock.png'))
					else: #current timer
						return 2, LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock.png'))
				beg = x.begin
				end = x.end
				if beginTime > beg and beginTime < end and endTime > end:
					clock_type |= pre_clock
				elif beginTime < beg and endTime > beg and endTime < end:
					clock_type |= post_clock
		if clock_type == 0:
			return 0, LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_add.png'))
		elif clock_type == pre_clock:
			return 3, LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_pre.png'))
		elif clock_type == post_clock:
			return 1, LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_post.png'))
		else:
			return 4, LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_prepost.png'))

	def getCleanExtDescription(self, event):
			name = event.getEventName().strip(" ").strip("\n").strip("\xc2\x8a")
			desc = event.getShortDescription().strip(" ").strip("\n").strip("\xc2\x8a") #.replace("\n"," - ")
			ext = event.getExtendedDescription().lstrip(" ").lstrip("\n").lstrip("\xc2\x8a").replace("\n"," ").replace("\xc2\x8a\xc2\x8a","\n")
			if desc and desc != event.getEventName():
				desc_list = desc.split("\n")
				if desc_list[0] == name:
					desc_list.pop(0)
				desc = " - ".join(desc_list).strip()
				if desc:
					desc = "%s" % (desc,)
			else:
				desc = ""
			if desc and ext:
				#print("[CSP] getCleanExtDescription 1 desc", ext)
				return "%s - %s" % (desc, ext)
			elif desc:
				return "%s" % (desc,)
			else:
				#print("[CSP] getCleanExtDescription 2 desc", ext)
				return "%s" % (ext,)
	
	def getProviderName(self, service):
		serviceHandler = eServiceCenter.getInstance()
		info = serviceHandler.info(service)
		if info is None:
			return ""
		provider = info.getInfoString(service,iServiceInformation.sProvider) or _("unknown")
		return provider
	
	def buildOptionEntry(self, service, **args):
		#Log.i("[CSP]")
		width = self.l.getItemSize().width()
		width -= self._componentSizes.get(self.KEY_END_MARGIN, 5)
		height = self.l.getItemSize().height()
		selected = args["selected"]
		sizes = componentSizes["EPGList"] # getIconWidth for Timersymbol on ShowPrimeTime
		iconWidth = sizes.get("iconWidth", 21) # getIconWidth for Timersymbol on ShowPrimeTime
		res = [ None ]
		showListNumbers = config.usage.configselection_showlistnumbers.value
		if isMerlin:
			listNumbersAlignment = config.usage.configselection_listnumbersalignment.value
		listNumerPosition = config.usage.configselection_listnumbersposition.value
		showPicons = self.mode == self.MODE_FAVOURITES and config.usage.configselection_showpicons.value
		showServiceName = self.mode == self.MODE_NORMAL or (self.mode == self.MODE_FAVOURITES and config.usage.configselection_showservicename.value)
		showEventNameUnderServiceName = config.usage.configselection_showeventnameunderservicename.value
		showProgressbar = config.usage.show_event_progress_in_servicelist.value
		progressbarPosition = config.usage.configselection_progressbarposition.value
		columnStyle = config.usage.configselection_columnstyle.value
		additionalposition = config.usage.configselection_additionaltimedisplayposition.value
		bigPicons = self.mode == self.MODE_FAVOURITES and config.usage.configselection_bigpicons.value
		secondlineinfo = config.usage.configselection_secondlineinfo.value
		# get service information
		service_info = self.service_center.info(service)
		isMarker = service.flags & eServiceReference.isMarker
		isPlayable = not(service.flags & eServiceReference.isDirectory or isMarker)
		recording = self._checkHasRecording(service, isPlayable)
		event = self.getEventFromService(service)
		
		# get addtimedisplay and calculate addtimedisplayWidth
		addtimedisplay, addtimedisplayWidth = self._buildOptionEntryAddTimeDisplay(event, isPlayable, columnStyle)
		
		# set timerstatus if show primetime
		timertyp = 0
		timerpng = None
		if self.showPrimeTime:
			addtimedisplay = ""
			addtimedisplayWidth = 0
			if event:
				ev = parseEvent(event)
				timertyp, timerpng = self.getPrimeTimeClockPixmap(service.toString(), ev[0], ev[1], ev[4])
				#print "[CSP] timertyp, service", timertyp, service.toString(), ev[2]
			if recording and timertyp != 2: recording = False #don't show current record on PrimeTime
		
		marked = 0
		if self.l.isCurrentMarked() and selected:
			marked = 2
		elif self.l.isMarked(service):
			if selected:
				marked = 2
			else:
				marked = 1
		if marked == 1: #  marked
			additionalInfoColor = serviceDescriptionColor = forgroundColor = self.markedForeground
			backgroundColor = self.markedBackground
			forgroundColorSel = backgroundColorSel = additionalInfoColorSelected = serviceDescriptionColorSelected = None
		elif marked == 2: # marked and selected
			additionalInfoColorSelected = serviceDescriptionColorSelected = forgroundColorSel = self.markedForegroundSelected
			backgroundColorSel = self.markedBackgroundSelected
			forgroundColor = additionalInfoColor = serviceDescriptionColor = backgroundColor = None
		else:
			if recording:
				forgroundColor = additionalInfoColor = serviceDescriptionColor = self.recordingColor
				forgroundColorSel = additionalInfoColorSelected = serviceDescriptionColorSelected = self.recordingColorSelected
				backgroundColor = backgroundColorSel = None
			else:
				forgroundColor = forgroundColorSel = backgroundColor = backgroundColorSel = None
				serviceDescriptionColor = self.serviceDescriptionColor
				serviceDescriptionColorSelected = self.serviceDescriptionColorSelected
				additionalInfoColor = self.additionalInfoColor
				additionalInfoColorSelected = self.additionalInfoColorSelected

		if (marked == 0 and isPlayable and service_info and not service_info.isPlayable(service, self.is_playable_ignore)):
			forgroundColor = forgroundColorSel = additionalInfoColor = additionalInfoColorSelected = serviceDescriptionColor = serviceDescriptionColorSelected = self.serviceNotAvail

		# set windowstyle
		if marked > 0:
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 0, 0, width , height, 1, RT_HALIGN_RIGHT, "", forgroundColor, forgroundColorSel, backgroundColor, backgroundColorSel))

		info = self.service_center.info(service)
		serviceName = info and info.getName(service) or "<n/a>"
		#event = info and info.getEvent(service)
		index = self.getCurrentIndex()
		xoffset = self._componentSizes.get(self.KEY_BEGIN_MARGIN, 5)
		pixmap = self._buildOptionEntryServicePixmap(service)
		drawProgressbar = isPlayable and showProgressbar and not self.showPrimeTime
		progressBarWidth = self._progressBarWidth(withOffset=True)
		textOffset = self._componentSizes.get(self.KEY_TEXT_OFFSET, 10)
		
		if self.useTemplates and config.usage.configselection_style.value != "default":

			#service number as formated text
			markers_before = self.l.getNumMarkersBeforeCurrent()
			servicenumberformat = config.usage.configselection_listnumberformat.value
			servicenumber_text = servicenumberformat % (self.numberoffset + index + 1 - markers_before)
			if config.usage.configselection_showlistnumbers.value:
				channelnumberServicename = servicenumber_text + " " + serviceName
			else:
				channelnumberServicename = serviceName
			
			#picon
			picon = None
			if isPlayable:
				picon = self._buildOptionEntryServicePicon(service)
			
			#progressbar percent
			percent = 0
			if event and event.getDuration():
				now = int(time())
				percent = 100 * (now - event.getBeginTime()) / event.getDuration()
			
			#eventname and short description
			eventName = ""
			eventName_shortdesc = ""
			eventName_fulldesc = ""
			time_remaining = ""
			time_percent = ""
			nowEventTime = ""
			eventImage = None
			if event:
				eventName = self.getEventNameFromEvent(event)
				eventName_shortdesc = event.getShortDescription()
				eventName_fulldesc = self.getCleanExtDescription(event)
				
				now = int(time())
				time_remaining = "+%d min" % int((event.getBeginTime() + event.getDuration() - now) // 60)
				time_percent   = "%d%%" % int(100 * (now - event.getBeginTime()) // event.getDuration())
				
				beginTime = localtime(event.getBeginTime())
				endTime = localtime(event.getBeginTime() + event.getDuration())
				nowEventTime = "%02d:%02d - %02d:%02d" % (beginTime[3],beginTime[4],endTime[3],endTime[4])
				
				# load EventImages if EventDataManager is installed
				if EventDataManager_installed:
					#try to load Eventimage
					eventId = "%s_%s" % (event.getEventId(), serviceName)
					#print("[CSP] before check downloadEventImage", eventId, event.getEventName(), serviceName)
					if eventId not in self.images_downloader_list:
						existFilename = downloadEventImage(event, boundFunction(self.downloadEventImageCallback, index, eventId), boundFunction(self.downloadEventInfoErrorInfo, eventId), timeout=5)
						if existFilename == True: # not exist, but download live
							#print("[CSP] add event", eventId)
							self.images_downloader_list.append(eventId)
							eventImageName = ""
						elif existFilename:
							eventImageName = existFilename
						else:
							eventImageName = getExistEventImageName(eventName.encode('utf-8'), event.getBeginTime())
						
						if not eventImageName: # try to load backdrop as fallback
							existFilename = downloadContentImage(event, boundFunction(self.downloadEventImageCallback, index, eventId), boundFunction(self.downloadEventInfoErrorInfo, eventId), imageType="backdrop")
							if existFilename == True: # not existing, but download from url
								#print("[CSP] add event", eventId)
								self.images_downloader_list.append(eventId)
								eventImageName = ""
							elif existFilename:
								eventImageName = existFilename
						
						#print("[CSP] found eventImageName", eventImageName)
						if fileExists(eventImageName):
							#print("[CSP] load EventImage as Pixmap", eventImageName)
							self.scale = AVSwitch().getFramebufferScale()
							self.picload.setPara((300, 170, self.scale[0], self.scale[1], False, 0, "#FF000000"))
							res = self.picload.startDecode(eventImageName, False)
							if not res:
								ptr = self.picload.getData()
								if ptr != None:
									eventImage = ptr
				
			self.eEPGCache = eEPGCache.getInstance()
			#next event
			moreNextEvents = ""
			if self.showPrimeTime:
				event_next = self.eEPGCache.lookupEventTime(service,event.getBeginTime()+event.getDuration()+60)
			else:
				event_next = self.eEPGCache.lookupEventTime(service, -1, 1)
			if event_next:
				beginTime = localtime(event_next.getBeginTime())
				endTime = localtime(event_next.getBeginTime()+event_next.getDuration())
				nextEventTimeName = "%02d:%02d - %02d:%02d %s" % (beginTime[3],beginTime[4],endTime[3],endTime[4], event_next.getEventName())
				nextEventTime = "%02d:%02d - %02d:%02d" % (beginTime[3],beginTime[4],endTime[3],endTime[4])
				nextEventName = "%s" % event_next.getEventName()
				
				# for moreNextEventsList from Template-Option 'moreNextEvents'
				if self.styleMoreNextEvents and len(self.styleMoreNextEvents)>1 and self.styleMoreNextEvents[0]:
					moreNextEvents = self.getMoreEventsTextList(service, event_next, beginTime, self.styleMoreNextEvents[0],self.styleMoreNextEvents[1])
			
			else:
				nextEventTimeName = "%s: n/a" % _("upcoming event")
				nextEventTime = "n/a"
				nextEventName = "%s: n/a" % _("upcoming event")
				if self.styleMoreNextEvents:
					moreNextEvents = _("no more next events")
			
			#primetime event
			now = localtime(time())
			dt = datetime(now.tm_year, now.tm_mon, now.tm_mday, 20, 15)
			self.stylePrimeTimeHeading = _("Primetime")
			if time() > mktime(dt.timetuple()):
				dt += timedelta(days=1) # skip to next day...
				self.stylePrimeTimeHeading = _("Primetime next day")
			primeTime = int(mktime(dt.timetuple()))
			primetimeEvent = self.eEPGCache.lookupEventTime(service, primeTime)
			primetimeEvents = ""
			if primetimeEvent:
				# for normal primetime-values time and name
				beginTime = localtime(primetimeEvent.getBeginTime())
				endTime = localtime(primetimeEvent.getBeginTime()+primetimeEvent.getDuration())
				primetimeEventTime = "%02d:%02d - %02d:%02d" % (beginTime[3],beginTime[4],endTime[3],endTime[4])
				primetimeEventName = "%s" % primetimeEvent.getEventName()
				
				# for primetimeEventsList from Template-Option 'primetimeEvents'
				if self.stylePrimetimeEvents and len(self.stylePrimetimeEvents)>1 and self.stylePrimetimeEvents[0]:
					primetimeEvents = self.getMoreEventsTextList(service, primetimeEvent, beginTime, self.stylePrimetimeEvents[0],self.stylePrimetimeEvents[1])
			
			else:
				primetimeEventTime = "n/a"
				primetimeEventName = "%s: n/a" % _("primetime event")
				if self.stylePrimetimeEvents:
					primetimeEvents = _("no primetime events")
			
			# for Merlin Shaderman tag bouquet services
			picInBouquet = None
			if isMerlin and not isMarker and isPlayable:
				if self.picInBouquet is not None:
					if service in self.bouquetServices and self.mode == self.MODE_NORMAL:
						picInBouquet = self.picInBouquet
			
			providerName = ""
			providerPicon = None
			if isPlayable:
				providerName = self.getProviderName(service)
				providerPicon = self.providerPiconLoader.getPicon(providerName)
			
			res = [ None ]
			#if template.startswith("MODE_FAVOURITES") and pixmap is not None: # on MARKER
			if isMarker: # on MARKER
				marker_text = serviceName
				marker_icon = pixmap
				serviceName = eventName = nextEventTimeName = nextEventTime = nextEventName = pixmap = picon = servicenumber_text = primetimeEventName = primetimeEventTime = primetimeEvents = moreNextEvents = self.stylePrimeTimeHeading = channelnumberServicename = providerName = providerPicon = eventImage = serviceNameEventName = None
				percent = -1 # on -1 don't paint the progressbar
			else:
				# on service-entries
				marker_text = None
				marker_icon = None
				
				#set default picon if picon not found
				if picon is None:
					tmp = resolveFilename(SCOPE_CURRENT_SKIN, "picon_default_csp.png")
					if fileExists(tmp):
						pngname = tmp
					else:
						tmp = resolveFilename(SCOPE_CURRENT_SKIN, "picon_default.png")
						if fileExists(tmp):
							pngname = tmp
						else:
							pngname = resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/picon_default.png")
					picon = LoadPixmap(cached = True, path = pngname)
				
				serviceNameEventName = "%s (%s)" % (channelnumberServicename, eventName)
				
				if not eventName:
					eventName = _("no event data") + " (%s)" % channelnumberServicename
					serviceNameEventName = "%s (%s)" % (channelnumberServicename, _("no event data"))
				if not eventName_shortdesc:
					eventName_shortdesc = _("no event data")
				if not eventName_fulldesc:
					eventName_fulldesc = _("no event data")
				
				if not eventImage:
					eventImage = picon
			
			res.extend((channelnumberServicename, eventName, pixmap , picon, percent, self.serviceEventProgressbarColor, self.serviceEventProgressbarColorSelected, self.serviceEventProgressbarBackColor, self.serviceEventProgressbarBackColorSelected, forgroundColor, forgroundColorSel, backgroundColor, backgroundColorSel, additionalInfoColor, additionalInfoColorSelected, serviceDescriptionColor, serviceDescriptionColorSelected, servicenumber_text, addtimedisplay, eventName_shortdesc, nextEventTimeName, time_remaining, time_percent, marker_text, self.picServiceEventProgressbar, eventName_fulldesc, marker_icon, nextEventName, nextEventTime, nowEventTime, primetimeEventName, primetimeEventTime, moreNextEvents, primetimeEvents, self.stylePrimeTimeHeading, channelnumberServicename, picInBouquet, providerName, providerPicon, eventImage, serviceNameEventName, 750, RT_VALIGN_TOP))
			
			#1 = serviceName 						# text=1 (with channelnummer by setup-option)
			#2 = eventName							# text=2
			#3 = FolderPic							# png=3
			#4 = Picon 								# png=4
			#5 = progress percent value				# percent=-5
			#6 = progressbar foreColor				# foreColor=MultiContentTemplateColor(6)
			#7 = progressbar foreColorSelected		# ...=MultiContentTemplateColor(7)
			#8 = progressbar backColor				# backColor=MultiContentTemplateColor(8)
			#9 = progressbar backColorSelected		# backColorSelected=MultiContentTemplateColor(9)
			#10 = forgroundColor					# ...=MultiContentTemplateColor(10)
			#11 = forgroundColorSel					# ...=MultiContentTemplateColor(11)
			#12 = backgroundColor					# ...=MultiContentTemplateColor(12)
			#13 = backgroundColorSel				# ...=MultiContentTemplateColor(13)
			#14 = additionalInfoColor				# ...=MultiContentTemplateColor(14)
			#15 = additionalInfoColorSelected		# ...=MultiContentTemplateColor(15)
			#16 = serviceDescriptionColor			# ...=MultiContentTemplateColor(16)
			#17 = serviceDescriptionColorSelected	# ...=MultiContentTemplateColor(17)
			#18 = servicenumber_text				# text=18
			#19 = addtimedisplay_text				# text=19
			#20 = eventName_shortdesc_text			# text=20
			#21 = nextEventTimeName_text			# text=21
			#22 = time_remaining_text				# text=22
			#23 = time_percent_text					# text=23
			#24 = marker_text						# text=24
			#25 = picServiceEventProgressbar		# png=25
			#26 = eventName_fullDescription_text	# text=26
			#27 = marker_icon						# png=27
			#28 = nextEventName_text				# text=28
			#29 = nextEventTime_text				# text=29 for example '14.30 - 15.30'
			#30 = nowEventTime_text					# text=30 for example '12.00 - 14.30'
			#31 = primetimeEventName_text			# text=31
			#32 = primetimeEventTime_text			# text=32 for example '20.15 - 21.45'
			#33 = moreNextEventsList_text			# text=33 like EventList-Converter
			#34 = primetimeEventList_text			# text=34 like EventList-Converter
			#35 = primetimeHeading_text				# text=35 (primetime or primetime next day)
			#36 = channelnumberServicename_text		# text=36 (with channelnummer by setup-option)
			#37 = picInBouquet (only merlin)		# png=37 (for merlin tag bouquetServices)
			#38 = providerName_text					# text=38 (show the providername of the service)
			#39 = providerPicon						# png=39 (in subfolder 'PiconProvider' in picon-folder)
			#40 = eventImage						# png=40 (load eventImages from EventDataManager)
			#41 = serviceNameEventName				# text=41 (show 'servicename (eventname)')
			#42 = width								# test-value
			#43 = valign							# test-value
			
			#print("[CSP] ProviderName, ProviderPicon", providerName, providerPicon)
			#print("[CSP] res", res)
			return res # exit if use template-style
		
		
		#following only if not use template-style
		#print("[CSP] create entry without template")
		
		# pic for marker, folder, servicegroup or dvb_pic
		if pixmap is not None:
			pixmap_size = self.picMarker.size()
			pix_width = pixmap_size.width()
			pix_height = pixmap_size.height()
			ypos = (height - pix_height) / 2
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xoffset, ypos, pix_width, pix_height, pixmap))
			xoffset += pix_width + self._componentSizes.get(self.KEY_PICON_OFFSET, 8)
		
		#for Merlin
		#elif isMerlin and config.usage.configselection_showdvbicons.value:
		elif config.usage.configselection_showdvbicons.value:
			# this is a hack. We assume as in the above function that the marker pic is always available
			pixmap_size = self.picMarker.size()
			pix_width = pixmap_size.width()
			xoffset += pix_width + self._componentSizes.get(self.KEY_PICON_OFFSET, 8)

		# for Merlin Shaderman tag bouquet services
		if isMerlin and self.showBouquetEntries and isPlayable:
			pixmap = self.picInBouquet
			if pixmap is not None:
				pixmap_size = pixmap.size()
				pix_width = pixmap_size.width()
				pix_height = pixmap_size.height()
				if service in self.bouquetServices and self.mode == self.MODE_NORMAL:
					ypos = (height - pix_height) / 2
					res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xoffset, ypos, pix_width, pix_height, pixmap))
				else:
					res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, 0, pix_width , pix_height, 1, RT_HALIGN_LEFT, "", forgroundColor, forgroundColorSel, backgroundColor, backgroundColorSel))
				xoffset += pix_width + self._componentSizes.get(self.KEY_INBOUQUET_OFFSET, 8)

		
		# servicenumber on first position
		listnumberwidth = 0
		if self.mode != self.MODE_NORMAL:
			if not (service.flags & eServiceReference.isMarker) and ((showListNumbers and not showServiceName and columnStyle) or (listNumerPosition=="0" and showListNumbers)):
				markers_before = self.l.getNumMarkersBeforeCurrent()
				servicenumberformat = config.usage.configselection_listnumberformat.value
				text = servicenumberformat % (self.numberoffset + index + 1 - markers_before)
				nameWidthmax = self._componentSizes.get(self.KEY_SERVICE_NUMBER_WIDTH, 50)
				dotWidth = 0
				if servicenumberformat == "%d.": # add dot to field-width if show with dot
					dotWidth = self._calcTextWidth(".", font=self.serviceNumberFont, size=eSize(nameWidthmax,0))
				listnumberwidth = nameWidthmax + dotWidth
				#for Merlin
				if isMerlin and listNumbersAlignment == "0": 
					align = RT_HALIGN_LEFT
				else:
					align = RT_HALIGN_RIGHT
				res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, 0, listnumberwidth , height, 1, align|RT_VALIGN_CENTER, text, forgroundColor, forgroundColorSel, backgroundColor, backgroundColorSel))
				xoffset += listnumberwidth + textOffset

		# picons
		if isPlayable and showPicons:
			picon = self._buildOptionEntryServicePicon(service)
			if bigPicons:
				pix_width = self._componentSizes.get(self.KEY_PICON_WIDTH_BIG, 108)
			else:
				pix_width = self._componentSizes.get(self.KEY_PICON_WIDTH, 58)
			if picon:
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xoffset, 0, pix_width, height, picon))
			xoffset += pix_width
			xoffset += self._componentSizes.get(self.KEY_PICON_OFFSET, 8)

		# progressbar between servicenumber and servicename
		if drawProgressbar and progressbarPosition == "0":
			res.append(self._buildOptionEntryProgressBar(event, xoffset, width, height))
			xoffset += progressBarWidth

		if columnStyle:
			rwidth = 0
			addoffset = 0
			servicenameWidth = 0
			# servicename
			if (isPlayable and showServiceName) or not isPlayable:
				if isPlayable:
					rwidth = servicenameWidth # space for servicename
				else:
					rwidth = width - xoffset # space for servicename
				xoffset_ServiceName = xoffset
				servicenameWidth = width - xoffset
				nheight = height
				if self.mode != self.MODE_NORMAL:
					# servicenumber if together with servicename
					if not (service.flags & eServiceReference.isMarker) and showListNumbers and listNumerPosition=="1":
						if showEventNameUnderServiceName and showServiceName: # set height for show in second line
							nheight = height - self.serviceInfoHeight
						markers_before = self.l.getNumMarkersBeforeCurrent()
						servicenumberformat = config.usage.configselection_listnumberformat.value
						text = servicenumberformat % (self.numberoffset + index + 1 - markers_before)
						nameWidthmax = self._componentSizes.get(self.KEY_SERVICE_NUMBER_WIDTH, 50)
						listnumberwidth = self._calcTextWidth(text, font=self.serviceNumberFont, size=eSize(width,0)) + textOffset
						res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, 0, listnumberwidth , nheight, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, text, forgroundColor, forgroundColorSel, backgroundColor, backgroundColorSel))
						xoffset += listnumberwidth 
						servicenameWidth = rwidth - listnumberwidth
					if showEventNameUnderServiceName and showServiceName and not isMarker:
						nheight = height - self.serviceInfoHeight
				
				# autocalculate the servicenameWidth to new max value from percent in the settings
				if not ((service.flags & eServiceReference.isMarker) or (service.flags & eServiceReference.isDirectory) or (service.flags & eServiceReference.isGroup)):
					restWidth = width
					restWidth -= xoffset_ServiceName
					progresswidth  = self._progressBarWidth(withOffset=True, withProgressBarSize=False) 
					progresswidth += self._progressBarWidth(withOffset=True, withProgressBarSize=True)
					if not drawProgressbar or (showEventNameUnderServiceName and secondlineinfo != "0" and self.mode == self.MODE_FAVOURITES):
						progresswidth = 0
					restWidth -= progresswidth
					addInfoWidth = addtimedisplayWidth
					if addtimedisplay == "" or (showEventNameUnderServiceName and secondlineinfo != "0" and self.mode == self.MODE_FAVOURITES):
						addInfoWidth = 0
					restWidth -= addInfoWidth
					percent_val = int(config.usage.configselection_servicenamecolwidth_percent.value)
					#calculate the eventnamewidth with percent from settings (of free restWidth)
					eventnamewidth = restWidth * ((100-percent_val)/float(100)) 
					if showEventNameUnderServiceName and self.mode == self.MODE_FAVOURITES and secondlineinfo == "0":
						eventnamewidth = 0
					servicenameWidth = restWidth - eventnamewidth
					if showListNumbers and listNumerPosition=="1" and self.mode == self.MODE_FAVOURITES:
						servicenameWidth -= listnumberwidth
				# end autocalculate the servicenameWidth to new max value from percent in the settings
				
				# servicename
				res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, 0, servicenameWidth , nheight, 2, RT_HALIGN_LEFT|RT_VALIGN_CENTER, serviceName, forgroundColor, forgroundColorSel, backgroundColor, backgroundColorSel))
				xoffset += servicenameWidth + textOffset
				#if service description under servicename set position to after service description
				if additionalposition == "0" and showEventNameUnderServiceName and drawProgressbar and progressbarPosition == "1" and self.mode == self.MODE_FAVOURITES:
					progressbarPosition = "2"
				# progressbar between servicename and service description
				if event and isPlayable and drawProgressbar and progressbarPosition == "1":
					res.append(self._buildOptionEntryProgressBar(event, xoffset, width, height))
					if not showEventNameUnderServiceName or self.mode != self.MODE_FAVOURITES:	
						xoffset += progressBarWidth # move xoffset only if not showEventNameUnderServiceName
			if event and isPlayable:
				rwidth = width - xoffset
				if drawProgressbar and progressbarPosition == "2":
					rwidth -= self._progressBarWidth(withOffset=True, withProgressBarSize=False)
					rwidth -= self._progressBarWidth(withOffset=True, withProgressBarSize=True)
				if addtimedisplay != "" :
					if additionalposition == "0":
						# add time text before service description
						iheight = height
						itop = 0
						if showEventNameUnderServiceName and showServiceName and self.mode == self.MODE_FAVOURITES:
							iheight = self.serviceInfoHeight
							itop = int((height - 2 * self.serviceInfoHeight) / 2)
						axoffset = xoffset
						if showEventNameUnderServiceName and drawProgressbar and progressbarPosition != "2" and self.mode == self.MODE_FAVOURITES:
							axoffset += progressBarWidth
							#pass
						if showEventNameUnderServiceName:
							axoffset -= textOffset*2 #add offset at the end of the add_text
						res.append((eListboxPythonMultiContent.TYPE_TEXT, axoffset, itop, addtimedisplayWidth, iheight, 0, RT_HALIGN_RIGHT|RT_VALIGN_CENTER, addtimedisplay, additionalInfoColor, additionalInfoColorSelected, backgroundColor, backgroundColorSel))
						addoffset = addtimedisplayWidth + textOffset
						if not showEventNameUnderServiceName or self.mode != self.MODE_FAVOURITES:
							xoffset += addoffset # move xoffset only if not showEventNameUnderServiceName
						rwidth -= addoffset
					elif additionalposition == "1":
						rwidth -= addtimedisplayWidth + textOffset
				
				# service description
				if (secondlineinfo != "0" or showEventNameUnderServiceName) and self.mode == self.MODE_FAVOURITES:
					top = 0
					sheight = self.serviceInfoHeight
					sxoffset = xoffset
					if showEventNameUnderServiceName: # eventname in second line
						eWidth = servicenameWidth
						if showListNumbers and listNumerPosition=="1":
							eWidth += listnumberwidth
						if showServiceName:
							top = int((height - 2 * self.serviceInfoHeight) / 2) + self.serviceInfoHeight
							sxoffset = xoffset_ServiceName
							if secondlineinfo == "0":
								eWidth = width - xoffset_ServiceName
						if self.showPrimeTime and timertyp != 0:
							res.extend((
								(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, sxoffset, top + sheight/2-iconWidth/2, iconWidth, iconWidth, timerpng), 
								(eListboxPythonMultiContent.TYPE_TEXT, sxoffset + iconWidth + textOffset, top, eWidth-iconWidth-textOffset, sheight, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, self.getEventNameFromEvent(event), serviceDescriptionColor, serviceDescriptionColorSelected, backgroundColor, backgroundColorSel)
							))
						else:
							res.append((eListboxPythonMultiContent.TYPE_TEXT, sxoffset, top, eWidth, sheight, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, self.getEventNameFromEvent(event), serviceDescriptionColor, serviceDescriptionColorSelected, backgroundColor, backgroundColorSel))
					else: # eventname in next column (don't use second line)
						sheight = self.serviceInfoHeight
						top = int((height - 2 * self.serviceInfoHeight) / 2)
						if self.showPrimeTime and timertyp != 0:
							res.extend((
								(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xoffset, top + sheight/2-iconWidth/2, iconWidth, iconWidth, timerpng), 
								(eListboxPythonMultiContent.TYPE_TEXT, xoffset + iconWidth + textOffset, top, rwidth-iconWidth-textOffset, sheight, 3, RT_HALIGN_LEFT|RT_VALIGN_CENTER, self.getEventNameFromEvent(event), serviceDescriptionColor, serviceDescriptionColorSelected, backgroundColor, backgroundColorSel)
							))
						else:
							res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, top, rwidth, sheight, 3, RT_HALIGN_LEFT|RT_VALIGN_CENTER, self.getEventNameFromEvent(event), serviceDescriptionColor, serviceDescriptionColorSelected, backgroundColor, backgroundColorSel))
					text = ""
					if secondlineinfo == "1": # shortdescription
						text = event.getShortDescription()
					elif secondlineinfo == "2": # next event with time
						if self.showPrimeTime:
							event_next = eEPGCache.getInstance().lookupEventTime(service,event.getBeginTime()+event.getDuration()+60)
						else:
							event_next = eEPGCache.getInstance().lookupEventTime(service, -1, 1)
						if event_next:
							beginTime = localtime(event_next.getBeginTime())
							endTime = localtime(event_next.getBeginTime()+event_next.getDuration())
							text = "%02d:%02d - %02d:%02d %s" % (beginTime[3],beginTime[4],endTime[3],endTime[4], event_next.getEventName())
						else:
							text = "%s: n/a" % _("upcoming event")
					awidth = rwidth
					if showEventNameUnderServiceName: 
						awidth = width - xoffset - textOffset # use full width for addInfo if showEventNameUnderServiceName
					# add text-value for addInfo in second line
					top = int((height - 2 * self.serviceInfoHeight) / 2) + self.serviceInfoHeight
					if secondlineinfo != "0":
						if secondlineinfo == "2" and self.showPrimeTime and event_next:
							ev = parseEvent(event_next)
							next_timertyp, next_timerpng = self.getPrimeTimeClockPixmap(service.toString(), ev[0], ev[1], ev[4])
							if next_timertyp !=0:
								res.extend((
									(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xoffset, top + sheight/2-iconWidth/2, iconWidth, iconWidth, next_timerpng),
									(eListboxPythonMultiContent.TYPE_TEXT, xoffset+ iconWidth + textOffset, top, awidth-iconWidth-textOffset, self.serviceInfoHeight, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, text, additionalInfoColor, additionalInfoColorSelected, backgroundColor, backgroundColorSel)
								))
							else:
								res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, top, awidth, self.serviceInfoHeight, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, text, additionalInfoColor, additionalInfoColorSelected, backgroundColor, backgroundColorSel))
						else:
							res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, top, awidth, self.serviceInfoHeight, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, text, additionalInfoColor, additionalInfoColorSelected, backgroundColor, backgroundColorSel))
				else:
					# add eventname in next column (if not use the second line)
					#print "[CSP] showPrimeTime, timertyp, EventName", self.showPrimeTime, timertyp, self.getEventNameFromEvent(event)
					if self.showPrimeTime and timertyp != 0:
						res.extend((
							(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, xoffset, height/2-iconWidth/2, iconWidth, iconWidth, timerpng), 
							(eListboxPythonMultiContent.TYPE_TEXT, xoffset + iconWidth + textOffset, 0, rwidth-iconWidth-textOffset, height, 3, RT_HALIGN_LEFT|RT_VALIGN_CENTER, self.getEventNameFromEvent(event), serviceDescriptionColor, serviceDescriptionColorSelected, backgroundColor, backgroundColorSel)
						))
					else:
						res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, 0, rwidth, height, 3, RT_HALIGN_LEFT|RT_VALIGN_CENTER, self.getEventNameFromEvent(event), serviceDescriptionColor, serviceDescriptionColorSelected, backgroundColor, backgroundColorSel))
				
				# progressbar after service description
				xoffset += rwidth
				if drawProgressbar and progressbarPosition == "2":
					if showEventNameUnderServiceName and addtimedisplay != "" and self.mode == self.MODE_FAVOURITES:
						xoffset += addoffset # move xoffset if showEventNameUnderServiceName
					xoffset += self._progressBarWidth(withOffset=True, withProgressBarSize=False)
					res.append(self._buildOptionEntryProgressBar(event, xoffset, width, height))
					xoffset += progressBarWidth
				
				# add time text at last position
				if addtimedisplay != "" and additionalposition == "1":
					aheight = height
					atop = 0
					if showEventNameUnderServiceName and showServiceName and self.mode != self.MODE_NORMAL:
						aheight = self.serviceInfoHeight
						atop = int((height - 2 * self.serviceInfoHeight) / 2)
					xoffset += textOffset
					res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, atop, addtimedisplayWidth , aheight, 0, RT_HALIGN_RIGHT|RT_VALIGN_CENTER, addtimedisplay, additionalInfoColor, additionalInfoColorSelected, backgroundColor, backgroundColorSel))

		# normal style, no columnStyle
		else: 
			if event and isPlayable:
				maxLength = width - xoffset
				if drawProgressbar and progressbarPosition == "2":
					# progressbar after service description
					maxLength -= progressBarWidth
				
				sheight = height
				firstxoffset = xoffset
				# set new high if event under servicename
				if showEventNameUnderServiceName and self.mode == self.MODE_FAVOURITES: 
					sheight = height - self.serviceInfoHeight
				# servicenumber
				if self.mode != self.MODE_NORMAL:
					if not (service.flags & eServiceReference.isMarker) and showListNumbers and listNumerPosition=="1":
						markers_before = self.l.getNumMarkersBeforeCurrent()
						servicenumberformat = config.usage.configselection_listnumberformat.value
						text = servicenumberformat % (self.numberoffset + index + 1 - markers_before)
						nameWidthmax = self._componentSizes.get(self.KEY_SERVICE_NUMBER_WIDTH, 50)
						nameWidth = self._calcTextWidth(text, font=self.serviceNumberFont, size=eSize(width,0)) + textOffset
						res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, 0, nameWidth , sheight, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, text, forgroundColor, forgroundColorSel, backgroundColor, backgroundColorSel))
						xoffset += nameWidth 
				
				# servicename without tabstyle
				length = self._calcTextWidth(serviceName, font=self.serviceNameFont, size=eSize(maxLength,0)) + textOffset
				res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, 0, length , sheight, 2, RT_HALIGN_LEFT|RT_VALIGN_CENTER, serviceName, forgroundColor, forgroundColorSel, backgroundColor, backgroundColorSel))
				xoffset += length
				if addtimedisplay != "":
					addtimedisplayFormat = "(%s %s)"
					if showEventNameUnderServiceName and self.mode == self.MODE_FAVOURITES:
						addtimedisplayFormat = "%s %s"
					if additionalposition == "1":
						# add time text after service description
						text = addtimedisplayFormat % (self.getEventNameFromEvent(event), addtimedisplay)
					else:
						# add time text before service description
						text = addtimedisplayFormat % (addtimedisplay, self.getEventNameFromEvent(event))
				else:
					# add eventName
					addtimedisplayFormat = "(%s)"
					if showEventNameUnderServiceName and self.mode == self.MODE_FAVOURITES:
						addtimedisplayFormat = "%s"
					text = addtimedisplayFormat % (self.getEventNameFromEvent(event))
				length = width - xoffset
				if drawProgressbar and progressbarPosition == "2":
					# progressbar after service description - calculate width of service description
					length -= progressBarWidth
				
				# size/pos-Values for add service description from variable text
				dheight = height
				dxoffset = xoffset
				top = 0
				dWidth = length
				fontsize = 3
				# set new size/pos-Values if event under servicename
				if showEventNameUnderServiceName and self.mode == self.MODE_FAVOURITES: 
					top = int((height - 2 * self.serviceInfoHeight) / 2) + self.serviceInfoHeight
					dheight = self.serviceInfoHeight
					dxoffset = firstxoffset
					dWidth = width - firstxoffset
					fontsize = 0
				# add service description from variable text
				if self.showPrimeTime and timertyp != 0:
					res.extend((
						(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, dxoffset, top + dheight/2-iconWidth/2, iconWidth, iconWidth, timerpng), 
						(eListboxPythonMultiContent.TYPE_TEXT, dxoffset + iconWidth + textOffset, top, dWidth-iconWidth-textOffset, dheight, fontsize, RT_HALIGN_LEFT|RT_VALIGN_CENTER, text, serviceDescriptionColor, serviceDescriptionColorSelected, backgroundColor, backgroundColorSel)
					))
				else:
					res.append((eListboxPythonMultiContent.TYPE_TEXT, dxoffset, top, dWidth , dheight, fontsize, RT_HALIGN_LEFT|RT_VALIGN_CENTER, text, serviceDescriptionColor, serviceDescriptionColorSelected, backgroundColor, backgroundColorSel))
				
				# add progressbar after service description
				if drawProgressbar and progressbarPosition == "2":
					xoffset += length + textOffset / 2
					res.append(self._buildOptionEntryProgressBar(event, xoffset, width, height))
			
			# only servicename if don't have an event
			else: 
				sheight = height
				# set new high of the content if show event under servicename
				if showEventNameUnderServiceName and not isMarker and self.mode == self.MODE_FAVOURITES: 
					sheight = self.serviceInfoHeight
				# servicenumber
				if self.mode != self.MODE_NORMAL:
					if not (service.flags & eServiceReference.isMarker) and showListNumbers and listNumerPosition=="1":
						markers_before = self.l.getNumMarkersBeforeCurrent()
						servicenumberformat = config.usage.configselection_listnumberformat.value
						text = servicenumberformat % (self.numberoffset + index + 1 - markers_before)
						nameWidthmax = self._componentSizes.get(self.KEY_SERVICE_NUMBER_WIDTH, 50)
						nameWidth = self._calcTextWidth(text, font=self.serviceNumberFont, size=eSize(width,0)) + textOffset 
						res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, 0, nameWidth , sheight, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, text, forgroundColor, forgroundColorSel, backgroundColor, backgroundColorSel))
						xoffset += nameWidth 
				# servicename
				res.append((eListboxPythonMultiContent.TYPE_TEXT, xoffset, 0, width - xoffset , sheight, 2, RT_HALIGN_LEFT|RT_VALIGN_CENTER, serviceName, forgroundColor, forgroundColorSel, backgroundColor, backgroundColorSel))
		#print("[CSP] res", res)
		return res

	def downloadEventImageCallback(self, index, eventId, retValue, eventImageName):
		#print("[CSP] refesh channellistEntry after downloaded image", eventImageName)
		if eventId in self.images_downloader_list:
			#print("[CSP] eventId remove", eventId)
			self.images_downloader_list.remove(eventId)
		self.l.invalidateEntry(index)

	def downloadEventInfoErrorInfo(self, eventId, error, url):
		if eventId in self.images_downloader_list:
			self.images_downloader_list.remove(eventId)
		#print("[CSP] EventImageDownload ERROR:", error, url)

	def getMoreEventsTextList(self, service, event, beginTime, counts=0, textWidth=0):
		# for moreEventsList for Template-Options 'moreNextEvents' and 'primetimeEvents'
		
		# set textRenderer to calculate values for eventTextList
		self.textRenderer.resize(eSize(textWidth + 1000,0)) # set to default width
		self.textRenderer.setFont(self.additionalInfoFont)
		self.textRenderer.setNoWrap(1)
		
		moreEvents = []
		eventName = "%02d:%02d %s" % (beginTime[3],beginTime[4],event.getEventName())
		if textWidth > 0:
			eventName = self.getCalculatedTextByWidth(eventName,textWidth)
		moreEvents.append(eventName)
		
		if counts==1:
			return "\n".join(moreEvents)
		
		test = ['XBT', (service.toString(), -1, event.getBeginTime() + event.getDuration(),24*60) ]
		epglist = self.eEPGCache.lookupEvent(test)
		i=2
		for event in epglist:
			if i>counts: break
			beginTime = localtime(event[0])
			eventName = "%02d:%02d %s" % (beginTime[3],beginTime[4], event[1])
			if textWidth > 0:
				eventName = self.getCalculatedTextByWidth(eventName,textWidth)
			moreEvents.append(eventName)
			i += 1
		
		# reset textRenderer to default values
		self.textRenderer.resize(eSize(self.getDesktopWith() // 3, 0)) 
		self.textRenderer.setNoWrap(0)
		
		return "\n".join(moreEvents)

	def getCalculatedTextByWidth(self, text, textWidth):
		calcwidth = self._calcTextWidth(text)
		#print ("[CSP] width1", calcwidth, textWidth, text)
		while calcwidth > textWidth:
			text1 = unicode(text, 'utf-8')[:-2].encode('utf-8')
			#print("[CSP] text", calcwidth, text)
			calcwidth1 = self._calcTextWidth(text1)
			#print ("[CSP] width2", calcwidth1, text)
			if calcwidth1 < textWidth:
				text2 = unicode(text, 'utf-8')[:-1].encode('utf-8')
				calcwidth2 = self._calcTextWidth(text2)
				if calcwidth2 <= textWidth:
					calcwidth=calcwidth2
					text= text2
				else:
					calcwidth=calcwidth1
					text = text1
			else:
				calcwidth=calcwidth1
				text = text1
		return text.rstrip()
	
	def applySkin(self, desktop, parent):
		#Log.i("[CSP]")
		for (attrib, value) in self.skinAttributes:
			if attrib == "serviceNumberFont":
				self.serviceNumberFont = parseFont(value, ((1,1),(1,1)))
			elif attrib == "mode":
				self.styleMode = {'vertical' : eListbox.layoutVertical,
				'grid' : eListbox.layoutGrid,
				'horizontal' : eListbox.layoutHorizontal
				}[value]
			elif attrib == "picServiceEventProgressbar":
				self.picServiceEventProgressbarPath = resolveFilename(SCOPE_CURRENT_SKIN, value)
			elif attrib == "scrollbarMode":
				self.styleScrollbarMode = { 
						"showOnDemand": eListbox.showOnDemand,
						"showAlways": eListbox.showAlways,
						"showNever": eListbox.showNever
					}[value]
			#save org fonts
			elif attrib == "serviceNameFont":
				self.orgFont2 = parseFont(value, ((1,1),(1,1)))
			elif attrib == "serviceInfoFont":
				self.orgFont3 =  parseFont(value, ((1,1),(1,1)))
			elif attrib == "serviceNumberFont":
				self.orgFont3 = parseFont(value, ((1,1),(1,1)))
			elif attrib == "additionalInfoFont":
				self.orgFont0 = parseFont(value, ((1,1),(1,1)))
		
		ServiceList.applySkin(self, desktop, parent)
		
		#save org itemWidth
		self.itemWidth = self.l.getItemSize().width()
		
		if self.useTemplates:
			self.applyTemplate()
			if config.usage.configselection_style.value == "default":
				self.setServiceListTemplateValues("default")
				self.l.setTemplate(None)

	def preWidgetRemove(self, instance):
		config.usage.configselection_showeventnameunderservicename.removeNotifier(self.setItemHeight)
		if not isMerlin:
			config.usage.configselection_showdvbicons.removeNotifier(self.setDVBIcons)
		ServiceList.preWidgetRemove(self, instance)

def replaceChannelSelection(session, **kwargs):
	#replace global calls for ChannelSelectionDisplaySettings (example the call from Merlin Main-Menu)
	import Screens.ChannelSelectionDisplaySettings
	Screens.ChannelSelectionDisplaySettings.ChannelSelectionDisplaySettings = ChannelSelectionDisplaySettings
	#replace call for ChannelSelectionDisplaySettings from ChannelSelection ContextMenu
	import Screens.ChannelSelection
	Screens.ChannelSelection.ChannelSelectionDisplaySettings = ChannelSelectionDisplaySettings
	
	#replace ChannelSelection channelSelected for ok-key
	if os_path.exists("/usr/lib/enigma2/python/Plugins/Extensions/PermanentTimeshift/plugin.py"):
		import Plugins.Extensions.PermanentTimeshift.plugin
		Plugins.Extensions.PermanentTimeshift.plugin.ChannelSelection_ori_channelSelected = ChannelSelection_channelSelected
	else:
		Screens.ChannelSelection.ChannelSelection.channelSelected = ChannelSelection_channelSelected
	
def Plugins(**kwargs):
	return [PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART], fnc=replaceChannelSelection)]
	
	
class CSP_ChannelSelectionPreview(ChannelSelection):
	IS_DIALOG = True

	def __init__(self, session):
		ChannelSelection.__init__(self, session)
		self.skinName = "ChannelSelection"
		#delete all actions
		for key in self.keys():
			if isinstance(self[key],ActionMap):
				del self[key]
		self["actions"] = ActionMap(["OkCancelActions","DirectionActions",],
			{
				"cancel": self.close,
				"ok": self.close,
				"left": self.keyLeft,
				"right": self.keyRight,
			},-2)
	
	def handleKey(self, KEY_VALUE):
		config.usage.configselection_style.handleKey(KEY_VALUE)
		self.servicelist.setServiceListTemplate(self.servicelist.root)
		self.servicelist.setList(self.servicelist._list)
		title = _("Preview") +  ": " + config.usage.configselection_style.value.replace("MODE_FAVOURITES_","").replace("MODE_FAVOURITES",_("default") + " " + _("template")).replace("default", _("default") + " " + _("style"))
		ChannelSelection.setTitle(self, title)
	
	def keyLeft(self):
		self.handleKey(KEY_LEFT)
	
	def keyRight(self):
		self.handleKey(KEY_RIGHT)
	
	def setTitle(self, title):
		title = "== " + _("Channel Selection") + " " + _("Preview") + " - " + _("close with exit") + " =="
		ChannelSelection.setTitle(self, title)


# ===== Example for ServiceList-Template in skin.xml ===========
"""
		<component type="ServiceList" beginMargin="3" endMargin="5" piconWidth="46" piconWidthBig="84" piconOffset="5" progressBarWidth="50" progressBarMargin="3" progressBarHeight="8" serviceInfoHeightAdd="8" serviceNumberWidth="55" textOffset="10" >
			<template>
				{"templates":
					{
						"default": (34, [ # needed dummy-template - not used
							MultiContentEntryPixmapAlphaTest(pos=(0,1), size=(30,30), png=3),
							MultiContentEntryText(pos=(40,2), size=(840,30), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=1, text=1),
						]),
						"MODE_FAVOURITES": (34, [ # template for channel-entries
							# empty line full width to fill empty rects
							MultiContentEntryText(pos=(0,0), size=(840,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
							# Picon
							MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(50,30), png=4),
							# ServiceName
							MultiContentEntryText(pos=(65,2), size=(200,35), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
							# EventName
							MultiContentEntryText(pos=(270,2), size=(560,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
							# Progressbar
							MultiContentEntryProgress(pos=(65,27),size=(665,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
							# Marker_Icon + Marker_Text
							MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(47,28), png=27),
							MultiContentEntryText(pos=(53,1), size=(780,34), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=0, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
						]),
						"MODE_FAVOURITES_PERCENT": (34, [ # alternative template for channel-entries
							# empty line full width to fill empty rects
							MultiContentEntryText(pos=(0,0), size=(840,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
							# Picon
							MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(50,30), png=4),
							# ServiceName
							MultiContentEntryText(pos=(65,2), size=(200,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
							# EventName
							MultiContentEntryText(pos=(270,2), size=(480,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
							# PercentText
							MultiContentEntryText(pos=(750,2), size=(60,34), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=1, text=23, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
							# Progressbar
							MultiContentEntryProgress(pos=(65,27),size=(665,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
							# Marker_Icon + Marker_Text
							MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(47,28), png=27),
							MultiContentEntryText(pos=(53,1), size=(780,34), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=0, text=24, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
						]),
						"MODE_NORMAL": (34, [ # template for folder-entries
							MultiContentEntryText(pos=(0,0), size=(840,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
							MultiContentEntryPixmapAlphaTest(pos=(1,0), size=(30,30), png=3),
							MultiContentEntryText(pos=(40,0), size=(840,34), flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
						]),
						"MODE_ALL": (34, [ # template for channel-entries in satellites, providers and all-list
							# empty line full width to fill empty rects
							MultiContentEntryText(pos=(0,0), size=(840,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text="", color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
							# Picon
							MultiContentEntryPixmapAlphaTest(pos=(1,1), size=(50,30), png=4),
							# ServiceName
							MultiContentEntryText(pos=(65,2), size=(200,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=1, color=MultiContentTemplateColor(10), color_sel=MultiContentTemplateColor(11), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
							# EventName
							MultiContentEntryText(pos=(270,2), size=(470,34), flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, font=1, text=2, color=MultiContentTemplateColor(16), color_sel=MultiContentTemplateColor(17), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
							# Remaining Time Text
							MultiContentEntryText(pos=(740,2), size=(70,34), flags=RT_HALIGN_RIGHT | RT_VALIGN_TOP, font=1, text=22, color=MultiContentTemplateColor(14), color_sel=MultiContentTemplateColor(15), backcolor=MultiContentTemplateColor(12),backcolor_sel=MultiContentTemplateColor(13)),
							# Progressbar
							MultiContentEntryProgress(pos=(65,27),size=(665,3), percent=-5, borderWidth=0, foreColor=MultiContentTemplateColor(6), backColor=MultiContentTemplateColor(7)),
						],True,None,{"mode": 1,"itemWidth": 840,"ProgressbarPixmapSize": (665,3),"bgPixmap": "skinpath/image_name.svg","selPixmap": "skinpath/image_name.svg", "pixmapSize": (316,300)}),
					},
					"fonts": [gFont("Regular",21),gFont("Regular",20), gFont("Regular", 32), gFont("Regular", 30)]
				}
			</template>
		</component>
"""
# Hinweise zur den Template-Optionen am Ende eines Templates
"""
],True,None,{"mode": 1,"itemWidth": 840,"ProgressbarPixmapSize": (665,3),"bgPixmap": "skinpath/image_name.svg","selPixmap": "skinpath/image_name.svg", "pixmapSize": (316,300), "moreNextEvents":(5,250), "primetimeEvents":(1,0)})
1. Wert: True = SelectionEnabled
2. Wert: None = ScrollbarMode
3. Wert: dict zur direkten Übergabe von Skin-Options für die Kanalliste:
* mode = Listmode der Kanalliste - 0 = vertical, 1 = horizontal, 2 = grid
* itemWidth = Breite eines Listeneintrages
* ProgressbarPixmapSize = Größe des ProgressbarPixmap
* bgPixmap = Hintergrundbild für die Zeilen (z.B. "bgPixmap": "Zombi-Shadow-FHD/bgPicture.svg")
* selPixmap = SelectionPixmap für die aktuelle Zeile (z.B. "selPixmap": "Zombi-Shadow-FHD/selPicture.svg")
* pixmapSize = Größe des bg/selPixmap
* useWidgetPixmaps = dabei werden die Pixmaps aus dem "list"-Widget des ChannelSelectionScreens verwendet
  (bei bgPixmap und selPixmap wird dann anstelle des Pfadnamens der Attribute-Name der Bilder aus dem list-Widget angegeben)
* moreNextEvents = Anzahl der nächstens Events als Text (je Zeile 1 Event) - Anzeige über text=33
* primetimeEvents = Anzahl der nächstens Events als Text (je Zeile 1 Event) - Anzeige über text=34
"""
#=== end of template-example ==============


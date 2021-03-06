# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MuseumsGIS
                                 A QGIS plugin
 MuseumsGIS GIS-plugin
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-03-03
        git sha              : $Format:%H$
        copyright            : (C) 2022 by Peter Jensen Maring, Arkæologisk IT, Moesgaard Museum
        email                : pje@moesgaardmuseum.dk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.core import  QgsVectorLayer, QgsRasterLayer, QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsRasterLayer, QgsVectorLayer
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QFileInfo
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu, QMessageBox
import xml.etree.ElementTree as et

# Initialize Qt resources from file resources.py
from .resources import *
from .historiske_kort_dockwidget import historiskekortDockWidget
import os.path

class MuseumsGIS:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir,'i18n','MuseumsGIS_{}.qm'.format(locale))
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)
        self.actions = []
        self.menu = self.tr(u'&MuseumsGIS')
        self.toolbar = self.iface.addToolBar(u'MuseumsGIS')
        self.toolbar.setObjectName(u'MuseumsGIS')
        self.pluginIsActive = False
        self.dockwidget = None

    def tr(self, message):
        return QCoreApplication.translate('MuseumsGIS', message)

    def loadTree(self):
        path = QFileInfo(os.path.realpath(__file__)).path()
        f = open(os.path.join(path,'museumsgis.qlr'), 'r').read()
        self.printtree(f)

    def printtree(self, s):
        tree = et.fromstring(s)
        tree = tree[0]

        #menu
        menu_bar = self.iface.mainWindow().menuBar()
        a = QMenu(menu_bar)
        a.setObjectName(self.tr("MuseumsGIS"))
        a.setTitle(self.tr("MuseumsGIS"))
        menu_bar.insertMenu(self.iface.firstRightStandardMenu().menuAction(), a)
        icon_path_info = os.path.join(os.path.dirname(__file__), "icon.png")
        self.action = QAction(QIcon(icon_path_info),'Historiske Kort (panel)',a)
        self.action.triggered.connect(self.showHistoriskeKort)
        a.addAction(self.action)
        a.addSeparator()

        local_helper = lambda _source,_label: lambda: self.addLayer(_source,_label)

        def displaytree(a,s):
            for child in s:
                if child.tag!="customproperties":
                    if "source" in child.attrib:
                        self.action = QAction(child.attrib["name"],a)
                        self.action.triggered.connect(local_helper(child.attrib["source"], child.attrib["name"]))
                        a.addAction(self.action)
                    else:
                        branch = QMenu(a)
                        branch.setObjectName(child.attrib["name"])
                        branch.setTitle(child.attrib["name"])
                        a.addMenu(branch)
                        displaytree(branch,child)

        displaytree(a,tree)

    def addLayer(self, source, label):
        rlayer = QgsRasterLayer(source, label, 'wms')
        rlayer.isValid()
        QgsProject.instance().addMapLayer(rlayer)
        print('Tilføjede lag',label, source)

    def initGui(self):
        self.run()

    def onClosePlugin(self):
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
        self.pluginIsActive = False


    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&MuseumsGIS'),
                action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar
        self.menu = None;

    def run(self):
        if not self.pluginIsActive:
            self.pluginIsActive = True
            if self.dockwidget == None:
                self.dockwidget = historiskekortDockWidget()
            self.loadTree()
            self.dockwidget.pushButton.clicked.connect(self.kortKnapKlik)
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

    
    def showHistoriskeKort(self):
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
        self.dockwidget.show()
        oversigtskort = QgsVectorLayer(os.path.join(self.plugin_dir,"tilemaps.geojson"),"Original-1 (1806-1822)","ogr")
        QgsProject.instance().addMapLayer(oversigtskort)
        antalKort = 0
        for feat in oversigtskort.getFeatures():
            antalKort +=1 
        QMessageBox.about(self.dockwidget,"MuseumsGIS", "Indlæste " + str(antalKort) + " Original-1 kort.\nFlere kort tilføjes hver uge. Husk at opdatere MuseumGIS-plugin i menuen Plugins -> Administrér og Installér Plugins.\nOpdateret 30-04-2022.")

    def kortKnapKlik(self):
        src_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        xform = QgsCoordinateTransform(src_crs, dest_crs, QgsProject().instance())
        converted = xform.transform(self.iface.mapCanvas().center())
        print("Find kort på: "+str(converted.x())+"/"+str(converted.y()))

        layer = QgsVectorLayer(os.path.join(self.plugin_dir,"tilemaps.geojson"),"tilemaps","ogr")
        feats = layer.getFeatures()
        for feat in feats:
            if feat.geometry().contains(converted):
                already_added = [lyr.source() for lyr in QgsProject.instance().mapLayers().values()]
                if feat["titel"] not in already_added:
                    QgsProject.instance().addMapLayer(QgsRasterLayer("type=xyz&url=https://www.museumsgis.dk/tilemaps/o1/fhm/"+feat["id"] +"/{z}/{x}/{y}.png&zmax=20&zmin=0", feat["titel"], "wms"))
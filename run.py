from astropy import units as u
from astropy.wcs import WCS
import astropy.io.fits as fits
import astropy.coordinates as coordinates
import ConfigParser as cp
import sys
sys.path.append('./config')
from config import cfg
sys.path.append('./logger')
from logger import log
import numpy as np
import glob
import os
import ccdproc
import re
import telnet
import starscoordinates
import alipysextractor
import plot
from datetime import datetime
import alipy
from collections import defaultdict
import warnings
warnings.filterwarnings("ignore")

# global variables
newObjectsList = []
directoryName = os.path.basename(os.path.normpath(cfg.file_path))


class RedObject:
    def __init__(self, name):
        self.name = name
        self.filesList = []
        self.isExists = False
        
    def add(self, elem):
        self.filesList.append(elem)
        self.isExists = True
        
    def getMedian(self):
        dataList = []
        for f in self.filesList:
            data = fits.getdata(f)
            dataList.append(data)
            
        array = np.array(dataList)
        median = np.median(array, axis = 0)
        
        self.median = median
        self.masterCCD = ccdproc.CCDData(self.median, unit=u.electron)
        
    def getExptime(self):
        hdu = fits.getheader(self.filesList[0])
        self.exptime = hdu[cfg.exptime]
        
class Reduction:
    def __init__(self, objectName):
        self.biases = RedObject('bias')
        self.darks = RedObject('dark')
        self.flats = RedObject('flat')
        self.objects = RedObject(objectName)
        self.redObjectsList = [self.biases, self.darks, self.flats]
        self.objectName = objectName

    def sortFrames(self):
        log.info('Sort frames to biases, flats and darks')
        print 'Sort frames to biases, flats and darks'
        
        os.chdir(cfg.file_path)
        fitsFiles = sorted(glob.glob(cfg.file_extension))
        
        for f in fitsFiles:
            hdr = fits.getheader(f)
            if hdr[cfg.target] == 'bias':
                self.biases.add(f)
            elif hdr[cfg.target] == 'dark':
                self.darks.add(f)
            elif hdr[cfg.target] == 'flat':
                self.flats.add(f)
            elif self.objectName in hdr[cfg.target].lower():
                self.objects.add(f)

    def getMedianForObjects(self):
        self.sortFrames()
        
        log.info('Create medians from list with red objects')
        print 'Create medians from list with red objects'
        
        for redObject in self.redObjectsList:
            if redObject.isExists:
                redObject.getMedian()
                
                if redObject.name == 'dark':
                    redObject.getExptime()
                    redObject.masterCCD.header[cfg.exptime] = master.exptime
                    
    def clean(self):
        types = '.new'
        allFiles = glob.glob(self.directory + '/*.*')
        for oneFile in allFiles:
            if not re.search(types, oneFile):
                os.remove(oneFile)
        log.info('Remove all unnecessary files created during reduction')
        print 'Remove all unnecessary files created during reduction'

    def reduceFrames(self):
        self.getMedianForObjects()
        log.info('Reducing frames started')
        print 'Reducing frames started'
        
        for obj in self.objects.filesList:
            data = ccdproc.CCDData.read(obj, unit=u.adu)
            dataWithDeviation = ccdproc.create_deviation(data, 
                                                        gain=1.5*u.electron/u.adu,
                                                        readnoise=5*u.electron)
            reducedObject = ccdproc.gain_correct(dataWithDeviation, 
                                                1.5*u.electron/u.adu)
            
            if self.biases.isExists:
                reducedObject = ccdproc.subtract_bias(reducedObject, 
                                                      self.biases.masterCCD)
            if self.darks.isExists:
                reducedObject = ccdproc.subtract_dark(reducedObject, 
                                                      self.darks.masterCCD, 
                                                      exposure_time=cfg.exptime, 
                                                      exposure_unit=u.second, 
                                                      scale=True)
            if self.flats.isExists:
                reducedObject = ccdproc.flat_correct(reducedObject, 
                                                     self.flats.masterCCD)
            
            self.directory = '../../Reduction/' + directoryName
            if not os.path.exists(self.directory):
                os.makedirs(self.directory)
            
            reducedObject.write(self.directory + '/' + obj, clobber=True)
            os.system('solve-field ' + self.directory + '/' + obj) # + ' --overwrite')
            
            objName, objExtension = os.path.splitext(self.directory + '/' + obj)
            
            if not os.path.exists(objName + '.new'):
                log.warning(objName + ' cannot be solved')
            else:
                newObjectsList.append(objName + '.new')
                log.info('Frame ' + objName + ' reduced')
            
        log.info('Reduced ' + str(len(newObjectsList)) + ' frames')
        print 'Reduced ' + str(len(newObjectsList)) + ' frames'
        self.clean()
        
class Photometry:
    def __init__(self, objectName, compStars):
        self.objectName = objectName
        self.compStars = compStars
        self.toAssoc = []
        self.plotDict = defaultdict(list)
        

    def getFromHorizon(self):  
        t = telnet.Telnet()
        
        hdrFirst = fits.getheader(newObjectsList[0])
        hdrLast = fits.getheader(newObjectsList[-1])
        startTime = datetime.strptime(hdrFirst[cfg.obsdate],
                                      "%Y-%m-%dT%H:%M:%S")
        endTime = datetime.strptime(hdrLast[cfg.obsdate],
                                    "%Y-%m-%dT%H:%M:%S")
        
        log.info('Getting asteroid\'s coordinates from Horizon started')
        print 'Getting asteroid\'s coordinates from Horizon started'

        results = t.takecoordinates(name = self.objectName, 
                                         start_date = startTime.strftime('%Y-%m-%d %H:%M'), 
                                         end_date = endTime.strftime('%Y-%m-%d %H:%M'), 
                                         interval = '1m')
        
        log.info('Getting asteroid\'s coordinates from Horizon finished')
        print 'Getting asteroid\'s coordinates from Horizon finished'
        
        return results

    def convertHorizonData(self):
        horizonData = self.getFromHorizon()
        convertedHorizonData = []
        for row in range(len(horizonData)):
            convertedHorizonData.append([horizonData[row][0], 
                                         coordinates.SkyCoord(horizonData[row][1], 
                                                              horizonData[row][2], 
                                                              unit=(u.hourangle, u.deg))])
        return convertedHorizonData

    def getCompStars(self):
        log.info('Getting stars\' coordinates from astroquery')
        print 'Getting stars\' coordinates from astroquery'
        
        starsCoordinates = starscoordinates.StarsCoordinates()
        
        hdrFirst = fits.getheader(newObjectsList[0])
        ra = hdrFirst[cfg.ra]
        dec = hdrFirst[cfg.dec]
        starstable = starsCoordinates.query_stars(ra, dec)
        starstable = starsCoordinates.sort_stars(starstable)
        
        return starstable

    def findNearest(self, date, lst):
        absValues = []
        for coords in lst:
            absValues.append(abs(coords[0]-date))

        return lst[absValues.index(min(absValues))][1:]

    def matchCoordFrames(self):
        coordsList = self.convertHorizonData()
        coordsDict = {}
        for obj in newObjectsList:
            hdr = fits.getheader(obj)
            jd = hdr[cfg.jd]
            coordsDict[obj] = [self.findNearest(jd, coordsList), jd]
        
        log.info('List with asteroid\'s coordinates matched with amount of object\'s frames')
        print 'List with asteroid\'s coordinates matched with amount of object\'s frames'
            
        return coordsDict

    def convertCoordinates(self, list_of_ra, list_of_dec, frame):     
        w = WCS(newObjectsList[frame]) 
        x, y = w.wcs_world2pix(list_of_ra, list_of_dec, 1) 
        if len(x) > 1: 
            for coord in range(self.compStars):
                row = str(x[coord]) + ' ' + str(y[coord]) + ' ' + str(coord+1)
                self.toAssoc.append(row)
        else:
            row = str(x[0]) + ' ' + str(y[0]) + ' 0'
            self.toAssoc.append(row)
            
        log.info('Ra and dec converted to x, y coords')
        print 'Ra and dec converted to x, y coords'

    def createAssoc(self):
        self.directory = '../../Photometry/' + directoryName
        if not os.path.exists(self.directory):
                os.makedirs(self.directory)
                
        with open(self.directory + '/assoc.coo', 'w') as assocfile:
            for row in self.toAssoc:
                assocfile.write(row + '\n')
                
        log.info('Edit assoc file')
        print 'Edit assoc file'
    
    def writeFinalFile(self):
        with open(self.directory + '/photoresults.dat', 'w') as photofile:
            listOfHeaders = ['JD','astero_mag','astero_magerr']
            for star in range(1, self.compStars + 1):
                listOfHeaders.append('star' + str(star) + '_mag')
                listOfHeaders.append('star' + str(star) + '_magerr')
            listOfHeaders.append('flag')
            for header in listOfHeaders:
                photofile.write(header + ' ')
            photofile.write('\n')
            for value in range(len(newObjectsList)):
                for header in listOfHeaders:
                    photofile.write(str(self.plotDict[header][value]) + ' ')
                photofile.write('\n')
                
        log.info('Data wrote to photoresult file')
        print 'Data wrote to photoresult file'
        
    def editDict(self):
        self.plotDict['astero_mag'] = self.plotDict['star0_mag']
        del self.plotDict['star0_mag']
        self.plotDict['astero_magerr'] = self.plotDict['star0_magerr']
        del self.plotDict['star0_magerr']

    def takeMag(self, ra, dec):
        log.info('Get magnitudo for wcs coordinates')
        print 'Get magnitudo for wcs coordinates'
        
        sexTractor = alipysextractor.Photometry()
        self.convertCoordinates([ra], [dec], 0)
        self.createAssoc()
        cat = sexTractor.runSextractor(newObjectsList[0], self.directory)
        self.toAssoc.pop()
        return cat['MAG_BEST'][0]

    def chooseStars(self, raList, decList, astra, astdec):
        log.info('Choose stars at most 2 magnitudo lighter than asteroid')
        print 'Choose stars at most 2 magnitudo lighter than asteroid'
        
        tempToAssoc = []
        starsLeft = self.compStars
        asteroidMag = self.takeMag(astra, astdec)
        star = 0
        while(starsLeft > 0):
            starMag = self.takeMag(raList[star], decList[star])
            if float(asteroidMag) - 2 < float(starMag):
                w = WCS(newObjectsList[0]) 
                x, y = w.wcs_world2pix(raList[star], decList[star], 1) 
                row = str(x) + ' ' + str(y) + ' ' + str(starsLeft)
                tempToAssoc.append(row)
                starsLeft -= 1
            star += 1
        self.toAssoc = tempToAssoc


    def run(self):
        log.info('Photometry has started')
        print 'Photometry has started'
        
        asteroidDict = self.matchCoordFrames()
        starstable = self.getCompStars()
        sexTractor = alipysextractor.Photometry()
        
        raList = starstable[0]
        decList = starstable[1]
        
        self.chooseStars(raList, decList,
                         asteroidDict[newObjectsList[0]][0][0].ra.deg,
                         asteroidDict[newObjectsList[0]][0][0].dec.deg)
        
        
        for frame in range(len(newObjectsList)):
            self.convertCoordinates([asteroidDict[newObjectsList[frame]][0][0].ra.deg],
                                    [asteroidDict[newObjectsList[frame]][0][0].dec.deg],
                                    frame)
            self.createAssoc()
            cat = sexTractor.runSextractor(newObjectsList[frame], self.directory)
            for i in range(self.compStars + 1):
                if str(cat['VECTOR_ASSOC'][i]) == '0':
                    self.plotDict['flag'].append(cat['FLAGS'][i])
                    if not str(cat['FLAGS'][i]) == '0':
                        log.info('An object in close neighbourhood of asteroid detected. Results of photometry may be unsettled')
                        print 'An object in close neighbourhood of asteroid detected. Results of photometry may be unsettled'
                self.plotDict['star' + str(cat['VECTOR_ASSOC'][i]) + '_mag'].append(cat['MAG_BEST'][i])
                self.plotDict['star' + str(cat['VECTOR_ASSOC'][i]) + '_magerr'].append(cat['MAGERR_BEST'][i])
            self.plotDict['JD'].append(asteroidDict[newObjectsList[frame]][1])
            
            self.toAssoc.pop()
        
        self.editDict()
        self.writeFinalFile()
        
        log.info('Photometry has just finished')
        print 'Photometry has just finished'
    
    
    
    
    
asteroid = raw_input('Set object\'s name\n').lower()
stars = int(raw_input('Set amount of comp stars\n'))
        
reduction = Reduction(asteroid)
reduction.reduceFrames()

photometry = Photometry(asteroid, stars)
photometry.run()

pl = plot.Plot(asteroid, stars, directoryName)
pl.draw()
    
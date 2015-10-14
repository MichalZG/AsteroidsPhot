import alipy
import astropy.coordinates as coordinates
import astropy.units as u

class Photometry:
    def runSextractor(self, newObject, directory):
	    #runs SExtractor for specified frame
        cat = alipy.pysex.run(newObject, keepcat = True, rerun = True, catdir = directory + '/cats/',
                              params = ['VECTOR_ASSOC(1)', 'FLUX_BEST', 'FLUXERR_BEST','MAG_BEST', 'MAGERR_BEST', 'FLAGS'], 
                              conf_args = {'VERBOSE_TYPE':'QUIET',
                                           'DETECT_THRESH':3.0,
                                           'ANALYSIS_THRESH':3.0,
                                           'BACKPHOTO_TYPE':'LOCAL',
                                           'BACKPHOTO_THICK':24,
                                           'ASSOC_RADIUS':10.0,
                                           'ASSOC_PARAMS':'1,2',
                                           'ASSOC_DATA':'3',
                                           'ASSOC_NAME':directory + '/assoc.coo'
                                            })
        return cat


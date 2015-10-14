
from astroquery.vizier import Vizier
import astropy.units as u
import astropy.coordinates as coordinates

class StarsCoordinates:
    
	#looks for stars in neighbourhood for specified coordinates
    def query_stars(self, ra, dec):
        c = coordinates.SkyCoord(ra = ra, dec = dec, unit=(u.hourangle, u.deg))
        r = 0.1 * u.deg
        v = Vizier(column_filters={'Rmag':">"+str(5.0), 'Rmag':"<"+str(15.0)})
        result = v.query_region(c,radius = r,catalog="NOMAD")
        return (result[0]['_RAJ2000', '_DEJ2000','Bmag','Vmag','Rmag'])
		
    #sorts list of stars (puts the best for being comparise stars in the first place)
    def sort_stars(self, starstable):
        starstable['b-v'] = starstable['Bmag'] - starstable['Vmag']
        starstable['v-r'] = starstable['Vmag'] - starstable['Rmag']
        starstable['sortby'] = abs(starstable['b-v'] - 0.656) + abs(starstable['v-r'] - 0.4)
        starstable.sort('sortby')
        return [starstable['_RAJ2000'].tolist(), starstable['_DEJ2000'].tolist()]

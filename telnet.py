import telnetlib
import re
import converter
import signal
import sys
sys.path.append('./logger')
from logger import log


class Telnet:
    def __init__(self):
        self.t = telnetlib.Telnet()

    def toJulianDate(self, date):
        date, hour = date.split(' ')
        hours, minutes = hour.split(':')
        year, month, day = date.split('-')
        month = converter.to_month(month)
        day = float(day)+ converter.hmsm_to_days(hour=float(hours),min=float(minutes),sec=0,micro=0)
        return converter.date_to_jd(float(year),month,day)

    def parse(self, text):
        ret = []
        pattdate = "(?P<date>....-.*-.. ..:..)"
        pattattr = " .."
        pattcoord1 = " (?P<coord1>.* .* .*) (?P<coord2>.* .* ..\..).*"
        patterndata = re.compile(pattdate + pattattr + pattcoord1)
        for match in re.finditer(patterndata, text): 
            ret.append([self.toJulianDate(match.group('date')),match.group('coord1'),match.group('coord2')])
        return ret

    def getcoor(self, name, start_date, end_date, interval):
        self.t.open('horizons.jpl.nasa.gov', 6775)
        expect = ( 
                ( r'Horizons>', name +'\n' ),#nazwa
                ( r'Continue.*:', 'y\n' ),
                ( r'Select.*E.phemeris.*:', 'E\n'),
                ( r'Observe.*:', 'o\n' ),
                ( r'Coordinate center.*:', '\n' ),#teleskop   
                ( r'Confirm selected station.*>', 'y\n'),
                ( r'Accept default output.*:', 'y\n'),
                ( r'Starting *UT.* :', start_date + '\n' ),#datastart
                ( r'Ending *UT.* :', end_date + '\n' ),
                ( r'Output interval.*:', interval + '\n' ),#interval
                ( r'Select table quant.* :', '1\n' ),#opcje
                ( r'Scroll . Page: .*%', ' '),
                ( r'Select\.\.\. .A.gain.* :', 'X\n' )
        )
        data = []
        while True:
                try:
                    answer = self.t.expect(list(i[0] for i in expect), 10)
                except EOFError:
                    break
                self.t.write(expect[answer[0]][1])
                if self.parse(answer[2]):
                    data += self.parse(answer[2])
        self.t.close()
        return data

    def handler(self, signum, frame):
        raise Exception("end of time")     

    def takecoordinates(self, name, start_date, end_date, interval): 
        signal.signal(signal.SIGALRM, self.handler)
        for i in range(5): #ilosc prob
                signal.alarm(30) # po ilu sekundach timeout
                try:
                    results = self.getcoor(name = name, start_date = start_date, end_date = end_date, interval = interval)
                    log.info('Data from Horizon succesfully downloaded')
                    if results == [] :
                        print 'Empty response from Horizon'
                        log.warning('Empty response from Horizon')
                    else:
                        signal.alarm(0)
                        return results
                except Exception, exc: 
                    print exc
                    log.exception('The name of asteroid is wrong or Horizon does not answer. ' +
                        'Please check asteroid name and try again later')
        raise Exception('The name of asteroid is wrong or Horizon does not answer. \n Please check asteroid name and try again later')


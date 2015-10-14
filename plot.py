import matplotlib.scale as sc
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.scale import ScaleBase as sb
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.backends.backend_pdf
import math
import converter
import datetime as dt
import matplotlib.axis as ax
from datetime import time, datetime
from scipy import stats

class Plot:
    def __init__(self, title, compStars, directoryName):
        self.compStars = compStars
        self.title = title
        self.path = '../../Photometry/' + directoryName
        self.compMags = []
        self.compErrs = []
        self.jdHours = []
        
    #zamieniamy ulamki dnia na godziny:
    def jd_day_to_hours(self, hours):
        timeHours = []
        for h in hours:
            time = converter.days_to_hmsm(h)
            timeNew = ['', '', '']
            for i in range(0, 3):
                if time[i] < 10:
                    timeNew[i] = '0' + str(time[i])
                else:
                    timeNew[i]= str(time[i])
            timeString = '%s:%s:%s' % (timeNew[0], timeNew[1], timeNew[2])
            timeHours.append(timeString)
        return timeHours
        
    def getData(self):
        data = np.loadtxt(self.path + '/photoresults.dat', skiprows=1)
        self.jd = data[:, 0]
        dateFromJD = converter.jd_to_date(self.jd[0])
        day = int(math.floor(dateFromJD[2]))
        self.date = [dateFromJD[0], dateFromJD[1], day]
        self.sourceMag = data[:, 1]
        self.sourceMagErr = data[:, 2] 
        for i in range(3, self.compStars * 2 + 3, 2):
            self.compMags.append(data[:, i])
            self.compErrs.append(data[:, i+1])
            
        for g in self.jd:
            date = converter.jd_to_date(g)
            day = int(math.floor(date[2]))
            self.jdHours.append(date[2] - day)
            
        self.timeHours = self.jd_day_to_hours(self.jdHours)
        self.datetimes = [datetime.strptime(t, "%H:%M:%S") for t in self.timeHours]
        
    
    def draw(self):
        self.getData()
        fig1 = plt.figure(1)
        
        # PIERWSZY PANEL

        subplt1 = plt.subplot(111) #Pierwszy uklad wspolrzednych
        subplt1.set_ylabel('Instrumental R magnitude')
        plt.title(self.title) 
        plt.suptitle(self.date)

        rys1 = plt.scatter(self.jdHours, self.sourceMag, c = 'red') #wykres planetoidy
        plt.errorbar(self.jdHours, self.sourceMag, yerr = self.sourceMagErr, fmt = 'o', c = 'red', ms = 5) #bledy planetoidy
        
        rys2 = plt.scatter(self.jdHours, self.compMags[0]) #wykres gwiazdy porownania
        plt.errorbar(self.jdHours, self.compMags[0], yerr = self.compErrs[0], fmt = 'o', c = 'black', ms = 5) #bledy gwiazdy porownania
        
        for i in range(1, self.compStars):
            plt.scatter(self.jdHours, self.compMags[i])
            plt.errorbar(self.jdHours, self.compMags[i], yerr = self.compErrs[1], fmt = 'o', c = 'black', ms = 5)


        hours_list = subplt1.get_xticks().tolist() #zbieramy etykiety z osi x do listy
        hours_list1 = self.jd_day_to_hours(hours_list) #przeksztalcamy etykiety (ulamki dni) na godziny
        subplt1.set_xticklabels(hours_list1, size = 10) #podmieniamy etykiety na osi x (wstawiamy godziny)

        plt.savefig(self.path + '/panel1.eps', format='eps')
        plt.savefig(self.path + '/panel1.png', format='png')

        #DRUGI PANEL
        
        fig2 = plt.figure()
        fig2.subplots_adjust(hspace = 0.001)
        
        if self.compStars<3:
            rows = 311
        else:
            rows = self.compStars*100 + 11

        subplt2 = plt.subplot(rows) #Drugi uklad wspolrzednych
        subplt2.set_ylabel('Relative R magnitude')
        subplt2.set_xticklabels(hours_list1, size = 10, visible = False)
        subplt2.set_ymargin(0.4)
        subplt2.autoscale(enable = True, axis= u'y', tight = True)

        rys3 = plt.scatter(self.jdHours, self.sourceMag - self.compMags[0]) #wykres planetoidy/gwiazde porownania
        plt.errorbar(self.jdHours, 
                     self.sourceMag - self.compMags[0], 
                     yerr = ((self.sourceMagErr) ** 2 + (self.compErrs[0]) ** 2) ** 0.5, 
                     fmt = 'o',
                     c = 'black',
                     ms = 5) #bledy planetoidy/gwiazde porownania
    

        for i in range(1, self.compStars):
            subplt3=plt.subplot(rows+i, sharex=subplt2)
            subplt3.set_xticklabels(hours_list1, size = 10, visible = False)
            subplt3.set_ymargin(0.5)
            subplt3.autoscale(enable = True, axis = u'y', tight = True)
            plt.scatter(self.jdHours, self.compMags[i] - self.compMags[0]) #wykres kolejnej gwiazdy/gwiazde porownania
            plt.errorbar(self.jdHours, 
                         self.compMags[i] - self.compMags[0],
                         yerr = ((self.compErrs[i]) ** 2 + (self.compErrs[0]) ** 2) ** 0.5,
                         fmt = 'o',
                         c = 'red',
                         ms = 5) #bledy drugiej gwiazdy/gwiazde porownania
            
            # Linear regression / residuals
            slope, intercept, r_value, p_value, std_err = stats.linregress(self.jdHours, self.compMags[i] - self.compMags[0])
            lst = []
            for d in (self.jdHours):
                    lst.append(slope * d + intercept)
            if np.std(self.compMags[i] - self.compMags[0]) > 0.0000001:
                    subplt3.plot(self.jdHours, 
                                 lst, 
                                 color = 'black',
                                 lw = 2, 
                                 label = "$\sigma_"+str(i)+"$="+str(np.round(np.std(self.compMags[i] - self.compMags[0]), 3)))

        if self.compStars > 1:
            hours_list = subplt3.get_xticks().tolist() #zbieramy etykiety z osi x do listy
            hours_list1 = self.jd_day_to_hours(hours_list) #przeksztalcamy etykity (ulamki dni) na godziny
            subplt3.set_xticklabels(hours_list1, size = 10, visible = True) #podmieniamy etykiety na osi x (wstawiamy godziny)
        else:
            hours_list = subplt2.get_xticks().tolist() #zbieramy etykiety z osi x do listy
            hours_list1 = self.jd_day_to_hours(hours_list) #przeksztalcamy etykity (ulamki dni) na godziny
            subplt2.set_xticklabels(hours_list1, size = 10, visible = True) #podmieniamy etykiety na osi x (wstawiamy godziny)

        pdf = matplotlib.backends.backend_pdf.PdfPages(self.path + '/lightcurve.pdf')
        pdf.savefig(fig1)
        pdf.savefig(fig2)
        pdf.close()

        plt.savefig(self.path + '/panel2.eps', format='eps')
        plt.savefig(self.path + '/panel2.png', format='png')
        plt.show() #wyswietla wykres w okienku
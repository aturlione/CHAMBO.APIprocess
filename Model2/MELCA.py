import requests
import json
import os
import numpy as np
import pandas as pd
import datetime
import socket
import numpy.matlib
import statistics
import math
from urllib3.connection import HTTPConnection
import matplotlib.pyplot as plt
import time
from pandas.core.common import flatten

HTTPConnection.default_socket_options = (
    HTTPConnection.default_socket_options + [
        (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
        (socket.SOL_TCP, socket.TCP_KEEPIDLE, 45),
        (socket.SOL_TCP, socket.TCP_KEEPINTVL, 10),
        (socket.SOL_TCP, socket.TCP_KEEPCNT, 6)
    ]
)

class LEM():

      
    #Método para obtener los datos de los diferentes métodos que hay en la API 
    def obtain_data(self,inputs,param=None):  
       
        url = "http://127.0.0.1:5050/Hydrographies/{0}".format(inputs["section"])
        print(url)
        headers = {'Accept':  'application/json'}
        s = requests.Session()
        r1 = s.get(url, headers=headers) 
        
        data1=json.loads(r1.text)
        if param:
            s = requests.Session()
            r1 = s.get(url, headers=headers,  json =param) 
            data1=json.loads(r1.text)
        return data1

#------------------------------------------------------
#                      Modelo MELCA
#------------------------------------------------------
    def run_melca(self,inputs):
        base_dir = os.getcwd()
        # 0- FICHEROS DE SALIDA
        fichres1='res_MELCA.xlsx' # fichero para escribir resultados generales
        vcres=int(inputs['sub_catchment_id']) #id cuenca para gráficas

        #1-LECTURA DE DATOS
        #1.1- Lee fichero de param con topologia de la red
        matpar=LEM().obtain_data(inputs)
        matpar = pd.DataFrame(matpar)
        vc=matpar.id #códigos de las cuencas 
        vc_str=[str(list(vc)[i]) for i in range(0,len(vc))] #transformo los códigos a str para usarlos como nombres de columnas en las tablas panda
        vd=matpar.fin #códigos cuencas destino
        
        vecs0=matpar.s0
        vecfcp=matpar.fcp
        vecfce=matpar.fce
        area=matpar.area

        nc=len(vc) #nº de cuencas

        #1.2- Lee series hidroclimáticas:Prec, temp_min, temp_max por subcuencas
        inputs_prec = {'section':'tablas-MELCA/prec'}
        inputs_tmin = {'section':'tablas-MELCA/tmin'}
        inputs_tmax = {'section':'tablas-MELCA/tmax'}

        datosprec=LEM().obtain_data(inputs_prec)
        datosprec=pd.DataFrame.from_dict(json.loads(datosprec))
        datostmin=LEM().obtain_data(inputs_tmin)
        datostmin=pd.DataFrame.from_dict(json.loads(datostmin))
        datostmax=LEM().obtain_data(inputs_tmax)
        datostmax=pd.DataFrame.from_dict(json.loads(datostmax))
        
        datosprec.index = pd.to_datetime(datosprec.index,unit='ms')
        datostmin.index = pd.to_datetime(datostmin.index,unit='ms')
        datostmax.index = pd.to_datetime(datostmax.index,unit='ms')

        
        vcser=datosprec.columns #códigos de las cuencas del fichero de series
        vcser=[int(list(vcser)[i]) for i in range(0,len(list(vcser)))] #lista con los códigos convertidos a números enteros

        set_vc=set(vc) #conjunto con códigos de las cuencas de origen
        set_vd=set(vd) #conjunto con códigos de las cuencas de destino
        set_vcser = set(vcser) #conjunto con códigos de las cuencas que tienen series temporales asociadas

        if len(list(set_vc.difference(set_vcser)))>0: 
            print('Hay cuencas sin serie climática asociada')
            print(list(set_vc.difference(set_vcser)))



        #Fecha comienzo de las series: 1/1/2000
        date_time_str_initial =inputs['initial date']
        date_time_str_final =inputs['final date']

        fechainic = datetime.datetime.strptime(date_time_str_initial, '%y-%m-%d')
        fechafin = datetime.datetime.strptime(date_time_str_final, '%y-%m-%d')            
           

        #Obtiene el vector de equivalencia entre vc y vcser
        vceq=[]
        for i in range(0,nc):
            index=vcser.index(list(vc)[i])
            vceq.append(vcser[index])
        
         
        #Series climaticas según el orden de vc, con los factores fcp y fce
        #la primera fila y columna son cabeceros y fechas 
        prec=datosprec[fechainic:fechafin][vc_str]
        factors=numpy.matlib.repmat(np.array(list(vecfcp)), len(prec),1) 
        prec=prec*factors #aplica coef. corr. de prec.
        tmin=datostmin[fechainic:fechafin][vc_str]
        tmax=datostmax[fechainic:fechafin][vc_str]

        #2- EJECUTA EL MELCA POR SUBCUENCAS
        #2.1 - listas donde guardaré los resultados

        qsims=[] #caudales simulados en mm/d
        pet=[] #evotranspiración
        area_ac=[] #area agregada
        prec_ac=[] #precipitacion agregada
        pet_ac=[] #evotranspiracion agregada
        qsim=[] #caudales simulados en m3/s
        qsim_ac=[] #caudales agregados
        precmed=[] #precipitacion media  mm/año
        petmed=[] #evotranspiracion media  mm/año
        qmed=[] #caudal medio 
        precmed_ac=[] #precipitacion media agregada mm/año
        petmed_ac=[] #evotranspiracion media agregada mm/año
        qmed_ac=[] # caudal medio agregado
        ce_ac=[] #coeficiente de de escorrentía 
        smax=[] # Capacidad máxima de almacenamiento
        

        for i in range(0,len(vc)):
            index= vc_str[i] #código cuenca
            datstr=pd.concat([prec[index],tmin[index],tmax[index]], axis=1) #series temporales
            datstr.columns=['prec','tmin','tmax']
            
            par= np.array([matpar.tau[i],vecs0[i],vecfcp[i],vecfce[i]])# parámetros MELCA.
            output_melca=self.fun_MELCA_v1(par,datstr) #calcula caudales espec.
            
            qsims.append(output_melca['qsim'])
            pet.append(output_melca['pet'])
            smax.append(output_melca['smax'])
            fa=list(area)[i]*1000/(3600*24) #de mm/d a m3/s
            qsim.append(fa*output_melca['qsim'])
            precmed.append(365.25*np.mean(prec[index]))
            petmed.append(365.25*np.mean(output_melca['pet']))
            qmed.append(np.mean(fa*output_melca['qsim']))
            

        #3- CALCULA LAS SERIES ACUMULADAS
        cc= list(set_vc.difference(set_vd)) #Obtiene cuencas de cabecera (las que no son destino de ninguna)

        ncc=len(cc)
        matcon=np.identity(nc)  #matriz de conectividades acum. Fila: cuenca receptora; col:cuencas tributarias

        prec_np=np.array(prec) #transformo los data frame en matrices con las dimensiones adecuadas para poder operar con ellos luego más facilmente 
        pet_np=np.array(pet)
        qsim_np=np.transpose(np.array(qsim))
        

        #Calcula matriz de conectividades
        for i in range(0,ncc):
            ipos=list(vc).index(cc[i]) #posicion de los indices de las cuencas de cabecera
            cdes=vd[ipos] #código de destino de las cuencas de cabecera
            ipostot=[]
            
            while cdes>0: #codigo de la cuenca de desembocadura
                ides=list(vc).index(cdes) #codigo de la cuenca de destino
                ipostot.append(ipos)
                matcon[ides,ipos]=1
                ipos=ides
                cdes=vd[ipos]



        for i in range(0,nc): 
            #ctrib=matcon[i,:]==1 #cuencas tributarias

            upper_path = self.Navigation(i+1,matcon) #obtengo los ids de todas las cuencas aguas arriba
            #ctrib=[upper_path[i]-1 for i in range(0,len(upper_path))] #indices de todas las cuencas aguas arriba
            ctrib=[list(vc).index(upper_path[i]) for i in range(0,len(upper_path))] #indices de todas las cuencas aguas arriba

            area_ac_val=sum(area[ctrib])
            prec_ac_val=np.sum(np.multiply(prec_np[:,ctrib],list(area[ctrib])),1)/area_ac_val          
            pet_ac_val=np.sum(np.multiply(pet_np[:,ctrib],list(area[ctrib])),1)/area_ac_val
            qsim_ac_val=np.sum(qsim_np[:,ctrib],1) 
            precmed_ac_val=365.25*np.mean(prec_ac_val,0)
            petmed_ac_val=365.25*np.mean(pet_ac_val,0)
            qmed_ac_val=np.mean(qsim_ac_val,0)
            fa=area_ac_val*1000/(3600*24)#de mm/d a m3/s
            ce_ac_val=np.divide(qmed_ac_val,(fa*precmed_ac_val/365.25))

            area_ac.append(area_ac_val)
            prec_ac.append(prec_ac_val)
            pet_ac.append(pet_ac_val)
            qsim_ac.append(np.transpose(qsim_ac_val))
            precmed_ac.append(precmed_ac_val)
            petmed_ac.append(petmed_ac_val)            
            qmed_ac.append(qmed_ac_val)
            ce_ac.append(ce_ac_val)
            
        q20_ac=np.quantile(qsim_ac, 0.2,1)
        q50_ac=np.quantile(qsim_ac, 0.5,1)
        q80_ac=np.quantile(qsim_ac, 0.8,1)
        q20_ac=np.transpose(q20_ac)
        q50_ac=np.transpose(q50_ac)
        q80_ac=np.transpose(q80_ac)
        

    # %%%%%%%%%%%%%%%%%%%%%%RESULTADOS%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Escribe resultados a fichero
        
        array2table = {'id':list(vc),'area':list(area),'area_ac':list(area_ac),'precmed':list(precmed),'petmed':list(petmed), 'qmed':list(qmed), 'precmed_ac':list(precmed_ac),
        'petmed_ac': list(petmed_ac),'qmed_ac': list(qmed_ac),'ce_ac': list(ce_ac),'q20_ac': list(q20_ac),'q50_ac': list(q50_ac),'q80_ac': list(q80_ac)}       

        trestor=pd.DataFrame(array2table)                
        trestor.to_excel(os.path.join(base_dir, "OUTPUTS", fichres1))
        idc=list(vc).index(vcres) #elije número de cuenca

            
        # %%%%%%%%%%%%%%%%%%%%%%%%%  GRÁFICOS %%%%%%%%%%%%%%%%%%%%%%%%%%%
        # Gráficas por meses (box-whiskers)
        # tipovar 1:pre; 2:pet, 3: caudal
        
        tspm=self.fun_acum(prec_ac[idc],fechainic,fechafin,1)['tspm']
        tspa=self.fun_acum(prec_ac[idc],fechainic,fechafin,1)['tspa']

        tsptm=self.fun_acum(pet_ac[idc],fechainic,fechafin,2)['tspm']
        tspeta=self.fun_acum(pet_ac[idc],fechainic,fechafin,2)['tspa']

        tsqm=self.fun_acum(qsim_ac[idc],fechainic,fechafin,3)['tspm']
        tsqa=self.fun_acum(qsim_ac[idc],fechainic,fechafin,3)['tspa']


        #FIG.2 gráfico box-whiskers de Prec, PET mensuales por subcuencas
        self.plots(tspm,'prec_mensual.pdf','Prec (mm/mes)',"Acumulado subcuenca {}".format(str(idc+1)))


        #FIG.3 gráfico box-whiskers de Prec, PET mensuales por subcuencas
        self.plots(tsqm,'Q.pdf',"Q (m3/s)","Acumulado subcuenca {}".format(str(idc+1)))

        #guardo los resultados diarios y mensuales en excels 
        qsim_ac_ids ={}
        qsim_ac_ids['dates']= pd.date_range(fechainic,fechafin,len(prec_ac[0]))

        for i in range(0,nc):
            qsim_ac_ids['sc{}'.format(str(i+1))]=qsim_ac[i]   


        result_qsims=pd.DataFrame(qsim_ac_ids)        
        result_qsims.to_excel(os.path.join(base_dir, "OUTPUTS", 'results_qsims_ac.xlsx'))

        # result_qsims.set_index('dates', inplace = True)
        # caudal_mensual = result_qsims.resample('M').mean()
        # caudal_mensual.to_excel(os.path.join(base_dir, "OUTPUTS", 'caudal_mensual.xlsx'))

        return {'dates':pd.date_range(fechainic,fechafin,len(prec_ac[0])),'qsim_ac':qsim_ac, 'matcon':matcon}
#-------------------------------------------------------------------------------   

    #-------------------------------------------------------------------------------   
    def plots(self,data,name_save,ylabel,title):
        fig=plt.figure()
        plt.plot(data)
        plt.title(title)
        plt.ylabel(ylabel)        
        plt.savefig(name_save, dpi=300, bbox_inches='tight')
        plt.close(fig)


    #-------------------------------------------------------------------------------
    #Modelo hidrológico basado en la ec. logí­stica con 4 parametros (diario)
    #*********************** READS PARS AND DATA******************************
    def fun_MELCA_v1(self,par,data):
        fce=par[3]

        prec=np.array(data['prec']) 
        tmin=list(data['tmin'])
        tmax=list(data['tmax'])
        
        tmed=[(tmin[i]+tmax[i])/2 for i in range(0,len(tmin))]
        pet=[fce*12.642/365.25*(tmed[i]+17.8)*(tmax[i]-tmin[i])**0.5 for i in range(0,len(tmin))] #mm/d
        qinic=np.mean(prec)*math.exp(-np.mean(pet)/np.mean(prec))#runoff de equilibrio inicial

        kq=1/par[0] #param desfase (inverso del tiempo caracterá­stico)= 1/tau
        kp0=1/par[1] #inverso de la capac de suelo S0
        tlan=25.465*math.log(par[1])-19.494
        lan=1/tlan
        c1=1 #param de Schreiber (fijo)

        #  Initialization
        nd=len(prec)
        rsim=np.zeros((nd,1)) #runoff series
        qsim=np.zeros(nd) #discharge series
        precprom=np.zeros((nd,1))
        petprom=np.zeros((nd,1))

        #********dynamic aridity ratio*********
        precprom[0]=np.mean(prec)/lan
        petprom[0]=np.mean(pet)/lan
        rsim[0]=qinic
        qsim[0]=qinic
        aux1=math.exp(-lan)
        aux2=(1-aux1)/lan

        for i in range(1,nd):
            precprom[i]=aux1*precprom[i-1]+aux2*prec[i]
            petprom[i]=aux1*petprom[i-1]+aux2*pet[i]
        
        arin=[petprom[i]/precprom[i] for i in range(0,len(petprom))]

        ceq=[math.exp(-c1*arin[i]) for i in range(0,len(arin))] #Schreiber modified

        kp=kp0*prec
        req=[prec[i]*ceq[i] for i in range(0,len(prec))]
        
        for i in range(1,nd):
            #RUNOFF GENERATION
            if req[i]>0:
                rsim[i]=req[i]*math.exp(kp[i])*rsim[i-1]/(req[i]+(-1+math.exp(kp[i]))*rsim[i-1])
            else:
                rsim[i]=(ceq[i])*rsim[i-1]/((ceq[i])+kp0*rsim[i-1])
         

        for i in range(1,nd):
            # RUNOFF ROUTING
            qsim[i]=rsim[i-1]+(rsim[i]-rsim[i-1])*(1-1/kq)+math.exp(-kq)*(qsim[i-1]-rsim[i-1]+(rsim[i]-rsim[i-1])/kq)
        
        smax=np.mean(petprom) 
        
        return {'qsim':qsim,'pet':pet,'smax':smax}

        
    #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    #  self.fun_acum(prec_ac[:,idc],fechainic,fechafin,1)
    def  fun_acum(self,yd,dateinic,datefin,tvar):
        
    #  NOTA: revisar fechas y los nombres de ejes y tí­tulo del gráfico generado
        dates =pd.date_range(dateinic,datefin,len(yd))
        
        timetable={'date':dates,'yd':yd}
        tsyd=pd.DataFrame(timetable)
        tsyd.set_index('date', inplace = True)


        if tvar == 1 or tvar == 2 :
            tspm=tsyd.resample('M').sum()
            tspa=tsyd.resample('y').sum()
        elif tvar == 3:
            tspm=tsyd.resample('M').mean()
            tspa=tsyd.resample('y').mean()

        return {'tsyd':tsyd,'tspm':tspm,'tspa':tspa}
#---------------------------------------------------------------------------------------
#---------------------------------CALCULATE VOLUMENS------------------------------------
#---------------------------------------------------------------------------------------
    def calculate_seassonal_flows(self,inputs, Outflows):       
        
        Seassonal_flow = {}

        Seassonal_Outflows = {'spring':[],'summer':[],'winter':[],'autumn':[]}

        sub_catchment_id = inputs['sub_catchment_id']

        dates = Outflows['dates']

        
        for i in range(0,len(dates)):
            date = dates[i]
            
            Outflow = Outflows['qsim_ac'][int(sub_catchment_id)-1][i]
            year = date.year

            seassons = [('summer', datetime.datetime(year,  1,  1),  datetime.datetime(year,  3, 20)), 
                    ('autumn', datetime.datetime(year,  3, 21),  datetime.datetime(year, 6, 20)),
                    ('winter', datetime.datetime(year, 6, 21),  datetime.datetime(year, 9, 20)),
                    ('spring', datetime.datetime(year,  9, 21),  datetime.datetime(year,  12, 21)),
                    ('summer', datetime.datetime(year,  12, 21),  datetime.datetime(year + 1,  3, 20))             
                    ]

            #Asigno estación a la fecha
            for estacion, inicio, fin in seassons:
                if inicio <= date <= fin:
                    seasson = estacion

            Seassonal_Outflows[seasson].append(Outflow)

        for seasson in ['spring','summer','winter','autumn']:
                    
            if len(Seassonal_Outflows[seasson])>0:
                Seassonal_flow[seasson]= sum(Seassonal_Outflows[seasson])/len(Seassonal_Outflows[seasson]) #flujo medio por estación.                    
                
                
        Seassonal_flow['annual'] = sum([Seassonal_flow[seasson] for seasson in Seassonal_flow.keys()])/4 #flujo medio anual.

       
        return {'Seassonal_flow' : Seassonal_flow, 'matcon': Outflows['matcon']} #el último id es es de la cuenca de destino.

#------------------------------------------------------------------------------------------------------------------------
    #Método calculate_resultant_volume:    
    #Resultado final, Agua disponible - demanda total
#------------------------------------------------------------------------------------------------------------------------
    def calculate_flows(self,inputs):

        #calculo el agua disponible: resultado de hydrobid - demanda ecosistémica

        ids = list(range(1,77)) #ids de todas las subciencas
        
        demandas_datos =  pd.DataFrame(self.obtain_data({'section': 'parametros-usos-demandas'})) #tabla con todas las demandas
        ecosistemica = pd.DataFrame(self.obtain_data({'section': 'ecosystems'})) #tabla con todas las demandas ecosistemicas
        caudal_prec = self.run_melca(inputs) #tabla con los caudales de precipitacion calculados por MELCA   


        #Calculo los valores agregados de las demandas, tasas de retorno y demandas ecosistemicas para cada subcuenca
        springDemands = []
        autumnDemand = []
        winterDemand = []
        summerDemand = []
        annualDemands = []

        springRet = []
        autumnRet = []
        winterRet = []
        summerRet = []
        annualRet = []

        springEco = []
        autumnEco = []
        winterEco = []
        summerEco = []
        annualEco = []

        springQ = []
        autumnQ = []
        winterQ = []
        summerQ = []
        annualQ = []

        dem_HUM_1 = []
        dem_IND_1 = []
        dem_ACU_1 = []
        dem_ENE_1 = []
        dem_RIE_1 = []

        ret_HUM_1 = []
        ret_IND_1 = []
        ret_ACU_1 = []
        ret_ENE_1 = []
        ret_RIE_1 = []

        for i in range(0,len(ids)):
            id=ids[i]
            springDemands.append(sum(demandas_datos['springDemand'][demandas_datos['inic']==id]))
            autumnDemand.append(sum(demandas_datos['autumnDemand'][demandas_datos['inic']==id]))
            winterDemand.append(sum(demandas_datos['winterDemand'][demandas_datos['inic']==id]))
            summerDemand.append(sum(demandas_datos['summerDemand'][demandas_datos['inic']==id]))
            annualDemands.append(sum(demandas_datos['annualDemand'][demandas_datos['inic']==id]))
             
           
            
            dem_HUM_1.append(sum(demandas_datos[(demandas_datos['tipo']=='HUM_1') & (demandas_datos['inic']==id)]['annualDemand'])) #fraccion de demandas por tipo
            dem_IND_1.append(sum(demandas_datos[(demandas_datos['tipo']=='IND_1') & (demandas_datos['inic']==id)]['annualDemand']))
            dem_ACU_1.append(sum(demandas_datos[(demandas_datos['tipo']=='ACU_1') & (demandas_datos['inic']==id)]['annualDemand']))
            dem_ENE_1.append(sum(demandas_datos[(demandas_datos['tipo']=='ENE_1') & (demandas_datos['inic']==id)]['annualDemand']))
            dem_RIE_1.append(sum(demandas_datos[(demandas_datos['tipo']=='RIE_1') & (demandas_datos['inic']==id)]['annualDemand']))

            springRet.append(sum(np.multiply(demandas_datos['returnRate'][demandas_datos['fin']==id],demandas_datos['annualDemand'][demandas_datos['fin']==id])))
            autumnRet.append(sum(np.multiply(demandas_datos['returnRate'][demandas_datos['fin']==id],demandas_datos['annualDemand'][demandas_datos['fin']==id])))
            winterRet.append(sum(np.multiply(demandas_datos['returnRate'][demandas_datos['fin']==id],demandas_datos['annualDemand'][demandas_datos['fin']==id])))
            summerRet.append(sum(np.multiply(demandas_datos['returnRate'][demandas_datos['fin']==id],demandas_datos['annualDemand'][demandas_datos['fin']==id])))
            annualRet.append(sum(np.multiply(demandas_datos['returnRate'][demandas_datos['fin']==id],demandas_datos['annualDemand'][demandas_datos['fin']==id])))
            
            
            
            ret_HUM_1.append(sum(demandas_datos[(demandas_datos['tipo']=='HUM_1') & (demandas_datos['fin']==id)]['returnRate'])) #fraccion de retornos por tipo
            ret_IND_1.append(sum(demandas_datos[(demandas_datos['tipo']=='IND_1') & (demandas_datos['fin']==id)]['returnRate']))
            ret_ACU_1.append(sum(demandas_datos[(demandas_datos['tipo']=='ACU_1') & (demandas_datos['fin']==id)]['returnRate']))
            ret_ENE_1.append(sum(demandas_datos[(demandas_datos['tipo']=='ENE_1') & (demandas_datos['fin']==id)]['returnRate']))
            ret_RIE_1.append(sum(demandas_datos[(demandas_datos['tipo']=='RIE_1') & (demandas_datos['fin']==id)]['returnRate']))

            springEco.append(sum(ecosistemica['springDemand'][ecosistemica['subcatchmentMELCAid']==id]))
            autumnEco.append(sum(ecosistemica['autumnDemand'][ecosistemica['subcatchmentMELCAid']==id]))
            winterEco.append(sum(ecosistemica['winterDemand'][ecosistemica['subcatchmentMELCAid']==id]))
            summerEco.append(sum(ecosistemica['summerDemand'][ecosistemica['subcatchmentMELCAid']==id]))
            annualEco.append(sum(ecosistemica['annualDemand'][ecosistemica['subcatchmentMELCAid']==id]))

            inputs_q=dict(inputs)
            inputs_q['sub_catchment_id']=str(id)
            springQ.append(self.calculate_seassonal_flows(inputs_q,caudal_prec)['Seassonal_flow']['spring'])
            autumnQ.append(self.calculate_seassonal_flows(inputs_q,caudal_prec)['Seassonal_flow']['autumn'])
            winterQ.append(self.calculate_seassonal_flows(inputs_q,caudal_prec)['Seassonal_flow']['winter'])
            summerQ.append(self.calculate_seassonal_flows(inputs_q,caudal_prec)['Seassonal_flow']['summer'])
            annualQ.append(self.calculate_seassonal_flows(inputs_q,caudal_prec)['Seassonal_flow']['annual'])

        #tablas con los valores finales para cada subcuenca
        results_demands=pd.DataFrame({'SpringDemands':springDemands,'autumnDemand':autumnDemand,'winterDemand':winterDemand,'summerDemand':summerDemand,'annualDemands':annualDemands,
        'dem_HUM_1' : dem_HUM_1, 'dem_IND_1': dem_IND_1, 'dem_ACU_1' : dem_ACU_1, 'dem_ENE_1' : dem_ENE_1, 'dem_RIE_1': dem_RIE_1 })
        results_returns=pd.DataFrame({'SpringDemands':springRet,'autumnDemand':autumnRet,'winterDemand':winterRet,'summerDemand':summerRet,'annualDemands':annualRet,
        'ret_HUM_1' : ret_HUM_1, 'ret_IND_1': ret_IND_1, 'ret_ACU_1' : ret_ACU_1, 'ret_ENE_1' : ret_ENE_1, 'ret_RIE_1': ret_RIE_1})
        results_eco=pd.DataFrame({'SpringDemands':springEco,'autumnDemand':autumnEco,'winterDemand':winterEco,'summerDemand':summerEco,'annualDemands':annualEco})
        results_Q=pd.DataFrame({'SpringQ':springQ,'autumnQ':autumnQ,'winterQ':winterQ,'summerQ':summerQ,'annualQ':annualQ})

        #escribo los resultados en archivos excels
        base_dir = os.getcwd()
        
        results_demands.to_excel(os.path.join(base_dir, "OUTPUTS", 'results_demands.xlsx'))
        results_returns.to_excel(os.path.join(base_dir, "OUTPUTS", 'results_returns.xlsx'))
        results_eco.to_excel(os.path.join(base_dir, "OUTPUTS", 'results_eco.xlsx'))
        results_Q.to_excel(os.path.join(base_dir, "OUTPUTS", 'results_Qs.xlsx'))

        datos = {'results_demands': results_demands, 'results_returns': results_returns, 'results_eco': results_eco, 'results_Q': results_Q}



        return datos

#--------------------------------------------------------------------------------------------------------------------
#                                                       Resutado Final
#--------------------------------------------------------------------------------------------------------------------
    def calculate_resultant_volume(self,inputs):
        #leo los resultados de calculate_flows
        base_dir = os.getcwd()
        # results_demands = pd.read_excel(os.path.join(base_dir, "OUTPUTS", 'results_demands.xlsx'), index_col=0)  
        # results_returns = pd.read_excel(os.path.join(base_dir, "OUTPUTS", 'results_returns.xlsx'), index_col=0)
        # results_eco = pd.read_excel(os.path.join(base_dir, "OUTPUTS", 'results_eco.xlsx'), index_col=0)
        # results_Q = pd.read_excel(os.path.join(base_dir, "OUTPUTS", 'results_Qs.xlsx'), index_col=0)

        datos = self.calculate_flows(inputs)
        results_demands = pd.DataFrame(datos['results_demands'])
        results_returns = pd.DataFrame(datos['results_returns'])
        results_eco = pd.DataFrame(datos['results_eco'])
        results_Q = pd.DataFrame(datos['results_Q'])


        #leo la matrix de conexiones
        matcon = pd.read_excel(os.path.join(base_dir, "OUTPUTS", 'matcon.xlsx'), index_col=0)
        matcon = np.array(matcon)
        ids = [int(inputs['sub_catchment_id'])]

        #obtengo los ids de todas las cuencas aguas arriba
        upper_path = self.Navigation(ids[0],matcon)

        matcon = matcon[0:75,0:75]
        
        #calculos los valores agregados aguas arriba
        SpringDemands_ac = []
        autumnDemand_ac = []
        winterDemand_ac = []
        summerDemand_ac = []
        annualDemand_ac = []

        SpringRet_ac = []
        autumnRet_ac = []
        winterRet_ac = []
        summerRet_ac = []
        annualRet_ac = []

        SpringEco_ac = []
        autumnEco_ac = []
        winterEco_ac = []
        summerEco_ac = []
        annualEco_ac = []

        HUM_1_Demands_ac = []
        IND_1_Demands_ac = []
        ACU_1_Demands_ac = []
        ENE_1_Demands_ac = []
        RIE_1_Demands_ac = []

        HUM_1_Ret_ac = []
        IND_1_Ret_ac = []
        ACU_1_Ret_ac = []
        ENE_1_Ret_ac = []
        RIE_1_Ret_ac = []

        print(results_demands['SpringDemands'])
        for i in ids: 
            #ctrib=matcon[i-1,:]==1 #indices de las cuencas tributarias
            ctrib=[upper_path[i]-1 for i in range(0,len(upper_path))] #indices de todas las cuencas aguas arriba

            SpringDemands_ac_val = sum(results_demands['SpringDemands'][ctrib])
            autumnDemand_ac_val = sum(results_demands['autumnDemand'][ctrib])
            winterDemand_ac_val = sum(results_demands['winterDemand'][ctrib])
            summerDemand_ac_val = sum(results_demands['summerDemand'][ctrib])
            annualDemand_ac_val = sum(results_demands['annualDemands'][ctrib])

            HUM_1_Demands_ac_val = sum(results_demands['dem_HUM_1'][ctrib])
            IND_1_Demands_ac_val = sum(results_demands['dem_IND_1'][ctrib])
            ACU_1_Demands_ac_val = sum(results_demands['dem_ACU_1'][ctrib])
            ENE_1_Demands_ac_val = sum(results_demands['dem_ENE_1'][ctrib])
            RIE_1_Demands_ac_val = sum(results_demands['dem_RIE_1'][ctrib])

            
            SpringRet_ac_val = sum(results_returns['SpringDemands'][ctrib])
            autumnRet_ac_val = sum(results_returns['autumnDemand'][ctrib])
            winterRet_ac_val = sum(results_returns['winterDemand'][ctrib])
            summerRet_ac_val = sum(results_returns['summerDemand'][ctrib])
            annualRet_ac_val = sum(results_returns['annualDemands'][ctrib])

            HUM_1_Ret_ac_val = sum(results_returns['ret_HUM_1'][ctrib])
            IND_1_Ret_ac_val = sum(results_returns['ret_IND_1'][ctrib])
            ACU_1_Ret_ac_val = sum(results_returns['ret_ACU_1'][ctrib])
            ENE_1_Ret_ac_val = sum(results_returns['ret_ENE_1'][ctrib])
            RIE_1_Ret_ac_val = sum(results_returns['ret_RIE_1'][ctrib])


            SpringEco_ac_val = sum(results_eco['SpringDemands'][ctrib])
            autumnEco_ac_val = sum(results_eco['autumnDemand'][ctrib])
            winterEco_ac_val = sum(results_eco['winterDemand'][ctrib])
            summerEco_ac_val = sum(results_eco['summerDemand'][ctrib])
            annualEco_ac_val = sum(results_eco['annualDemands'][ctrib])


            SpringDemands_ac.append(SpringDemands_ac_val)
            autumnDemand_ac.append(autumnDemand_ac_val)
            winterDemand_ac.append(winterDemand_ac_val)
            summerDemand_ac.append(summerDemand_ac_val)
            annualDemand_ac.append(annualDemand_ac_val)

            SpringRet_ac.append(SpringRet_ac_val)
            autumnRet_ac.append(autumnRet_ac_val)
            winterRet_ac.append(winterRet_ac_val)
            summerRet_ac.append(summerRet_ac_val)
            annualRet_ac.append(annualRet_ac_val)

            SpringEco_ac.append(SpringEco_ac_val)
            autumnEco_ac.append(autumnEco_ac_val)
            winterEco_ac.append(winterEco_ac_val)
            summerEco_ac.append(summerEco_ac_val)
            annualEco_ac.append(annualEco_ac_val)

            HUM_1_Demands_ac.append(HUM_1_Demands_ac_val)  
            IND_1_Demands_ac.append(IND_1_Demands_ac_val) 
            ACU_1_Demands_ac.append(ACU_1_Demands_ac_val)
            ENE_1_Demands_ac.append(ENE_1_Demands_ac_val) 
            RIE_1_Demands_ac.append(RIE_1_Demands_ac_val) 

            HUM_1_Ret_ac.append(HUM_1_Ret_ac_val)  
            IND_1_Ret_ac.append(IND_1_Ret_ac_val) 
            ACU_1_Ret_ac.append(ACU_1_Ret_ac_val)
            ENE_1_Ret_ac.append(ENE_1_Ret_ac_val) 
            RIE_1_Ret_ac.append(RIE_1_Ret_ac_val) 

        # #resultados finales
        # springFlow = results_Q['SpringQ'][ids[0]-1] - SpringEco_ac[0] - SpringDemands_ac[0] + SpringRet_ac[0]
        # autumnFlow = results_Q['autumnQ'][ids[0]-1] - autumnEco_ac[0] - autumnDemand_ac[0] + autumnRet_ac[0]
        # winterFlow = results_Q['winterQ'][ids[0]-1] - winterEco_ac[0] - winterDemand_ac[0] + winterRet_ac[0]
        # summerFlow = results_Q['summerQ'][ids[0]-1] - summerEco_ac[0] - summerDemand_ac[0] + summerRet_ac[0]
        # annualFlow = results_Q['annualQ'][ids[0]-1] - annualEco_ac[0] - annualDemand_ac[0] + annualRet_ac[0]

        #resultados finales
        springFlow = results_Q['SpringQ'][ids[0]-1] - SpringDemands_ac[0] + SpringRet_ac[0]
        autumnFlow = results_Q['autumnQ'][ids[0]-1] - autumnDemand_ac[0] + autumnRet_ac[0]
        winterFlow = results_Q['winterQ'][ids[0]-1] - winterDemand_ac[0] + winterRet_ac[0]
        summerFlow = results_Q['summerQ'][ids[0]-1] - summerDemand_ac[0] + summerRet_ac[0]
        annualFlow = results_Q['annualQ'][ids[0]-1] - annualDemand_ac[0] + annualRet_ac[0]


        #caudales de precipitacion
        qprec ={'springFlow': results_Q['SpringQ'][ids[0]-1], 
                'autumnFlow': results_Q['autumnQ'][ids[0]-1],
                'winterFlow':results_Q['winterQ'][ids[0]-1],
                'summerFlow':results_Q['summerQ'][ids[0]-1],
                'annualFlow':results_Q['annualQ'][ids[0]-1]}
        
        #caudales ecosistemicos
        Eco ={'springFlow': SpringEco_ac[0], 'autumnFlow':autumnEco_ac[0],'winterFlow':winterEco_ac[0],'summerFlow':summerEco_ac[0],'annualFlow':annualEco_ac[0]}
        #demandas
        demandas = {'springFlow': SpringDemands_ac[0], 'autumnFlow':autumnDemand_ac[0],'winterFlow':winterDemand_ac[0],'summerFlow':summerDemand_ac[0],'annualFlow':annualDemand_ac[0]}
        #retornos        
        retornos ={'springFlow': SpringRet_ac[0], 'autumnFlow':autumnRet_ac[0],'winterFlow':winterRet_ac[0],'summerFlow':summerRet_ac[0],'annualFlow':annualRet_ac[0]}

        #tipos de mandas
        tipos_demandas={'HUM_1':HUM_1_Demands_ac[0],'IND_1':IND_1_Demands_ac[0],'ACU_1':ACU_1_Demands_ac[0],'ENE_1':ENE_1_Demands_ac[0],'RIE_1':RIE_1_Demands_ac[0]}

        #tipos de retornos
        tipos_retornos={'HUM_1':HUM_1_Ret_ac[0],'IND_1':IND_1_Ret_ac[0],'ACU_1':ACU_1_Ret_ac[0],'ENE_1':ENE_1_Ret_ac[0],'RIE_1':RIE_1_Ret_ac[0]}

        #resultados finales
        resultado_final ={'springFlow': springFlow, 'autumnFlow':autumnFlow,'winterFlow':winterFlow,'summerFlow':summerFlow,
        'annualFlow':annualFlow}


        

        resultados = {'resultado_final':resultado_final, 'qprec':qprec, 'demanda_ecosistemica': Eco, 'demandas': demandas, 'retornos': retornos, 'tipos_demandas': tipos_demandas, 'tipos_retornos': tipos_retornos }
        df_resultados = pd.DataFrame(resultados)
        df_resultados.to_excel(os.path.join(base_dir, "OUTPUTS", 'resultados.xlsx'))

        return resultados

#-----------------------------------------------------------------------------------------------------------------
#                     Encuentra todas las cuencas aguas arriba que alimentan una cuenca dada
#-----------------------------------------------------------------------------------------------------------------
    def Navigation(self,nodo,matcon):
        matcon=matcon-np.identity(76)
        cabeceras =[]
        for id in range(1,77):
            uppers=np.where(matcon[id-1,:]==1)[0]
            if len(uppers)==0:
                cabeceras.append(id)


        paths={}
        for id in cabeceras:
            ids=[id]
            lowers=np.where(matcon[:,id-1]==1)[0]
            while len(lowers)>0:
                
                ids.append(lowers[0]+1)
                lowers=np.where(matcon[:,lowers[0]]==1)[0]
            
            paths[str(id)]=ids

        paths_id=[]
        #nodo=64
        for id in paths.keys():
            if nodo in paths[id]:
                index= paths[id].index(nodo)
                paths_id.append(paths[id][0:index+1])
        


        flat_list = list(flatten(paths_id))
        upper_sub_catchments =list(set(flat_list))
        #print(upper_sub_catchments)

        return upper_sub_catchments



        






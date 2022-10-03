# -*- coding: utf-8 -*-
"""
Created on Mon Apr 25 12:10:54 2022
@author: Anabela Turlione
"""

import requests
import json
import pandas as pd
from datetime import  datetime
import time
import socket
from urllib3.connection import HTTPConnection
from MELCA import LEM

# HTTPConnection.default_socket_options = (
#     HTTPConnection.default_socket_options + [
#         (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
#         (socket.SOL_TCP, socket.TCP_KEEPIDLE, 45),
#         (socket.SOL_TCP, socket.TCP_KEEPINTVL, 10),
#         (socket.SOL_TCP, socket.TCP_KEEPCNT, 6)
#     ]
# )


class CalculateVolumens:

      
    # #Método para obtener los datos de los diferentes métodos que hay en la API 
    # def obtain_data(self,inputs,param=None):  
      
    #     url = "{0}/v1/public/{1}".format(
    #             inputs["url_api_satd_katari"],
    #             inputs["section"])

    #     headers = {'Accept':  'application/json'}
    #     s = requests.Session()
    #     r1 = s.get(url, headers=headers) 
    #     data1=json.loads(r1.text)
    #     if param:
    #         s = requests.Session()
    #         r1 = s.get(url, headers=headers,  json =param) 
    #         data1=json.loads(r1.text)
    #     return data1
#------------------------------------------------------------------------------------------------------------------------    
    #Método hydrobid: 
    #Aplico el modelo hydrobid a una cuenca dada en un rango de fechas dado
#------------------------------------------------------------------------------------------------------------------------            
    def run_MELCA(self,inputs):
        print('Calculating MELCA on subcatchments ...'.format(inputs['catchment_id']))

        #obtengo la sub-catchment
        result = LEM.run_melca(inputs)           

        return result


#------------------------------------------------------------------------------------------------------------------------    
    #Método water_sources:
    
    #Calcula el flujo debido a todas las fuentes de agua (pozos y embalces)
#------------------------------------------------------------------------------------------------------------------------
    def water_sources(self,inputs):

        water_sources_data2 = {}
        for source in ['wells','dams']:
            inputs["section"] = '{0}/{1}'.format(source,inputs['sub_catchment_id'])
            water_sources_data2[source] = LEM.obtain_data(inputs)
          
      
        return water_sources_data2     
#------------------------------------------------------------------------------------------------------------------------        
    # Método calculate_OutFlow:
    
    # Dado el id de una cuenca, fecha de inicio y fecha de fin, encuentro todas las upper-catchments 
    #y calculo el outflow para cada una usando hydrobid
#------------------------------------------------------------------------------------------------------------------------        
    def calculate_OutFlow(self,inputs,plot=False):

        inputs_obtain_data = {'section':'{0}/{1}/upper-sub-catchments-hydrobid/geo-json'.format(inputs['section'],inputs['catchment_id'])
                             ,'url_api_satd_katari':inputs['url_api_satd_katari']}

        #obtengo todas las "upper-sub-catchments" correspondientes
        uppers = self.obtain_data(inputs_obtain_data)
        
        #obtengo los parámetros de cada "upper-sub-catchment" para usar en hydrobid
        idss=[]
        results={}

        for i in range(0,len(uppers['features'])): 

            #ids            
            ids = uppers['features'][i]['properties']['id']
            
            idss.append(ids)
            
            #Ataco en ApiProcess el método Hydrobid para obtener el caudal m3/s de cada una de las cuencas en un período de tiempo.

            inputs_upper_hydrobid = dict(inputs)
            inputs_upper_hydrobid['catchment_id'] = str(ids)
            inputs_upper_hydrobid['section'] = '{0}/{1}/geo-json'.format(inputs["section"],str(ids))

            inputs_water_sources = dict(inputs)
            inputs_water_sources ['catchment_id'] = str(ids)
            
            water_sources = self.water_sources(inputs)
            

            if i ==0:
                results[str(ids)]=self.hydrobid(inputs_upper_hydrobid) #sólo calculo hydrobid para la cuenca de más abajo
                id_0 = ids
            else:
                results[str(ids)]= {'Modeled Outflow [m3/day]':{'0':0.0},'Date':{'0':'09/12/2012'}} 

                if len(water_sources['dams']['features']) >0:
                    hydro_aux = self.hydrobid(inputs_upper_hydrobid) # calculo hydrobid para las upper-subcatchments que tienen embalces
                    results[str(id_0)] = results[str(id_0)] - hydro_aux # resto este valor al de la subcatchment de mas abajo.

        return results
#------------------------------------------------------------------------------------------------------------------------        
    #Método calculate_total_volumes:
    
    #caculate total volume using results from "calculate_Outflows"
#------------------------------------------------------------------------------------------------------------------------        
    
    def calculate_entering_volumes(self,inputs,results):
        print('Calculate entering volumes ...')
        
        
        Seassonal_flow = {}
        Seassonal_volume = {}
        inputs_hydrobid = dict(inputs)

        #hydrobid en las upper-subcatchmens
        inputs_hydrobid['section'] = '{0}/{1}/geo-json'.format(inputs["section"],inputs['catchment_id'])

        for sub_catchment in results.keys():
            Outflows = pd.DataFrame(results[sub_catchment])['Modeled Outflow [m3/day]']             

            dates = pd.DataFrame(results[sub_catchment])['Date']

            Seassonal_Outflows = {'spring':[],'summer':[],'winter':[],'autumn':[]}
            Seassonal_flow[sub_catchment] = {'spring':[],'summer':[],'winter':[],'autumn':[]}
  
            for i in range(0,len(dates)):
                date = datetime.strptime(dates[i],'%d/%m/%Y')
                Outflow = Outflows[i]
                year = date.year

                seassons = [('summer', datetime(year,  1,  1),  datetime(year,  3, 20)), 
                  ('autumn', datetime(year,  3, 21),  datetime(year, 6, 20)),
                  ('winter', datetime(year, 6, 21),  datetime(year, 9, 20)),
                  ('spring', datetime(year,  9, 21),  datetime(year,  12, 21)),
                  ('summer', datetime(year,  12, 21),  datetime(year + 1,  3, 20))             
                  ]

                #Asigno estación a la fecha
                for estacion, inicio, fin in seassons:
                    if inicio <= date <= fin:
                        seasson = estacion

                Seassonal_Outflows[seasson].append(Outflow)

            for seasson in ['spring','summer','winter','autumn']:

                
                if len(Seassonal_Outflows[seasson])>0:
                    Seassonal_flow[sub_catchment][seasson]= sum(Seassonal_Outflows[seasson])/len(Seassonal_Outflows[seasson]) #flujo medio por estación.                    
                else:
                    del Seassonal_flow[sub_catchment][seasson]
                    
            
            Seassonal_flow[sub_catchment]['annual'] = sum([Seassonal_flow[sub_catchment][seasson] for seasson in Seassonal_flow[sub_catchment].keys()])/4 #flujo medio anual.
           
        fin = time.time()

       
        return {'Seassonal_flow':Seassonal_flow}


#------------------------------------------------------------------------------------------------------------------------    
    #Método obtain_water_demands:
    
    #Calculate water demands
#------------------------------------------------------------------------------------------------------------------------

    def obtain_water_demands(self,inputs):        
        
        print('Calculating {0} for {1} ...'.format(inputs['section_demand'],inputs['catchment_id']))

        #obtengo las demandas        
        inputs_obtain_data = inputs        
        inputs_obtain_data['section']='{0}/geo-json?sub-catchment-hydrobid-id={1}'.format(inputs['section_demand'],inputs['catchment_id'])  
            
        water_demands = self.obtain_data(inputs_obtain_data)
        
        water_summer = []
        water_winter = []
        water_autumn = []
        water_spring = []
        water_annual = []        

        return_summer = []
        return_winter = []
        return_autumn = []
        return_spring = []
        return_annual = []

        for i in range(0,len(water_demands['features'])):

            water_winter.append(water_demands['features'][i]['properties']['winterDemand'])
            rwinter = water_demands['features'][i]['properties']['returnRate']
            if rwinter:
                return_winter.append(rwinter*water_demands['features'][i]['properties']['winterDemand'])

            water_summer.append(water_demands['features'][i]['properties']['summerDemand'])
            rsummer = water_demands['features'][i]['properties']['returnRate']
            if rsummer:
                return_summer.append(rsummer*water_demands['features'][i]['properties']['summerDemand'])

            water_autumn.append(water_demands['features'][i]['properties']['autumnDemand'])
            rautumn = water_demands['features'][i]['properties']['returnRate']
            if rautumn:
                return_autumn.append(rautumn*water_demands['features'][i]['properties']['autumnDemand'])

            water_spring.append(water_demands['features'][i]['properties']['springDemand'])
            rspring = water_demands['features'][i]['properties']['returnRate']
            if rspring:
                return_spring.append(rspring*water_demands['features'][i]['properties']['springDemand'])

            water_annual.append(water_demands['features'][i]['properties']['annualDemand'])
            rannual = water_demands['features'][i]['properties']['returnRate']
            if rannual:
                return_annual.append(rannual*water_demands['features'][i]['properties']['annualDemand']) 

        #considero que las demandas vienen dadas en flujos: m3/day, entonces calculo los valores medios para cada estación.

        total_winter = 0
        total_summer = 0
        total_autumn = 0
        total_spring = 0
        total_annual = 0

        if len(water_winter)>0:
            total_winter = sum(water_winter)

        if len(water_summer)>0:
            total_summer = sum(water_summer)

        if len(water_autumn)>0:
            total_autumn = sum(water_autumn)

        if len(water_spring)>0:
            total_spring = sum(water_spring)

        if len(water_annual)>0:
            total_annual = sum(water_annual)

        total_returned_winter = 0
        total_returned_summer = 0
        total_returned_autumn = 0
        total_returned_spring = 0
        total_returned_annual = 0

        if len(return_winter)>0:
            total_returned_winter = sum(return_winter)
        if len(return_summer)>0:
            total_returned_summer = sum(return_summer)
        if len(return_autumn)>0:   
            total_returned_autumn = sum(return_autumn)
        if len(return_spring)>0:
            total_returned_spring = sum(return_spring)

        if len(return_annual)>0:
            total_returned_annual = sum(return_annual)

        returned_flows = {'winter':total_returned_winter,'summer':total_returned_summer,
                          'autumn':total_returned_autumn,'spring':total_returned_spring,
                          'annual':total_returned_annual}

        demands_flows = {'winter' : total_winter, 'summer': total_summer, 'autumn' : total_autumn, 'spring' : total_spring, 'annual': total_annual}
       
        return {'demanded_flows':demands_flows, 'returned_flows': returned_flows}
        

    
#------------------------------------------------------------------------------------------------------------------------
    #Método available_water:    
    #Agua disponible: volumen entrante - demanda ecosistémica
#------------------------------------------------------------------------------------------------------------------------
        
    def available_water(self,inputs=None,customs=None):
        
        seassons = ['spring','summer','winter','autumn','annual']
        seassons2 = ['springFlow','summerFlow','winterFlow','autumnFlow','annualFlow']    

        if customs:
            total_volumes_sources_ids = customs['water_sources']
            total_hydro_flows = customs['hydrobid_flows']
            ecosystem_demands = customs['ecosystems_demands']
        else:
            #Obtengo los caudales entrantes con hydrobid
            results=self.calculate_OutFlow(inputs)
            
            #Calculo los volumenes totales entrantes (resultados de hydrobid)
            entering_volumes = self.calculate_entering_volumes(inputs,results)  
            total_hydro_flows = entering_volumes['Seassonal_flow']

            #Calculo la demanda Ecosistémica y aportaciones de agua
            ecosystem_demands = {}
            water_sources = {}
            for id in total_hydro_flows.keys():
                inputs_obtain_water_demands = {'catchment_id' :id,
                        'section_demand':'hydrographies/ecosystems',
                        'url_api_satd_katari':inputs['url_api_satd_katari'],
                        'url_api_apiprocess':inputs['url_api_apiprocess']
                        }     

                
                ecosystems = self.obtain_water_demands(inputs_obtain_water_demands)
                ecosystem_demands[id]= ecosystems['demanded_flows'] 

                inputs_water_sources = dict(inputs)
                inputs_water_sources['catchment_id'] = id
                sources = self.water_sources(inputs_water_sources) 
                water_sources[id] = sources
            
            
            total_volumes_sources = {'spring':0,'summer':0,'winter':0,'autumn':0,'annual':0}         
            
            
            total_volumes_sources_ids = {}
            for sub_catchment in total_hydro_flows.keys():
                for source in water_sources[sub_catchment].keys():
                    for i in range(len(water_sources[sub_catchment][source]['features'])):    
                        for j in range(len(seassons2)):            
                            if water_sources[sub_catchment][source]['features'][i]['properties'][seassons2[j]]:
                                total_volumes_sources[seassons[j]] += water_sources[sub_catchment][source]['features'][i]['properties'][seassons2[j]]
                total_volumes_sources_ids[sub_catchment] = total_volumes_sources

#------------------------------------------
        total_flows = {}
        ecosystems_total = {}
        sources_total = {}
        final_result = {}
        

        #Flujo entrante total  
        for seasson in total_hydro_flows[list(total_hydro_flows.keys())[0]].keys():                      
            total_flows[seasson] = total_hydro_flows[list(total_hydro_flows.keys())[0]][seasson]
            ecosystems_total[seasson] = 0
            sources_total[seasson] = 0
            for sub_catchment in total_hydro_flows.keys():                    
                ecosystems_total[seasson] += ecosystem_demands[sub_catchment][seasson]
                sources_total[seasson] += total_volumes_sources_ids[sub_catchment][seasson]
            final_result[seasson] = max(0,total_flows[seasson]-ecosystems_total[seasson]+sources_total[seasson]) 
        

        return {'total_hydro_flows': total_hydro_flows ,'final_result': final_result,'water_sources':sources_total}
    
    
#------------------------------------------------------------------------------------------------------------------------
    #Método calculate_resultant_volume:    
    #Resultado final, Agua disponible - demanda total
#------------------------------------------------------------------------------------------------------------------------
    def calculate_resultant_volume(self,inputs):
        inicio = time.time() 

        #calculo el agua disponible: resultado de hydrobid - demanda ecosistémica
        available_water = self.available_water(inputs=inputs)
        
        available_water_flows = available_water['final_result']
        total_hydro_flows = available_water['total_hydro_flows']
        water_sources =  available_water['water_sources']
        water_demands = {}
        water_returns = {}
        for id in total_hydro_flows.keys():
            print(id)
            #calculo las demandas de aguas      
            demands = {}
            returns = {}
                    
            inputs_potable = {'catchment_id': id  ,
                    'section_demand':'hydrographies/potable-water-demands',
                    'url_api_satd_katari':inputs['url_api_satd_katari'],
                    'url_api_apiprocess':inputs['url_api_apiprocess']
                    } 

            inputs_irrigations = {'catchment_id' :id  ,
                    'section_demand':'hydrographies/irrigations',
                    'url_api_satd_katari':inputs['url_api_satd_katari'],
                    'url_api_apiprocess':inputs['url_api_apiprocess']
                    } 

            inputs_mining = {'catchment_id' :id  ,
                    'section_demand':'socioeconomics/mining-centers',
                    'url_api_satd_katari':inputs['url_api_satd_katari'],
                    'url_api_apiprocess':inputs['url_api_apiprocess']
                    }             
      
            #Calculo la demanda de Agua Potable        
            potable_water_demands = self.obtain_water_demands(inputs_potable)
            if potable_water_demands:
                demands['potable-water-demands']=potable_water_demands['demanded_flows']
                returns['potable-water-demands']=potable_water_demands['returned_flows']
            #Calculo la demanda de Riego
            irrigations = self.obtain_water_demands(inputs_irrigations)
            if irrigations:
                demands['irrigations']=irrigations['demanded_flows']
                returns['irrigations']=irrigations['returned_flows'] 
            #Calculo la demanda de Act. Industriales 
            mining_centers = self.obtain_water_demands(inputs_mining)
            if mining_centers:
                demands['mining_centers']=mining_centers['demanded_flows']
                returns['mining_centers']=mining_centers['returned_flows']

            water_demands[id] = demands    
            water_returns[id] = returns
             

        total_demand = {}
        total_returned = {}
        final_result = {}
        
        for seasson in available_water_flows.keys():
            #demanda total

            total_demand[seasson] = 0
            total_returned[seasson]  = 0
            for id in total_hydro_flows.keys():
                total_demand[seasson] += sum([water_demands[id][demand_kind][seasson] for demand_kind in water_demands[id].keys()])
                
                total_returned[seasson] += sum([water_returns[id][demand_kind][seasson] for demand_kind in water_returns[id].keys()])
                #agua disponible - demanda total
                final_result[seasson] = available_water_flows[seasson]-total_demand[seasson]+total_returned[seasson]
        
        #calculo la navegación
        navigation_section = dict(inputs)
        navigation_section['section'] = 'hydrographies/sub-catchments-hydrobid/{0}/sub-catchment-hydrobid-navigations'.format(inputs['catchment_id'] )
        navigation = self.obtain_data(navigation_section)
        
        
        

        #change flows to volumes [m3]
        if inputs['total volumens in m3']:
            total_hydro_vols = self.units_change(total_hydro_flows)
            total_returned = self.units_change(total_returned)   
            water_demands_m3 = self.units_change(water_demands)            
            total_demand_m3 = self.units_change(total_demand)
            final_result_m3 = self.units_change(final_result)
            water_sources_m3 = self.units_change(water_sources)

            output_results = {'total hydrobid volumes [m3]':total_hydro_vols,'hydrobid volumes [m3]':total_hydro_vols, 'water_demands [m3]': water_demands_m3,'total demands [m3]':total_demand_m3,'total returned volumens [m3]':total_returned,
                    'final result [m3]':final_result_m3, 'water sources [m3]':water_sources_m3,'navigation' : navigation} 
        else:                
            #flows [m3/day]
            output_results = {'total hydrobid flow [m3/day]':available_water_flows,'hydrobid flows [m3/day]':total_hydro_flows, 'water_demands [m3/day]': water_demands,'total demands [m3/day]':total_demand,'total returned flows [m3/day]':total_returned,
            'final result [m3/day]':final_result, 'water sources [m3/day]':water_sources,'navigation' : navigation}        

        fin = time.time()

        print('total time ',fin-inicio)        
        
        return output_results
#---------------------------------------------------------------------------------------------------
    def units_change(self,result):

        seassons_duration = {'spring':89.9,'summer':89.0,'winter': 93.7 ,'autumn': 92.7 ,'annual':365.3}
        result_m3 = dict(result)

        
        for index in result.keys():
            if type(result[index]) == dict:
                for index2 in result[index].keys():
                    if type(result[index][index2]) == dict:
                        for index3 in result[index][index2].keys():
                            result_m3[index][index2][index3] = result[index][index2][index3]*seassons_duration[index3]
                    else: 
                        result_m3[index][index2] = result[index][index2]*seassons_duration[index2]
            else:
                result_m3[index] = result[index]*seassons_duration[index]
            
        return result_m3
#---------------------------------------------------------------------------------------------------

    def custom_parameters(self,customs):        
        
        #calculo el agua disponible: resultado de hydrobid - demanda ecosistémica
        available_water = self.available_water(customs=customs)
        
        available_water_flows = available_water['final_result']
        total_hydro_flows = available_water['total_hydro_flows']
        water_sources = available_water['water_sources']
        

        water_demands = customs['water_demands']
        water_returned = customs['water_returned %']

        total_demand = {}
        final_result = {}
        returned_flows = {}

        seassons = ['spring','summer','winter','autumn','annual']
        for seasson in seassons:

            #demanda total
            total_demand[seasson] = 0
            for id in total_hydro_flows.keys():
                total_demand[seasson] += sum([water_demands[id][demand_kind][seasson] for demand_kind in water_demands[id].keys()])
                returned_flows[seasson] = total_demand[seasson]*water_returned[seasson]
                #agua disponible - demanda total
                final_result[seasson] = available_water_flows[seasson]-total_demand[seasson]+returned_flows[seasson]
        
        
                #calculo la navegación
        navigation_section = dict(customs)
        navigation_section['section'] = 'hydrographies/sub-catchments-hydrobid/{0}/sub-catchment-hydrobid-navigations'.format(customs['subcatchment_id'] )
        navigation = self.obtain_data(navigation_section)

        output_results = {'final result [m3/day]':final_result}
        output_results = {'total hydrobid flow [m3/day]':total_hydro_flows,'hydrobid flows [m3/day]':total_hydro_flows, 'water_demands [m3/day]': water_demands,'total demands [m3/day]':total_demand,'total returned flows [m3/day]':returned_flows,
            'final result [m3/day]':final_result, 'water sources [m3/day]':water_sources,'navigation' : navigation}  

              
        return output_results


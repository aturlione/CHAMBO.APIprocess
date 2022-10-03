import json
from flask import request,jsonify
from flask_restx import Resource, fields
from Model2 import MELCA
from xml.dom import minidom
import os
import requests




def start(apiflask):
    try:
        del os.environ["DISPLAY"]
    except KeyError:
        print("No display variable found")
    ns = apiflask.namespace(
        "CHAMBO Models", description="CHAMBO Models"
    )
    current_folder = os.path.dirname(os.path.realpath(__file__))
    f = open(os.path.join(current_folder, "config.json"))
    config = json.load(f)



# #-------------------------------------------------------------------------------

    Calculate_resultant_flows_params = apiflask.model(
        "MELCA_params",
        { "sub_catchment_id":fields.String,
          "initial date": fields.String,
          "final date" : fields.String,
        },
    )

    @ns.route("/Calculate_resultant_flows")
    class calculate_volumens(Resource):

        @ns.expect(Calculate_resultant_flows_params)
        def post(self):
            try:                        
                                       
                inputs={'sub_catchment_id':None,
                'section':'parametros-MELCA',
                'initial date':None,
                'final date': None,
                'API':True,
                'total volumens in m3':False
                }
                payload = request.json

                inputs['sub_catchment_id'] = payload['sub_catchment_id']
                inputs['initial date'] = payload['initial date']
                inputs['final date'] = payload['final date']

                print(inputs)

                response =  MELCA.LEM().calculate_resultant_volume(inputs)
            
                print(type(response)) 
                json_results = jsonify(response)
                
                return json_results
            except Exception as ex:
                raise Exception(ex)

   

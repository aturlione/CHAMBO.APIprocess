import unittest
import Model2.MELCA as MELCA 
import pandas as pd

class TestPythonModule(unittest.TestCase):
    """Example test"""

    def test_obtain_data(self):
        
        #inputs = {'section':'LEM/historical'}
        #param = {"id":1, "Nombre": "Abusu"}
        inputs = {'section':'parametro-LEM/1'}
        #response = LEM.LEM().obtain_data(inputs,param)
        response = MELCA.LEM().obtain_data(inputs)
        df = pd.DataFrame(list(response.items())) 

        print(df)
        # #print (pd.DataFrame(response))
        # self.assertIsNotNone(response)
        # #self.assertEqual(type(response), dict)
        


if __name__ == '__main__':
    unittest.main()
import unittest
import Model2.MELCA as MELCA 
import pandas as pd


class TestPythonModule(unittest.TestCase):
    """Example test"""

    def test_melca(self):
        
        inputs={'sub_catchment_id':'73',
                'section':'parametros-MELCA',
                'initial date':'00-01-01',
                'final date': '19-12-31',
                'API':False,
                'total volumens in m3':False
                }

        response = MELCA.LEM().calculate_resultant_volume(inputs)
        print(response)

        self.assertIsNotNone(response)
        self.assertEqual(type(response), dict)
        


if __name__ == '__main__':
    unittest.main()
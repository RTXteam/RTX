import logging
import sys
import connexion
from flask_testing import TestCase

from openapi_server.provider import CustomJSONProvider

def eprint(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

class BaseTestCase(TestCase):

    def create_app(self):
        logging.getLogger('connexion.operation').setLevel('ERROR')
        app = connexion.App(__name__, specification_dir='../openapi/')
        app.json_provider_class = CustomJSONProvider
        eprint(f"Using JSON provider: {type(app.app.json)}")
        app.add_api('openapi.yaml', pythonic_params=True)
        return app.app

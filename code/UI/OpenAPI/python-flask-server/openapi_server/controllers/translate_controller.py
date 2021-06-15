import connexion
import six

from openapi_server.models.query import Query  # noqa: E501
from openapi_server import util

#from ParseQuestion import ParseQuestion


def translate(request_body=None):  # noqa: E501
    """Translate natural language question into a standardized query

     # noqa: E501

    :param request_body: Question information to be translated
    :type request_body: Dict[str, ]

    :rtype: List[Query]
    """
    if connexion.request.is_json:
        question = connexion.request.get_json()
        #questionParser = ParseQuestion()
        #query = questionParser.format_response(question)
        #return(query)
        return( { "status": 501, "title": "Translate not implemented", "detail": "The Translate function used to work, but have been disabled", "type": "about:blank" }, 501 )
    else:
        return( { "status": 400, "title": "body content not JSON", "detail": "Required body content is not JSON", "type": "about:blank" }, 400 )

import connexion
from swagger_server.models.query import Query
from swagger_server.models.question import Question
from datetime import date, datetime
from typing import List, Dict
from six import iteritems
from ..util import deserialize_date, deserialize_datetime
from QuestionTranslator import QuestionTranslator

def translate(body):
    """
    Translate natural language question into a standardized query
    
    :param body: Question object that needs to be translated
    :type body: dict | bytes

    :rtype: List[Query]
    """

    query = None
    if connexion.request.is_json:
        #body = Question.from_dict(connexion.request.get_json())
        question = connexion.request.get_json()
        txltr = QuestionTranslator()
        query = txltr.translate(question)
    return query

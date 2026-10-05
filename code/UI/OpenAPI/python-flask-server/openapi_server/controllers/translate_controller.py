import connexion


def translate(request_body=None):  # noqa: E501
    """Translate natural language question into a standardized query

     # noqa: E501

    :param request_body: Question information to be translated
    :type request_body: Dict[str, ]

    :rtype: list[dict[str, str]]
    """
    if connexion.request.is_json:
        return( { "status": "501",
                  "title": "/translate not implemented",
                  "detail": "The /translate function used to work, but has been disabled",
                  "type": "about:blank" },
                501 )
    else:
        return( { "status": "400",
                  "title": "body content not JSON",
                  "detail": "Required body content is not JSON",
                  "type": "about:blank" },
                400 )

def example_questions(request_body=None):  # noqa: E501
    """Request a list of example questions that ARAX can answer

     # noqa: E501


    :rtype: list[dict[str, str]]
    """
    return [{
            "status": "501",
            "title": "/exampleQuestions not implemented",
            "detail": "The /exampleQuestions function used to work, "
            "but has been disabled", "type": "about:blank"
    }], 501

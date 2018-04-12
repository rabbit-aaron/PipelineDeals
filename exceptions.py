class PipelineDealsException(Exception):
    pass


class PipelineDealsHTTPException(PipelineDealsException):
    def __init__(self, response=None):
        self.response = response


class PipelineDealsHTTP500Exception(PipelineDealsHTTPException):
    pass

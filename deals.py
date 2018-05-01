from .base import PipelineDealsObject, Collection


class Deal(PipelineDealsObject):
    pass


class DealCollection(Collection):

    instance_klass = Deal
    api_path = 'deals'
    name_space = 'deal'  # used during creation


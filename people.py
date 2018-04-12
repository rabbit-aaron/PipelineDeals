from .base import PipelineDealsObject, Collection


class Person(PipelineDealsObject):
    pass


class PersonCollection(Collection):

    instance_klass = Person
    api_path = 'people'
    name_space = 'person'  # used during creation

    def create(self, check_for_duplicates=False, deliver_assignment_email=True,  **attrs):
        extra_params = {
            'check_for_duplicates': str(bool(check_for_duplicates)).lower(),
            'deliver_assignment_email': str(bool(deliver_assignment_email)).lower(),
        }
        return super(PersonCollection, self).create(extra_params=extra_params, **attrs)
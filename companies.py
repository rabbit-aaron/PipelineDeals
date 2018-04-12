from .base import PipelineDealsObject, Collection


class Company(PipelineDealsObject):
    pass


class CompanyCollection(Collection):

    instance_klass = Company
    api_path = 'companies'
    name_space = 'company'  # used during creation

    def create(self, check_for_duplicates=False,  **attrs):
        extra_params = {
            'check_for_duplicates': str(bool(check_for_duplicates)).lower(),
        }
        return super(CompanyCollection, self).create(extra_params=extra_params, **attrs)

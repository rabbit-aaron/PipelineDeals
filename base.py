import requests
import urllib
from exceptions import PipelineDealsHTTP500Exception, PipelineDealsException, PipelineDealsHTTPException


class Page(object):

    def __init__(self, instance_klass, page_data):
        self.page_data = page_data
        self.instance_klass = instance_klass
        self.number = self.page_data['pagination']['page']
        self.pages = self.page_data['pagination']['pages']

    def __iter__(self):
        for entry in self.page_data['entries']:
            yield self.instance_klass(entry)


class PipelineDeals(object):
    protocal = 'https'
    domain = 'api.pipelinedeals.com'
    prefix = 'api/v3'

    def __init__(self, api_key=None, format='json', *args, **kwargs):
        self.format = format
        self.api_key = api_key
        if not api_key:
            self.api_key = 'JKSnuAGV6SvrKpEf3I'  # TODO: change this to settings

    def _get_exception_by_status(self, status_code):
        if status_code == 200:
            return None
        elif status_code == 500:
            return PipelineDealsHTTP500Exception
        else:
            return PipelineDealsHTTPException

    def _request(self, method, *args, **kwargs):
        method = getattr(requests, method, None)
        if not method:
            raise ValueError('Method {method} is not supported'.format(method=method))
        response = method(*args, **kwargs)

        exception = self._get_exception_by_status(response.status_code)

        if exception:
            raise exception(response)

        return response.json()

    def _get(self, *args, **kwargs):
        return self._request('get', *args, **kwargs)

    def _post(self, *args, **kwargs):
        return self._request('post', *args, **kwargs)

    def endpoint(self, api_path, object_id=None, extra_params=None, include_page_params=True, page=1, per_page=200):
        if extra_params is None:
            extra_params = {}

        query_params = {
            'api_key': self.api_key,
        }

        query_params.update(extra_params)

        if include_page_params:
            query_params.update({
                'page': page,
                'per_page': per_page,
            })

        detail = '/{object_id}'.format(object_id=object_id) if object_id else ''

        return '{self.protocal}://{self.domain}/{self.prefix}/{api_path}{detail}.{self.format}/?{query_string}'.format(
            self=self,
            api_path=api_path,
            detail=detail,
            query_string=urllib.urlencode(query_params)
        )

    def fetch_iter(self, api_path, extra_params=None):
        """
        Fetch resource page by page until it reaches the last page
        """
        page = 1
        pages = float('inf')
        while page <= pages:
            endpoint = self.endpoint(api_path, extra_params=extra_params, page=page)
            result = self._get(endpoint)
            if result:
                for entry in result['entries']:
                    yield entry
                pages = result['pagination']['pages']
                page = result['pagination']['page']
                page += 1


class PipelineDealsObject(object):

    def __init__(self, data):
        self.data = data

    def items(self):
        return self.data.items()

    def get(self, attr, default=None):
        return self.data.get(attr, default)

    def __repr__(self):
        return '{self.__class__.__name__}<{self.id}>'.format(self=self)


class Collection(PipelineDeals):

    class FailedToCreate(PipelineDealsException):
        pass

    class DoesNotExist(PipelineDealsException):
        pass

    instance_klass = None
    api_path = None

    def _iter(self, extra_params=None, per_page=200, max_pages=1):
        current_page = 1
        while True:
            if current_page > max_pages > 0:
                break
            endpoint = self.endpoint(self.api_path, extra_params=extra_params, page=current_page, per_page=per_page)
            result = self._get(endpoint)
            page = Page(self.instance_klass, result)
            for entry in page:
                yield entry
            if page.number == page.pages:
                break
            current_page += 1

    def create(self, extra_params=None, **attrs):
        endpoint = self.endpoint(self.api_path, include_page_params=False, extra_params=extra_params)
        try:
            result = self._post(endpoint, data={
                '{self.name_space}[{attr}]'.format(self=self, attr=attr): val for attr, val in attrs.items()
            })
            return self.instance_klass(result)
        except PipelineDealsHTTPException as e:
            if e.response.status_code == 422:
                raise self.FailedToCreate(e.response.json())
            raise e

    def all(self, per_page=200, max_pages=1):
        return self._iter(None, per_page, max_pages)

    def filter(self, per_page=200, max_pages=1, **conditions):
        extra_params = {
            'conditions[{}]'.format(condition): value for condition, value in conditions.items()
        }
        return self._iter(extra_params, per_page, max_pages)

    def get(self, object_id):
        try:
            endpoint = self.endpoint(self.api_path, object_id=object_id, include_page_params=False)
            result = self._get(endpoint)
            return self.instance_klass(result)
        except PipelineDealsHTTPException as e:
            if e.response.status_code == 404:
                raise self.DoesNotExist(u'{self.instance_klass.__name__} with id {object_id} does not exist'.format(
                    self=self, object_id=object_id
                ))
            raise e

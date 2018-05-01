import requests
import urllib

from .exceptions import (
    PipelineDealsException,
    PipelineDealsHTTPException,
    PipelineDealsHTTP404Exception,
    PipelineDealsHTTP422Exception,
    PipelineDealsHTTP500Exception,
)


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
    protocol = 'https'
    domain = 'api.pipelinedeals.com'
    prefix = 'api/v3'

    EXCEPTION_MAPPING = {
        404: PipelineDealsHTTP404Exception,
        422: PipelineDealsHTTP422Exception,
        500: PipelineDealsHTTP500Exception,
    }

    def __init__(self, api_key, format='json', *args, **kwargs):
        self.format = format
        self.api_key = api_key

    def _get_exception_by_status(self, status_code):
        if 200 <= status_code < 300:
            return None
        exception = self.EXCEPTION_MAPPING.get(status_code)
        return exception or PipelineDealsHTTPException

    def _request(self, method, *args, **kwargs):
        method = getattr(requests, method, None)
        if not method:
            raise ValueError('Method {method} is not supported'.format(method=method))
        response = method(*args, **kwargs)

        exception = self._get_exception_by_status(response.status_code)

        if exception:
            raise exception(response)

        if int(response.headers.get('content-length', '0')):
            return response.json()

    def _get(self, *args, **kwargs):
        return self._request('get', *args, **kwargs)

    def _post(self, *args, **kwargs):
        return self._request('post', *args, **kwargs)

    def _put(self, *args, **kwargs):
        return self._request('put', *args, **kwargs)

    def _delete(self, *args, **kwargs):
        return self._request('delete', *args, **kwargs)

    def endpoint(self, api_path, object_id=None, extra_params=None, include_page_params=True, page=1, per_page=200):
        if extra_params is None:
            extra_params = {}

        query_params = {
            'api_key': self.api_key,
        }

        query_params.update(extra_params)

        if include_page_params:
            query_params.update({'page': page, 'per_page': per_page})

        detail = '/{object_id}'.format(object_id=object_id) if object_id is not None else ''

        return '{self.protocol}://{self.domain}/{self.prefix}/{api_path}{detail}.{self.format}/?{query_string}'.format(
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
        return '{self.__class__.__name__}<{self.data[id]}>'.format(self=self)


class Collection(PipelineDeals):

    class FailedToUpdate(PipelineDealsException):
        pass

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
            result = self._post(endpoint, json={
                self.name_space: attrs
            })
            return self.instance_klass(result)
        except PipelineDealsHTTP422Exception as e:
            raise self.FailedToCreate(e.response.json())

    def get_or_create(self, conditions, **attrs):
        """
        find an object that meets the condition,
        only the first will be returned if there are more than one result
        note that the match might not be exact as that is the API's behaviour

        NOTE: Keep in mind the look up provided by PipelineDeals is a fuzzy look up, result might not work as expected,
        you might need to manually check the return object and decide whether the creation is needed

        :param conditions: this will be used as Collection.filter(per_page=1, **conditions)
        :param attrs:  this will be used as Collection.create(**attrs)
        :return: (True, object) if object is created, or (False, object) if found

        """

        result = list(self.filter(per_page=1, **conditions))
        if result:
            return False, result[0]
        return True, self.create(**attrs)

    def all(self, per_page=200, max_pages=1):
        return self._iter(None, per_page, max_pages)

    def filter(self, per_page=200, max_pages=1, **conditions):
        extra_params = {
            'conditions[{}]'.format(condition): value for condition, value in conditions.items()
        }
        return self._iter(extra_params, per_page, max_pages)

    def update(self, obj, **attrs):
        """
        :param obj: either an object (instance of PipelineDealsObject's subclass) or an object id
        :return: updated object
        """
        if isinstance(obj, self.instance_klass):
            object_id = obj.get('id')
        else:
            object_id = obj

        endpoint = self.endpoint(self.api_path, object_id=object_id, include_page_params=False)

        try:
            result = self._put(endpoint, json={
                self.name_space: attrs
            })
            return self.instance_klass(result)
        except PipelineDealsHTTP404Exception:
            raise self.DoesNotExist(u'{self.instance_klass.__name__} with id {object_id} does not exist'.format(
                self=self, object_id=object_id
            ))
        except PipelineDealsHTTP422Exception:
            raise self.FailedToUpdate(result.json())


    def delete(self, obj):
        """
        :param obj: either an object (instance of PipelineDealsObject's subclass) or an object id
        """
        if isinstance(obj, self.instance_klass):
            object_id = obj.get('id')
        else:
            object_id = obj

        endpoint = self.endpoint(self.api_path, object_id=object_id, include_page_params=False)

        try:
            self._delete(endpoint)
        except PipelineDealsHTTP404Exception:
            raise self.DoesNotExist(u'{self.instance_klass.__name__} with id {object_id} does not exist'.format(
                self=self, object_id=object_id
            ))

    def get_by_id(self, object_id):
        try:
            endpoint = self.endpoint(self.api_path, object_id=object_id, include_page_params=False)
            result = self._get(endpoint)
            return self.instance_klass(result)
        except PipelineDealsHTTP404Exception:
            raise self.DoesNotExist(u'{self.instance_klass.__name__} with id {object_id} does not exist'.format(
                self=self, object_id=object_id
            ))


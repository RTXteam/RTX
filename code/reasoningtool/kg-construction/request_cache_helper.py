import requests
import requests_cache
import hashlib

_DEFAULT_HEADERS = requests.utils.default_headers()

requests_cache.install_cache("orangeboard")

def get_timestamp(url):

    def _to_bytes(s, encoding='utf-8'):
        return bytes(s, encoding)

    def create_key(request):
        url, body = request.url, request.body
        key = hashlib.sha256()
        key.update(_to_bytes(request.method.upper()))
        key.update(_to_bytes(url))
        if request.body:
            key.update(_to_bytes(body))
        return key.hexdigest()

    def url_to_key(url):
        session = requests.Session()
        return create_key(session.prepare_request(requests.Request('GET', url)))

    results = requests_cache.get_cache()
    key_url = url_to_key(url)
    if key_url in results.responses:
        back_obj, timestamp = results.responses[key_url]
        return timestamp
    return None


if __name__ == '__main__':

    url = 'http://cohd.io/api/association/obsExpRatio?dataset_id=1&concept_id_1=192855&domain=Procedure'
    url1 = 'http://cohd.io/api/association/obsExpRatio?dataset_id=1&concept_id_1=192853&domain=Procedure'
    url2 = 'http://cohd.io/api/association/obsExpRatio?dataset_id=1&concept_id_1=192854&domain=Procedure'

    res = requests.get(url)
    res = requests.get(url1)

    print(get_timestamp(url))
    print(get_timestamp(url1))
    print(get_timestamp(url2))
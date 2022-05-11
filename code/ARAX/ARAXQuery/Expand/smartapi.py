"""SmartAPI registry access utility."""

import requests
import requests_cache
import re
from functools import lru_cache

class SmartAPI:
    """SmartAPI."""

    def __init__(self):
        """Initialize."""
        self.base_url = "http://smart-api.info/api"


    @lru_cache(maxsize=None)
    def get_all_trapi_endpoint_info(self):
        """Find all endpoints that match a query for TRAPI and return all the data about each of them"""
        """Find all endpoints that match a query for TRAPI."""
        with requests_cache.disabled():
            response_content = requests.get(
                self.base_url + "/query?limit=1000&q=TRAPI",
                headers={"accept": "application/json"},
            )

        endpoints = []

        try:
            response_content.raise_for_status()
            response_dict = response_content.json()
        except:
            return endpoints

        for hit in response_dict["hits"]:
            endpoints.append(hit)
        return endpoints


    @lru_cache(maxsize=None)
    def get_operations_endpoints(self):
        """Find all endpoints that support at least one workflow operation."""
        endpoints = self.get_trapi_endpoints()

        operations_endpoints = []
        for endpoint in endpoints:
            if endpoint["operations"] is not None:
                operations_endpoints.append(endpoint)

        return operations_endpoints


    @lru_cache(maxsize=None)
    def get_trapi_endpoints(self, version=None):
        """Find all endpoints that match a query for TRAPI."""
        with requests_cache.disabled():
            response_content = requests.get(
                self.base_url + "/query?limit=1000&q=TRAPI",
                headers={"accept": "application/json"},
            )

        endpoints = []

        try:
            response_content.raise_for_status()
            response_dict = response_content.json()
        except:
            return endpoints

        for hit in response_dict["hits"]:
            try:
                url = hit["servers"][0]["url"]
            except (KeyError, IndexError):
                url = None
            try:
                url_version = hit["info"]["x-trapi"]["version"]
            except KeyError:
                url_version = None
            try:
                operations = hit["info"]["x-trapi"]["operations"]
            except KeyError:
                operations = None

            try:
                infores_name = hit["info"]["x-translator"]["infores"]
            except KeyError:
                infores_name = None

            try:
                component = hit["info"]["x-translator"]["component"]
            except KeyError:
                component = None

            try:
                title = hit["info"]["title"]
            except KeyError:
                title = None

            servers = []
            for server in hit["servers"]:
                try:
                    url = server["url"]
                except KeyError:
                    url = None
                try:
                    description = server["description"]
                except KeyError:
                    description = None
                try:
                    maturity = server["x-maturity"]
                except KeyError:
                    maturity = None
                log.debug("DEBUGGING LOOP HERE")
                servers.append({"description": description, "url": url, "maturity": maturity})

            if version is not None:
                if url_version is None:
                    continue
                match = re.match(version, url_version)
                if not match:
                    continue

            endpoints.append({
                "servers": servers,
                "operations": operations,
                "version": url_version,
                "component": component,
                "infores_name": infores_name,
                "title": title
            })

        return endpoints


    @lru_cache(maxsize=None)
    def get_kps(self, version=None, reqMaturity=None):
        """Find all endpoints that match a query for TRAPI which are classified as KPs"""

        endpoints = self.get_trapi_endpoints()
        KPs = list(filter(lambda x: x["component"] == "KP", endpoints))
        return KPs

    @lru_cache(maxsize=None)
    def get_dev_kps(self, version=None, reqMaturity=None):
        """Find all endpoints that match a query for TRAPI which are classified as KPs and have servers which are classified as 'development'"""

        KPs = self.get_kps()
        # remove servers from server list which are not "development"
        for KP in KPs:
            dev_servers = [server for server in KP["servers"] if server["maturity"] == "development"]
            # dev_servers = list(filter(lambda x: x["maturity"] == "development", dev_servers))
            KP["servers"] = dev_servers
        # remove KPs which have no servers left after removing non-dev servers
        # KPs = list(filter(lambda x: len(KP["servers"]) > 0, KPs))

        return KPs

    @lru_cache(maxsize=None)
    def get_prod_kps(self, version=None, reqMaturity=None):
        """Find all endpoints that match a query for TRAPI which are classified as KPs and have servers which are classified as 'development'"""

        KPs = self.get_kps()
        # remove servers from server list which are not "production"
        for KP in KPs:
            dev_servers = KP["servers"]
            dev_servers = list(filter(lambda x: x["maturity"] == "production", dev_servers))
            KP["servers"] = dev_servers
        # remove KPs which have no servers left after removing non-prod servers
        KPs = list(filter(lambda x: len(KP["servers"]) > 0, KPs))

        return KPs


def main():
    """Run CLI."""
    import argparse
    import json

    argparser = argparse.ArgumentParser(
        description="CLI testing of the ResponseCache class"
    )
    argparser.add_argument(
        "--get_trapi_endpoints",
        action="count",
        help="Get a list of TRAPI endpoints",
    )
    argparser.add_argument(
        "--get_operations_endpoints",
        action="count",
        help="Get a list of TRAPI endpoints that support operations",
    )
    argparser.add_argument(
        "--version",
        action="store",
        help="TRAPI version number to limit to (e.g. '1.1')",
    )
    args = argparser.parse_args()

    if (
        args.get_trapi_endpoints is None
        and args.get_operations_endpoints is None
    ):
        argparser.print_help()
        return

    smartapi = SmartAPI()

    if args.get_trapi_endpoints:
        endpoints = smartapi.get_trapi_endpoints(version=args.version)
        print(json.dumps(endpoints, sort_keys=True, indent=2))

    if args.get_operations_endpoints:
        endpoints = smartapi.get_operations_endpoints()
        print(json.dumps(endpoints, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

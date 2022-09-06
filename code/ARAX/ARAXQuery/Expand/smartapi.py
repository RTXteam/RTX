"""SmartAPI registry access utility."""

import requests
import requests_cache
import json
import re
from functools import lru_cache

class SmartAPI:
    """SmartAPI."""

    def __init__(self):
        """Initialize."""
        self.base_url = "http://smart-api.info/api"
        self.kps_excluded_by_version = set()
        self.kps_excluded_by_maturity = set()


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


    # @lru_cache(maxsize=None)
    def get_operations_endpoints(self, version=None, whitelist=None, blacklist=None):
        """Find all endpoints that support at least one workflow operation."""
        endpoints = self.get_trapi_endpoints(whitelist=whitelist, blacklist=blacklist)

        operations_endpoints = []
        for endpoint in endpoints:
            if endpoint["operations"] is not None:
                operations_endpoints.append(endpoint)

        return operations_endpoints


    # @lru_cache(maxsize=None)
    def get_trapi_endpoints(self, version=None, whitelist=None, blacklist=None):
        """Find all endpoints that match a query for TRAPI."""
        self.kps_excluded_by_version = set()
        self.kps_excluded_by_maturity = set()

        with requests_cache.disabled():
            response_content = requests.get(
                self.base_url + "/query?limit=1000&q=TRAPI&raw=1",
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
                servers.append({"description": description, "url": url, "maturity": maturity})
            if len(servers) == 0:
                continue

            if version is not None:
                if url_version is None:
                    if component == "KP":
                        self.kps_excluded_by_version.add(infores_name)
                    continue
                match = re.match(version, url_version)
                if not match:
                    if component == "KP":
                        self.kps_excluded_by_version.add(infores_name)
                    continue

            try:
                smartapi_url = "https://smart-api.info/ui/" + hit["_id"]
            except:
                smartapi_url = None

            endpoints.append({
                "servers": servers,
                "operations": operations,
                "version": url_version,
                "component": component,
                "infores_name": infores_name,
                "title": title,
                "smartapi_url": smartapi_url
            })

        if whitelist:
            endpoints = [ep for ep in endpoints if ep["infores_name"] in whitelist]
        if blacklist:
            endpoints = [ep for ep in endpoints if ep["infores_name"] not in blacklist]

        return endpoints

    # helper for collate_and_print
    def _stringify_list(self, string_list):
        if len(string_list) == 0:
            return ""
        pretty_list = string_list[0]
        for elem in string_list[1:]:
            pretty_list += ", " + elem
        return pretty_list


    def collate_and_print(self, endpoints):
        """Pretty print list of trapi endpoints. This function takes list of JSON-formatted TRAPI endpoints, aggregates entries that share the same infores name, and then prints their names and maturity levels in a formatted table. This is intended to get a quick view of endpoints when used with the -p/--pretty flag via the CLI"""
        # collate all endpoint entries into a dict
        entries = {}
        for ep in endpoints:
            infores_name = str(ep["infores_name"])
            component = str(ep["component"])
            maturities = {server["maturity"] for server in ep["servers"] if server["maturity"] != None}
            n_entries = 1
            # if new entry, start with n_entries = 1
            if infores_name not in entries:
                entries[infores_name] = [component,maturities,n_entries]
            # if existing entry, combine maturities sets and increment n_entries
            else:
                entries[infores_name][1] |= maturities
                entries[infores_name][2] += 1

        # convert entries dict to sorted list of 'rows'
        rows = []
        for name in entries:
            row = [name] + entries[name]
            # convert maturity set to more readable string format
            row[2] = list(row[2])
            row[2].sort()
            row[2] = self._stringify_list(row[2])
            rows.append(row)
        rows.sort(key=lambda x:x[0])

        if len(rows) == 0:
            print("No results")
            return

        # find longest elements in columns to determine column width
        l1 = max(len(row[0]) for row in rows)+1
        l2 = max(len(row[2]) for row in rows)+1
        # pretty print rows
        format_str = "{:<"+str(l1)+"}{:<10}{:<"+str(l2)+"}{:<4}"
        print(format_str.format("infores name","component","maturities","n_entries"))
        for row in rows:
            print(format_str.format(*row))


    def _filter_kps_by_maturity(self, KPs, req_maturity, flexible, hierarchy):
        """Return a list of KPs which have been filtered based on the maturity attribute of their servers. If flexible is false, it will remove servers from each KP whose maturity does not match req_maturity. If flexible is true, it will use the specified 'hierarchy' to look use the next best maturity level for each server until at least one server has been found. It returns only the KPs with servers remaining after they have been filtered in this way."""
        if not flexible:
            for kp in KPs:
                kp["servers"] = [server for server in kp["servers"] if server["maturity"] == req_maturity]
            KPs = [kp for kp in KPs if len(kp["servers"]) != 0]
            return KPs

        # if reqMaturity is 'testing' and the default hierarchy is used
        # it should look something like this, where | is the maturity_thresh:
        # ['development', 'staging', | 'testing', 'production']
        # and it will consider both 'testing' and 'production' maturities valid
        maturity_thresh = hierarchy.index(req_maturity)
        acceptable_maturities = hierarchy[maturity_thresh:]
        for kp in KPs:
            for maturity in acceptable_maturities:
                servers = [server for server in kp["servers"] if server["maturity"] == maturity]
                if len(servers) != 0:
                    kp["servers"] = servers
                    break
            else:
                kp["servers"] = []

        KPs = [kp for kp in KPs if len(kp["servers"]) != 0]
        return KPs


    # @lru_cache(maxsize=None)
    def get_kps(self, log=None, version=None, req_maturity=None, flexible=False, hierarchy=None, whitelist=None, blacklist=None):
        """Find all endpoints that match a query for TRAPI which are classified as KPs. If req_maturity is given and flexible is false, this will only return KPs and KP servers with maturity levels that match req_maturity. If flexible is true, the hierarchy will be used to find the preferred maturity level if no servers match req_maturity for that KP. If no hierarchy is given, the hierarchy compliant with the standard set by Translator will be used. The whitelist and blacklist should be given as sets of infores_names, which can be used to restrict the list of KPs that are returned. Note that some KPs may not have infores names."""

        endpoints = self.get_trapi_endpoints(version=version, whitelist=whitelist, blacklist=blacklist)
        all_KPs = [ep for ep in endpoints if ep["component"] == "KP"]

        if req_maturity:
            if hierarchy == None:
                hierarchy = ["development","staging","testing","production"]
            if req_maturity not in hierarchy:
                raise ValueError("Invalid maturity passed to get_kps")
            KPs = self._filter_kps_by_maturity(all_KPs, req_maturity, flexible, hierarchy)
        else:
            KPs = all_KPs

        accepted_KP_names = [kp["infores_name"] for kp in KPs]
        self.kps_excluded_by_maturity = {kp["infores_name"] for kp in all_KPs if kp["infores_name"] not in accepted_KP_names}

        return KPs



def setup_cli():
    """Setup and return argparser for the CLI."""

    import argparse
    argparser = argparse.ArgumentParser(
        description="CLI Interface of the smartapi class which enables users to fetch TRAPI endpoints from the smartapi registry"
    )
    argparser.add_argument(
        "results_type",
        choices=["get_trapi_endpoints", "get_operations_endpoints", "get_kps"],
        help="Specifying what type of results to return",
    )
    argparser.add_argument(
        "-p",
        "--pretty",
        action="store_true",
        help="Used to produce output in 'pretty' table form instead of raw json. This also collates registry entries based on the infores name"
    )
    argparser.add_argument(
        "-m",
        "--req_maturity",
        action="store",
        help="Optionally used with 'get_kps' to filter results to KPs with a specific maturity level"
    )
    argparser.add_argument(
        "-f",
        "--flexible",
        action="store_true",
        help="Optionally used when --req_maturity is given. If flexible is not given, only KPs with specified maturity will be returned. Otherwise, KPs with the next best maturity (as specified in the --hierarchy) will be included when there are no servers matching --req_maturity"
    )
    argparser.add_argument(
        "-i",
        "--hierarchy",
        action="store",
        nargs="+",
        help="Optionally used as the ordering of the four KP maturity levels used when --req_maturity and --flexible are given"
    )
    argparser.add_argument(
        "-w",
        "--whitelist",
        action="store",
        nargs="*",
        help="A list of infores names which is optionally used to filter results"
    )
    argparser.add_argument(
        "-b",
        "--blacklist",
        action="store",
        nargs="*",
        help="A list of infores names which is optionally used to filter results"
    )
    argparser.add_argument(
        "-v",
        "--version",
        action="store",
        help="TRAPI version number to limit to (e.g. '1.1')",
    )
    return argparser


def main():
    """Run CLI."""

    argparser = setup_cli()
    args = argparser.parse_args()

    smartapi = SmartAPI()

    if args.results_type == "get_trapi_endpoints":
        if args.req_maturity or args.flexible or args.hierarchy:
            argparser.print_help()
            return
        output = smartapi.get_trapi_endpoints(version=args.version, whitelist=args.whitelist, blacklist=args.blacklist)

    elif args.results_type == "get_operations_endpoints":
        if args.req_maturity or args.flexible or args.hierarchy:
            argparser.print_help()
            return
        output = smartapi.get_operations_endpoints(whitelist=args.whitelist, blacklist=args.blacklist)

    elif args.results_type == "get_kps":
        if (args.hierarchy or args.flexible) and (args.req_maturity == None):
            argparser.print_help()
            return
        if args.hierarchy and args.flexible == None:
            argparser.print_help()
            return
        output = smartapi.get_kps(version=args.version, req_maturity=args.req_maturity, flexible=args.flexible, hierarchy=args.hierarchy, whitelist=args.whitelist, blacklist=args.blacklist)

    if args.pretty:
        smartapi.collate_and_print(output)
    else:
        print(json.dumps(output, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

import requests
import json

infores_dict = { 'infores:arax': [] }

url = "https://arax.ci.transltr.io/api/arax/v1.4/status?authorization=smartapi"
response = requests.get(url)

if response.status_code == 200:
    smartapi_entries = response.json()
  
    for entry in smartapi_entries:
        if entry['component'] == 'KP':
            infores_dict['infores:arax'].append(entry['infores_name'])

    with open('arax_infores_list.json', 'w') as outfile:
        print(json.dumps(infores_dict, indent=2, sort_keys=True), file=outfile)
else:
    print(f"Error downloading file: {response.status_code}")






import webbrowser
from datetime import datetime
import json
import os
import msal
import requests
import shutil
from tqdm.auto import tqdm
from tqdm.utils import CallbackIOWrapper

GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
SCOPES = ["User.ReadWrite"]
remote_folder_name = "test"

def generate_access_token(scopes):
    with open('APP_ID', 'r') as file:
       APP_ID = file.read()    
        
    # Save Session Token as a token file
    access_token_cache = msal.SerializableTokenCache()

    # read the token file
    if os.path.exists('ms_graph_api_token.json'):
        access_token_cache.deserialize(open("ms_graph_api_token.json", "r").read())
        token_detail = json.load(open('ms_graph_api_token.json',))
        token_detail_key = list(token_detail['AccessToken'].keys())[0]
        token_expiration = datetime.fromtimestamp(int(token_detail['AccessToken'][token_detail_key]['expires_on']))
        if datetime.now() > token_expiration:
            os.remove('ms_graph_api_token.json')
            access_token_cache = msal.SerializableTokenCache()

    # assign a SerializableTokenCache object to the client instance
    client = msal.PublicClientApplication(client_id=APP_ID, token_cache=access_token_cache)

    accounts = client.get_accounts()
    if accounts:
        # load the session
        token_response = client.acquire_token_silent(scopes, accounts[0])
    else:
        # authetnicate your accoutn as usual
        flow = client.initiate_device_flow(scopes=scopes)
        print('user_code: ' + flow['user_code'])
        print('URL: ' + 'https://microsoft.com/devicelogin')
        webbrowser.open('https://microsoft.com/devicelogin')
        token_response = client.acquire_token_by_device_flow(flow)

    with open('ms_graph_api_token.json', 'w') as _f:
        _f.write(access_token_cache.serialize())

    return token_response


def uploadFile(file_path, file_name):
    try:
        url = GRAPH_API_ENDPOINT + f"/me/drive/items/root:/{remote_folder_name}/{file_name}:/content"
        file_size = os.path.getsize(os.path.join(file_path, file_name))
        headers = {
            "Authorization": "bearer " + generate_access_token(APP_ID, SCOPES)['access_token'],
                'Content-Length': str(file_size)
            }
        with open(os.path.join(file_path, file_name), 'rb') as f:
            with tqdm(desc=f"Uploading {file_name}", total=file_size, unit="B", unit_scale=True, unit_divisor=1024) as t:
                reader_wrapper = CallbackIOWrapper(t.update, f, "read")
                requests.put(url, headers=headers, data=reader_wrapper)
    except:
         print(f"An exception occurred while trying to upload file : {file_name}")

            
def downloadFile(file_id, save_location):
    access_token = generate_access_token(APP_ID, scopes=SCOPES)
    headers = {
        'Authorization': 'Bearer ' + access_token['access_token']
    }


    response_file_info = requests.get(
        GRAPH_API_ENDPOINT + f'/me/drive/items/{file_id}',
           headers=headers
       )
       
    file_url = response_file_info.json().get("@microsoft.graph.downloadUrl") 
    file_name = response_file_info.json().get("name")
        
    with requests.get(file_url, stream=True) as r:
        total_length = int(r.headers.get("Content-Length"))
        # implement progress bar via tqdm
        with tqdm.wrapattr(r.raw, "read", total=total_length, desc="")as raw:
           # save the output to a file
            with open(os.path.join(save_location, file_name), 'wb') as output:
                shutil.copyfileobj(raw, output)
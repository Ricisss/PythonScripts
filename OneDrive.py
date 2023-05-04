import webbrowser
from datetime import datetime
import json
import os
import msal
import requests
import shutil
import time
from tqdm.auto import tqdm
from tqdm.utils import CallbackIOWrapper
import concurrent.futures

GRAPH_API_ENDPOINT = 'https://graph.microsoft.com/v1.0'
SCOPES = ["User.ReadWrite"]
remote_folder_name = "test"
#hunk_size = 327680 * 192
chunk_size = 327680 * 10

def generate_access_token(scopes):
    with open('APP_ID', 'r') as file:
       APP_ID = file.read().strip()    
        
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
            "Authorization": "bearer " + generate_access_token(SCOPES)['access_token'],
                'Content-Length': str(file_size)
            }
        with open(os.path.join(file_path, file_name), 'rb') as f:
            with tqdm(desc=f"Uploading {file_name}", total=file_size, unit="B", unit_scale=True, unit_divisor=1024) as t:
                reader_wrapper = CallbackIOWrapper(t.update, f, "read")
                requests.put(url, headers=headers, data=reader_wrapper)
    except Exception as e:
        print(e)

            
def downloadFile(file_id, save_location):
    access_token = generate_access_token(scopes=SCOPES)
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
    return file_name


def uploadLargeFile(file_path, folder_id):
    #GET SESSION URL
    access_token = generate_access_token(SCOPES)
    headers = {
        'Authorization': 'Bearer ' + access_token['access_token']
    }

    file_name = os.path.basename(file_path)

    if not os.path.exists(file_path):
        raise Exception(f"{file_name} not found")

    with open(file_path, 'rb') as upload:
        media_content = upload.read()

    request_body={
        "@microsoft.graph.conflictBehavior": "rename",
        "description": "description",
        "fileSystemInfo": { "@odata.type": "microsoft.graph.fileSystemInfo" },
        "name": file_name
    }


    response_upload_session = requests.post(
        GRAPH_API_ENDPOINT + f'/me/drive/items/{folder_id}:/{file_name}:/createUploadSession',
        headers = headers,
        json=request_body
    )

    #UPLOAD DATA TO SESSION
    with open(file_path, 'rb') as upload:
        time_start = time.time();
        total_file_size = os.path.getsize(file_path)
        chunk_size = 327680 * 192
        #chunk_size = 327680 * 50
        print(f"Chunk size: {chunk_size/1024/1024}MiB")
        chunk_number = total_file_size // chunk_size
        chunk_leftover = total_file_size - (chunk_size * chunk_number)
        counter = 0
        print(f"Total Chunks: {chunk_number}")

        while True:
            chunk_data = upload.read(chunk_size)
            start_index = counter * chunk_size 
            end_index = start_index + chunk_size

            if not chunk_data:
                break
            if counter == chunk_number:
                end_index = start_index + chunk_leftover

            headers = {
                "Content-Length" : f"{chunk_size}",
                "Content-range" : f"bytes {start_index}-{end_index-1}/{total_file_size}"
            }

            try:
                upload_url = response_upload_session.json()['uploadUrl']
                chunkl_data_upload_status = requests.put(upload_url,headers=headers,data=chunk_data)

                if "createdBy" in chunkl_data_upload_status.json():
                    speed_estimate = (chunk_size * counter) / (time.time()-time_start) / 1024 / 1024
                    speed_estimate = round(speed_estimate, 2)
                    print(f"DONE in { round(time.time()-time_start, 2)}s {speed_estimate}MiB/s")
                else:
                    counter += 1   
                    speed_estimate = (chunk_size * counter) / (time.time()-time_start) / 1024 / 1024
                    speed_estimate = round(speed_estimate, 2)
                    print(f"Upload Progress: {speed_estimate} MB/s {counter}/{chunk_number}")
                                                                                                  

            except Exception as e:
                print(e)
                break
                
def uploadLargeFileConcurent(file_path, folder_id, MAX_THREADS):
    global upload
    #GET SESSION URL
    access_token = generate_access_token(SCOPES)
    headers = {
        'Authorization': 'Bearer ' + access_token['access_token']
    }

    file_name = os.path.basename(file_path)

    if not os.path.exists(file_path):
        raise Exception(f"{file_name} not found")

    #with open(file_path, 'rb') as upload:
    #    media_content = upload.read()

    request_body={
        "@microsoft.graph.conflictBehavior": "rename",
        "description": "description",
        "fileSystemInfo": { "@odata.type": "microsoft.graph.fileSystemInfo" },
        "name": file_name
    }


    response_upload_session = requests.post(
        GRAPH_API_ENDPOINT + f'/me/drive/items/{folder_id}:/{file_name}:/createUploadSession',
        headers = headers,
        json=request_body
    )

    #UPLOAD DATA TO SESSION

    with open(file_path, 'rb') as upload:
        print(f"Chunk size: {chunk_size/1024/1024}MiB")
        global chunk_number
        global chunk_leftover 
        global upload_url
        global total_file_size
        global time_start
        
        time_start = time.time();
        total_file_size = os.path.getsize(file_path)
        chunk_number = total_file_size // chunk_size
        chunk_leftover = total_file_size - (chunk_size * chunk_number)
        upload_url = response_upload_session.json()['uploadUrl']
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                res = executor.map(uploadChunk,  range(chunk_number+1))
                
            speed_estimate = (chunk_size * chunk_number) / (time.time()-time_start) / 1024 / 1024
            speed_estimate = round(speed_estimate, 2)
            print(f"DONE in { round(time.time()-time_start, 2)}s {speed_estimate}MiB/s")
            
        except Exception as e:
            print(e)
    


        
def uploadChunk(i):
    try:        
        print(f"starting upload {i}")
        chunk_data = upload.read(chunk_size)
        print(hash(chunk_data))
        start_index = i * chunk_size 
        end_index = start_index + chunk_size

        if i == chunk_number:
            end_index = start_index + chunk_leftover

        print(f"{start_index}/{end_index}")
        headers = {
            "Content-Length" : f"{chunk_size}",
            "Content-range" : f"bytes {start_index}-{end_index-1}/{total_file_size}"
        }        

        chunkl_data_upload_status = requests.put(upload_url,headers=headers,data=chunk_data)
        speed_estimate = (chunk_size * i) / (time.time()-time_start) / 1024 / 1024
        speed_estimate = round(speed_estimate, 2)
        print(f"Upload Progress: {speed_estimate} MB/s {i}/{chunk_number}   {chunkl_data_upload_status}")
        return chunkl_data_upload_status    
    
    except Exception as e:
            print(e)
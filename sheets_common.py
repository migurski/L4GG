from oauth2client.service_account import ServiceAccountCredentials
from apiclient import discovery

LOG_NAME = 'googleapiclient.discovery_cache'

def make_service(cred_data):
    '''
    '''
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_data, scopes)
    return discovery.build('sheets', 'v4', credentials=creds)

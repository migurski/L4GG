#!/usr/bin/env python3
import os, sys, json, logging, datetime
from apiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials

def make_service(cred_data):
    '''
    '''
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_data, scopes)
    return discovery.build('sheets', 'v4', credentials=creds)

def get_fields(service, sheet_id, sheet_name):
    '''
    '''
    # Get column names for selected sheet
    request = service.spreadsheets().values().get(spreadsheetId=sheet_id,
        range="'{}'!A1:Z1".format(sheet_name))

    fields = request.execute().get('values', [[]])[0]
    return fields

def post_form(service, sheet_id, formdata):
    '''
    '''
    # Sheets are named by U.S. state
    sheet_name = '{State} Responses'.format(**formdata)

    fields = ['Timestamp', 'County', 'State', 'First', 'Last', 'Email',
              'Zip (Home)', 'Zip (Work)', 'Practice Status', 'Link']
    values = [formdata.get(name, None) for name in fields]
    
    print('Fields:', json.dumps(fields))
    print('Values:', json.dumps(values))
    
    # Post a new row to selected sheet
    request = service.spreadsheets().values().append(spreadsheetId=sheet_id,
        range=sheet_name, body={'values': [values]}, valueInputOption='USER_ENTERED',
        # Rate-limiting: https://developers.google.com/sheets/api/query-parameters
        quotaUser=True)

    range = request.execute().get('updates', {}).get('updatedRange')
    print('Range:', range)
    
    return 0

def lambda_handler(event, context):
    print('Event:', json.dumps(event))
    
    # silence annoying debug output from Google libraries:
    # https://github.com/google/google-api-python-client/issues/299#issuecomment-255793971
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
    
    # retrieve credentials stored in environment vars
    creds = json.loads(os.environ['webform_serviceaccount'])
    sheet_id = os.environ['spreadsheet_id']
    redirect_url = os.environ['redirect']
    service = make_service(creds)
    
    # Assemble form data
    event_data = event.get('data', {})
    formdata = {
        'Timestamp': str(datetime.datetime.utcnow()),
        'County': event_data.get('county'),
        'State': event_data.get('state'),
        'First': event_data.get('first_name'),
        'Last': event_data.get('last_name'),
        'Email': event_data.get('email'),
        'Zip (Home)': event_data.get('home_zip'),
        'Zip (Work)': event_data.get('work_zip'),
        'Practice Status': event_data.get('practice_status'),
        'Link': event_data.get('link'),
        }
    
    post_form(service, sheet_id, formdata)
    return {'Location': redirect_url}

def main(filename, sheet_id):
    with open(filename) as file:
        creds = json.load(file)
        service = make_service(creds)
    formdata = {
        'Timestamp': str(datetime.datetime.utcnow()),
        'County': 'Alameda',
        'State': 'CA',
        'First': 'Lionel',
        'Last': 'Hutz',
        'Email': 'lhutz@example.com',
        'Zip (Home)': '94608',
        'Zip (Work)': '94612',
        'Practice Status': 'A-Okay',
        'Link': 'https://example.com',
        }
    return post_form(service, sheet_id, formdata)

if __name__ == '__main__':
    filename, sheet_id = sys.argv[1:]
    exit(main(filename, sheet_id))

import os, sys, json, logging, datetime
from apiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials

def make_service(cred_data):
    '''
    '''
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_data, scopes)
    return discovery.build('sheets', 'v4', credentials=creds)

def post_form(service, sheet_id, formdata):
    '''
    '''
    # Sheets are named by U.S. state
    sheet_name = '{State} Responses'.format(**formdata)

    # Get column names for selected sheet
    request = service.spreadsheets().values().get(spreadsheetId=sheet_id,
        range="'{}'!A1:Z1".format(sheet_name))

    fields = request.execute().get('values', [[]])[0]
    values = [formdata.get(name, None) for name in fields]
    
    print('Fields:', json.dumps(fields))
    print('Values:', json.dumps(values))
    
    # Post a new row to selected sheet
    request = service.spreadsheets().values().append(spreadsheetId=sheet_id,
        range=sheet_name, body={'values': [values]}, valueInputOption='USER_ENTERED')

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
    name = event.get('data', {}).get('name')
    state = event.get('data', {}).get('state')
    timestamp = str(datetime.datetime.utcnow())
    formdata = dict(Timestamp=timestamp, Name=name, State=state)
    
    post_form(service, sheet_id, formdata)
    return {'Location': redirect_url}

def main(filename, sheet_id):
    with open(filename) as file:
        creds = json.load(file)
        service = make_service(creds)
    formdata = dict(Timestamp=str(datetime.datetime.utcnow()), Name='Lionel Hutz', State='CA')
    return post_form(service, sheet_id, formdata)

if __name__ == '__main__':
    filename, sheet_id = sys.argv[1:]
    exit(main(filename, sheet_id))

#!/usr/bin/env python3
import os, sys, json, logging, datetime
import sheets_common

def get_fields(service, sheet_id, sheet_name):
    '''
    '''
    # Get column names for selected sheet
    request = service.spreadsheets().values().get(spreadsheetId=sheet_id,
        range="'{}'!A1:Z1".format(sheet_name))

    fields = request.execute().get('values', [[]])[0]
    return fields

def lambda_handler(event, context):
    print('Lambda event:', json.dumps(event))
    
    # silence annoying debug output from Google libraries:
    # https://github.com/google/google-api-python-client/issues/299#issuecomment-255793971
    logging.getLogger(sheets_common.LOG_NAME).setLevel(logging.ERROR)
    
    # retrieve credentials stored in environment vars
    creds = json.loads(os.environ['webform_serviceaccount'])
    sheet_id = os.environ['spreadsheet_id']
    error_url = os.environ['error_url']
    redirect_url = os.environ['redirect_url']
    sqs_url = os.environ['sqs_url']
    error_chance = float(os.environ['error_chance'])
    service = sheets_common.make_service(creds)
    
    # Assemble form data
    event_data = event.get('data', {})
    campaigns = [value for (key, value) in event_data.items() if key.startswith('campaigns_')]
    formdata = {
        'Timestamp': str(datetime.datetime.utcnow()),
        'County': event_data.get('county'),
        'State': event_data.get('state') or 'Stateless',
        'First': event_data.get('first_name'),
        'Last': event_data.get('last_name'),
        'Email': event_data.get('email'),
        'Primary Zip': event_data.get('zip_code'),
        'Practice Status': event_data.get('practice_status'),
        'Campaigns': ', '.join(sorted(campaigns)),
        'Coordinating': event_data.get('coordinating'),
        }
    
    try:
        sheets_common.post_form(service, sheet_id, sqs_url, error_chance, formdata)
    except Exception as e:
        print('Uncaught error:', e)
        return {'Location': error_url}
    else:
        return {'Location': redirect_url}

def main(filename, sheet_id, sqs_url):
    with open(filename) as file:
        creds = json.load(file)
        service = sheets_common.make_service(creds)
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
    return sheets_common.post_form(service, sheet_id, sqs_url, .5, formdata)

if __name__ == '__main__':
    filename, sheet_id, sqs_url = sys.argv[1:]
    exit(main(filename, sheet_id, sqs_url))

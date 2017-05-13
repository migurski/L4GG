#!/usr/bin/env python3
import os, sys, json, logging, datetime, random
import boto3, sheets_common

def get_fields(service, sheet_id, sheet_name):
    '''
    '''
    # Get column names for selected sheet
    request = service.spreadsheets().values().get(spreadsheetId=sheet_id,
        range="'{}'!A1:Z1".format(sheet_name))

    fields = request.execute().get('values', [[]])[0]
    return fields

def post_form(service, sheet_id, sqs_url, error_chance, formdata):
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
    try:
        # Randomly fail to keep a trickle of messages flowing to the queue.
        if random.random() < error_chance:
            raise RuntimeError('Randomly errored')

        # Append data to Google Spreadsheets.
        request = service.spreadsheets().values().append(spreadsheetId=sheet_id,
            range=sheet_name, body={'values': [values]}, valueInputOption='USER_ENTERED',
            # Rate-limiting: https://developers.google.com/sheets/api/query-parameters
            quotaUser=True)

    except Exception as e:
        # Send errors to the queue.
        client = boto3.client('sqs')
        message = json.dumps(dict(values=values, error=repr(e)), indent=2)
        response = client.send_message(QueueUrl=sqs_url, MessageBody=message)
        print('SQS Message ID:', response.get('MessageId'))
    
    else:
        range = request.execute().get('updates', {}).get('updatedRange')
        print('Range:', range)
    
    return 0

def lambda_handler(event, context):
    print('Event:', json.dumps(event))
    
    # silence annoying debug output from Google libraries:
    # https://github.com/google/google-api-python-client/issues/299#issuecomment-255793971
    logging.getLogger(sheets_common.LOG_NAME).setLevel(logging.ERROR)
    
    # retrieve credentials stored in environment vars
    creds = json.loads(os.environ['webform_serviceaccount'])
    sheet_id = os.environ['spreadsheet_id']
    redirect_url = os.environ['redirect']
    sqs_url = os.environ['sqs_url']
    error_chance = float(os.environ['error_chance'])
    service = sheets_common.make_service(creds)
    
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
    
    post_form(service, sheet_id, sqs_url, error_chance, formdata)
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
    return post_form(service, sheet_id, sqs_url, .5, formdata)

if __name__ == '__main__':
    filename, sheet_id, sqs_url = sys.argv[1:]
    exit(main(filename, sheet_id, sqs_url))

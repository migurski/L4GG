#!/usr/bin/env python3
import os, sys, json, logging, datetime, random
from apiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials
import boto3

def make_service(cred_data):
    '''
    '''
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(cred_data, scopes)
    return discovery.build('sheets', 'v4', credentials=creds)

def repost_form(service, sheet_id, sqs_url):
    '''
    '''
    client = boto3.client('sqs')
    response = client.receive_message(QueueUrl=sqs_url, VisibilityTimeout=10)
    messages = response.get('Messages', [])
    
    for message in messages:
        body = json.loads(message['Body'])
        values, error = body['values'], body['error']
        print('MessageId:', message['MessageId'])
        print('Values:', values)
        print('Error:', error)
    
        # Post a new row to selected sheet
        try:
            # Append data to Google Spreadsheets.
            request = service.spreadsheets().values().append(spreadsheetId=sheet_id,
                range=sheet_name, body={'values': [values]}, valueInputOption='USER_ENTERED',
                # Rate-limiting: https://developers.google.com/sheets/api/query-parameters
                quotaUser=True)

        except Exception as e:
            print('New error:', e)
    
        else:
            range = request.execute().get('updates', {}).get('updatedRange')
            client.delete_message(QueueUrl=sqs_url, ReceiptHandle=message['ReceiptHandle'])
            print('Range:', range)

def main(filename, sheet_id, sqs_url):
    with open(filename) as file:
        creds = json.load(file)
        service = make_service(creds)
    return repost_form(service, sheet_id, sqs_url)

if __name__ == '__main__':
    filename, sheet_id, sqs_url = sys.argv[1:]
    exit(main(filename, sheet_id, sqs_url))

#!/usr/bin/env python3
import os, sys, json, logging
import sheets_common

def lambda_handler(event, context):
    print('Lambda event:', json.dumps(event))
    
    # silence annoying debug output from Google libraries:
    # https://github.com/google/google-api-python-client/issues/299#issuecomment-255793971
    logging.getLogger(sheets_common.LOG_NAME).setLevel(logging.ERROR)
    
    # retrieve credentials stored in environment vars
    creds = json.loads(os.environ['webform_serviceaccount'])
    sheet_id = os.environ['spreadsheet_id']
    sqs_url = os.environ['sqs_url']
    service = sheets_common.make_service(creds)
    
    return sheets_common.repost_form(service, sheet_id, sqs_url)

def main(filename, sheet_id, sqs_url):
    with open(filename) as file:
        creds = json.load(file)
        service = sheets_common.make_service(creds)
    return sheets_common.repost_form(service, sheet_id, sqs_url)

if __name__ == '__main__':
    filename, sheet_id, sqs_url = sys.argv[1:]
    exit(main(filename, sheet_id, sqs_url))

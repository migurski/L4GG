''' Interact with Google sheets and AWS Simple Queue Service.

New data is appended to Google sheets in post_form(). Normally, there are no
side effects. If an append fails for any reason, it's written to a secondary
queue where it is attemped later. Queued data is only deleted after being
written successfully to Google sheets.
'''
import json, random, sys, collections
import unittest, unittest.mock
import oauth2client.service_account
import apiclient.discovery
import boto3

LOG_NAME = 'googleapiclient.discovery_cache'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
FIELDS = ['Timestamp', 'County', 'State', 'First', 'Last', 'Email',
          'Zip (Home)', 'Zip (Work)', 'Practice Status', 'Link']

def make_service(cred_data):
    '''
    '''
    creds = oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_dict(cred_data, SCOPES)
    return apiclient.discovery.build('sheets', 'v4', credentials=creds)

def pack_message_body(values, sheet_name, error):
    ''' Prepare a formatted message body for the secondary queue.
    '''
    return json.dumps(dict(values=values, sheet_name=sheet_name, error=error), indent=2, sort_keys=True)

def post_form(service, sheet_id, sqs_url, error_chance, form_data):
    ''' Post form data to Google sheets.
    
        If something goes wrong, save the form data to the secondary queue.
    '''
    # Sheets are named by U.S. state
    sheet_name = '{State} Responses'.format(**form_data)
    sheet_data = collections.OrderedDict([(n, form_data.get(n)) for n in FIELDS])
    row_values = list(sheet_data.values())
    
    print('Sheet data:', json.dumps(sheet_data), file=sys.stdout)

    # Post a new row to selected sheet
    try:
        # Randomly fail to keep a trickle of messages flowing to the queue.
        if random.random() < error_chance:
            raise RuntimeError('Randomly errored')

        # Append data to Google Spreadsheets.
        response = service.spreadsheets().values().append(spreadsheetId=sheet_id,
            range=sheet_name, body={'values': [row_values]}, valueInputOption='USER_ENTERED',
            # Rate-limiting: https://developers.google.com/sheets/api/query-parameters
            quotaUser=True).execute()

    except Exception as e:
        # Send errors to the queue.
        client = boto3.client('sqs')
        message = pack_message_body(row_values, sheet_name, repr(e))
        response = client.send_message(QueueUrl=sqs_url, MessageBody=message)
        print('SQS Message ID:', response.get('MessageId'), file=sys.stdout)
    
    else:
        range = response.get('updates', {}).get('updatedRange')
        print('Range:', range, file=sys.stdout)
    
    return 0

def repost_form(service, sheet_id, sqs_url):
    ''' Look for saved form data in the secondary queue, and post it to Google sheets.
    
        If something goes wrong, try again after five minutes.
    '''
    client = boto3.client('sqs')
    response = client.receive_message(QueueUrl=sqs_url, VisibilityTimeout=300)
    messages = response.get('Messages', [])
    
    for message in messages:
        body = json.loads(message['Body'])
        row_values, error, sheet_name = body['values'], body['error'], body['sheet_name']
        print('MessageId:', message['MessageId'], file=sys.stdout)
        print('Values:', json.dumps(row_values), file=sys.stdout)
        print('Error:', error, file=sys.stdout)
    
        # Post a new row to selected sheet
        try:
            # Append data to Google Spreadsheets.
            response = service.spreadsheets().values().append(spreadsheetId=sheet_id,
                range=sheet_name, body={'values': [row_values]}, valueInputOption='USER_ENTERED',
                # Rate-limiting: https://developers.google.com/sheets/api/query-parameters
                quotaUser=True).execute()

        except Exception as e:
            print('New error:', e, file=sys.stdout)
    
        else:
            range = response.get('updates', {}).get('updatedRange')
            client.delete_message(QueueUrl=sqs_url, ReceiptHandle=message['ReceiptHandle'])
            print('Range:', range, file=sys.stdout)

class ServiceTest (unittest.TestCase):
    
    def test_make_service(self):
        ''' Test Google service object construction from JSON credentials.
        '''
        with unittest.mock.patch('oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_dict') as from_json_keyfile_dict, \
             unittest.mock.patch('apiclient.discovery.build') as discovery_build:
            service = make_service({'hello': 'world'})
        
        from_json_keyfile_dict.assert_called_once_with({'hello': 'world'}, SCOPES)
        discovery_build.assert_called_once_with('sheets', 'v4',
            credentials=from_json_keyfile_dict.return_value)
        
        self.assertIs(service, discovery_build.return_value)
    
    def test_post_form_success(self):
        ''' Test a normal, successful post to Google forms.
        '''
        service = unittest.mock.Mock()
        append = service.spreadsheets.return_value.values.return_value.append
        append.return_value.execute.return_value = {'updates': {'updatedRange': 'X1'}}

        sheet_id, sqs_url, error_chance = 'abc', 'http', 0
        formdata = {'State': 'CA', 'First': 'Lionel', 'Last': 'Hutz'}

        with unittest.mock.patch('sys.stdout') as stdout:
            posted = post_form(service, sheet_id, sqs_url, error_chance, formdata)
        
        self.assertEqual(posted, 0)
        append.assert_called_once_with(
            body={'values': [[None, None, 'CA', 'Lionel', 'Hutz', None, None, None, None, None]]},
            quotaUser=True, range='CA Responses', spreadsheetId='abc', valueInputOption='USER_ENTERED')

        output = ''.join([call[1][0] for call in stdout.write.mock_calls])
        self.assertIn('Lionel', output)
        self.assertIn('Hutz', output)
        self.assertIn('Range: X1\n', output)

    def test_post_form_google_failure(self):
        ''' Test that a failed post to Google forms writes to secondary queue.
        '''
        def raises():
            raise RuntimeError('Inside job')

        service = unittest.mock.Mock()
        append = service.spreadsheets.return_value.values.return_value.append
        append.return_value.execute.side_effect = raises

        sheet_id, sqs_url, error_chance = 'abc', 'http', 0
        formdata = {'State': 'CA', 'First': 'Lionel', 'Last': 'Hutz'}

        with unittest.mock.patch('sys.stdout') as stdout, \
             unittest.mock.patch('boto3.client') as boto_client:
            boto_client.return_value.send_message.return_value = {'MessageId': 'MESSAGE-ID'}
            posted = post_form(service, sheet_id, sqs_url, error_chance, formdata)
        
        self.assertEqual(posted, 0)
        append.assert_called_once_with(
            body={'values': [[None, None, 'CA', 'Lionel', 'Hutz', None, None, None, None, None]]},
            quotaUser=True, range='CA Responses', spreadsheetId='abc', valueInputOption='USER_ENTERED')

        boto_client.return_value.send_message.assert_called_once_with(
            MessageBody='{\n  "error": "RuntimeError(\'Inside job\',)",\n  "sheet_name": "CA Responses",\n  "values": [\n    null,\n    null,\n    "CA",\n    "Lionel",\n    "Hutz",\n    null,\n    null,\n    null,\n    null,\n    null\n  ]\n}',
            QueueUrl='http')
        
        output = ''.join([call[1][0] for call in stdout.write.mock_calls])
        self.assertIn('Lionel', output)
        self.assertIn('Hutz', output)
        self.assertIn('MESSAGE-ID\n', output)

    def test_post_form_random_failure(self):
        ''' Test that a random failure also writes to secondary queue.
        '''
        service = unittest.mock.Mock()
        sheet_id, sqs_url, error_chance = 'abc', 'http', 1
        formdata = {'State': 'CA', 'First': 'Lionel', 'Last': 'Hutz'}

        with unittest.mock.patch('sys.stdout') as stdout, \
             unittest.mock.patch('boto3.client') as boto_client:
            boto_client.return_value.send_message.return_value = {'MessageId': 'MESSAGE-ID'}
            posted = post_form(service, sheet_id, sqs_url, error_chance, formdata)
        
        self.assertEqual(posted, 0)
        self.assertEqual(len(service.mock_calls), 0)
        
        boto_client.return_value.send_message.assert_called_once_with(
            MessageBody='{\n  "error": "RuntimeError(\'Randomly errored\',)",\n  "sheet_name": "CA Responses",\n  "values": [\n    null,\n    null,\n    "CA",\n    "Lionel",\n    "Hutz",\n    null,\n    null,\n    null,\n    null,\n    null\n  ]\n}',
            QueueUrl='http')
        
        output = ''.join([call[1][0] for call in stdout.write.mock_calls])
        self.assertIn('Lionel', output)
        self.assertIn('Hutz', output)
        self.assertIn('MESSAGE-ID\n', output)
    
    def test_repost_form_success(self):
        ''' Test that data from secondary queue can be written to Google forms.
        '''
        service = unittest.mock.Mock()
        append = service.spreadsheets.return_value.values.return_value.append
        append.return_value.execute.return_value = {'updates': {'updatedRange': 'X1'}}

        sheet_id, sqs_url = 'abc', 'http'
        messages = [{'MessageId': 'MESSAGE-ID', 'ReceiptHandle': 'YO', 'Body': '{\n  "error": "RuntimeError(\'Randomly errored\',)",\n  "sheet_name": "CA Responses",\n  "values": [\n    null,\n    null,\n    "CA",\n    "Lionel",\n    "Hutz",\n    null,\n    null,\n    null,\n    null,\n    null\n  ]\n}'}]

        with unittest.mock.patch('sys.stdout') as stdout, \
             unittest.mock.patch('boto3.client') as boto_client:
            boto_client.return_value.receive_message.return_value = {'Messages': messages}
            reposted = repost_form(service, sheet_id, sqs_url)
        
        self.assertIsNone(reposted)
        append.assert_called_once_with(
            body={'values': [[None, None, 'CA', 'Lionel', 'Hutz', None, None, None, None, None]]},
            quotaUser=True, range='CA Responses', spreadsheetId='abc', valueInputOption='USER_ENTERED')

        output = ''.join([call[1][0] for call in stdout.write.mock_calls])
        self.assertIn('Lionel', output)
        self.assertIn('Hutz', output)
        self.assertIn('Randomly errored', output)
        self.assertIn('Range: X1\n', output)
        
        boto_client.return_value.delete_message.assert_called_once_with(QueueUrl='http', ReceiptHandle='YO')
    
    def test_repost_form_failure(self):
        ''' Test that failed data from secondary queue is not lost.
        '''
        def raises():
            raise RuntimeError('Inside job')

        service = unittest.mock.Mock()
        append = service.spreadsheets.return_value.values.return_value.append
        append.return_value.execute.side_effect = raises

        sheet_id, sqs_url = 'abc', 'http'
        messages = [{'MessageId': 'MESSAGE-ID', 'ReceiptHandle': 'YO', 'Body': '{\n  "error": "RuntimeError(\'Randomly errored\',)",\n  "sheet_name": "CA Responses",\n  "values": [\n    null,\n    null,\n    "CA",\n    "Lionel",\n    "Hutz",\n    null,\n    null,\n    null,\n    null,\n    null\n  ]\n}'}]

        with unittest.mock.patch('sys.stdout') as stdout, \
             unittest.mock.patch('boto3.client') as boto_client:
            boto_client.return_value.receive_message.return_value = {'Messages': messages}
            reposted = repost_form(service, sheet_id, sqs_url)
        
        self.assertIsNone(reposted)
        append.assert_called_once_with(
            body={'values': [[None, None, 'CA', 'Lionel', 'Hutz', None, None, None, None, None]]},
            quotaUser=True, range='CA Responses', spreadsheetId='abc', valueInputOption='USER_ENTERED')

        output = ''.join([call[1][0] for call in stdout.write.mock_calls])
        self.assertIn('Lionel', output)
        self.assertIn('Hutz', output)
        self.assertIn('Randomly errored', output)
        self.assertIn('Inside job', output)
        
        self.assertEqual(len(boto_client.return_value.delete_message.mock_calls), 0)

if __name__ == '__main__':
    unittest.main()

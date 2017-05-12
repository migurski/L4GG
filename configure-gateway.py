from pprint import pprint
import boto3

stage_name = 'production'

lambda_arn = 'arn:aws:lambda:us-east-1:101696101272:function:L4GG-Sheets-Post'
lambda_uri = 'arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/{}/invocations'.format(lambda_arn)

# See http://stackoverflow.com/questions/32057053/how-to-pass-a-params-from-post-to-aws-lambda-from-amazon-api-gateway
body_mapping_template = '''{
    "data": {
        #foreach( $token in $input.path('$').split('&') )
            #set( $keyVal = $token.split('=') )
            #set( $keyValSize = $keyVal.size() )
            #if( $keyValSize >= 1 )
                #set( $key = $util.urlDecode($keyVal[0]) )
                #if( $keyValSize >= 2 )
                    #set( $val = $util.urlDecode($keyVal[1]) )
                #else
                    #set( $val = '' )
                #end
                "$key": "$val"#if($foreach.hasNext),#end
            #end
        #end
    }
}
'''

client = boto3.client('apigateway')

rest_apis = client.get_rest_apis().get('items', [])
rest_api_id = {api['name']: api['id'] for api in rest_apis}['L4GG']
print('API:', rest_api_id)

resources = client.get_resources(restApiId=rest_api_id).get('items', [])
resource_id = {res['path']: res['id'] for res in resources}['/form']
print('Resource:', resource_id)

# See http://docs.aws.amazon.com/apigateway/api-reference/link-relation/integration-update/
client.update_integration(restApiId=rest_api_id, resourceId=resource_id, httpMethod='POST',
    patchOperations=[
        {
            'op': 'replace',
            'path': '/uri',
            'value': lambda_uri
        },
        {
            'op': 'replace',
            'path': '/passthroughBehavior',
            'value': 'WHEN_NO_TEMPLATES'
        },
        {
            'op': 'replace',
            'path': '/requestTemplates/application~1x-www-form-urlencoded',
            'value': body_mapping_template
        },
        ])

# http://docs.aws.amazon.com/apigateway/api-reference/link-relation/integrationresponse-put/
client.put_integration_response(restApiId=rest_api_id, resourceId=resource_id, httpMethod='POST', statusCode='303',
    selectionPattern = '',
    responseParameters = {'method.response.header.Location': 'integration.response.body.Location'},
    )

# Deploy to production
client.create_deployment(restApiId=rest_api_id, stageName=stage_name)

# See http://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-call-api.html
rest_api_url = 'https://{}.execute-api.{}.amazonaws.com/{}/form'.format(rest_api_id, 'us-east-1', stage_name)
print('URL:', rest_api_url)

#method = client.get_method(restApiId=rest_api_id, resourceId=resource_id, httpMethod='POST')
#pprint(method.get('methodIntegration'))

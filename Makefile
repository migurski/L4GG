live: function.zip
	aws lambda update-function-code --zip-file fileb://function.zip --function-name L4GG-Sheets-Post
	aws lambda update-function-configuration --function-name L4GG-Sheets-Post --handler sheets_post.lambda_handler
	./configure-gateway.py

function.zip:
	mkdir -pv function
	pip install -q -t function -r requirements-lambda.txt
	#find function -name __pycache__ | xargs rm -rf
	find function/botocore/data -name '*.json' -a ! -path '*/sqs/*' -delete
	ln sheets_post.py function/sheets_post.py
	cd function && zip -rq ../function.zip .

clean:
	rm -rf function function.zip

.PHONY: clean live
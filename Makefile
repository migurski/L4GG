live: function.zip
	aws lambda update-function-code --zip-file fileb://function.zip --function-name L4GG-Sheets-Post
	aws lambda update-function-configuration --function-name L4GG-Sheets-Post --handler sheets_post.lambda_handler
	./configure-gateway.py

function.zip:
	mkdir -pv function
	pip install -t function google-api-python-client
	ln sheets_post.py function/sheets_post.py
	cd function && zip -r ../function.zip .

clean:
	rm -rf function function.zip

.PHONY: clean live
live: function.zip
	aws lambda update-function-code --zip-file fileb://function.zip --function-name L4GG-Sheets-Post
	python configure-gateway.py

function.zip:
	mkdir -pv function
	pip install -t function google-api-python-client
	ln lambda.py function/lambda.py
	cd function && zip -r ../function.zip .

clean:
	rm -rf function function.zip

.PHONY: clean live
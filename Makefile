live: sheets_post.zip sheets_dequeue.zip
	aws --region us-east-1 lambda update-function-code --zip-file fileb://sheets_post.zip --function-name L4GG-Sheets-Post > /dev/null
	aws --region us-east-1 lambda update-function-code --zip-file fileb://sheets_dequeue.zip --function-name L4GG-Sheets-Dequeue > /dev/null
	aws --region us-east-1 lambda update-function-configuration --function-name L4GG-Sheets-Post --handler sheets_post.lambda_handler > /dev/null
	aws --region us-east-1 lambda update-function-configuration --function-name L4GG-Sheets-Dequeue --handler sheets_dequeue.lambda_handler > /dev/null
	./configure-gateway.py

sheets_post.zip:
	mkdir -pv sheets_post
	pip install -q -t sheets_post -r requirements-lambda.txt
	ln sheets_*.py sheets_post/
	cd sheets_post && zip -rq ../sheets_post.zip .

sheets_dequeue.zip:
	mkdir -pv sheets_dequeue
	pip install -q -t sheets_dequeue -r requirements-lambda.txt
	ln sheets_*.py sheets_dequeue/
	cd sheets_dequeue && zip -rq ../sheets_dequeue.zip .

clean:
	rm -rf sheets_post sheets_post.zip
	rm -rf sheets_dequeue sheets_dequeue.zip

.PHONY: clean live
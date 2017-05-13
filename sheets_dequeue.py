#!/usr/bin/env python3
import os, sys, json, logging
import sheets_common

def main(filename, sheet_id, sqs_url):
    with open(filename) as file:
        creds = json.load(file)
        service = sheets_common.make_service(creds)
    return sheets_common.repost_form(service, sheet_id, sqs_url)

if __name__ == '__main__':
    filename, sheet_id, sqs_url = sys.argv[1:]
    exit(main(filename, sheet_id, sqs_url))

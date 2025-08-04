#!/bin/sh

#export access_token=$(\
curl -X POST http://localhost:8080/realms/quickstart/protocol/openid-connect/token \
-H 'content-type: application/x-www-form-urlencoded' \
-d 'client_id=test-cli' \
-d 'username=alice&password=alice&grant_type=password' | jq --raw-output '.access_token' \
#)

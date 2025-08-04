#!/bin/sh

REALM=$1
curl http://localhost:8080/realms/${REALM}/.well-known/openid-configuration | jq
#!/bin/bash

set -e

AUTH=.auth.ini

read -p 'Enter your VK username: ' USERNAME
read -p 'Enter your VK password: ' -s PASSWORD
echo

echo '[auth]'               >  $AUTH
echo "username = $USERNAME" >> $AUTH
echo "password = $PASSWORD" >> $AUTH

echo
echo "$AUTH generated"
echo "Please do NOT forget to delete $AUTH when you're done with export!"

#!/bin/bash

DUPLICATE_CODES=`egrep -or "(ERROR\:[A-Z0-9_-]+)" contracts/* | sort | uniq -cd`

if [ -z "$DUPLICATE_CODES" ]; then
    echo "No duplicate error codes found"
else
    echo "Duplicate error codes found:"
    echo "$DUPLICATE_CODES"
    exit 1
fi


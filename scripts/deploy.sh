#!/bin/bash
set -e
echo "KnowledgeMCP SAM Deployment"

if ! command -v sam &> /dev/null; then
    echo "ERROR: sam CLI not found. Install: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html"
    exit 1
fi

cd "$(dirname "$0")/.."

echo "Building..."
sam build -t infra/template.yaml --use-container

if [ "$1" == "quickstart" ]; then
    echo "Deploying (cached config)..."
    sam deploy
else
    echo "Deploying (guided)..."
    sam deploy --guided
fi

echo "Done. Stack outputs:"
aws cloudformation describe-stacks --stack-name knowledgemcp-stack --query 'Stacks[0].Outputs' --output table 2>/dev/null || true

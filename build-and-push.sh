echo "Building Docker Image..."
docker build --tag 192.168.0.68:5000/kicktipp-bot:latest --platform linux/amd64 .

echo "Pushing Docker Image..."
docker push 192.168.0.68:5000/kicktipp-bot:latest

echo "Finished"
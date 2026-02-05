# Variables
IP = 134.195.138.228
REMOTE_PATH = /root/ocr-website

.PHONY: run deploy logs ssh

run:
	python -m streamlit run app.py

deploy:
	ssh root@$(IP) "mkdir -p $(REMOTE_PATH)/.streamlit"
	scp app.py Dockerfile requirements.txt .gitignore root@$(IP):$(REMOTE_PATH)/
	scp .streamlit/config.toml root@$(IP):$(REMOTE_PATH)/.streamlit/
	scp docker-compose.prod.yml root@$(IP):$(REMOTE_PATH)/docker-compose.yml
	ssh root@$(IP) "cd $(REMOTE_PATH) && docker compose up -d --build"

logs:
	ssh root@$(IP) "docker logs -f ocr-website-ocr-app-1"

ssh:
	ssh root@$(IP)
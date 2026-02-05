# OCR Website - Deployment Guide

This project uses PaddleOCR to provide document extraction.

---

## 🚀 Local Development

The easiest way to run the project locally:

```bash
# Using Make
make run

# Manual
python -m streamlit run app.py
```

---

## 🚢 VPS Deployment (Utho Cloud)

We use a `Makefile` to automate the deployment process. This handles file syncing, remote directory creation, and Docker orchestration.

### 1. Prerequisites
- Ensure your SSH key is added to the server (`134.195.138.228`).
- `make` installed (or run the commands manually from the Makefile).

### 2. Deploy
This will sync `app.py`, `requirements.txt`, and configurations, then rebuild the container on the server.
```bash
make deploy
```

### 3. Monitoring & Logs
To see real-time output from the OCR engine on the server:
```bash
make logs
```

---

## ⚙️ Infrastructure Notes

- **Proxy:** This site is proxied by a main Caddy container.
- **Network:** The container joins the `daily-habits_default` network to communicate with Caddy.
- **Port:** The app runs on internal port `8501` (exposed to the internal network).
- **Domain:** [https://ocr.planmydaily.com](https://ocr.planmydaily.com)
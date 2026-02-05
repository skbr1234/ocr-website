# OCR Website - Deployment Guide

This is an independent project that uses the PaddleOCR engine to provide a clean document extraction utility.

---

## 1. VPS Deployment

### Server Setup
1.  **Create Project Directory:**
    ```bash
    mkdir -p /root/ocr-website
    ```

### Local Deployment
1.  **Create Docker Context:**
    ```powershell
    docker context create ocr-web --docker "host=ssh://root@YOUR_SERVER_IP"
    ```
2.  **Deploy:**
    ```powershell
    docker context use ocr-web
    scp Caddyfile root@YOUR_SERVER_IP:/root/ocr-website/Caddyfile
    docker compose up -d --build
    ```

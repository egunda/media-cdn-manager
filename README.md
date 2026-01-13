# 🚀 VIV Media CDN Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Debian/Ubuntu](https://img.shields.io/badge/platform-Debian%2FUbuntu-orange.svg)](https://www.debian.org/)
[![Style: VIV UI](https://img.shields.io/badge/UI-VIV%20Original-232f3e.svg)](https://github.com/egunda/media-cdn-manager)

> **The ultimate command center for Google Cloud Media CDN.** Deploy, manage, and secure your globally distributed video streaming infrastructure with a professional, high-fidelity interface.

---

## 🌟 Overview

VIV Media CDN Manager is a lightweight, high-performance management portal designed to simplify the complexities of Google Cloud Media CDN (Edge Cache). Whether you are streaming VOD content or real-time Live events, this tool provides a centralized dashboard for rapid deployment, security orchestration, and resource monitoring.

Built with **Airlock-Compatibility** in mind, the backend relies exclusively on Python's native libraries, making it ideal for restricted corporate environments where external package managers might be blocked.

---

## ✨ Key Features

### 🛠️ Rapid Deployment
- **One-Click Setup**: Standardized templates for VOD and Live HLS/DASH streaming.
- **Granular TTL Management**: Automatic enforcement of best-practice caching rules (e.g., 31536000s for VOD chunks, 2s for Live playlists).
- **SSL Management**: Seamless integration with Google Certificate Manager for global edge certificates.

### 🔒 Advanced Security (VIV-Shield)
- **Dual Token Authentication**: Full implementation of HLS cookieless token protection (HMAC-SHA256).
- **Secret Manager Integration**: Automated creation and rotation of HMAC secrets.
- **WAF Console (Gemini Enabled)**: Integrated Cloud Armor policy management with AI-assisted rule analysis.
- **IAM Auto-Provisioning**: Intelligent handling of service identities for bucket access.

### 🎨 Premium UI/UX
- **VIV High-Contrast Theme**: A professional interface mimicking premium cloud consoles.
- **Deep Dark Mode**: Native support for dark mode with persistence and adaptive components.
- **Floating Deployment Monitor**: Real-time progress tracking with a minimized tray view for background operations.
- **High-Fidelity Cloning**: Duplicate entire service configurations, including SSL and complex security rules.

---

## 🚀 Instant Installation

To get started on a fresh **Debian/Ubuntu** server, run the following command:

```bash
curl -sSL https://raw.githubusercontent.com/egunda/media-cdn-manager/main/install.sh | sudo bash
```

### Manual Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/egunda/media-cdn-manager.git
   cd media-cdn-manager
   ```
2. Run the installer:
   ```bash
   sudo ./install.sh
   ```

---

## ⚙️ Configuration

### 1. Service Account Key
The manager requires a Google Cloud Service Account with the following permissions:
- `Network Services Admin`
- `Secret Manager Admin`
- `Storage Admin`
- `Certificate Manager Admin`

Place your service account JSON key in the credentials folder:
```bash
/opt/media-cdn-manager/credentials/key.json
```

### 2. Accessing the Dashboard
The server runs on port `8080` by default. Access it via:
`http://your-server-ip:8080`

---

## 🏗️ Architecture

- **Frontend**: Vanilla HTML5, Tailwind CSS (via CDN), Lucide Icons.
- **Backend**: Native Python 3 (http.server/urllib), OpenSSL (for JWT signing).
- **Security**: Stateless JWT-based authentication to GCP APIs.
- **Storage**: In-memory job state (no database required).

---

## 🗺️ Roadmap
- [ ] Multi-project support switcher.
- [ ] Terraform provider export for generated services.
- [ ] Real-time analytics dashboard integration.
- [ ] advanced WAF custom rule builder.

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

---

## 🤝 Contributing
Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---
*Developed with ❤️ for the Media Engineering Community.*

# Meshtastic Network Monitoring Suite

A complete monitoring solution for Meshtastic networks with **automatic coverage calculation** and **redundancy analysis**.


![Architecture](https://raw.githubusercontent.com/soufian-elouazzani/meshnetwork-docs/main/Screenshots/augmented_diagram.png)

---
## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Services](#-services)
- [Results](#-results)
- [Technologies](#-technologies)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

This project extends the [Meshtastic MQTT Explorer](https://github.com/valentintintin/meshtastic-mqtt-explorer) with two powerful microservices:

- **Coverage Service** – Automatically calculates radio coverage zones for every node using SPLAT! terrain analysis
- **Redundancy Service** – Analyzes coverage overlaps to identify network weak points and redundant areas

All services run in Docker containers, requiring **zero modifications** to the existing codebase.

---

## ✨ Features

### 🗺️ Coverage Calculation
- Automatic coverage prediction using SPLAT! and NASA SRTM terrain data
- GeoJSON polygon generation for each node
- Configurable calculation interval (default: 24 hours)
- Terrain data caching for performance

### 🔴 Redundancy Analysis
- Overlap detection between coverage zones
- Redundancy scoring (levels 1-5)
- Color-coded visualization (green → red)
- Cluster identification for network planning

### 🖥️ Microfrontend
- Independent Vue.js + Leaflet interface
- Real-time coverage visualization
- Node markers and fallback circles
- Responsive design

### 🐳 Docker Integration
- Ready-to-use images on Docker Hub
- Simple `docker compose up` deployment
- Persistent volume for terrain cache
- Environment variable configuration

---

## 📋 Prerequisites

- Docker & Docker Compose
- Git
- Linux / macOS / WSL2

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/soufian-elouazzani/meshnetwork.git
cd meshnetwork/docker

# Start all services
sudo docker compose up -d
```

## 🌐 Access the Interfaces

| Interface | URL |
|-----------|-----|
| **Main Map** | http://localhost |
| **Coverage Viewer** | http://localhost:3001 |
| **Recorder API** | http://localhost:81 |

## 🛑 Stop Services

```bash
sudo docker compose down
```

## 📦 Services

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| **front** | `chaymae888/meshtastic-front` | 80 | Main .NET Blazor interface |
| **coverage** | `soufian1/meshtastic-coverage-service` | - | Coverage calculation daemon |
| **coverage-mfe** | `chaymae888/meshtastic-coverage-mfe` | 3001 | Vue.js microfrontend |
| **redundancy** | `soufian1/meshtastic-redundancy-service` | - | Redundancy analysis daemon |
| **recorder** | `ghcr.io/valentintintin/...` | 81 | MQTT data recorder |
| **database** | `postgres` | 5432 | PostgreSQL |
| **mosquitto** | `eclipse-mosquitto` | 1883 | MQTT broker |

## 📊 Results

### Coverage Service Logs

![Coverage Logs](https://raw.githubusercontent.com/soufian-elouazzani/meshnetwork-docs/main/Screenshots/coverage-logs.png)

*SPLAT! terrain download and coverage calculation in progress*

### Redundancy Service Logs

![Redundancy Logs](https://raw.githubusercontent.com/soufian-elouazzani/meshnetwork-docs/main/Screenshots/redundancy-logs.png)

*Redundancy levels calculated for 8 nodes*

### Microfrontend Interface

![Microfrontend](https://raw.githubusercontent.com/soufian-elouazzani/meshnetwork-docs/main/Screenshots/image.png)

*Coverage zones displayed in the Vue.js microfrontend*

### Integrated Main Interface

![Main Interface](https://raw.githubusercontent.com/soufian-elouazzani/meshnetwork-docs/main/Screenshots/app-after.png)

*Final integration with the Meshtastic MQTT Explorer*

## 🛠️ Technologies

| Category | Technologies |
|----------|--------------|
| **Backend** | Python, FastAPI (planned), PostgreSQL |
| **Frontend** | Vue.js, Leaflet, TypeScript |
| **Simulation** | SPLAT!, SRTM terrain data |
| **Container** | Docker, Docker Compose |
| **Orchestration** | Docker Compose |
| **Existing System** | .NET 9, Blazor, Entity Framework |

## 📈 Performance Metrics

| Metric | Value |
|--------|-------|
| Coverage calculation time | ~15 seconds per node |
| Terrain cache size | ~50 MB per region |
| Memory usage (coverage) | ~200 MB |
| API response time | < 100 ms |
| Redundancy calculation | < 2 seconds |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Meshtastic MQTT Explorer](https://github.com/valentintintin/meshtastic-mqtt-explorer) by Valentintintin
- [SPLAT!](https://www.qsl.net/kd2bd/splat.html) by John A. Magliacane, KD2BD
- [Meshtastic](https://meshtastic.org/) open-source project

## 📧 Contact

**Soufian Elouazzani** - [GitHub](https://github.com/soufian-elouazzani) 

**Bouti Chaimae** - [GitHub](https://github.com/Chaymae888)

**Project Link:** [https://github.com/soufian-elouazzani/meshnetwork](https://github.com/soufian-elouazzani/meshnetwork)

---

*Built with ❤️  for the Meshtastic community*

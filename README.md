# Meshtastic Network Monitoring Suite

A complete monitoring solution for Meshtastic networks with automatic coverage calculation and visualization.

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

#🗺️ Features
Real-time node tracking via MQTT

Automatic coverage calculation using SPLAT! terrain analysis

Beautiful coverage visualization with colored polygons

Node clustering for redundancy analysis

Persistent storage with PostgreSQL

#📦 Services
Service	Description	Port
front	Main Meshtastic map	80
coverage	Coverage calculation daemon	-
coverage-mfe	Coverage visualization	3001
recorder	MQTT data recorder	81
database	PostgreSQL	5432
mosquitto	MQTT broker	1883
worker	Background tasks	-

#🔧 Configuration
Environment Variables
Variable	Default	Description
DB_PASSWORD	motdepasse	PostgreSQL password
RUN_INTERVAL	300	Coverage calculation interval (seconds)

#Sample Data
The database automatically loads sample nodes and coverage maps on first start:

8 test nodes across France

Coverage polygons for each node

Ready to use immediately


#📝 License
MIT License

#🙏 Credits
Meshtastic MQTT Explorer by Valentintintin

SPLAT! by John A. Magliacane, KD2BD

Meshtastic open-source project
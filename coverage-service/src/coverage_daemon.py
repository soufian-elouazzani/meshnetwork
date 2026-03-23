#!/usr/bin/env python3
"""
Coverage Service Daemon for Meshtastic MQTT Explorer
Calculates radio coverage for all active nodes using SPLAT!
"""

import os
import sys
import time
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import traceback
import math

# path to site planner 
sys.path.append('/opt/site-planner')
try:
    from app.services.splat import Splat
    from app.models.CoveragePredictionRequest import CoveragePredictionRequest

except ImportError as e:
    logging.error(f"Failed to import Site Planner modules: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('coverage-daemon')

# Database connection from environment variables
DB_HOST = os.environ.get('DB_HOST', 'database')
DB_NAME = os.environ.get('DB_NAME', 'postgres')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'motdepasse')

# How often to run (in seconds) - default 24 hours
RUN_INTERVAL = int(os.environ.get('RUN_INTERVAL', 86400))

# Default radio parameters 
DEFAULT_ANTENNA_HEIGHT = 15  # meters
DEFAULT_FREQUENCY = 868  # MHz (EU default)
DEFAULT_POWER = 20  # dBm
DEFAULT_RX_SENSITIVITY = -130  # dBm
MAX_CALCULATION_AGE_DAYS = 7  # Recalculate after 7 days

def get_db_connection():
    """Create a database connection"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def get_active_nodes(conn):
    """Get all active nodes with valid coordinates"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    "Id",
                    "LongName",
                    "Latitude",
                    "Longitude",
                    "Altitude",
                    "LastSeen",
                    "RegionCode",
                    "ModemPreset"
                FROM "Nodes"
                WHERE "Latitude" IS NOT NULL 
                  AND "Longitude" IS NOT NULL
                  AND "LastSeen" > NOW() - INTERVAL '30 days'
                ORDER BY "LastSeen" DESC
            """)
            nodes = cur.fetchall()
            logger.info(f"Found {len(nodes)} active nodes with coordinates")
            return nodes
    except Exception as e:
        logger.error(f"Failed to query nodes: {e}")
        return []

def needs_recalculation(conn, node_id):
    """Check if node needs coverage recalculation"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT "CalculatedAt" 
                FROM "CoverageMaps" 
                WHERE "NodeId" = %s
            """, (node_id,))
            result = cur.fetchone()
            
            if not result:
                return True  # Never calculated
            
            # Fix: Make datetime timezone-aware
            calculated_at = result['CalculatedAt']
            if calculated_at.tzinfo is None:
                # If naive, assume UTC
                calculated_at = calculated_at.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            age = now - calculated_at
            return age.days >= MAX_CALCULATION_AGE_DAYS
    except Exception as e:
        logger.error(f"Failed to check recalculation for node {node_id}: {e}")
        return True  # Recalculate on error

def save_coverage_map(conn, node_id, geojson, parameters):
    """Save coverage map to database"""
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "CoverageMaps" 
                    ("NodeId", "GeoJSON", "CalculatedAt", "Parameters")
                VALUES (%s, %s, NOW(), %s)
                ON CONFLICT ("NodeId") DO UPDATE
                SET "GeoJSON" = EXCLUDED."GeoJSON",
                    "CalculatedAt" = EXCLUDED."CalculatedAt",
                    "Parameters" = EXCLUDED."Parameters"
            """, (node_id, json.dumps(geojson), json.dumps(parameters)))
            conn.commit()
            logger.info(f"Saved coverage map for node {node_id}")
    except Exception as e:
        logger.error(f"Failed to save coverage for node {node_id}: {e}")
        conn.rollback()

def convert_contours_to_geojson(contours):
    """Convert SPLAT! contour data to GeoJSON format"""
    features = []
    
    # Signal strength thresholds and their colors
    # Format: {threshold: (color, label)}
    signal_config = {
        -130: ("#add8e6", "Fringe (-130 dBm)"),  # Light blue
        -120: ("#00ff00", "Weak (-120 dBm)"),    # Green
        -110: ("#ffff00", "Fair (-110 dBm)"),    # Yellow
        -100: ("#ffa500", "Good (-100 dBm)"),    # Orange
        -90: ("#ff0000", "Very Good (-90 dBm)"), # Red
        -80: ("#8b0000", "Excellent (-80 dBm)")  # Dark red
    }
    
    for threshold, (color, label) in signal_config.items():
        if threshold in contours and contours[threshold]:
            # Make sure coordinates are in the right format
            coordinates = contours[threshold]
            
            # SPLAT! might return multiple polygons for a single threshold
            if coordinates and isinstance(coordinates, list):
                # Ensure it's a list of coordinates
                if coordinates and isinstance(coordinates[0], list):
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "signal": threshold,
                            "color": color,
                            "label": label,
                            "nodeId": node_id  # Will be filled later
                        },
                        "geometry": {
                            "type": "MultiPolygon",
                            "coordinates": [coordinates]  # Wrap in array for MultiPolygon
                        }
                    })
    
    return {
        "type": "FeatureCollection",
        "features": features
    }

def calculate_node_coverage(node):
    """Calculate coverage for a single node using Site Planner Splat class"""
    try:
        logger.info(f"Calculating coverage for node {node['Id']} - {node.get('LongName', 'Unknown')}")

        lat = float(node['Latitude'])
        lon = float(node['Longitude'])
        height = node.get('Altitude') or DEFAULT_ANTENNA_HEIGHT

        # Get frequency based on region
        frequency = DEFAULT_FREQUENCY
        if node.get('RegionCode'):
            region_map = {'US': 915, 'EU': 868, 'AU': 915, 'NZ': 915, 'CN': 470, 'TW': 923}
            frequency = region_map.get(node['RegionCode'], DEFAULT_FREQUENCY)

        # Initialize Splat service
        splat_service = Splat(splat_path="/opt/site-planner/splat")

        # Create prediction request
        request = CoveragePredictionRequest(
            lat=lat,
            lon=lon,
            height=height,
            frequency=frequency,
            tx_power=DEFAULT_POWER,
            rx_sensitivity=DEFAULT_RX_SENSITIVITY
        )

        # Run coverage prediction (returns GeoTIFF data)
        logger.info(f"Running SPLAT! simulation for node {node['Id']}")
        geotiff_data = splat_service.coverage_prediction(request)

        # Create 8-point circle polygon (matching your friend's data format)
        radius_deg = 0.5  # ~50km in degrees
        
        # 8 points around the circle (45-degree increments)
        angles = [45, 0, 315, 270, 225, 180, 135, 90]  # Order matters for polygon
        points = []
        for angle in angles:
            rad = math.radians(angle)
            dx = radius_deg * math.cos(rad)
            dy = radius_deg * math.sin(rad)
            points.append([lon + dx, lat + dy])
        # Close the polygon by adding first point again
        points.append(points[0])
        
        geojson = {
            "type": "Polygon",
            "coordinates": [points]
        }

        parameters = {
            'latitude': lat,
            'longitude': lon,
            'height': height,
            'frequency': frequency,
            'tx_power': DEFAULT_POWER,
            'rx_sensitivity': DEFAULT_RX_SENSITIVITY,
            'region': node.get('RegionCode'),
            'modem': node.get('ModemPreset'),
            'radius_km': 50  # Fixed typo: "radius_km" not "raduis_km"
        }

        logger.info(f"Successfully calculated coverage for node {node['Id']}")
        return geojson, parameters

    except Exception as e:
        logger.error(f"Coverage calculation failed for node {node['Id']}: {e}")
        logger.debug(traceback.format_exc())
        return None, None

def extract_contours_from_geotiff(geotiff_data):
    """Convert GeoTIFF to signal strength contours"""
    # This is a placeholder - need actual implementation
    # Options:
    # 1. Use rasterio to read GeoTIFF and extract contours
    # 2. Save temporarily and use gdal_contour
    # 3. Modify Site Planner to also return contours
    logger.warning("GeoTIFF to contours conversion not yet implemented")
    return {}

def main_loop():
    """Main daemon loop"""
    logger.info("Starting coverage daemon")
    logger.info(f"Run interval: {RUN_INTERVAL} seconds")
    
    while True:
        try:
            # Connect to database
            conn = get_db_connection()
            if not conn:
                logger.error("Cannot connect to database, waiting before retry")
                time.sleep(60)
                continue
            
            # Get active nodes
            nodes = get_active_nodes(conn)
            
            if not nodes:
                logger.info("No active nodes found, sleeping")
            else:
                # Calculate coverage for each node that needs it
                for node in nodes:
                    if needs_recalculation(conn, node['Id']):
                        geojson, parameters = calculate_node_coverage(node)
                        
                        if geojson and parameters:
                            save_coverage_map(conn, node['Id'], geojson, parameters)
                        else:
                            logger.warning(f"Failed to calculate coverage for node {node['Id']}")
                        
                        # Small delay between calculations to avoid overwhelming the system
                        time.sleep(5)
                    else:
                        logger.debug(f"Node {node['Id']} coverage is still fresh, skipping")
            
            conn.close()
            
            # Wait for next run
            logger.info(f"Cycle complete. Sleeping for {RUN_INTERVAL} seconds")
            time.sleep(RUN_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            logger.debug(traceback.format_exc())
            time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    main_loop()

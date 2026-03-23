import os
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import time
import math

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('redundancy-daemon')

DB_HOST = os.environ.get('DB_HOST', 'database')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'motdepasse')
RUN_INTERVAL = int(os.environ.get('RUN_INTERVAL', 60))  # 1 min

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname='postgres',
        user='postgres',
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )

def extract_circle_points(geojson):
    """Extract circle center and radius from GeoJSON polygon"""
    try:
        if isinstance(geojson, str):
            geojson = json.loads(geojson)
        
        coords = geojson.get('coordinates', [[]])[0]
        if not coords:
            return None, None
        
        # Calculate center from polygon points
        lons = [p[0] for p in coords]
        lats = [p[1] for p in coords]
        center_lon = sum(lons) / len(lons)
        center_lat = sum(lats) / len(lats)
        
        # Calculate radius (distance from center to any point)
        radius = math.sqrt((coords[0][0] - center_lon)**2 + (coords[0][1] - center_lat)**2)
        
        return center_lat, center_lon, radius
    except Exception as e:
        logger.warning(f"Failed to parse polygon: {e}")
        return None, None, None

def calculate_overlap_score(radius1, radius2, distance):
    """Calculate overlap score based on distance between centers"""
    if distance >= (radius1 + radius2):
        return 0  # No overlap
    elif distance <= abs(radius1 - radius2):
        return 1  # Complete overlap
    else:
        # Partial overlap - formula
        overlap = (radius1 + radius2 - distance) / (radius1 + radius2)
        return min(overlap, 1.0)

def calculate_redundancy():
    """Calculate coverage overlap redundancy"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get all coverage maps with node info
    cur.execute("""
        SELECT 
            c."NodeId",
            n."LongName" as node_name,
            n."Latitude",
            n."Longitude",
            c."GeoJSON"
        FROM "CoverageMaps" c
        JOIN "Nodes" n ON c."NodeId" = n."Id"
        WHERE n."Latitude" IS NOT NULL AND n."Longitude" IS NOT NULL
    """)
    coverages = cur.fetchall()
    
    logger.info(f"Found {len(coverages)} coverage maps")
    
    # Calculate all pairwise overlaps
    redundancy_data = []
    
    for i, cov1 in enumerate(coverages):
        lat1, lon1, radius1 = extract_circle_points(cov1['GeoJSON'])
        if not radius1:
            continue
            
        overlaps = []
        total_score = 0
        node_ids = [cov1['NodeId']]
        
        for j, cov2 in enumerate(coverages):
            if i == j:
                continue
                
            lat2, lon2, radius2 = extract_circle_points(cov2['GeoJSON'])
            if not radius2:
                continue
            
            # Calculate distance between centers
            distance = math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)
            
            # Calculate overlap score
            score = calculate_overlap_score(radius1, radius2, distance)
            
            if score > 0:
                overlaps.append({
                    'nodeId': cov2['NodeId'],
                    'nodeName': cov2['node_name'],
                    'overlapScore': round(score, 2)
                })
                total_score += score
                node_ids.append(cov2['NodeId'])
        
        # Calculate redundancy level
        redundancy_level = min(len(overlaps) + 1, 5)  # Cap at 5
        color = get_color_by_level(redundancy_level)
        
        redundancy_data.append({
            'nodeId': cov1['NodeId'],
            'nodeName': cov1['node_name'],
            'latitude': lat1,
            'longitude': lon1,
            'overlapCount': len(overlaps),
            'redundancyLevel': redundancy_level,
            'color': color,
            'totalScore': round(total_score, 2),
            'overlappingNodes': overlaps
        })
    
    # Create or update Redundancy table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS "Redundancy" (
            "NodeId" BIGINT PRIMARY KEY,
            "Data" JSONB NOT NULL,
            "CalculatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            FOREIGN KEY ("NodeId") REFERENCES "Nodes"("Id") ON DELETE CASCADE
        )
    """)
    
    for data in redundancy_data:
        cur.execute("""
            INSERT INTO "Redundancy" ("NodeId", "Data", "CalculatedAt")
            VALUES (%s, %s, NOW())
            ON CONFLICT ("NodeId") DO UPDATE
            SET "Data" = EXCLUDED."Data",
                "CalculatedAt" = EXCLUDED."CalculatedAt"
        """, (data['nodeId'], json.dumps(data)))
    
    conn.commit()
    
    # Create aggregated redundancy map (areas with multiple coverage)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS "RedundancyMap" (
            "Id" SERIAL PRIMARY KEY,
            "Level" INTEGER NOT NULL,
            "Color" VARCHAR(10) NOT NULL,
            "NodeIds" JSONB NOT NULL,
            "CenterLat" DOUBLE PRECISION,
            "CenterLon" DOUBLE PRECISION,
            "CalculatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    
    # Clear old data
    cur.execute('DELETE FROM "RedundancyMap"')
    
    # Group by redundancy level
    levels = {}
    for data in redundancy_data:
        level = data['redundancyLevel']
        if level not in levels:
            levels[level] = []
        levels[level].append({
            'nodeId': data['nodeId'],
            'lat': data['latitude'],
            'lon': data['longitude']
        })
    
    # Insert aggregated data
    for level, nodes in levels.items():
        avg_lat = sum(n['lat'] for n in nodes) / len(nodes)
        avg_lon = sum(n['lon'] for n in nodes) / len(nodes)
        
        cur.execute("""
            INSERT INTO "RedundancyMap" ("Level", "Color", "NodeIds", "CenterLat", "CenterLon")
            VALUES (%s, %s, %s, %s, %s)
        """, (
            level,
            get_color_by_level(level),
            json.dumps([n['nodeId'] for n in nodes]),
            avg_lat,
            avg_lon
        ))
    
    conn.commit()
    conn.close()
    
    # Log summary
    logger.info(f"Redundancy calculated for {len(redundancy_data)} nodes")
    for level in sorted(levels.keys()):
        logger.info(f"  Level {level} ({get_color_by_level(level)}): {len(levels[level])} nodes")

def get_color_by_level(level):
    colors = {
        1: '#00ff00',   # Green - low redundancy
        2: '#ffff00',   # Yellow - medium
        3: '#ffa500',   # Orange - good
        4: '#ff6600',   # Orange-red - high
        5: '#ff0000'    # Red - very high
    }
    return colors.get(level, '#00ff00')

def main():
    logger.info("Starting Redundancy Service")
    logger.info(f"Run interval: {RUN_INTERVAL} seconds")
    
    while True:
        try:
            calculate_redundancy()
            logger.info(f"Cycle complete. Sleeping for {RUN_INTERVAL} seconds")
            time.sleep(RUN_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Shutting down")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()

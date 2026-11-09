"""
SIMEA-Port Service
Sistema Inteligente de Macroeconomia e Estabilidade Ambiental
Controle Portuário Inteligente

This service provides:
- Port management and monitoring
- Cargo tracking and optimization
- Environmental impact analysis
- Integration with SIMEA Pool Soberano
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ============================================================================
# DATABASE SCHEMA - SIMEA-Port
# ============================================================================

class PortSchema:
    """
    SIMEA-Port Database Schema
    
    Collections/Tables:
    1. ports - Port information and metadata
    2. cargo_operations - Cargo movement and tracking
    3. environmental_metrics - Environmental impact data
    4. port_insights - Processed insights and analytics
    5. integrations - Integration with Pool Soberano
    """
    
    @staticmethod
    def get_port_schema():
        return {
            "id": "string (uuid)",
            "name": "string",
            "code": "string (IATA/UN code)",
            "region": "string (Norte, Nordeste, Centro-Oeste, Sudeste, Sul)",
            "location": {
                "latitude": "float",
                "longitude": "float",
                "city": "string",
                "state": "string"
            },
            "capacity": {
                "max_cargo_ton": "float",
                "max_ships": "integer",
                "current_utilization": "float (percentage)"
            },
            "metrics": {
                "carga_total": "float (ton)",
                "eficiencia": "float (percentage)",
                "emissao_co2": "float (ton)",
                "energia_consumida": "float (kWh)",
                "operacoes_dia": "integer"
            },
            "environmental": {
                "carbon_footprint": "float",
                "renewable_energy_pct": "float",
                "waste_recycling_pct": "float",
                "water_usage": "float (m3)"
            },
            "financial": {
                "revenue": "float",
                "cost": "float",
                "profit_margin": "float",
                "investments": "float"
            },
            "status": "string (operational, maintenance, closed)",
            "created_at": "datetime",
            "updated_at": "datetime"
        }
    
    @staticmethod
    def get_cargo_schema():
        return {
            "id": "string (uuid)",
            "port_id": "string",
            "ship_id": "string",
            "type": "string (import, export, transshipment)",
            "cargo_type": "string (container, bulk, liquid, etc)",
            "weight_ton": "float",
            "value": "float",
            "origin": "string",
            "destination": "string",
            "status": "string (pending, in_progress, completed, cancelled)",
            "start_time": "datetime",
            "end_time": "datetime",
            "environmental_impact": {
                "co2_emission": "float",
                "energy_used": "float",
                "waste_generated": "float"
            },
            "created_at": "datetime"
        }
    
    @staticmethod
    def get_environmental_schema():
        return {
            "id": "string (uuid)",
            "port_id": "string",
            "date": "date",
            "co2_emissions": "float",
            "no2_emissions": "float",
            "so2_emissions": "float",
            "particulate_matter": "float",
            "water_quality": "float",
            "noise_levels": "float",
            "biodiversity_index": "float",
            "compliance_score": "float",
            "created_at": "datetime"
        }
    
    @staticmethod
    def get_insight_schema():
        return {
            "id": "string (uuid)",
            "port_id": "string",
            "metric_type": "string (efficiency, capacity, environmental, financial)",
            "value": "float",
            "trend": "string (up, down, stable)",
            "trend_pct": "float",
            "benchmark": "float",
            "recommendations": "list[string]",
            "generated_at": "datetime",
            "valid_until": "datetime"
        }
    
    @staticmethod
    def get_integration_schema():
        return {
            "id": "string (uuid)",
            "port_id": "string",
            "pool_company_id": "string",
            "integration_type": "string (logistics, financial, environmental)",
            "status": "string (active, pending, inactive)",
            "data_shared": "list[string]",
            "sync_frequency": "string",
            "last_sync": "datetime",
            "created_at": "datetime"
        }


# ============================================================================
# MOCK DATA GENERATOR
# ============================================================================

def generate_mock_ports() -> List[Dict[str, Any]]:
    """Generate mock port data for development"""
    ports = [
        {
            "id": "port-001",
            "name": "Porto de Santos",
            "code": "BRSSA",
            "region": "Sudeste",
            "location": {
                "latitude": -23.9608,
                "longitude": -46.3128,
                "city": "Santos",
                "state": "SP"
            },
            "capacity": {
                "max_cargo_ton": 150000000,
                "max_ships": 50,
                "current_utilization": 85.5
            },
            "metrics": {
                "carga_total": 125000000,
                "eficiencia": 85,
                "emissao_co2": -150000,
                "energia_consumida": 50000000,
                "operacoes_dia": 250
            },
            "environmental": {
                "carbon_footprint": 150000,
                "renewable_energy_pct": 25.0,
                "waste_recycling_pct": 85.0,
                "water_usage": 1000000
            },
            "financial": {
                "revenue": 2500000000,
                "cost": 1800000000,
                "profit_margin": 28.0,
                "investments": 500000000
            },
            "status": "operational",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-11-09T00:00:00Z"
        },
        {
            "id": "port-002",
            "name": "Porto do Rio de Janeiro",
            "code": "BRRIO",
            "region": "Sudeste",
            "location": {
                "latitude": -22.8975,
                "longitude": -43.1781,
                "city": "Rio de Janeiro",
                "state": "RJ"
            },
            "capacity": {
                "max_cargo_ton": 120000000,
                "max_ships": 40,
                "current_utilization": 78.3
            },
            "metrics": {
                "carga_total": 98000000,
                "eficiencia": 78,
                "emissao_co2": -120000,
                "energia_consumida": 45000000,
                "operacoes_dia": 200
            },
            "environmental": {
                "carbon_footprint": 120000,
                "renewable_energy_pct": 20.0,
                "waste_recycling_pct": 80.0,
                "water_usage": 800000
            },
            "financial": {
                "revenue": 2000000000,
                "cost": 1500000000,
                "profit_margin": 25.0,
                "investments": 400000000
            },
            "status": "operational",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-11-09T00:00:00Z"
        },
        {
            "id": "port-003",
            "name": "Porto de Paranaguá",
            "code": "BRPNG",
            "region": "Sul",
            "location": {
                "latitude": -25.5167,
                "longitude": -48.5000,
                "city": "Paranaguá",
                "state": "PR"
            },
            "capacity": {
                "max_cargo_ton": 100000000,
                "max_ships": 35,
                "current_utilization": 82.1
            },
            "metrics": {
                "carga_total": 85000000,
                "eficiencia": 82,
                "emissao_co2": -100000,
                "energia_consumida": 40000000,
                "operacoes_dia": 180
            },
            "environmental": {
                "carbon_footprint": 100000,
                "renewable_energy_pct": 30.0,
                "waste_recycling_pct": 88.0,
                "water_usage": 600000
            },
            "financial": {
                "revenue": 1800000000,
                "cost": 1300000000,
                "profit_margin": 27.8,
                "investments": 350000000
            },
            "status": "operational",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-11-09T00:00:00Z"
        },
        {
            "id": "port-004",
            "name": "Porto de Itaqui",
            "code": "BRITQ",
            "region": "Nordeste",
            "location": {
                "latitude": -2.5883,
                "longitude": -44.2019,
                "city": "São Luís",
                "state": "MA"
            },
            "capacity": {
                "max_cargo_ton": 80000000,
                "max_ships": 30,
                "current_utilization": 75.4
            },
            "metrics": {
                "carga_total": 62000000,
                "eficiencia": 75,
                "emissao_co2": -80000,
                "energia_consumida": 35000000,
                "operacoes_dia": 150
            },
            "environmental": {
                "carbon_footprint": 80000,
                "renewable_energy_pct": 15.0,
                "waste_recycling_pct": 75.0,
                "water_usage": 500000
            },
            "financial": {
                "revenue": 1500000000,
                "cost": 1200000000,
                "profit_margin": 20.0,
                "investments": 300000000
            },
            "status": "operational",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-11-09T00:00:00Z"
        },
        {
            "id": "port-005",
            "name": "Porto de Belém",
            "code": "BRBEL",
            "region": "Norte",
            "location": {
                "latitude": -1.4550,
                "longitude": -48.4892,
                "city": "Belém",
                "state": "PA"
            },
            "capacity": {
                "max_cargo_ton": 60000000,
                "max_ships": 25,
                "current_utilization": 70.2
            },
            "metrics": {
                "carga_total": 48000000,
                "eficiencia": 70,
                "emissao_co2": -60000,
                "energia_consumida": 30000000,
                "operacoes_dia": 120
            },
            "environmental": {
                "carbon_footprint": 60000,
                "renewable_energy_pct": 10.0,
                "waste_recycling_pct": 70.0,
                "water_usage": 400000
            },
            "financial": {
                "revenue": 1200000000,
                "cost": 1000000000,
                "profit_margin": 16.7,
                "investments": 200000000
            },
            "status": "operational",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-11-09T00:00:00Z"
        }
    ]
    return ports


def generate_mock_cargo(ports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate mock cargo operations"""
    cargo_types = ["container", "bulk", "liquid", "break_bulk", "roll_on_roll_off"]
    cargo_statuses = ["pending", "in_progress", "completed"]
    cargo_operations = []
    
    for port in ports:
        for i in range(10):
            cargo_operations.append({
                "id": f"cargo-{port['id']}-{i:03d}",
                "port_id": port["id"],
                "ship_id": f"ship-{random.randint(1000, 9999)}",
                "type": random.choice(["import", "export", "transshipment"]),
                "cargo_type": random.choice(cargo_types),
                "weight_ton": random.uniform(1000, 50000),
                "value": random.uniform(1000000, 50000000),
                "origin": random.choice(["China", "USA", "Germany", "Brazil", "Argentina", "Japan"]),
                "destination": random.choice(["Brazil", "China", "USA", "Europe", "Africa", "Australia"]),
                "status": random.choice(cargo_statuses),
                "start_time": (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                "end_time": (datetime.now() + timedelta(days=random.randint(1, 15))).isoformat() if random.random() > 0.3 else None,
                "environmental_impact": {
                    "co2_emission": random.uniform(100, 5000),
                    "energy_used": random.uniform(1000, 50000),
                    "waste_generated": random.uniform(10, 500)
                },
                "created_at": datetime.now().isoformat()
            })
    
    return cargo_operations


def generate_mock_environmental(ports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate mock environmental metrics"""
    environmental_data = []
    
    for port in ports:
        for day in range(30):
            date = (datetime.now() - timedelta(days=day)).strftime("%Y-%m-%d")
            environmental_data.append({
                "id": f"env-{port['id']}-{date}",
                "port_id": port["id"],
                "date": date,
                "co2_emissions": random.uniform(1000, 10000),
                "no2_emissions": random.uniform(50, 500),
                "so2_emissions": random.uniform(50, 500),
                "particulate_matter": random.uniform(10, 100),
                "water_quality": random.uniform(7.0, 9.5),
                "noise_levels": random.uniform(40, 80),
                "biodiversity_index": random.uniform(0.5, 1.0),
                "compliance_score": random.uniform(80, 100),
                "created_at": datetime.now().isoformat()
            })
    
    return environmental_data


# ============================================================================
# API ENDPOINTS
# ============================================================================

# Initialize mock data
PORTS = generate_mock_ports()
CARGO_OPERATIONS = generate_mock_cargo(PORTS)
ENVIRONMENTAL_DATA = generate_mock_environmental(PORTS)


@app.route('/api/port/schema', methods=['GET'])
def get_schema():
    """Get SIMEA-Port database schema"""
    return jsonify({
        "status": "success",
        "data": {
            "port": PortSchema.get_port_schema(),
            "cargo": PortSchema.get_cargo_schema(),
            "environmental": PortSchema.get_environmental_schema(),
            "insight": PortSchema.get_insight_schema(),
            "integration": PortSchema.get_integration_schema()
        },
        "message": "SIMEA-Port Database Schema"
    })


@app.route('/api/port/ports', methods=['GET'])
def get_ports():
    """Get all ports with optional filters"""
    region = request.args.get('region')
    status = request.args.get('status')
    
    filtered_ports = PORTS
    
    if region:
        filtered_ports = [p for p in filtered_ports if p['region'].lower() == region.lower()]
    
    if status:
        filtered_ports = [p for p in filtered_ports if p['status'].lower() == status.lower()]
    
    return jsonify({
        "status": "success",
        "data": filtered_ports,
        "count": len(filtered_ports),
        "message": "Ports retrieved successfully"
    })


@app.route('/api/port/ports/<port_id>', methods=['GET'])
def get_port(port_id: str):
    """Get a specific port by ID"""
    port = next((p for p in PORTS if p['id'] == port_id), None)
    
    if not port:
        return jsonify({
            "status": "error",
            "message": "Port not found"
        }), 404
    
    # Add related cargo operations
    related_cargo = [c for c in CARGO_OPERATIONS if c['port_id'] == port_id]
    related_env = [e for e in ENVIRONMENTAL_DATA if e['port_id'] == port_id]
    
    port['cargo_operations'] = related_cargo
    port['environmental_data'] = related_env
    
    return jsonify({
        "status": "success",
        "data": port,
        "message": "Port retrieved successfully"
    })


@app.route('/api/port/cargo', methods=['GET'])
def get_cargo():
    """Get all cargo operations"""
    port_id = request.args.get('port_id')
    status = request.args.get('status')
    cargo_type = request.args.get('type')
    
    filtered_cargo = CARGO_OPERATIONS
    
    if port_id:
        filtered_cargo = [c for c in filtered_cargo if c['port_id'] == port_id]
    
    if status:
        filtered_cargo = [c for c in filtered_cargo if c['status'].lower() == status.lower()]
    
    if cargo_type:
        filtered_cargo = [c for c in filtered_cargo if c['type'].lower() == cargo_type.lower()]
    
    return jsonify({
        "status": "success",
        "data": filtered_cargo,
        "count": len(filtered_cargo),
        "message": "Cargo operations retrieved successfully"
    })


@app.route('/api/port/environmental', methods=['GET'])
def get_environmental():
    """Get environmental metrics"""
    port_id = request.args.get('port_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    filtered_env = ENVIRONMENTAL_DATA
    
    if port_id:
        filtered_env = [e for e in filtered_env if e['port_id'] == port_id]
    
    if start_date:
        filtered_env = [e for e in filtered_env if e['date'] >= start_date]
    
    if end_date:
        filtered_env = [e for e in filtered_env if e['date'] <= end_date]
    
    return jsonify({
        "status": "success",
        "data": filtered_env,
        "count": len(filtered_env),
        "message": "Environmental data retrieved successfully"
    })


@app.route('/api/port/insights', methods=['GET'])
def get_insights():
    """Generate and return insights for ports"""
    insights = []
    
    # Calculate insights for each port
    for port in PORTS:
        # Efficiency insights
        port_cargo = [c for c in CARGO_OPERATIONS if c['port_id'] == port['id']]
        completed_cargo = [c for c in port_cargo if c['status'] == 'completed']
        efficiency = len(completed_cargo) / len(port_cargo) * 100 if port_cargo else 0
        
        # Environmental insights
        port_env = [e for e in ENVIRONMENTAL_DATA if e['port_id'] == port['id']]
        avg_compliance = sum(e['compliance_score'] for e in port_env) / len(port_env) if port_env else 0
        
        # Financial insights
        total_value = sum(c['value'] for c in port_cargo)
        
        insights.append({
            "port_id": port['id'],
            "port_name": port['name'],
            "region": port['region'],
            "metrics": {
                "efficiency": {
                    "value": round(efficiency, 2),
                    "trend": "up" if efficiency > port['metrics']['eficiencia'] else "down",
                    "trend_pct": round(efficiency - port['metrics']['eficiencia'], 2),
                    "benchmark": 85.0
                },
                "capacity_utilization": {
                    "value": port['capacity']['current_utilization'],
                    "trend": "stable",
                    "trend_pct": 0,
                    "benchmark": 80.0
                },
                "environmental_compliance": {
                    "value": round(avg_compliance, 2),
                    "trend": "up" if avg_compliance > 90 else "stable",
                    "trend_pct": round(avg_compliance - 90, 2),
                    "benchmark": 95.0
                },
                "financial_performance": {
                    "value": round(total_value, 2),
                    "trend": "up",
                    "trend_pct": round((total_value / port['financial']['revenue']) * 100, 2) if port['financial']['revenue'] > 0 else 0,
                    "benchmark": port['financial']['revenue']
                }
            },
            "recommendations": [
                f"Increase efficiency to {min(95, port['metrics']['eficiencia'] + 5)}%",
                f"Reduce CO2 emissions by {round(port['environmental']['carbon_footprint'] * 0.1, 2)} tons",
                f"Increase renewable energy usage to {min(50, port['environmental']['renewable_energy_pct'] + 10)}%"
            ],
            "generated_at": datetime.now().isoformat(),
            "valid_until": (datetime.now() + timedelta(hours=24)).isoformat()
        })
    
    return jsonify({
        "status": "success",
        "data": insights,
        "count": len(insights),
        "message": "Insights generated successfully"
    })


@app.route('/api/port/insights/<port_id>', methods=['GET'])
def get_port_insights(port_id: str):
    """Get insights for a specific port"""
    port = next((p for p in PORTS if p['id'] == port_id), None)
    
    if not port:
        return jsonify({
            "status": "error",
            "message": "Port not found"
        }), 404
    
    # Generate detailed insights for this port
    port_cargo = [c for c in CARGO_OPERATIONS if c['port_id'] == port_id]
    port_env = [e for e in ENVIRONMENTAL_DATA if e['port_id'] == port_id]
    
    completed_cargo = [c for c in port_cargo if c['status'] == 'completed']
    efficiency = len(completed_cargo) / len(port_cargo) * 100 if port_cargo else 0
    avg_compliance = sum(e['compliance_score'] for e in port_env) / len(port_env) if port_env else 0
    total_value = sum(c['value'] for c in port_cargo)
    total_weight = sum(c['weight_ton'] for c in port_cargo)
    
    insight = {
        "port_id": port_id,
        "port_name": port['name'],
        "region": port['region'],
        "detailed_metrics": {
            "cargo_operations": {
                "total": len(port_cargo),
                "completed": len(completed_cargo),
                "pending": len([c for c in port_cargo if c['status'] == 'pending']),
                "in_progress": len([c for c in port_cargo if c['status'] == 'in_progress']),
                "total_value": round(total_value, 2),
                "total_weight": round(total_weight, 2)
            },
            "efficiency": {
                "current": round(efficiency, 2),
                "target": 95.0,
                "gap": round(95.0 - efficiency, 2),
                "trend": "up" if efficiency > port['metrics']['eficiencia'] else "down"
            },
            "capacity": {
                "utilization": port['capacity']['current_utilization'],
                "max_capacity": port['capacity']['max_cargo_ton'],
                "available": port['capacity']['max_cargo_ton'] - port['metrics']['carga_total'],
                "utilization_pct": port['capacity']['current_utilization']
            },
            "environmental": {
                "avg_compliance": round(avg_compliance, 2),
                "carbon_footprint": port['environmental']['carbon_footprint'],
                "renewable_energy_pct": port['environmental']['renewable_energy_pct'],
                "waste_recycling_pct": port['environmental']['waste_recycling_pct']
            },
            "financial": {
                "revenue": port['financial']['revenue'],
                "cost": port['financial']['cost'],
                "profit_margin": port['financial']['profit_margin'],
                "investments": port['financial']['investments']
            }
        },
        "recommendations": [
            f"Optimize cargo handling to improve efficiency from {efficiency}% to 95%",
            f"Invest in renewable energy to increase from {port['environmental']['renewable_energy_pct']}% to 50%",
            f"Improve waste recycling from {port['environmental']['waste_recycling_pct']}% to 95%",
            f"Increase capacity utilization from {port['capacity']['current_utilization']}% to 90%"
        ],
        "generated_at": datetime.now().isoformat(),
        "valid_until": (datetime.now() + timedelta(hours=24)).isoformat()
    }
    
    return jsonify({
        "status": "success",
        "data": insight,
        "message": "Port insights retrieved successfully"
    })


@app.route('/api/port/pool-integration', methods=['GET'])
def get_pool_integration():
    """Get integration data between ports and Pool Soberano"""
    integrations = []
    
    for port in PORTS:
        # Simulate integration with Pool Soberano companies
        # In a real implementation, this would come from the database
        integrations.append({
            "port_id": port['id'],
            "port_name": port['name'],
            "region": port['region'],
            "integrated_companies": random.randint(5, 20),
            "total_integration_value": random.uniform(100000000, 500000000),
            "data_shared": ["cargo_volume", "efficiency_metrics", "environmental_data", "financial_performance"],
            "sync_frequency": "real-time",
            "last_sync": datetime.now().isoformat(),
            "status": "active",
            "benefits": {
                "efficiency_improvement": round(random.uniform(5, 15), 2),
                "cost_reduction": round(random.uniform(2, 10), 2),
                "emission_reduction": round(random.uniform(5, 20), 2)
            }
        })
    
    return jsonify({
        "status": "success",
        "data": integrations,
        "count": len(integrations),
        "message": "Pool Soberano integration data retrieved successfully"
    })


@app.route('/api/port/pool-integration/<port_id>', methods=['GET'])
def get_port_pool_integration(port_id: str):
    """Get detailed integration data for a specific port"""
    port = next((p for p in PORTS if p['id'] == port_id), None)
    
    if not port:
        return jsonify({
            "status": "error",
            "message": "Port not found"
        }), 404
    
    # Generate detailed integration data
    num_companies = random.randint(5, 20)
    
    integration = {
        "port_id": port_id,
        "port_name": port['name'],
        "region": port['region'],
        "integrated_companies": num_companies,
        "companies": [
            {
                "id": f"pool-{i:03d}",
                "name": f"Company {i}",
                "segment": random.choice(["Agro Sustentável", "Biodiversidade", "Energia Renovável", "Logística", "Captura de Carbono"]),
                "contribution": random.uniform(10000000, 100000000),
                "yield_pct": round(random.uniform(5, 20), 2),
                "integration_type": random.choice(["logistics", "financial", "environmental", "all"]),
                "sync_status": "active",
                "last_sync": datetime.now().isoformat()
            }
            for i in range(num_companies)
        ],
        "total_integration_value": random.uniform(100000000, 500000000),
        "data_shared": ["cargo_volume", "efficiency_metrics", "environmental_data", "financial_performance"],
        "sync_frequency": "real-time",
        "last_sync": datetime.now().isoformat(),
        "status": "active",
        "benefits": {
            "efficiency_improvement": round(random.uniform(5, 15), 2),
            "cost_reduction": round(random.uniform(2, 10), 2),
            "emission_reduction": round(random.uniform(5, 20), 2),
            "profit_increase": round(random.uniform(3, 12), 2)
        },
        "impact_analysis": {
            "before_integration": {
                "efficiency": round(port['metrics']['eficiencia'] - random.uniform(5, 10), 2),
                "cost": port['financial']['cost'] * 1.1,
                "emissions": port['environmental']['carbon_footprint'] * 1.15
            },
            "after_integration": {
                "efficiency": port['metrics']['eficiencia'],
                "cost": port['financial']['cost'],
                "emissions": port['environmental']['carbon_footprint']
            }
        }
    }
    
    return jsonify({
        "status": "success",
        "data": integration,
        "message": "Port Pool Soberano integration retrieved successfully"
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "success",
        "service": "SIMEA-Port",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "ports": len(PORTS),
        "cargo_operations": len(CARGO_OPERATIONS),
        "environmental_records": len(ENVIRONMENTAL_DATA)
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

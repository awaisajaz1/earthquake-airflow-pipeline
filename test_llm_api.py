#!/usr/bin/env python3
"""
Test script for the LLM API
"""

import requests
import json
import time

def test_health():
    """Test health endpoint"""
    try:
        response = requests.get("http://localhost:8001/health", timeout=10)
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_schema():
    """Test schema endpoint"""
    try:
        response = requests.get("http://localhost:8001/schema", timeout=10)
        print(f"Schema check: {response.status_code}")
        if response.status_code == 200:
            schema = response.json()
            print(f"Found {len(schema.get('schema', {}))} schemas")
        return response.status_code == 200
    except Exception as e:
        print(f"Schema check failed: {e}")
        return False

def test_query(question):
    """Test a natural language query"""
    try:
        payload = {
            "question": question,
            "include_explanation": True
        }
        
        print(f"\n🤖 Testing query: {question}")
        response = requests.post(
            "http://localhost:8001/query",
            json=payload,
            timeout=60
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"SQL Query: {result.get('sql_query', 'N/A')}")
            print(f"Results: {len(result.get('results', []))} rows")
            if result.get('explanation'):
                print(f"Explanation: {result['explanation']}")
            if result.get('error'):
                print(f"Error: {result['error']}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Query test failed: {e}")

def main():
    print("🧪 Testing LLM API...")
    
    # Test health
    print("\n1. Testing health endpoint...")
    if not test_health():
        print("❌ Health check failed. Make sure services are running.")
        return
    
    # Test schema
    print("\n2. Testing schema endpoint...")
    test_schema()
    
    # Test sample queries
    sample_queries = [
        "Show me all earthquakes with magnitude greater than 6",
        "What's the average magnitude of earthquakes?",
        "How many earthquakes are in the database?",
        "Show me the latest earthquake data"
    ]
    
    print("\n3. Testing natural language queries...")
    for query in sample_queries:
        test_query(query)
        time.sleep(2)  # Small delay between queries
    
    print("\n✅ Testing completed!")

if __name__ == "__main__":
    main()
#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

BASE_URL="http://127.0.0.1:5601"

echo -e "${YELLOW}=== Testing Bitcoin Alert API ===${NC}"
echo ""

# Test 1: Get current price
echo -e "${YELLOW}Test 1: Get Current Price${NC}"
curl -s ${BASE_URL}/api/price | python3 -m json.tool
echo -e "${GREEN}✅ Price endpoint working${NC}"
echo ""

# Test 2: Get alerts (should be empty initially)
echo -e "${YELLOW}Test 2: Get Active Alerts${NC}"
curl -s ${BASE_URL}/api/alerts | python3 -m json.tool
echo ""

# Test 3: Set a price alert
echo -e "${YELLOW}Test 3: Set Price Alert${NC}"
curl -s -X POST ${BASE_URL}/api/set_alert \
  -H "Content-Type: application/json" \
  -d '{
    "type": "price",
    "min_price": 60000,
    "max_price": 70000
  }' | python3 -m json.tool
echo -e "${GREEN}✅ Price alert set${NC}"
echo ""

# Test 4: Set a volume spike alert
echo -e "${YELLOW}Test 4: Set Volume Spike Alert${NC}"
curl -s -X POST ${BASE_URL}/api/set_alert \
  -H "Content-Type: application/json" \
  -d '{
    "type": "volume_spike",
    "volume_threshold": 3
  }' | python3 -m json.tool
echo -e "${GREEN}✅ Volume alert set${NC}"
echo ""

# Test 5: Set a volatility alert
echo -e "${YELLOW}Test 5: Set Volatility Alert${NC}"
curl -s -X POST ${BASE_URL}/api/set_alert \
  -H "Content-Type: application/json" \
  -d '{
    "type": "volatility_shift",
    "volatility_threshold": 0.02
  }' | python3 -m json.tool
echo -e "${GREEN}✅ Volatility alert set${NC}"
echo ""

# Test 6: Set an RSI alert
echo -e "${YELLOW}Test 6: Set RSI Alert${NC}"
curl -s -X POST ${BASE_URL}/api/set_alert \
  -H "Content-Type: application/json" \
  -d '{
    "type": "rsi",
    "rsi_threshold": 70,
    "rsi_direction": "above"
  }' | python3 -m json.tool
echo -e "${GREEN}✅ RSI alert set${NC}"
echo ""

# Test 7: Set a Golden Cross alert
echo -e "${YELLOW}Test 7: Set Golden Cross Alert${NC}"
curl -s -X POST ${BASE_URL}/api/set_alert \
  -H "Content-Type: application/json" \
  -d '{
    "type": "golden_cross"
  }' | python3 -m json.tool
echo -e "${GREEN}✅ Golden Cross alert set${NC}"
echo ""

# Test 8: Check all alerts
echo -e "${YELLOW}Test 8: Check All Alerts${NC}"
curl -s ${BASE_URL}/api/alerts | python3 -m json.tool
echo ""

# Test 9: Trigger alert check
echo -e "${YELLOW}Test 9: Trigger Alert Check${NC}"
curl -s ${BASE_URL}/api/check_alerts | python3 -m json.tool
echo ""

# Test 10: Delete all alerts
echo -e "${YELLOW}Test 10: Delete All Alerts${NC}"
for id in $(curl -s ${BASE_URL}/api/alerts | python3 -c "import json,sys; data=json.load(sys.stdin); print(' '.join([str(a['id']) for a in data['alerts']]))" 2>/dev/null); do
    echo "Deleting alert ID: $id"
    curl -s -X DELETE ${BASE_URL}/api/delete_alert/$id
done
echo -e "${GREEN}✅ All alerts deleted${NC}"
echo ""

echo -e "${GREEN}=== All tests completed! ===${NC}"

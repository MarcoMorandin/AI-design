#!/bin/bash
# Test Script for Agent Registry Service
# This script contains various curl commands for testing the Agent Registry API

# Configuration
HOST=${1:-"localhost:8000"}
EXAMPLE_AGENT_URL=${2:-"http://localhost:8003"}

# Colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Help function
show_help() {
    echo -e "${BLUE}Usage:${NC}"
    echo -e "  $0 [registry_host:port] [agent_url]"
    echo
    echo -e "${BLUE}Options:${NC}"
    echo -e "  registry_host:port  Registry server address (default: localhost:8080)"
    echo -e "  agent_url           Mock agent server URL (default: http://localhost:8000)"
    echo
    echo -e "${BLUE}Commands:${NC}"
    echo -e "  $0                  Run all tests"
    echo -e "  $0 info             Show registry service info"
    echo -e "  $0 health           Check service health"
    echo -e "  $0 register         Register an agent"
    echo -e "  $0 list             List all agents"
    echo -e "  $0 get <id>         Get details for specific agent"
    echo -e "  $0 refresh <id>     Refresh agent card"
    echo -e "  $0 unregister <id>  Unregister an agent"
    echo -e "  $0 help             Show this help"
}

# Check for help command
if [ "$1" == "help" ] || [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    show_help
    exit 0
fi

# Check for curl
if ! command -v curl &> /dev/null
then
    echo -e "${RED}Error: curl command is not found. Please install curl.${NC}"
    exit 1
fi

# Check for jq
if ! command -v jq &> /dev/null
then
    echo -e "${RED}Error: jq command is not found. Please install jq.${NC}"
    exit 1
fi

echo -e "${BLUE}=== Agent Registry Test Script ===${NC}"
echo -e "Target Registry: ${YELLOW}$HOST${NC}"
echo -e "Target Agent: ${YELLOW}$EXAMPLE_AGENT_URL${NC}"
echo

# Test service info
test_service_info() {
    echo -e "${BLUE}Testing service info...${NC}"
    curl -s -X GET http://$HOST/ | jq .
    echo
}

# Test health check
test_health_check() {
    echo -e "${BLUE}Testing health check...${NC}"
    HEALTH_STATUS=$(curl -s -X GET http://$HOST/health | jq -r '.status')
    
    if [ "$HEALTH_STATUS" == "healthy" ]; then
        echo -e "${GREEN}Service is healthy${NC}"
    else
        echo -e "${YELLOW}Service health status: $HEALTH_STATUS${NC}"
    fi
    
    curl -s -X GET http://$HOST/health | jq .
    echo
}

# Register an agent
register_agent() {
    echo -e "${BLUE}Registering agent...${NC}"
    AGENT_ID=$(curl -s -X POST http://$HOST/register \
      -H "Content-Type: application/json" \
      -d "{\"url\": \"$EXAMPLE_AGENT_URL\"}" | jq -r '.agent_id')
    
    if [ -z "$AGENT_ID" ] || [ "$AGENT_ID" == "null" ]; then
        echo -e "${RED}Failed to register agent${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Successfully registered agent with ID: $AGENT_ID${NC}"
    echo "$AGENT_ID" # Return the agent ID
    return 0
}

# List all agents
list_agents() {
    echo -e "${BLUE}Listing all agents...${NC}"
    curl -s -X GET http://$HOST/agents | jq .
    echo
}

# Get agent details
get_agent_details() {
    local AGENT_ID=$1
    if [ -z "$AGENT_ID" ]; then
        echo -e "${RED}Agent ID is required${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Getting details for agent $AGENT_ID...${NC}"
    curl -s -X GET http://$HOST/agents/$AGENT_ID | jq .
    echo
}

# Refresh agent card
refresh_agent_card() {
    local AGENT_ID=$1
    if [ -z "$AGENT_ID" ]; then
        echo -e "${RED}Agent ID is required${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Refreshing agent card for $AGENT_ID...${NC}"
    curl -s -X POST http://$HOST/refresh/$AGENT_ID | jq .
    echo
}

# Unregister agent
unregister_agent() {
    local AGENT_ID=$1
    if [ -z "$AGENT_ID" ]; then
        echo -e "${RED}Agent ID is required${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Unregistering agent $AGENT_ID...${NC}"
    curl -s -X DELETE http://$HOST/agents/$AGENT_ID | jq .
    echo
}

# Run all tests
run_all_tests() {
    echo -e "${BLUE}Running all tests...${NC}"
    echo
    
    test_service_info
    test_health_check
    
    AGENT_ID=$(register_agent)
    if [ $? -eq 0 ]; then
        list_agents
        get_agent_details "$AGENT_ID"
        refresh_agent_card "$AGENT_ID"
        unregister_agent "$AGENT_ID"
        list_agents
    fi
    
    echo -e "${GREEN}All tests completed${NC}"
}

# Run individual test based on command line argument
# Skip the first two arguments if they look like host:port or URL parameters
if [[ "$1" == *":"* && "$1" != "info" && "$1" != "register" && "$1" != "list" && "$1" != "get" && "$1" != "refresh" && "$1" != "unregister" && "$1" != "help" ]]; then
    # First arg is host:port
    if [[ "$2" == "http"* ]]; then
        # Second arg is the agent URL
        COMMAND="$3"
        PARAM="$4"
    else
        # No agent URL specified
        COMMAND="$2"
        PARAM="$3"
    fi
else
    COMMAND="$1"
    PARAM="$2"
fi

case "$COMMAND" in
    info)
        test_service_info
        ;;
    health)
        test_health_check
        ;;
    register)
        register_agent
        ;;
    list)
        list_agents
        ;;
    get)
        get_agent_details "$PARAM"
        ;;
    refresh)
        refresh_agent_card "$PARAM"
        ;;
    unregister)
        unregister_agent "$PARAM"
        ;;
    help)
        show_help
        ;;
    *)
        run_all_tests
        ;;
esac

exit 0

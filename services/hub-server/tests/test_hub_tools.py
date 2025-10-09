"""
Test Hub Server Tools

Tests for Hub Server management and orchestration tools.
"""

import asyncio
import sys
from pathlib import Path
import logging

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import Hub tools
sys.path.insert(0, str(parent_dir / "app"))
from mcp_server import HubTools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_test_header(test_name: str):
    """Print test header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}TEST: {test_name}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_result(success: bool, message: str = ""):
    """Print test result"""
    if success:
        print(f"{Colors.GREEN}[PASS]{Colors.END} {message}")
    else:
        print(f"{Colors.RED}[FAIL]{Colors.END} {message}")


async def test_hub_status():
    """
    Test 1: Hub Status
    Get comprehensive Hub status including all Spokes
    """
    print_test_header("Hub Status - Comprehensive System Check")

    try:
        hub_tools = HubTools()
        result = await hub_tools.hub_status({})

        # Validate result structure
        assert "hub" in result, "Missing 'hub' in result"
        assert "spokes" in result, "Missing 'spokes' in result"
        assert "tools" in result, "Missing 'tools' in result"
        assert "summary" in result, "Missing 'summary' in result"

        # Validate hub info
        assert result["hub"]["name"] == "fin-hub", "Incorrect hub name"
        assert result["hub"]["status"] == "operational", "Hub not operational"

        # Validate summary
        assert result["summary"]["total_spokes"] == 3, "Should have 3 spokes"
        assert result["summary"]["hub_operational"] == True, "Hub should be operational"

        print(f"Hub Status: {result['hub']['status']}")
        print(f"Total Spokes: {result['summary']['total_spokes']}")
        print(f"Healthy Spokes: {result['summary']['healthy_spokes']}")
        print(f"Total Tools: {result['summary']['total_tools']}")

        print_result(True, "Hub status check successful")
        return True

    except Exception as e:
        logger.error(f"Hub status test failed: {e}", exc_info=True)
        print_result(False, f"Error: {str(e)}")
        return False


async def test_list_spokes():
    """
    Test 2: List Spokes
    List all Spoke services with their health status
    """
    print_test_header("List Spokes - Service Discovery")

    try:
        hub_tools = HubTools()
        result = await hub_tools.list_spokes({})

        # Validate result structure
        assert "total_spokes" in result, "Missing 'total_spokes'"
        assert "healthy_spokes" in result, "Missing 'healthy_spokes'"
        assert "spokes" in result, "Missing 'spokes' list"
        assert "timestamp" in result, "Missing 'timestamp'"

        # Check spoke count
        assert result["total_spokes"] == 3, "Should have 3 spokes"
        assert len(result["spokes"]) == 3, "Should list 3 spokes"

        # Validate each spoke has required fields
        required_fields = ["name", "endpoint", "status", "available"]
        for spoke in result["spokes"]:
            for field in required_fields:
                assert field in spoke, f"Spoke missing field: {field}"

        print(f"Total Spokes: {result['total_spokes']}")
        print(f"Healthy Spokes: {result['healthy_spokes']}")
        print(f"\nSpoke Details:")
        for spoke in result["spokes"]:
            status_color = Colors.GREEN if spoke["available"] else Colors.RED
            print(f"  - {spoke['name']}: {status_color}{spoke['status']}{Colors.END} ({spoke['endpoint']})")

        print_result(True, "List spokes successful")
        return True

    except Exception as e:
        logger.error(f"List spokes test failed: {e}", exc_info=True)
        print_result(False, f"Error: {str(e)}")
        return False


async def test_get_spoke_tools_all():
    """
    Test 3: Get Spoke Tools - All Spokes
    Get all available tools from all Spoke services
    """
    print_test_header("Get Spoke Tools - All Spokes")

    try:
        hub_tools = HubTools()
        result = await hub_tools.get_spoke_tools({"spoke_name": "all"})

        # Validate result structure
        assert "spokes_queried" in result, "Missing 'spokes_queried'"
        assert "total_tools" in result, "Missing 'total_tools'"
        assert "tools_by_spoke" in result, "Missing 'tools_by_spoke'"

        # Check tool counts
        expected_tools = {
            "market": 13,
            "risk": 8,
            "portfolio": 8
        }

        for spoke, expected_count in expected_tools.items():
            assert spoke in result["tools_by_spoke"], f"Missing spoke: {spoke}"
            actual_count = result["tools_by_spoke"][spoke]["tool_count"]
            assert actual_count == expected_count, f"{spoke} should have {expected_count} tools, got {actual_count}"

        print(f"Spokes Queried: {result['spokes_queried']}")
        print(f"Total Tools: {result['total_tools']}")
        print(f"\nTools by Spoke:")
        for spoke, info in result["tools_by_spoke"].items():
            print(f"  - {spoke}: {info['tool_count']} tools ({info['status']})")

        print_result(True, "Get all spoke tools successful")
        return True

    except Exception as e:
        logger.error(f"Get spoke tools test failed: {e}", exc_info=True)
        print_result(False, f"Error: {str(e)}")
        return False


async def test_get_spoke_tools_specific():
    """
    Test 4: Get Spoke Tools - Specific Spoke
    Get tools from a specific Spoke (market)
    """
    print_test_header("Get Spoke Tools - Market Spoke Only")

    try:
        hub_tools = HubTools()
        result = await hub_tools.get_spoke_tools({"spoke_name": "market"})

        # Validate result
        assert "tools_by_spoke" in result, "Missing 'tools_by_spoke'"
        assert "market" in result["tools_by_spoke"], "Missing market spoke"
        assert result["tools_by_spoke"]["market"]["tool_count"] == 13, "Market should have 13 tools"

        # Should only query one spoke
        assert result["spokes_queried"] == 1, "Should only query 1 spoke"

        print(f"Spoke Queried: market")
        print(f"Tool Count: {result['tools_by_spoke']['market']['tool_count']}")
        print(f"Status: {result['tools_by_spoke']['market']['status']}")

        print_result(True, "Get specific spoke tools successful")
        return True

    except Exception as e:
        logger.error(f"Get specific spoke tools test failed: {e}", exc_info=True)
        print_result(False, f"Error: {str(e)}")
        return False


async def test_hub_health_check():
    """
    Test 5: Hub Health Check
    Perform comprehensive health check on Hub and all Spokes
    """
    print_test_header("Hub Health Check - System-Wide Health")

    try:
        hub_tools = HubTools()
        result = await hub_tools.hub_health_check({})

        # Validate result structure
        assert "hub_healthy" in result, "Missing 'hub_healthy'"
        assert "all_spokes_healthy" in result, "Missing 'all_spokes_healthy'"
        assert "spokes" in result, "Missing 'spokes' list"
        assert "health_score" in result, "Missing 'health_score'"
        assert "timestamp" in result, "Missing 'timestamp'"
        assert "issues" in result, "Missing 'issues' list"

        # Hub should be healthy
        assert result["hub_healthy"] == True, "Hub should be healthy"

        # Health score should be 0-100
        assert 0 <= result["health_score"] <= 100, "Health score should be 0-100"

        print(f"Hub Healthy: {Colors.GREEN if result['hub_healthy'] else Colors.RED}{result['hub_healthy']}{Colors.END}")
        print(f"All Spokes Healthy: {Colors.GREEN if result['all_spokes_healthy'] else Colors.RED}{result['all_spokes_healthy']}{Colors.END}")
        print(f"Health Score: {result['health_score']:.1f}%")

        if not result["all_spokes_healthy"]:
            print(f"\n{Colors.YELLOW}Issues Detected:{Colors.END}")
            for issue in result["issues"]:
                print(f"  - {issue}")

        print(f"\nDetailed Spoke Health:")
        for spoke in result["spokes"]:
            status_color = Colors.GREEN if spoke["available"] else Colors.RED
            print(f"  - {spoke['name']}: {status_color}{spoke['status']}{Colors.END}")

        print_result(True, "Hub health check successful")
        return True

    except Exception as e:
        logger.error(f"Hub health check test failed: {e}", exc_info=True)
        print_result(False, f"Error: {str(e)}")
        return False


async def test_call_spoke_tool_valid():
    """
    Test 6: Call Spoke Tool - Valid Request
    Test routing a tool call to a Spoke (placeholder functionality)
    """
    print_test_header("Call Spoke Tool - Valid Request")

    try:
        hub_tools = HubTools()
        result = await hub_tools.call_spoke_tool({
            "spoke_name": "market",
            "tool_name": "stock_quote",
            "tool_arguments": {"symbol": "AAPL"}
        })

        # Validate result (placeholder returns success message)
        assert "success" in result, "Missing 'success' field"
        assert "spoke" in result, "Missing 'spoke' field"
        assert "tool" in result, "Missing 'tool' field"

        # For placeholder, should be successful
        assert result["success"] == True, "Should succeed (placeholder)"
        assert result["spoke"] == "market", "Spoke should be 'market'"
        assert result["tool"] == "stock_quote", "Tool should be 'stock_quote'"

        print(f"Success: {result['success']}")
        print(f"Spoke: {result['spoke']}")
        print(f"Tool: {result['tool']}")
        print(f"Message: {result.get('message', 'N/A')}")

        print_result(True, "Call spoke tool (valid) successful")
        return True

    except Exception as e:
        logger.error(f"Call spoke tool test failed: {e}", exc_info=True)
        print_result(False, f"Error: {str(e)}")
        return False


async def test_call_spoke_tool_invalid():
    """
    Test 7: Call Spoke Tool - Invalid Spoke
    Test error handling for invalid spoke name
    """
    print_test_header("Call Spoke Tool - Invalid Spoke")

    try:
        hub_tools = HubTools()
        result = await hub_tools.call_spoke_tool({
            "spoke_name": "invalid_spoke",
            "tool_name": "some_tool"
        })

        # Should return error
        assert "success" in result, "Missing 'success' field"
        assert result["success"] == False, "Should fail for invalid spoke"
        assert "error" in result, "Missing 'error' field"
        assert "invalid_spoke" in result["error"].lower(), "Error should mention invalid spoke"

        print(f"Success: {result['success']}")
        print(f"Error: {result['error']}")
        if "available_spokes" in result:
            print(f"Available Spokes: {result['available_spokes']}")

        print_result(True, "Invalid spoke error handling successful")
        return True

    except Exception as e:
        logger.error(f"Invalid spoke test failed: {e}", exc_info=True)
        print_result(False, f"Error: {str(e)}")
        return False


async def test_call_spoke_tool_missing_params():
    """
    Test 8: Call Spoke Tool - Missing Parameters
    Test error handling for missing required parameters
    """
    print_test_header("Call Spoke Tool - Missing Parameters")

    try:
        hub_tools = HubTools()
        result = await hub_tools.call_spoke_tool({
            # Missing both spoke_name and tool_name
        })

        # Should return error
        assert "success" in result, "Missing 'success' field"
        assert result["success"] == False, "Should fail for missing params"
        assert "error" in result, "Missing 'error' field"

        print(f"Success: {result['success']}")
        print(f"Error: {result['error']}")

        print_result(True, "Missing parameters error handling successful")
        return True

    except Exception as e:
        logger.error(f"Missing params test failed: {e}", exc_info=True)
        print_result(False, f"Error: {str(e)}")
        return False


async def run_all_tests():
    """
    Run all Hub Server tests.
    """
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"Hub Server - Test Suite")
    print(f"{'='*60}{Colors.END}\n")

    tests = [
        ("Hub Status", test_hub_status),
        ("List Spokes", test_list_spokes),
        ("Get Spoke Tools - All", test_get_spoke_tools_all),
        ("Get Spoke Tools - Specific", test_get_spoke_tools_specific),
        ("Hub Health Check", test_hub_health_check),
        ("Call Spoke Tool - Valid", test_call_spoke_tool_valid),
        ("Call Spoke Tool - Invalid", test_call_spoke_tool_invalid),
        ("Call Spoke Tool - Missing Params", test_call_spoke_tool_missing_params),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"Test Summary")
    print(f"{'='*60}{Colors.END}\n")

    total = len(results)
    passed = sum(1 for _, success in results if success)
    failed = total - passed

    for test_name, success in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if success else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {status} - {test_name}")

    print(f"\n{Colors.BOLD}Total: {total}, Passed: {Colors.GREEN}{passed}{Colors.END}, "
          f"Failed: {Colors.RED}{failed}{Colors.END}{Colors.BOLD}")

    success_rate = (passed / total * 100) if total > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%{Colors.END}\n")

    # Additional info
    if failed > 0:
        print(f"{Colors.YELLOW}Note: Some tests may fail if Spoke services are not running.{Colors.END}")
        print(f"{Colors.YELLOW}To start Spoke services:{Colors.END}")
        print(f"  python services/market-spoke/mcp_server.py")
        print(f"  python services/risk-spoke/mcp_server.py")
        print(f"  python services/portfolio-spoke/mcp_server.py\n")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

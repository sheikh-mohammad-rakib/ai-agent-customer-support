import json
from database import (
    get_order,
    update_order_status,
    search_faqs,
    log_tool_execution
)

# Tool Schemas compatible with Qwen Cloud / OpenAI function calling format
SUPPORT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Look up an order's current status, shipping carrier, tracking number, and purchased items by order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The customer's order ID (e.g. ORD-1001 or 1001)"
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "initiate_return",
            "description": "Initiate a return request for an order and generate an RMA return label.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID to initiate a return for."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Customer's reason for returning the item (e.g. defective, wrong size, changed mind)"
                    }
                },
                "required": ["order_id", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_faq",
            "description": "Search Acme Retail's customer support knowledge base for return policies, shipping timelines, warranties, or exchanges.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query or question keywords (e.g. 'return window' or 'shipping time')"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Flag the call for warm handoff or immediate human supervisor callback when the customer requests a manager or has a complex issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why the call is being escalated to a human supervisor."
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Urgency level of the escalation."
                    }
                },
                "required": ["reason"]
            }
        }
    }
]


async def execute_tool(name: str, arguments: dict, call_id: str = "SIMULATOR"):
    """
    Executes the requested tool and logs the execution in the SQLite database.
    """
    result = {}

    if name == "lookup_order":
        order_id = arguments.get("order_id", "")
        order = get_order(order_id)
        if order:
            result = {
                "success": True,
                "order_id": order["order_id"],
                "customer_name": order["customer_name"],
                "status": order["status"],
                "carrier": order["carrier"],
                "tracking_number": order["tracking_number"],
                "items": order["items"],
                "total_amount": order["total_amount"]
            }
        else:
            result = {
                "success": False,
                "error": f"Order '{order_id}' was not found in Acme Retail's database. Please verify the number."
            }

    elif name == "initiate_return":
        order_id = arguments.get("order_id", "")
        reason = arguments.get("reason", "Customer requested return")
        order = get_order(order_id)
        if order:
            update_order_status(order_id, "Pending Return")
            rma_number = f"RMA-{order['order_id'].replace('ORD-', '')}-8891"
            result = {
                "success": True,
                "order_id": order["order_id"],
                "new_status": "Pending Return",
                "rma_number": rma_number,
                "return_label_status": "Pre-paid return shipping label generated and emailed to customer.",
                "reason": reason
            }
        else:
            result = {
                "success": False,
                "error": f"Cannot initiate return: Order '{order_id}' was not found."
            }

    elif name == "search_faq":
        query = arguments.get("query", "")
        matches = search_faqs(query)
        result = {
            "success": True,
            "query": query,
            "matches": matches
        }

    elif name == "escalate_to_human":
        reason = arguments.get("reason", "Customer request")
        urgency = arguments.get("urgency", "medium")
        ticket_id = "ESC-9941"
        result = {
            "success": True,
            "ticket_id": ticket_id,
            "status": "Supervisor Alerted",
            "message": f"Warm handoff ticket #{ticket_id} created with {urgency.upper()} urgency. A human specialist will follow up.",
            "reason": reason
        }
    else:
        result = {
            "success": False,
            "error": f"Unknown tool: {name}"
        }

    # Log execution in SQLite DB
    log_tool_execution(call_id, name, arguments, result)
    return result

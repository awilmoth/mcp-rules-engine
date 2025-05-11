#!/usr/bin/env python3
import os
import sys
import logging
import json
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

# Create log directories
app_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(app_dir, 'RulesEngineMCP')
os.makedirs(log_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'rules_engine.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RulesEngine")

# Import MCP and other required libraries
try:
    from mcp.server.fastmcp import FastMCP, Context
    import uvicorn
    from fastapi import FastAPI, Request, Response
    from pydantic import BaseModel, Field
    
    logger.info("Successfully imported required libraries")
except ImportError as e:
    logger.error(f"Failed to import required libraries: {e}")
    logger.info("Installing required libraries...")
    
    try:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "mcp", "uvicorn", "fastapi", "pydantic"], check=True)
        
        # Import again after installation
        from mcp.server.fastmcp import FastMCP, Context
        import uvicorn
        from fastapi import FastAPI, Request, Response
        from pydantic import BaseModel, Field
        
        logger.info("Successfully installed and imported required libraries")
    except Exception as e:
        logger.error(f"Failed to install required libraries: {e}")
        print(f"Error: Failed to install required libraries. Please install them manually: pip install mcp uvicorn fastapi pydantic")
        sys.exit(1)

# ----------------- Rule Models ------------------

class Rule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    condition: str  # Regular expression or other matching condition
    action: str = "redact"  # Type of action: "redact", "transform", "flag", "block", etc.
    replacement: str = "<REDACTED>"  # For redaction rules
    parameters: Dict[str, Any] = {}  # Action-specific parameters
    enabled: bool = True
    priority: int = 0  # Higher priority rules run first
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "SSN",
                "description": "US Social Security Number",
                "condition": r"\b\d{3}-\d{2}-\d{4}\b",
                "action": "redact",
                "replacement": "<SSN>",
                "parameters": {},
                "enabled": True,
                "priority": 10
            }
        }

class RuleSet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    rules: List[str] = []  # List of rule IDs
    enabled: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class RuleEngineConfig(BaseModel):
    rules: Dict[str, Rule] = {}  # Using a dict for faster lookups by ID
    rule_sets: Dict[str, RuleSet] = {}
    default_rule_set: str = "default"

# Global configuration
config = RuleEngineConfig()

# ----------------- Rules Engine ------------------

class RulesEngine:
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        """Load configuration from file."""
        global config
        
        config_file = os.path.join(log_dir, 'rules_config.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    # Convert dictionaries to model objects
                    rules = {id: Rule(**rule) for id, rule in data.get('rules', {}).items()}
                    rule_sets = {id: RuleSet(**rule_set) for id, rule_set in data.get('rule_sets', {}).items()}
                    default_rule_set = data.get('default_rule_set', 'default')
                    
                    config = RuleEngineConfig(
                        rules=rules,
                        rule_sets=rule_sets,
                        default_rule_set=default_rule_set
                    )
                logger.info(f"Loaded {len(config.rules)} rules and {len(config.rule_sets)} rule sets")
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")
                self.add_default_rules()
        else:
            # Add default rules if file doesn't exist
            self.add_default_rules()
            self.save_config()
    
    def save_config(self):
        """Save configuration to file."""
        global config
        
        config_file = os.path.join(log_dir, 'rules_config.json')
        try:
            # Convert to dict for JSON serialization
            data = {
                'rules': {id: rule.model_dump() for id, rule in config.rules.items()},
                'rule_sets': {id: rule_set.model_dump() for id, rule_set in config.rule_sets.items()},
                'default_rule_set': config.default_rule_set
            }
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(config.rules)} rules and {len(config.rule_sets)} rule sets")
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
    
    def add_default_rules(self):
        """Add default rules and rule sets."""
        global config
        
        # Create default rule set
        default_set_id = "default"
        default_set = RuleSet(
            id=default_set_id,
            name="Default",
            description="Default rule set with common patterns"
        )
        
        # Add default rules
        default_rules = [
            Rule(
                name="SSN",
                description="US Social Security Number",
                condition=r"\b\d{3}-\d{2}-\d{4}\b",
                action="redact",
                replacement="<SSN>",
                priority=100
            ),
            Rule(
                name="Credit Card",
                description="Credit Card Number",
                condition=r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
                action="redact",
                replacement="<CREDIT_CARD>",
                priority=90
            ),
            Rule(
                name="Email",
                description="Email Address",
                condition=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                action="redact",
                replacement="<EMAIL>",
                priority=80
            ),
            Rule(
                name="Phone",
                description="Phone Number",
                condition=r"\b(?:\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
                action="redact",
                replacement="<PHONE>",
                priority=70
            ),
            Rule(
                name="Credentials",
                description="API Keys, Passwords, etc.",
                condition=r"(password|api[_-]?key|access[_-]?token|secret)[=:]\s*\S+",
                action="redact",
                replacement="<CREDENTIAL>",
                priority=60
            ),
            Rule(
                name="IP Address",
                description="IPv4 Address",
                condition=r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
                action="redact",
                replacement="<IP_ADDRESS>",
                priority=50
            ),
            Rule(
                name="URL",
                description="Web URL",
                condition=r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)",
                action="flag",
                replacement="<URL>",
                parameters={"flag_reason": "Contains URL", "severity": "info"},
                priority=40
            ),
            Rule(
                name="Profanity Block",
                description="Block text with strong profanity",
                condition=r"\b(f\*\*k|sh\*t)\b",  # Simplified for example
                action="block",
                parameters={"reason": "Contains strong profanity", "severity": "high"},
                priority=200  # Higher priority to block first
            ),
            Rule(
                name="Date Transform",
                description="Transform dates to standard format",
                condition=r"\b(0?[1-9]|1[0-2])/(0?[1-9]|[12][0-9]|3[01])/(19|20)\d{2}\b",
                action="transform",
                parameters={"transform_type": "date", "format": "%Y-%m-%d"},
                priority=30
            )
        ]
        
        # Add rules to config
        rule_ids = []
        for rule in default_rules:
            rule_id = rule.id
            config.rules[rule_id] = rule
            rule_ids.append(rule_id)
        
        # Update rule set with rule IDs
        default_set.rules = rule_ids
        config.rule_sets[default_set_id] = default_set
        config.default_rule_set = default_set_id
        
        logger.info(f"Added {len(default_rules)} default rules")
    
    def get_rule_by_id(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        return config.rules.get(rule_id)
    
    def get_rules_by_set(self, rule_set_id: Optional[str] = None) -> List[Rule]:
        """Get all rules in a rule set."""
        if rule_set_id is None:
            rule_set_id = config.default_rule_set
        
        rule_set = config.rule_sets.get(rule_set_id)
        if not rule_set:
            return []
        
        return [config.rules[rule_id] for rule_id in rule_set.rules if rule_id in config.rules]
    
    def add_rule(self, rule: Rule) -> str:
        """Add a new rule and return its ID."""
        rule_id = rule.id
        rule.updated_at = datetime.now().isoformat()
        
        config.rules[rule_id] = rule
        
        # Add to default rule set if no set is specified
        default_set_id = config.default_rule_set
        if default_set_id in config.rule_sets:
            config.rule_sets[default_set_id].rules.append(rule_id)
            config.rule_sets[default_set_id].updated_at = datetime.now().isoformat()
        
        self.save_config()
        return rule_id
    
    def update_rule(self, rule_id: str, rule: Rule) -> bool:
        """Update an existing rule."""
        if rule_id not in config.rules:
            return False
        
        rule.id = rule_id  # Ensure ID doesn't change
        rule.updated_at = datetime.now().isoformat()
        
        config.rules[rule_id] = rule
        self.save_config()
        return True
    
    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule and remove it from all rule sets."""
        if rule_id not in config.rules:
            return False
        
        # Remove from all rule sets
        for rule_set_id, rule_set in config.rule_sets.items():
            if rule_id in rule_set.rules:
                rule_set.rules.remove(rule_id)
                rule_set.updated_at = datetime.now().isoformat()
        
        # Remove the rule
        del config.rules[rule_id]
        
        self.save_config()
        return True
    
    def add_rule_set(self, rule_set: RuleSet) -> str:
        """Add a new rule set and return its ID."""
        rule_set_id = rule_set.id
        rule_set.updated_at = datetime.now().isoformat()
        
        config.rule_sets[rule_set_id] = rule_set
        self.save_config()
        return rule_set_id
    
    def update_rule_set(self, rule_set_id: str, rule_set: RuleSet) -> bool:
        """Update an existing rule set."""
        if rule_set_id not in config.rule_sets:
            return False
        
        rule_set.id = rule_set_id  # Ensure ID doesn't change
        rule_set.updated_at = datetime.now().isoformat()
        
        config.rule_sets[rule_set_id] = rule_set
        self.save_config()
        return True
    
    def delete_rule_set(self, rule_set_id: str) -> bool:
        """Delete a rule set."""
        if rule_set_id not in config.rule_sets:
            return False
        
        # Don't delete the default rule set
        if rule_set_id == config.default_rule_set:
            return False
        
        del config.rule_sets[rule_set_id]
        self.save_config()
        return True
    
    def set_default_rule_set(self, rule_set_id: str) -> bool:
        """Set the default rule set."""
        if rule_set_id not in config.rule_sets:
            return False
        
        config.default_rule_set = rule_set_id
        self.save_config()
        return True
    
    def process_text(self, text: str, rule_set_ids: Optional[List[str]] = None,
                   context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process text through rules engine."""
        if not text:
            return {"processed_text": text, "results": [], "status": "success"}
        
        # Get rules to apply
        rules_to_apply = []
        
        if rule_set_ids:
            # Get rules from specified rule sets
            for rule_set_id in rule_set_ids:
                rules_to_apply.extend(self.get_rules_by_set(rule_set_id))
        else:
            # Get rules from default rule set
            rules_to_apply = self.get_rules_by_set()
        
        # Filter enabled rules and sort by priority
        rules_to_apply = [rule for rule in rules_to_apply if rule.enabled]
        rules_to_apply.sort(key=lambda r: r.priority, reverse=True)
        
        # Process text through rules
        processed_text = text
        results = []
        
        for rule in rules_to_apply:
            try:
                # Apply rule based on action type
                if rule.action == "block":
                    # Check if text should be blocked
                    if re.search(rule.condition, processed_text):
                        reason = rule.parameters.get("reason", "Blocked by rule")
                        severity = rule.parameters.get("severity", "high")
                        
                        return {
                            "processed_text": "",
                            "results": [{
                                "rule_id": rule.id,
                                "rule_name": rule.name,
                                "action": "block",
                                "reason": reason,
                                "severity": severity
                            }],
                            "status": "blocked"
                        }
                
                elif rule.action == "redact":
                    # Redact matching text
                    pattern = re.compile(rule.condition)
                    matches = pattern.findall(processed_text)
                    
                    for match in matches:
                        if isinstance(match, tuple):  # If capturing groups
                            match = match[0]  # Use first group
                        
                        results.append({
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "action": "redact",
                            "original": match,
                            "replacement": rule.replacement
                        })
                    
                    processed_text = pattern.sub(rule.replacement, processed_text)
                
                elif rule.action == "flag":
                    # Flag matching text without changing it
                    pattern = re.compile(rule.condition)
                    matches = pattern.findall(processed_text)
                    
                    for match in matches:
                        if isinstance(match, tuple):  # If capturing groups
                            match = match[0]  # Use first group
                        
                        results.append({
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "action": "flag",
                            "text": match,
                            "flag_reason": rule.parameters.get("flag_reason", "Flagged by rule"),
                            "severity": rule.parameters.get("severity", "info")
                        })
                
                elif rule.action == "transform":
                    # Transform matching text
                    transform_type = rule.parameters.get("transform_type")
                    
                    if transform_type == "date":
                        # Date transformation example
                        date_format = rule.parameters.get("format", "%Y-%m-%d")
                        
                        def date_replacer(match):
                            try:
                                # Simple US date format MM/DD/YYYY to format
                                from datetime import datetime
                                date_str = match.group(0)
                                date = datetime.strptime(date_str, "%m/%d/%Y")
                                return date.strftime(date_format)
                            except:
                                return match.group(0)
                        
                        pattern = re.compile(rule.condition)
                        matches = pattern.findall(processed_text)
                        
                        for match in matches:
                            if isinstance(match, tuple):  # If capturing groups
                                match = match[0]  # Use first group
                            
                            try:
                                from datetime import datetime
                                date = datetime.strptime(match, "%m/%d/%Y")
                                transformed = date.strftime(date_format)
                                
                                results.append({
                                    "rule_id": rule.id,
                                    "rule_name": rule.name,
                                    "action": "transform",
                                    "original": match,
                                    "transformed": transformed,
                                    "transform_type": transform_type
                                })
                            except:
                                pass  # Skip failed transformations
                        
                        processed_text = pattern.sub(date_replacer, processed_text)
                    
                    # Add more transformation types as needed
                
                # Add more action types as needed
            
            except Exception as e:
                logger.error(f"Error applying rule {rule.name}: {str(e)}")
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "action": "error",
                    "error": str(e)
                })
        
        return {
            "processed_text": processed_text,
            "results": results,
            "status": "success"
        }

# Initialize rules engine
rules_engine = RulesEngine()

# ----------------- MCP Tools ------------------

class RedactTextRequest(BaseModel):
    text: str

class ProcessTextRequest(BaseModel):
    text: str
    rule_sets: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None

# Create an MCP server with newer protocol version and stdio transport
class CustomFastMCP(FastMCP):
    """Custom FastMCP server that supports both legacy and newer protocol formats,
    as well as stdio transport for direct integration with Claude."""

    def __init__(self, name: str):
        super().__init__(name)
        logger.info("Initializing CustomFastMCP server with support for latest protocol and stdio transport")

    def stdio(self):
        """Add stdio transport support for direct integration with Claude."""
        import json
        import sys

        logger.info("Starting MCP server with stdio transport")

        # Helper to handle MCP messages
        def handle_message(message_str):
            try:
                message = json.loads(message_str)
                logger.info(f"Received message: {message_str[:100]}...")

                # Define a mapping of tool names to their functions
                tool_map = {
                    # Core tools
                    "redact_text": redact_text,
                    "process_text": process_text,

                    # Rule management tools
                    "get_rules": get_rules,
                    "get_rule": get_rule,
                    "add_rule": add_rule,
                    "update_rule": update_rule,
                    "delete_rule": delete_rule,

                    # Rule set management tools
                    "get_rule_sets": get_rule_sets,
                    "get_rule_set": get_rule_set,
                    "add_rule_set": add_rule_set,
                    "update_rule_set": update_rule_set,
                    "delete_rule_set": delete_rule_set,
                    "set_default_rule_set": set_default_rule_set
                }

                # Support both legacy and new MCP protocol formats
                if message.get("method") == "execute":
                    # Legacy format
                    tool_name = message.get("params", {}).get("name")
                    params = message.get("params", {}).get("parameters", {})
                    message_id = message.get("id")

                    logger.info(f"Executing tool: {tool_name} with params {params}")

                    if tool_name in tool_map:
                        try:
                            result = tool_map[tool_name](**params)
                            response = {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "result": result
                            }
                        except Exception as e:
                            logger.error(f"Error executing tool {tool_name}: {str(e)}")
                            response = {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "error": {
                                    "code": -32603,
                                    "message": str(e)
                                }
                            }
                    else:
                        logger.error(f"Tool not found: {tool_name}")
                        response = {
                            "jsonrpc": "2.0",
                            "id": message_id,
                            "error": {
                                "code": -32601,
                                "message": f"Tool not found: {tool_name}"
                            }
                        }

                elif message.get("method") == "tools/call":
                    # Newer format
                    tool_name = message.get("params", {}).get("name")
                    params = message.get("params", {}).get("parameters", {})
                    message_id = message.get("id")

                    logger.info(f"Executing tool (new protocol): {tool_name} with params {params}")

                    if tool_name in tool_map:
                        try:
                            result = tool_map[tool_name](**params)
                            response = {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "result": result
                            }
                        except Exception as e:
                            logger.error(f"Error executing tool {tool_name}: {str(e)}")
                            response = {
                                "jsonrpc": "2.0",
                                "id": message_id,
                                "error": {
                                    "code": -32603,
                                    "message": str(e)
                                }
                            }
                    else:
                        logger.error(f"Tool not found: {tool_name}")
                        response = {
                            "jsonrpc": "2.0",
                            "id": message_id,
                            "error": {
                                "code": -32601,
                                "message": f"Tool not found: {tool_name}"
                            }
                        }

                # Direct method call (when method name matches a tool)
                elif message.get("method") in tool_map:
                    tool_name = message.get("method")
                    params = message.get("params", {})
                    message_id = message.get("id")

                    logger.info(f"Executing tool via direct method call: {tool_name}")
                    result = tool_map[tool_name](**params)

                    response = {
                        "jsonrpc": "2.0",
                        "id": message_id,
                        "result": result
                    }

                # Handle method list request
                elif message.get("method") == "rpc.discover":
                    logger.info("Handling 'rpc.discover' method")
                    tools = []
                    for tool_name, tool_fn in tool_map.items():
                        tools.append({
                            "name": tool_name,
                            "description": tool_fn.__doc__ or "",
                            "parameters": {}  # Would need more introspection to get params
                        })

                    return {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "result": {
                            "methods": tools
                        }
                    }
                else:
                    # Unknown method
                    logger.error(f"Unknown method: {message.get('method')}")
                    response = {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "error": {
                            "code": -32601,
                            "message": f"Unknown method: {message.get('method')}"
                        }
                    }

                # Output the response
                logger.info(f"Sending response: {json.dumps(response)[:100]}...")
                return json.dumps(response)

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON: {message_str}")
                return json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                })
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                return json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                })

        # Read input lines and process each one
        try:
            logger.info("Stdio transport ready, waiting for input...")
            while True:
                line = sys.stdin.readline()
                if not line:
                    logger.info("End of input, exiting...")
                    break

                response = handle_message(line.strip())
                sys.stdout.write(response + "\n")
                sys.stdout.flush()

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, exiting...")
        except Exception as e:
            logger.error(f"Stdio transport error: {str(e)}")
            raise

# Create server with protocol support
mcp_server = CustomFastMCP("Rules Engine")

# ----------------- MCP Tools ------------------

@mcp_server.tool()
def process_text(text: str, rule_sets: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Process text through the rules engine.
    
    Args:
        text: The text to process
        rule_sets: Optional IDs of rule sets to apply (default: default rule set)
        context: Additional context for rule application (optional)
        
    Returns:
        A dictionary containing processed text and results
    """
    return rules_engine.process_text(text, rule_sets, context)

@mcp_server.tool()
def redact_text(text: str) -> Dict[str, Any]:
    # Patched for redaction functionality
    result = rules_engine.process_text(text)
    processed_text = result.get("processed_text", text)
    matches = []

    for item in result.get("results", []):
        if item.get("action") == "redact":
            matches.append({
                "original": item.get("original", ""),
                "replacement": item.get("replacement", ""),
                "rule_name": item.get("rule_name", "")
            })

    return {
        "redacted_text": processed_text,
        "matches": matches
    }

@mcp_server.tool()
def get_rules(rule_set_id: Optional[str] = None) -> Dict[str, Any]:
    """Get all rules or rules in a specific rule set.
    
    Args:
        rule_set_id: Optional rule set ID (default: all rules)
        
    Returns:
        A dictionary containing rules
    """
    if rule_set_id:
        rules_list = rules_engine.get_rules_by_set(rule_set_id)
        return {"rules": [rule.model_dump() for rule in rules_list]}
    else:
        return {"rules": [rule.model_dump() for rule in config.rules.values()]}

@mcp_server.tool()
def get_rule(rule_id: str) -> Dict[str, Any]:
    """Get a specific rule by ID.
    
    Args:
        rule_id: Rule ID
        
    Returns:
        A dictionary containing the rule
    """
    rule = rules_engine.get_rule_by_id(rule_id)
    
    if not rule:
        return {"error": f"Rule not found: {rule_id}"}
    
    return {"rule": rule.model_dump()}

@mcp_server.tool()
def add_rule(name: str, condition: str, action: str, description: str = "", 
             replacement: str = "<REDACTED>", parameters: Dict[str, Any] = {}, 
             priority: int = 0) -> Dict[str, Any]:
    """Add a new rule.
    
    Args:
        name: Rule name
        description: Rule description
        condition: Regular expression or other matching condition
        action: Type of action: redact, transform, flag, block, etc.
        replacement: Replacement text for redaction rules
        parameters: Additional parameters for the action
        priority: Rule priority (higher runs first)
        
    Returns:
        A dictionary containing the new rule ID and rule
    """
    try:
        # Create rule from parameters
        rule = Rule(
            name=name,
            description=description,
            condition=condition,
            action=action,
            replacement=replacement,
            parameters=parameters,
            priority=priority
        )
        
        # Validate regex
        try:
            re.compile(rule.condition)
        except re.error as e:
            return {"error": f"Invalid regex pattern: {str(e)}"}
        
        # Add rule
        rule_id = rules_engine.add_rule(rule)
        
        return {"rule_id": rule_id, "rule": rule.model_dump()}
    except Exception as e:
        return {"error": f"Error adding rule: {str(e)}"}

@mcp_server.tool()
def update_rule(rule_id: str, name: Optional[str] = None, description: Optional[str] = None,
                condition: Optional[str] = None, action: Optional[str] = None,
                replacement: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None,
                enabled: Optional[bool] = None, priority: Optional[int] = None) -> Dict[str, Any]:
    """Update an existing rule.
    
    Args:
        rule_id: Rule ID
        name: Rule name
        description: Rule description
        condition: Regular expression or other matching condition
        action: Type of action: redact, transform, flag, block, etc.
        replacement: Replacement text for redaction rules
        parameters: Additional parameters for the action
        enabled: Whether the rule is enabled
        priority: Rule priority (higher runs first)
        
    Returns:
        A dictionary containing the rule ID and updated rule
    """
    # Get existing rule
    existing_rule = rules_engine.get_rule_by_id(rule_id)
    
    if not existing_rule:
        return {"error": f"Rule not found: {rule_id}"}
    
    # Update rule fields
    update_params = {}
    for field, value in [
        ("name", name), 
        ("description", description), 
        ("condition", condition), 
        ("action", action), 
        ("replacement", replacement), 
        ("parameters", parameters), 
        ("enabled", enabled), 
        ("priority", priority)
    ]:
        if value is not None:
            update_params[field] = value
    
    # Update rule fields
    for field, value in update_params.items():
        setattr(existing_rule, field, value)
    
    # Validate regex
    if condition is not None:
        try:
            re.compile(existing_rule.condition)
        except re.error as e:
            return {"error": f"Invalid regex pattern: {str(e)}"}
    
    # Update rule
    success = rules_engine.update_rule(rule_id, existing_rule)
    
    if not success:
        return {"error": "Failed to update rule"}
    
    return {"rule_id": rule_id, "rule": existing_rule.model_dump()}

@mcp_server.tool()
def delete_rule(rule_id: str) -> Dict[str, Any]:
    """Delete a rule.
    
    Args:
        rule_id: Rule ID
        
    Returns:
        A dictionary indicating success or failure
    """
    success = rules_engine.delete_rule(rule_id)
    
    if not success:
        return {"error": f"Failed to delete rule: {rule_id}"}
    
    return {"success": True, "rule_id": rule_id}

@mcp_server.tool()
def get_rule_sets() -> Dict[str, Any]:
    """Get all rule sets.
    
    Returns:
        A dictionary containing all rule sets
    """
    rule_sets = {id: rule_set.model_dump() for id, rule_set in config.rule_sets.items()}
    default_rule_set = config.default_rule_set
    
    return {"rule_sets": rule_sets, "default_rule_set": default_rule_set}

@mcp_server.tool()
def get_rule_set(rule_set_id: str) -> Dict[str, Any]:
    """Get a specific rule set.
    
    Args:
        rule_set_id: Rule set ID
        
    Returns:
        A dictionary containing the rule set and its rules
    """
    rule_set = config.rule_sets.get(rule_set_id)
    
    if not rule_set:
        return {"error": f"Rule set not found: {rule_set_id}"}
    
    # Get rules in the set
    rules_list = rules_engine.get_rules_by_set(rule_set_id)
    
    return {
        "rule_set": rule_set.model_dump(),
        "rules": [rule.model_dump() for rule in rules_list],
        "is_default": rule_set_id == config.default_rule_set
    }

@mcp_server.tool()
def add_rule_set(name: str, description: str = "", rule_ids: List[str] = []) -> Dict[str, Any]:
    """Add a new rule set.
    
    Args:
        name: Rule set name
        description: Rule set description
        rule_ids: List of rule IDs to include
        
    Returns:
        A dictionary containing the new rule set ID and rule set
    """
    try:
        # Create rule set from parameters
        rule_set = RuleSet(
            name=name,
            description=description,
            rules=rule_ids
        )
        
        # Add rule set
        rule_set_id = rules_engine.add_rule_set(rule_set)
        
        return {"rule_set_id": rule_set_id, "rule_set": rule_set.model_dump()}
    except Exception as e:
        return {"error": f"Error adding rule set: {str(e)}"}

@mcp_server.tool()
def update_rule_set(rule_set_id: str, name: Optional[str] = None, 
                   description: Optional[str] = None, rule_ids: Optional[List[str]] = None,
                   enabled: Optional[bool] = None) -> Dict[str, Any]:
    """Update an existing rule set.
    
    Args:
        rule_set_id: Rule set ID
        name: Rule set name
        description: Rule set description
        rule_ids: List of rule IDs to include
        enabled: Whether the rule set is enabled
        
    Returns:
        A dictionary containing the rule set ID and updated rule set
    """
    # Get existing rule set
    existing_rule_set = config.rule_sets.get(rule_set_id)
    
    if not existing_rule_set:
        return {"error": f"Rule set not found: {rule_set_id}"}
    
    # Update rule set fields
    update_params = {}
    for field, value in [
        ("name", name),
        ("description", description),
        ("rules", rule_ids),
        ("enabled", enabled)
    ]:
        if value is not None:
            update_params[field] = value
    
    # Update rule set fields
    for field, value in update_params.items():
        setattr(existing_rule_set, field, value)
    
    # Update rule set
    success = rules_engine.update_rule_set(rule_set_id, existing_rule_set)
    
    if not success:
        return {"error": "Failed to update rule set"}
    
    return {"rule_set_id": rule_set_id, "rule_set": existing_rule_set.model_dump()}

@mcp_server.tool()
def delete_rule_set(rule_set_id: str) -> Dict[str, Any]:
    """Delete a rule set.
    
    Args:
        rule_set_id: Rule set ID
        
    Returns:
        A dictionary indicating success or failure
    """
    success = rules_engine.delete_rule_set(rule_set_id)
    
    if not success:
        return {"error": f"Failed to delete rule set: {rule_set_id}"}
    
    return {"success": True, "rule_set_id": rule_set_id}

@mcp_server.tool()
def set_default_rule_set(rule_set_id: str) -> Dict[str, Any]:
    """Set the default rule set.
    
    Args:
        rule_set_id: Rule set ID
        
    Returns:
        A dictionary indicating success or failure
    """
    success = rules_engine.set_default_rule_set(rule_set_id)
    
    if not success:
        return {"error": f"Failed to set default rule set: {rule_set_id}"}
    
    return {"success": True, "default_rule_set": rule_set_id}

# ----------------- FastAPI App ------------------

def create_fastapi_app():
    """Create a FastAPI app with explicit endpoints for both MCP and direct access."""
    app = FastAPI(title="Rules Engine MCP Server", version="1.0.0")
    
    # Root endpoint for service discovery
    @app.get("/")
    async def root():
        return {
            "name": "Rules Engine MCP Server",
            "version": "1.0.0",
            "status": "active",
            "endpoints": [
                "/redact_text",
                "/process_text",
                "/mcp",
                "/sse",
                "/mcp-tools",
                "/health"
            ]
        }
    
    # Health check endpoints
    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": "1.0.0"}

    @app.get("/healthcheck")
    async def healthcheck():
        return {"status": "ok", "version": "1.0.0"}
    
    # MCP tools endpoint
    @app.get("/mcp-tools")
    async def get_mcp_tools():
        logger.info("Tools info requested at /mcp-tools")
        tools = []
        # Get tools from registered functions
        # The FastMCP library might have different attribute names in different versions
        if hasattr(mcp_server, '_tools'):
            tool_dict = mcp_server._tools
        elif hasattr(mcp_server, '_tool_registry'):
            tool_dict = mcp_server._tool_registry
        else:
            # Fallback to hardcoded tools if we can't find the registry
            tool_dict = {
                "redact_text": {"fn": redact_text},
                "process_text": {"fn": process_text},
                "get_rules": {"fn": get_rules},
                "get_rule": {"fn": get_rule},
                "add_rule": {"fn": add_rule},
                "update_rule": {"fn": update_rule},
                "delete_rule": {"fn": delete_rule},
                "get_rule_sets": {"fn": get_rule_sets},
                "get_rule_set": {"fn": get_rule_set},
                "add_rule_set": {"fn": add_rule_set},
                "update_rule_set": {"fn": update_rule_set},
                "delete_rule_set": {"fn": delete_rule_set},
                "set_default_rule_set": {"fn": set_default_rule_set}
            }
            logger.warning("Could not find MCP tool registry, using hardcoded tool list")

        # Manually add our tools since we know which ones we've registered
        tools = [
            {
                "name": "redact_text",
                "description": "Redacts sensitive information from text based on configured patterns.",
                "parameters": {
                    "text": {
                        "type": "string",
                        "description": "The text to redact"
                    }
                }
            },
            {
                "name": "process_text",
                "description": "Processes text through rules engine with options for rule sets.",
                "parameters": {
                    "text": {
                        "type": "string",
                        "description": "The text to process"
                    },
                    "rule_sets": {
                        "type": "array",
                        "description": "Optional IDs of rule sets to apply",
                        "items": {
                            "type": "string"
                        }
                    },
                    "context": {
                        "type": "object",
                        "description": "Additional context for rule application"
                    }
                }
            }
        ]

        return {"tools": tools}
    
    # Direct tool endpoints for simplified access
    @app.post("/redact_text")
    async def direct_redact_text(request: RedactTextRequest):
        logger.info(f"Direct redact_text request received with {len(request.text)} characters")
        result = redact_text(request.text)
        return result

    # Direct access to process_text
    @app.post("/process_text")
    async def direct_process_text(request: ProcessTextRequest):
        logger.info(f"Direct process_text request received with {len(request.text)} characters")
        result = process_text(request.text, request.rule_sets, request.context)
        return result
    
    # MCP JSON-RPC endpoint
    @app.post("/mcp")
    async def handle_mcp_request(request: Request):
        """Handle MCP JSON-RPC requests explicitly."""
        try:
            data = await request.json()
            method = data.get("method")
            params = data.get("params", {})
            request_id = data.get("id")

            logger.info(f"MCP endpoint received method: {method} with params keys: {list(params.keys())}")

            # Define a mapping of tool names to their functions
            tool_map = {
                # Core tools
                "redact_text": redact_text,
                "process_text": process_text,

                # Rule management tools
                "get_rules": get_rules,
                "get_rule": get_rule,
                "add_rule": add_rule,
                "update_rule": update_rule,
                "delete_rule": delete_rule,

                # Rule set management tools
                "get_rule_sets": get_rule_sets,
                "get_rule_set": get_rule_set,
                "add_rule_set": add_rule_set,
                "update_rule_set": update_rule_set,
                "delete_rule_set": delete_rule_set,
                "set_default_rule_set": set_default_rule_set
            }

            # If method is a direct tool call (when method name directly matches a tool)
            if method in tool_map:
                logger.info(f"Executing tool directly: {method}")
                result = tool_map[method](**params)

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }

            # Handle legacy MCP protocol 'execute' method
            elif method == "execute":
                logger.info("Handling legacy 'execute' method")
                tool_name = params.get("name")
                tool_params = params.get("parameters", {})

                if tool_name in tool_map:
                    logger.info(f"Executing tool via legacy protocol: {tool_name}")
                    result = tool_map[tool_name](**tool_params)

                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result
                    }
                else:
                    logger.error(f"Tool not found: {tool_name}")
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {tool_name}"
                        }
                    }

            # Handle newer MCP protocol 'tools/call' method
            elif method == "tools/call":
                logger.info("Handling new 'tools/call' method")
                tool_name = params.get("name")
                tool_params = params.get("parameters", {})

                if tool_name in tool_map:
                    logger.info(f"Executing tool via new protocol: {tool_name}")
                    result = tool_map[tool_name](**tool_params)

                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": result
                    }
                else:
                    logger.error(f"Tool not found: {tool_name}")
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {tool_name}"
                        }
                    }

            # Handle method list request
            elif method == "rpc.discover":
                logger.info("Handling 'rpc.discover' method")
                # Return the tools listed in our /mcp-tools endpoint
                tools_response = await get_mcp_tools()
                tools = tools_response.get("tools", [])

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "methods": tools
                    }
                }

            else:
                logger.error(f"Unknown method: {method}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }

        except Exception as e:
            logger.error(f"Error handling MCP request: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "jsonrpc": "2.0",
                "id": data.get("id") if "data" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }

    # SSE (Server-Sent Events) endpoint for MCP streaming
    @app.get("/sse")
    async def mcp_sse(request: Request):
        """Handle Server-Sent Events (SSE) for MCP requests."""
        from fastapi.responses import StreamingResponse
        import asyncio
        import json

        logger.info("SSE connection established")

        async def event_generator():
            # Send initial connected event
            yield "event: connected\ndata: {}\n\n"

            # Keep connection alive
            while True:
                # Send an empty comment to keep connection alive
                yield ": keepalive\n\n"
                await asyncio.sleep(30)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
    
    return app

# ----------------- Main ------------------

def detect_transport():
    """Detect if we should use stdio or http transport based on environment."""
    # Check if we're running through the MCP client which sets up specific environment
    # or if we're running directly (HTTP server mode)
    if os.environ.get("MCP_STDIO_TRANSPORT") == "true":
        return "stdio"
    else:
        return "http"

def detect_os():
    """Detect the operating system."""
    import platform
    system = platform.system()
    logger.info(f"Detected operating system: {system}")
    return system

def run_server():
    """Run the appropriate server based on the detected transport."""
    transport = detect_transport()

    if transport == "stdio":
        logger.info("Starting MCP server with stdio transport")
        mcp_server.stdio()
    else:
        logger.info("Starting MCP server with HTTP transport")
        app = create_fastapi_app()

        host = "0.0.0.0"

        # Use different ports based on OS
        system = detect_os()
        if system == "Windows":
            port = 6367  # Windows port
        else:
            port = 6366  # Linux/Unix port

        # Run with uvicorn
        logger.info(f"Server will run on http://{host}:{port}")
        uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    logger.info("Starting Rules Engine MCP Server...")
    logger.info(f"Log directory: {log_dir}")
    logger.info("MCP server is starting...")
    
    try:
        # Run appropriate server based on transport
        run_server()
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        print(f"Error starting server: {str(e)}")
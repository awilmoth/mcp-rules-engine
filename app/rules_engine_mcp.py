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
    from pydantic import BaseModel, Field
    
    logger.info("Successfully imported required libraries")
except ImportError as e:
    logger.error(f"Failed to import required libraries: {e}")
    logger.info("Installing required libraries...")
    
    try:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "mcp", "uvicorn", "pydantic"], check=True)
        
        # Import again after installation
        from mcp.server.fastmcp import FastMCP, Context
        import uvicorn
        from pydantic import BaseModel, Field
        
        logger.info("Successfully installed and imported required libraries")
    except Exception as e:
        logger.error(f"Failed to install required libraries: {e}")
        print(f"Error: Failed to install required libraries. Please install them manually: pip install mcp uvicorn pydantic")
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

# ----------------- FastMCP Server ------------------

# Create an MCP server
mcp_server = FastMCP("Rules Engine")

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
    """Redact text using redaction rules (legacy).
    
    Args:
        text: The text to redact
        
    Returns:
        A dictionary containing redacted text and matches
    """
    # Get only redaction rules
    redaction_rules = []
    for rule_id, rule in config.rules.items():
        if rule.action == "redact" and rule.enabled:
            redaction_rules.append(rule_id)
    
    # Create a temporary rule set with only redaction rules
    temp_rule_set = RuleSet(
        id="temp_redaction",
        name="Temporary Redaction Set",
        rules=redaction_rules
    )
    
    # Process text with just redaction rules
    result = rules_engine.process_text(text, ["temp_redaction"])
    
    # Format response to match legacy redact_text
    redacted_text = result.get("processed_text", text)
    matches = []
    
    for item in result.get("results", []):
        if item.get("action") == "redact":
            matches.append({
                "original": item.get("original", ""),
                "replacement": item.get("replacement", ""),
                "rule_name": item.get("rule_name", "")
            })
    
    return {
        "redacted_text": redacted_text,
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

# ----------------- Main ------------------

def detect_transport():
    """Detect if we should use stdio or http transport based on environment."""
    # Check if we're running through the MCP client which sets up specific environment
    # or if we're running directly (HTTP server mode)
    if os.environ.get("MCP_STDIO_TRANSPORT") == "true":
        return "stdio"
    else:
        return "http"

def run_server():
    """Run the appropriate server based on the detected transport."""
    transport = detect_transport()
    
    if transport == "stdio":
        logger.info("Starting MCP server with stdio transport")
        mcp_server.stdio()
    else:
        logger.info("Starting MCP server with HTTP transport")
        app = mcp_server.streamable_http_app()
        
        host = "0.0.0.0"
        port = 6366
        
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
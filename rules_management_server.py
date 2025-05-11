#!/usr/bin/env python3
import os
import sys
import json
import logging
import uuid
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RulesManagementServer")

# Get the project directory
project_dir = Path(os.path.dirname(os.path.abspath(__file__)))

# Create rules directory if it doesn't exist
rules_dir = project_dir / "app" / "RulesEngineMCP"
rules_dir.mkdir(parents=True, exist_ok=True)

# Rules config file path
rules_config_path = rules_dir / "rules_config.json"

# --------------------- Data Models ---------------------

class Rule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    condition: str  # Regular expression
    action: str = "redact"  # Type of action: "redact", "transform", "flag", "block"
    replacement: str = "<REDACTED>"  # For redaction rules
    parameters: Dict[str, Any] = {}  # Action-specific parameters
    enabled: bool = True
    priority: int = 0  # Higher priority runs first
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class RuleSet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    rules: List[str] = []  # List of rule IDs
    enabled: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class RuleEngineConfig(BaseModel):
    rules: Dict[str, Rule] = {}
    rule_sets: Dict[str, RuleSet] = {}
    default_rule_set: str = "default"

# --------------------- Rule Management ---------------------

class RuleManager:
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self) -> RuleEngineConfig:
        """Load the rule configuration from file."""
        if rules_config_path.exists():
            try:
                with open(rules_config_path, 'r') as f:
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
                return config
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")
                return self.create_default_config()
        else:
            # Create default config if file doesn't exist
            return self.create_default_config()
    
    def save_config(self) -> bool:
        """Save the current configuration to file."""
        try:
            # Convert to dict for JSON serialization
            data = {
                'rules': {id: rule.dict() for id, rule in self.config.rules.items()},
                'rule_sets': {id: rule_set.dict() for id, rule_set in self.config.rule_sets.items()},
                'default_rule_set': self.config.default_rule_set
            }
            
            with open(rules_config_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(self.config.rules)} rules and {len(self.config.rule_sets)} rule sets")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def create_default_config(self) -> RuleEngineConfig:
        """Create default configuration with sample rules."""
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
                id="ssn",
                name="SSN",
                description="US Social Security Number",
                condition=r"\b\d{3}-\d{2}-\d{4}\b",
                action="redact",
                replacement="<SSN>",
                priority=100
            ),
            Rule(
                id="cc",
                name="Credit Card",
                description="Credit Card Number",
                condition=r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
                action="redact",
                replacement="<CREDIT_CARD>",
                priority=90
            ),
            Rule(
                id="email",
                name="Email",
                description="Email Address",
                condition=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                action="redact",
                replacement="<EMAIL>",
                priority=80
            ),
            Rule(
                id="phone",
                name="Phone",
                description="Phone Number",
                condition=r"\b(?:\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
                action="redact",
                replacement="<PHONE>",
                priority=70
            ),
            Rule(
                id="credentials",
                name="Credentials",
                description="API Keys, Passwords, etc.",
                condition=r"(password|api[_-]?key|access[_-]?token|secret)[=:]\s*\S+",
                action="redact",
                replacement="<CREDENTIAL>",
                priority=60
            )
        ]
        
        # Create config
        config = RuleEngineConfig()
        
        # Add rules to config
        for rule in default_rules:
            config.rules[rule.id] = rule
            default_set.rules.append(rule.id)
        
        # Add rule set to config
        config.rule_sets[default_set_id] = default_set
        config.default_rule_set = default_set_id
        
        logger.info(f"Created default configuration with {len(default_rules)} rules")
        
        # Save to file
        self.config = config
        self.save_config()
        
        return config
    
    def get_all_rules(self) -> Dict[str, Rule]:
        """Get all rules."""
        return self.config.rules
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        return self.config.rules.get(rule_id)
    
    def add_rule(self, rule: Rule) -> str:
        """Add a new rule and return its ID."""
        # Generate an ID if not provided
        if not rule.id or rule.id in self.config.rules:
            rule.id = rule.name.lower().replace(" ", "_") + "_" + str(uuid.uuid4())[:8]
        
        # Set timestamps
        rule.created_at = datetime.now().isoformat()
        rule.updated_at = datetime.now().isoformat()
        
        # Add to config
        self.config.rules[rule.id] = rule
        
        # Add to default rule set
        default_set_id = self.config.default_rule_set
        if default_set_id in self.config.rule_sets:
            if rule.id not in self.config.rule_sets[default_set_id].rules:
                self.config.rule_sets[default_set_id].rules.append(rule.id)
                self.config.rule_sets[default_set_id].updated_at = datetime.now().isoformat()
        
        # Save config
        self.save_config()
        
        return rule.id
    
    def update_rule(self, rule_id: str, **kwargs) -> bool:
        """Update an existing rule with the provided fields."""
        if rule_id not in self.config.rules:
            return False
        
        # Get existing rule
        rule = self.config.rules[rule_id]
        
        # Update fields
        for field, value in kwargs.items():
            if hasattr(rule, field) and field != "id":  # Don't change the ID
                setattr(rule, field, value)
        
        # Update timestamp
        rule.updated_at = datetime.now().isoformat()
        
        # Save config
        self.save_config()
        
        return True
    
    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule and remove it from all rule sets."""
        if rule_id not in self.config.rules:
            return False
        
        # Remove from all rule sets
        for rule_set_id, rule_set in self.config.rule_sets.items():
            if rule_id in rule_set.rules:
                rule_set.rules.remove(rule_id)
                rule_set.updated_at = datetime.now().isoformat()
        
        # Remove the rule
        del self.config.rules[rule_id]
        
        # Save config
        self.save_config()
        
        return True
    
    def redact_text(self, text: str) -> Dict[str, Any]:
        """Process text through the rules engine."""
        if not text:
            return {"redacted_text": "", "matches": []}
        
        redacted = text
        matches = []
        
        # Get all enabled rules, sorted by priority
        rules = [r for r in self.config.rules.values() if r.enabled]
        rules.sort(key=lambda r: r.priority, reverse=True)
        
        # Apply each rule
        for rule in rules:
            try:
                # Compile the regex
                pattern = re.compile(rule.condition)
                
                # Find all matches
                rule_matches = list(pattern.finditer(redacted))
                
                # Process matches in reverse order to avoid offsetting issues
                for match in reversed(rule_matches):
                    original = match.group(0)
                    
                    # Add to matches list
                    matches.append({
                        "original": original,
                        "replacement": rule.replacement,
                        "rule_name": rule.name
                    })
                    
                    # Replace in the text
                    start, end = match.span()
                    redacted = redacted[:start] + rule.replacement + redacted[end:]
            except Exception as e:
                logger.error(f"Error applying rule {rule.name}: {str(e)}")
        
        # Return the redacted text and matches
        return {
            "redacted_text": redacted,
            "matches": matches
        }

# --------------------- FastAPI App ---------------------

# Create the FastAPI app
app = FastAPI(title="Rules Management API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create rule manager
rule_manager = RuleManager()

# Serve the HTML file
@app.get("/", response_class=HTMLResponse)
async def get_homepage():
    with open(project_dir / "rules_management.html", "r") as f:
        return f.read()

# --------------------- API Endpoints ---------------------

@app.get("/redact_rules")
async def get_rules():
    """Get all rules."""
    rules = rule_manager.get_all_rules()
    return {"rules": {id: rule.dict() for id, rule in rules.items()}}

@app.get("/get_rule")
async def get_rule(rule_id: str):
    """Get a specific rule by ID."""
    rule = rule_manager.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
    return {"rule": rule.dict()}

@app.post("/add_rule")
async def add_rule(request: Request):
    """Add a new rule."""
    try:
        data = await request.json()
        
        # Create rule from data
        rule = Rule(
            name=data.get("name"),
            description=data.get("description", ""),
            condition=data.get("condition"),
            action=data.get("action", "redact"),
            replacement=data.get("replacement", "<REDACTED>"),
            parameters=data.get("parameters", {}),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 50)
        )
        
        # Validate regex
        try:
            re.compile(rule.condition)
        except re.error as e:
            raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")
        
        # Add rule
        rule_id = rule_manager.add_rule(rule)
        rule = rule_manager.get_rule(rule_id)
        
        return {"rule_id": rule_id, "rule": rule.dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding rule: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adding rule: {str(e)}")

@app.post("/update_rule")
async def update_rule(request: Request):
    """Update an existing rule."""
    try:
        data = await request.json()
        rule_id = data.get("rule_id")
        
        if not rule_id:
            raise HTTPException(status_code=400, detail="rule_id is required")
        
        # Check if rule exists
        if not rule_manager.get_rule(rule_id):
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
        
        # Extract update fields
        update_fields = {}
        for field in ["name", "description", "condition", "action", "replacement", "parameters", "enabled", "priority"]:
            if field in data:
                update_fields[field] = data[field]
        
        # Validate regex if provided
        if "condition" in update_fields:
            try:
                re.compile(update_fields["condition"])
            except re.error as e:
                raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {str(e)}")
        
        # Update rule
        success = rule_manager.update_rule(rule_id, **update_fields)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update rule")
        
        # Get updated rule
        rule = rule_manager.get_rule(rule_id)
        
        return {"rule_id": rule_id, "rule": rule.dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rule: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating rule: {str(e)}")

@app.post("/delete_rule")
async def delete_rule(request: Request):
    """Delete a rule."""
    try:
        data = await request.json()
        rule_id = data.get("rule_id")
        
        if not rule_id:
            raise HTTPException(status_code=400, detail="rule_id is required")
        
        # Check if rule exists
        if not rule_manager.get_rule(rule_id):
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")
        
        # Delete rule
        success = rule_manager.delete_rule(rule_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete rule")
        
        return {"success": True, "rule_id": rule_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting rule: {str(e)}")

@app.post("/redact_text")
async def redact_text_endpoint(request: Request):
    """Redact text using the rules engine."""
    try:
        data = await request.json()
        text = data.get("text", "")
        
        result = rule_manager.redact_text(text)
        
        return result
    except Exception as e:
        logger.error(f"Error redacting text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error redacting text: {str(e)}")

# --------------------- Main ---------------------

def main():
    """Run the server."""
    try:
        # Run the server
        uvicorn.run(
            "rules_management_server:app",
            host="0.0.0.0",
            port=7890,
            reload=True
        )
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
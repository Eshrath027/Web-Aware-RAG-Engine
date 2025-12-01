#!/usr/bin/env python3
"""
Validate Semgrep findings using Claude AI to identify false positives.

This script reads a Semgrep JSON report, analyzes each finding by examining
the actual source code, and determines if findings are true or false positives.
"""

import json
import os
import sys
from pathlib import Path
from anthropic import Anthropic

def read_file_content(file_path: str, start_line: int = None, end_line: int = None) -> str:
    """Read file content, optionally limiting to specific line range."""
    try:
        with open(file_path, 'r') as f:
            if start_line and end_line:
                lines = f.readlines()
                # Get context around the finding (10 lines before and after)
                context_start = max(0, start_line - 11)
                context_end = min(len(lines), end_line + 10)
                return ''.join(lines[context_start:context_end])
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def validate_finding_with_claude(client: Anthropic, finding: dict, repo_root: str) -> dict:
    """Use Claude to validate a single Semgrep finding."""

    # Extract finding details
    path = finding.get('path', '')
    start_line = finding.get('start', {}).get('line')
    end_line = finding.get('end', {}).get('line')
    check_id = finding.get('check_id', '')
    message = finding.get('extra', {}).get('message', '')

    # Read the actual source code
    full_path = os.path.join(repo_root, path)
    code_content = read_file_content(full_path, start_line, end_line)

    # Prepare prompt for Claude
    prompt = f"""Analyze this Semgrep security finding and determine if it's a true positive or false positive.

**Finding Details:**
- Rule ID: {check_id}
- File: {path}
- Lines: {start_line}-{end_line}
- Message: {message}

**Source Code Context:**
```
{code_content}
```

**Full Finding Data:**
```json
{json.dumps(finding, indent=2)}
```

Please analyze:
1. Is this a TRUE POSITIVE (real security vulnerability) or FALSE POSITIVE (benign code)?
2. Provide a detailed reason explaining your determination

Consider:
- Whether user input is involved and properly validated
- If the vulnerability is actually exploitable
- Framework-specific protections
- Code context and data flow
- Whether the flagged code path is reachable

Respond in JSON format:
{{
  "is_false_positive": true/false,
  "validation_reason": "Detailed explanation here",
  "confidence": "high/medium/low"
}}
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse Claude's response
        response_text = response.content[0].text

        # Extract JSON from response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        validation_result = json.loads(response_text)

        # Add validation fields to the original finding
        finding['is_false_positive'] = validation_result.get('is_false_positive', False)
        finding['validation_reason'] = validation_result.get('validation_reason', '')
        finding['validation_confidence'] = validation_result.get('confidence', 'medium')

        return finding

    except Exception as e:
        print(f"Error validating finding: {str(e)}", file=sys.stderr)
        finding['is_false_positive'] = None
        finding['validation_reason'] = f"Error during validation: {str(e)}"
        finding['validation_confidence'] = 'low'
        return finding

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_semgrep_with_claude.py <semgrep_json_file> [output_file]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else f"{input_file}.validated.json"

    # Get API key from environment
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Initialize Anthropic client
    client = Anthropic(api_key=api_key)

    # Read Semgrep findings
    try:
        with open(input_file, 'r') as f:
            semgrep_data = json.load(f)
    except Exception as e:
        print(f"Error reading {input_file}: {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Get repository root (assuming script is in repo root)
    repo_root = os.path.dirname(os.path.abspath(input_file))

    # Process each finding
    results = semgrep_data.get('results', [])
    total = len(results)

    print(f"Validating {total} Semgrep findings...")

    for idx, finding in enumerate(results, 1):
        print(f"Processing finding {idx}/{total}: {finding.get('check_id', 'unknown')}")
        results[idx - 1] = validate_finding_with_claude(client, finding, repo_root)

    # Update the results
    semgrep_data['results'] = results

    # Add validation metadata
    semgrep_data['validation_metadata'] = {
        'validator': 'claude-ai',
        'model': 'claude-sonnet-4-5',
        'total_findings': total,
        'false_positives': sum(1 for r in results if r.get('is_false_positive') == True),
        'true_positives': sum(1 for r in results if r.get('is_false_positive') == False)
    }

    # Write validated results
    with open(output_file, 'w') as f:
        json.dump(semgrep_data, f, indent=2)

    print(f"\nValidation complete!")
    print(f"Total findings: {total}")
    print(f"False positives: {semgrep_data['validation_metadata']['false_positives']}")
    print(f"True positives: {semgrep_data['validation_metadata']['true_positives']}")
    print(f"\nValidated results saved to: {output_file}")

if __name__ == "__main__":
    main()

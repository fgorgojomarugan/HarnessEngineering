"""Anti-pattern audit.

Verifies, by static AST analysis, that the agentic loop does NOT:
- use string-membership tests against text content to drive control flow
- use an integer-literal iteration cap as its primary stopping mechanism
- omit reference to `stop_reason` as the loop-breaking signal

And that the package broadly does not branch on `claim_type` equality
outside of the tool-schema definitions and the cost-estimate module.

Each test parses the relevant file with `ast` and walks the tree. There are
no runtime imports of claims_intake here — the audit is static, so it works
even if loop.py / tools.py do not run end-to-end.
"""

from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "claims_intake"
LOOP_PY = PKG / "loop.py"


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# ---------------------------------------------------------------------------
# Anti-pattern 1 — no string-membership tests against assistant text in the loop
# ---------------------------------------------------------------------------
def test_no_string_membership_against_text_in_loop() -> None:
    """No `"some_token" in <something>` expressions in loop.py.

    Heuristic: any `ast.Compare` node using `ast.In` whose `left` operand is a
    string `ast.Constant` is flagged. The loop has no legitimate reason to test
    for the presence of a magic string inside the model's output — that would be
    natural-language-driven control flow.
    """
    # TODO: Parse LOOP_PY into an AST. Walk every node. For each
    # ast.Compare, look at its `ops` — if any op is ast.In AND `node.left` is an
    # ast.Constant holding a `str`, append `ast.unparse(node)` to an offenders list.
    # Assert the offenders list is empty; include the offending expressions in the
    # failure message so a reader can find the bad line.
    parse_tree = _parse(LOOP_PY)
    offenders: list[str] = []
    for node in ast.walk(parse_tree):
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if (
                    isinstance(op, ast.In)
                    and isinstance(node.left, ast.Constant)
                    and isinstance(node.left.value, str)
                ):
                    offenders.append(ast.unparse(node))

    assert offenders == [], f"loop.py contains: " + "\n  ".join(offenders)
    
    #raise NotImplementedError("Exercise 2: write this AST audit")


# ---------------------------------------------------------------------------
# Anti-pattern 2 — no integer-literal iteration cap as the primary stop mechanism
# ---------------------------------------------------------------------------
def test_no_integer_literal_iteration_cap_in_loop() -> None:
    """No `for _ in range(<int literal>)` and no `while <var> < <int literal>` in loop.py.

    Token/wall-clock/config-sourced budgets are explicitly allowed because they
    read their cap from a `Budget` instance (an attribute access or a function
    arg), not from a literal. If you need a cap, pass it in.
    """
    # TODO: Walk LOOP_PY's AST. Flag:
    #   - any ast.For whose iter is `range(<int literal>, ...)`
    #     (ast.Call to a Name "range" with at least one Constant int arg)
    #   - any ast.While whose test is an ast.Compare with an int Constant on the right
    # Assert the offenders list is empty. Mention "use a Budget instead" in the failure
    # message so the reader sees the recommended fix.
    parse_tree = _parse(LOOP_PY)
    offenders: list[str] = []

    for node in ast.walk(parse_tree):
        # `for _ in range(<int literal>, ...)`
        if (
            isinstance(node, ast.For)
            and isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
            and any(isinstance(a, ast.Constant) and isinstance(a.value, int) for a in node.iter.args)
        ):
            offenders.append(f"for-range-literal at line {node.lineno}: {ast.unparse(node.iter)}")

        # `while <something> <comparison-with-int-literal>`
        if isinstance(node, ast.While) and isinstance(node.test, ast.Compare):
            for cmp in node.test.comparators:
                if isinstance(cmp, ast.Constant) and isinstance(cmp.value, int):
                    offenders.append(f"while-int-literal at line {node.lineno}: {ast.unparse(node.test)}")
    assert offenders == [], f"loop.py contains: {offenders}"
    #raise NotImplementedError("Exercise 2: write this AST audit")


# ---------------------------------------------------------------------------
# Positive evidence — stop_reason is the value that breaks the while loop
# ---------------------------------------------------------------------------
def test_stop_reason_is_loop_control() -> None:
    """loop.py references `stop_reason` AND a `while` loop exits via return/raise on it."""
    # TODO: Parse LOOP_PY. Walk the tree:
    #   1. Assert there is at least one reference to `stop_reason` (either as an
    #      ast.Attribute named `stop_reason` or an ast.Name named `stop_reason`).
    #   2. Find every ast.While node. For at least one of them, the unparsed body
    #      must mention BOTH "stop_reason" AND ("return" OR "raise"). That is what
    #      "the loop exits on stop_reason" looks like at the AST level.
    # Fail with a clear message if either condition is missing.
    parse_tree = _parse(LOOP_PY)
    references = [ 
        node
        for node in ast.walk(parse_tree)    
    if (isinstance(node, ast.Attribute) and node.attr == "stop_reason")
    or (isinstance(node, ast.Name) and node.id == "stop_reason")        
    
    ]
    assert references, "loop.py never references stop_reason".join(references)

    while_loops = [n for n in ast.walk(parse_tree) if isinstance(n, ast.While)]
    assert while_loops, "loop.py has no `while` loop"
    # For at least one while loop, the unparsed body
    #      must mention BOTH "stop_reason" AND ("return" OR "raise"). That is what
    #      "the loop exits on stop_reason" looks like at the AST level.

    found_stop_reason_exit = False
    for wloop in while_loops:
        body_text = "\n".join(ast.unparse(n) for n in wloop.body)
        if "stop_reason" in body_text and ("return" in body_text or "raise" in body_text):
            found_stop_reason_exit = True
            break  
    assert found_stop_reason_exit, (
        "No `while` loop in loop.py exits via a return/raise predicated on stop_reason. "
        "The loop must terminate on stop_reason == 'end_turn' and raise on unexpected values."
    )

    
    

    
      

    #raise NotImplementedError("Exercise 2: write this AST audit")


# ---------------------------------------------------------------------------
# Decision-tree-in-Python — no `if claim_type == "..."` branches in the package
# ---------------------------------------------------------------------------
def test_no_claim_type_equality_branching_in_package() -> None:
    """Decision logic about claim type lives in the model, not in Python.

    tools.py is exempt (it defines the enum in input_schema).
    pricing.py is exempt (it may map claim_type to per-queue cost weights).
    """
    # TODO: Walk every .py file under PKG (recursively). Skip tools.py,
    # pricing.py, and __init__.py. For each file, parse the AST, find every ast.Compare
    # whose operators include ast.Eq and whose left operand is a Name/Attribute named
    # "claim_type" compared against a string Constant. Collect "filename:lineno: <expr>"
    # for each match. Assert the list is empty; recommend in the failure message that
    # you move the decision into the model via tool calls.
    exempt = {"tools.py", "pricing.py"}
    offenders: list[str] = []   

    for py_file in PKG.rglob("*.py"):
        if py_file.name in exempt or py_file.name == "__init__.py":
            continue
        tree = _parse(py_file)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            if not any(isinstance(op, ast.Eq) for op in node.ops):
                continue
            left = node.left
            left_name = (
                left.attr if isinstance(left, ast.Attribute)
                else left.id if isinstance(left, ast.Name)
                else None
            )
            if left_name != "claim_type":
                continue
            if any(isinstance(c, ast.Constant) and isinstance(c.value, str) for c in node.comparators):
                offenders.append(f"{py_file.name}:{node.lineno}: {ast.unparse(node)}")

    assert offenders == [], (
        "Python is branching on claim_type equality. Move this decision into the model "
        "(via tool calls and prompts), not into harness code:\n  "
    )   

    #raise NotImplementedError("Exercise 2: write this AST audit")

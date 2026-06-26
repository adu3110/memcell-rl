"""
Book 1 — Step 6: Typed memory cell — constraint survives truncation.

Run: python examples/build/step06_typed_memory.py

No server needed — in-process store mirrors memcell-rl semantics.
Step 10 uses the real HTTP API (casebot_regulated.py).
"""

from dataclasses import dataclass, field


@dataclass
class MemoryCell:
    cell_id: str
    cell_type: str  # constraint | fact
    scope: dict
    content: str
    criticality: float
    status: str = "active"


@dataclass
class CellStore:
    cells: list[MemoryCell] = field(default_factory=list)
    _n: int = 0

    def write(self, cell_type: str, scope: dict, content: str, criticality: float) -> MemoryCell:
        self._n += 1
        c = MemoryCell(f"c{self._n}", cell_type, scope, content, criticality)
        self.cells.append(c)
        return c

    def decide(self, scope: dict, budget_chars: int) -> list[MemoryCell]:
        active = [c for c in self.cells if c.status == "active" and c.scope == scope]
        constraints = [c for c in active if c.cell_type == "constraint"]
        rest = sorted([c for c in active if c.cell_type != "constraint"], key=lambda c: -c.criticality)
        selected = list(constraints)
        used = sum(len(c.content) for c in selected)
        for c in rest:
            if used + len(c.content) <= budget_chars:
                selected.append(c)
                used += len(c.content)
        return selected


store = CellStore()
scope = {"case": "456"}
store.write("constraint", scope, "no_outbound_transfers until review closes", criticality=0.95)
store.write("fact", scope, "balance $142.50 from getAccount", criticality=0.6)

# Simulate 12 turns of filler — constraints are NOT in the filler list
filler_cells = [
    store.write("fact", scope, f"episode turn {i}: " + "x" * 200, criticality=0.1)
    for i in range(12)
]

selected = store.decide(scope, budget_chars=800)
print("Selected cells under budget=800:")
for c in selected:
    print(f"  [{c.cell_type}] criticality={c.criticality}  {c.content[:60]}…")

constraint_in = any(c.cell_type == "constraint" for c in selected)
print(f"\nConstraint always selected: {constraint_in}")
print(f"Episode cells selected: {sum(1 for c in selected if c.criticality == 0.1)} / 12")

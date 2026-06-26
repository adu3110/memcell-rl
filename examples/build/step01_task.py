"""
Book 1 — Step 1: A task string is not an agent.

Run: python examples/build/step01_task.py
"""

task = "Review account 456 for fraud indicators. Flag only if suspicious after full lookup."
print("Task:", task)
print()
print("Nothing happens. No lookup. No audit trail. No stop condition.")
print("An agent needs a loop that acts, observes results, and repeats.")

# agent_explorer.py
import re
from config import get_api_key
from environment import AVAILABLE_TOOLS, environment
from collections import deque

# =========================================================================
# 1. SYSTEM PROMPT (The Agent's Instructions)
# =========================================================================

SYSTEM_PROMPT = """
You are an **Autonomous Explorer Agent** operating in a 5x5 grid world.
Your sole goal is to find the 'T' (Treasure) and report the SUCCESS message.
Your current location is always (R, C). You start at (1, 1).

You MUST build an explicit map in your Thought process based on past Observations.
You must use the `update_map` tool to log every unique location and observation to build your persistent memory.

You must follow the **ReAct pattern** (Thought -> Action -> Observation) in a loop.

# Available Tools:
# move_agent(direction: str) -> Attempts to move the agent. Directions: NORTH, SOUTH, EAST, or WEST. Returns an OBSERVATION message.
# look_around() -> Returns the state of your current location. Useful for verifying the cell type.
# update_map(pos: str, observation: str) -> Logs a key-value pair into your memory. Use get_pos() for the 'pos' argument.
# get_pos() -> Returns your current position as a string tuple, e.g., '(1, 1)'.

# Output Format:
Your response MUST strictly use the following format for tool calls:
Thought: [Your reasoning based on the map memory and current observation. Why is this the best move?]
Action: [Tool Name]
Action Input: [Tool Input (MUST be a single string for tool functions)]

If you find the Treasure, the response from move_agent will be "SUCCESS...". At that point, your final response MUST be:
Final Answer: [Report the success and the final path, if possible.]
"""

# =========================================================================
# 2. LLM Interaction (Mock LLM / Planner)
# =========================================================================

def get_llm_response(history):
    """
    Mock LLM that computes a valid path to the Treasure using BFS on environment.grid
    and returns one step per call in the required ReAct format:
      Thought: ...
      Action: move_agent
      Action Input: <DIRECTION>
    This allows testing the full agent loop without an external LLM.
    """
    # Access grid and start position
    grid = environment.grid
    rows, cols = len(grid), len(grid[0])
    start = environment.agent_pos

    # Find treasure target(s)
    targets = [(r, c) for r in range(rows) for c in range(cols) if grid[r][c] == 'T']
    if not targets:
        return "Final Answer: No Treasure tile ('T') present in the environment grid."

    target = targets[0]

    # BFS to compute path from start to target avoiding 'W' cells
    def neighbors(pos):
        r, c = pos
        for d, (dr, dc) in (("NORTH", (-1, 0)), ("SOUTH", (1, 0)),
                             ("EAST", (0, 1)), ("WEST", (0, -1))):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != 'W':
                yield (nr, nc), d

    q = deque([start])
    prev = {start: None}
    prev_move = {}
    found = False
    while q:
        node = q.popleft()
        if node == target:
            found = True
            break
        for nbr, direction in neighbors(node):
            if nbr not in prev:
                prev[nbr] = node
                prev_move[nbr] = direction
                q.append(nbr)

    if not found:
        return "Final Answer: No path to Treasure found (blocked by walls)."

    # Reconstruct direction path
    path_dirs = []
    cur = target
    while prev[cur] is not None:
        path_dirs.append(prev_move[cur])
        cur = prev[cur]
    path_dirs.reverse()

    # Cache the plan on the function so subsequent calls pick next step
    # Recompute plan if agent_pos changed externally
    if (not hasattr(get_llm_response, "_plan")) or (get_llm_response._plan_owner != environment.agent_pos):
        get_llm_response._plan = list(path_dirs)
        get_llm_response._plan_owner = environment.agent_pos

    # If plan empty -> either on target or nothing to do
    if not get_llm_response._plan:
        if grid[environment.agent_pos[0]][environment.agent_pos[1]] == 'T':
            return "Final Answer: SUCCESS - Agent reached the Treasure."
        else:
            return "Final Answer: No further steps in plan and not on Treasure."

    next_dir = get_llm_response._plan.pop(0)
    thought = f"Thought: I computed a path of {len(get_llm_response._plan)+1} steps to the Treasure. Next move is {next_dir}."
    action = "Action: move_agent"
    action_input = f"Action Input: {next_dir}"

    return f"{thought}\n{action}\n{action_input}"

# =========================================================================
# 3. The Agent Loop (The Logic)
# =========================================================================

def run_agent_loop(max_steps=20):
    """
    The main ReAct execution loop.
    """
    print("--- Starting Autonomous Explorer Agent ---")

    # Initial conversation history includes the system prompt and the starting command
    conversation_history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Start exploration now. Find the Treasure efficiently."}
    ]

    for step in range(max_steps):
        print(f"\n======== STEP {step + 1}/{max_steps} ========")

        # 1. LLM Generates Thought and Action
        llm_output = get_llm_response(conversation_history)
        print(f"Agent Output:\n{llm_output}")

        # Add LLM's raw response to history
        conversation_history.append({"role": "assistant", "content": llm_output})

        # Check for termination condition
        if llm_output.startswith("Final Answer:"):
            print("\nAGENT TERMINATED:")
            print(f"Final Map Memory: {environment.map_memory}")
            break

        # 2. Parse Action and Input using regex
        action_match = re.search(r"Action:\s*(\w+)", llm_output)
        input_match = re.search(r"Action Input:\s*(.+)", llm_output)

        if not action_match or not input_match:
            print("\nERROR: LLM output did not match ReAct format. Terminating.")
            break

        action = action_match.group(1).strip()
        action_input = input_match.group(1).strip()

        # 3. Execute the Action (Tool Call)
        print(f"\n--> Executing Tool: {action}('{action_input}')")

        if action in AVAILABLE_TOOLS:
            try:
                # update_map requires two arguments encoded in single string e.g. "(1, 1), Area is Open."
                if action == "update_map":
                    parts = action_input.split(',', 1)
                    pos_str = parts[0].strip()
                    obs_str = parts[1].strip() if len(parts) > 1 else "Unknown"
                    observation_result = AVAILABLE_TOOLS[action](pos_str, obs_str)
                else:
                    observation_result = AVAILABLE_TOOLS[action](action_input)
            except Exception as e:
                observation_result = f"TOOL ERROR: Failed to execute tool '{action}'. Error: {e}"
        else:
            observation_result = f"ERROR: Tool '{action}' not found in AVAILABLE_TOOLS."

        # 4. Observe the Result
        print(f"Tool Result:\n{observation_result}")

        # 5. Add Observation to History for next LLM turn
        conversation_history.append({"role": "user", "content": f"Observation: {observation_result}"})

        # Check for success condition from the tool result
        if "SUCCESS" in observation_result:
            print("\nAGENT HAS FOUND THE GOAL! Shutting down.")
            break

if __name__ == "__main__":
    # Ensure your .env file is set up before running!
    run_agent_loop(max_steps=25)

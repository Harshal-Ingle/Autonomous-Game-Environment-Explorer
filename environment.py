# environment.py

class SimpleEnvironment:
    def __init__(self):
        # 5x5 Grid: 0=Open, 'W'=Wall, 'T'=Treasure/Goal
        self.grid = [
            ['W', 'W', 'W', 'W', 'W'],
            ['W', 0, 0, 'W', 'W'],
            ['W', 0, 'W', 0, 'T'],
            ['W', 0, 0, 0, 'W'],
            ['W', 'W', 'W', 'W', 'W'],
        ]
        self.agent_pos = (1, 1)  # (row, col) - Starting point
        self.map_memory = {}     # Agent's internal map/memory (Key: "(r, c)", Value: "Observation")

    def get_pos(self):
        """Tool: Returns the agent's current position as a string tuple."""
        return str(self.agent_pos)

    def update_map(self, pos: str, observation: str):
        """Tool: Explicitly stores observation in the agent's memory."""
        self.map_memory[pos] = observation
        return f"OBSERVATION: Map memory updated for location {pos}."

    def look_around(self):
        """Tool: Describes the current cell's state."""
        r, c = self.agent_pos
        current_cell = self.grid[r][c]

        if current_cell == 'T':
            return "SUCCESS: You are standing on the Treasure tile!"

        return f"OBSERVATION: You are at {r, c}. This area is Open."

    def move_agent(self, direction: str):
        """Tool: Attempts to move the agent and returns a status observation."""
        r, c = self.agent_pos
        new_r, new_c = r, c

        direction = direction.upper()

        if direction == 'NORTH': new_r -= 1
        elif direction == 'SOUTH': new_r += 1
        elif direction == 'EAST': new_c += 1
        elif direction == 'WEST': new_c -= 1
        else:
            return "ERROR: Invalid direction. Use NORTH, SOUTH, EAST, or WEST."

        # Check grid boundaries and walls
        if (0 <= new_r < len(self.grid) and
            0 <= new_c < len(self.grid[0]) and
            self.grid[new_r][new_c] != 'W'):

            # Successful move
            self.agent_pos = (new_r, new_c)

            if self.grid[new_r][new_c] == 'T':
                return "SUCCESS: GOAL FOUND. You have reached the Treasure!"
            else:
                return f"OBSERVATION: Moved successfully. New position: {self.agent_pos}. Area is Open."
        else:
            return "OBSERVATION: Movement blocked by a Wall or grid boundary. Position remains unchanged."

# Initialize the environment and the tools dictionary
environment = SimpleEnvironment()
AVAILABLE_TOOLS = {
    "move_agent": environment.move_agent,
    "look_around": environment.look_around,
    "update_map": environment.update_map,
    "get_pos": environment.get_pos
}

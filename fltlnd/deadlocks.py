from flatland.envs.agent_utils import RailAgentStatus


class DeadlocksDetector:
    """
    Class containing code to track deadlocks during an episode.
    """

    def __init__(self):
        self.directions = [
            # North
            (-1, 0),
            # East
            (0, 1),
            # South
            (1, 0),
            # West
            (0, -1)]

        self.deadlocks = []

    def reset(self, num_agents):
        """
        Reset deadlock counters.
        :param num_agents:
        :return:
        """
        self.deadlocks = [False for _ in range(num_agents)]

    def step(self, env):
        """
        Check for new deadlocks, updates counter and returns it.
        :param env: The environment
        :return: the updated deadlocks
        """
        agents = []
        for a in range(env.get_num_agents()):
            if env.agents[a].status == RailAgentStatus.ACTIVE:
                agents.append(a)
                if not self.deadlocks[a]:
                    self.deadlocks[a] = self._check_deadlocks(agents, self.deadlocks, env)
                if not (self.deadlocks[a]):
                    del agents[-1]
            else:
                self.deadlocks[a] = False

        return self.deadlocks

    def _check_feasible_transitions(self, pos_a1, transitions, env):
        """
        Function used to collect chains of blocked agents.
        :param pos_a1: position of a1
        :param transitions: the transition map
        :param env: the railway
        :return: the agent a2 blocking a1 or None if not present
        """
        for direction, values in enumerate(self.directions):
            if transitions[direction] == 1:
                position_check = (pos_a1[0] + values[0], pos_a1[1] + values[1])
                if not (env.cell_free(position_check)):
                    for a2 in range(env.get_num_agents()):
                        if env.agents[a2].position == position_check:
                            return a2

        return None

    def _check_next_pos(self, a1, env):
        """
        Check the next pos and the possible transitions of an agent to find deadlocks.
        :param a1: agent
        :param env: railway
        :return:
        """
        pos_a1 = env.agents[a1].position
        dir_a1 = env.agents[a1].direction

        if env.rail.get_transitions(pos_a1[0], pos_a1[1], dir_a1)[dir_a1] == 1:
            position_check = (pos_a1[0] + self.directions[dir_a1][0], pos_a1[1] + self.directions[dir_a1][1])
            if not (env.cell_free(position_check)):
                for a2 in range(env.get_num_agents()):
                    if env.agents[a2].position == position_check:
                        return a2
        else:
            return self._check_feasible_transitions(pos_a1, env.rail.get_transitions(pos_a1[0], pos_a1[1], dir_a1), env)

    def _check_deadlocks(self, a1, deadlocks, env):
        """
        Recursive procedure to find out whether agents in a1 are in a deadlock.
        :param a1: agents to check
        :param deadlocks: current collections of deadlocked agents
        :param env: railway
        :return: True if a1 is in a deadlock
        """
        a2 = self._check_next_pos(a1[-1], env)

        # No agents in front
        if a2 is None:
            return False
        # Deadlocked agent in front or loop chain found
        if deadlocks[a2] or a2 in a1:
            return True

        # Investigate further
        a1.append(a2)
        deadlocks[a2] = self._check_deadlocks(a1, deadlocks, env)

        # If the agent a2 is in deadlock also a1 is
        if deadlocks[a2]:
            return True

        # Back to previous recursive call
        del a1[-1]
        return False

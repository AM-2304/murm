import json
from pathlib import Path

from murm.agents.model import AgentProfile, AgentState, OpinionBias
from murm.llm.provider import LLMProvider

class AgentInterviewer:
    """
    Loads saved agents from a simulation run and allows post-simulation interviews.
    This creates the capability to ask an agent 'why did you change your mind?'
    after the simulation is finished.
    """

    def __init__(self, run_dir: Path, llm: LLMProvider):
        self._run_dir = run_dir
        self._llm = llm
        self._agents: dict[str, dict] = {}
        self._load_agents()

    def _load_agents(self):
        agents_path = self._run_dir / "agents.json"
        if not agents_path.exists():
            raise FileNotFoundError(f"agents.json not found in {self._run_dir}. Did the simulation finish saving?")
        
        with open(agents_path, "r") as f:
            data = json.load(f)
            
        for d in data:
            self._agents[d["agent_id"]] = d

    def list_agents(self) -> list[dict]:
        return [
            {
                "agent_id": a["agent_id"],
                "name": a["name"],
                "occupation": a["occupation"],
                "final_opinion": a.get("final_state", {}).get("current_opinion", "unknown"),
                "posts_made": a.get("final_state", {}).get("posts_made", 0)
            }
            for a in self._agents.values()
        ]

    async def interview_agent(self, agent_id: str, question: str) -> str:
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not found in this run.")
            
        agent_data = self._agents[agent_id]
        
        # We parse it into an AgentProfile just to use its prompt building logic
        profile = AgentProfile.from_dict(agent_data)
        
        final_state_data = agent_data.get("final_state", {})
        opinion_history = "\n".join(final_state_data.get("opinion_history", []))
        if not opinion_history:
            opinion_history = "No opinion shifts occurred."

        system_prompt = (
            "You are a simulated persona who just participated in a multi-round debate. "
            "An analyst is now interviewing you about your experience and the opinions you formed.\n\n"
            "Here is your profile:\n"
            f"{profile.to_prompt_context()}\n\n"
            "Here is your opinion shift history during the simulation:\n"
            f"{opinion_history}\n\n"
            "Stay completely in character. Answer the analyst's question based ONLY on your persona "
            "and what you would realistically think. Be direct, natural, and do not break character."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        # We don't force JSON here, just plain text response
        try:
            response = await self._llm.complete(messages, temperature=0.7, max_tokens=300)
            return response.strip()
        except Exception as e:
            return f"[Failed to interview agent: {e}]"

// Agent HQ layout + teams. Agent ids must match what the scheduled agents write into data/<team>/state.json.
// kind = what clicking that robot opens: brief | research | ideas | stats
window.HQ_CONFIG = {
  repo: "omarjaradat2006-sudo/agent-hq",
  teams: [
    { id: "tiktok", name: "TikTok", color: "#ff4d79", grid: [0, 0], tagline: "Trends, hooks and scripts for your main page", ideaWord: "Scripts",
      agents: [
        { id: "analyst", name: "Analyst", role: "Finds outlier videos", kind: "research" },
        { id: "strategist", name: "Strategist", role: "Picks what to film next", kind: "ideas" },
        { id: "copywriter", name: "Copywriter", role: "Hooks and full scripts", kind: "ideas" },
        { id: "collector", name: "Data Collector", role: "Pulls your stats hourly", kind: "stats" } ] },
    { id: "youtube", name: "YouTube", color: "#ff8a3d", grid: [1, 0], tagline: "Bounce Theory and Ambient Escape", ideaWord: "Video ideas",
      agents: [
        { id: "lead", name: "Channel Lead", role: "Runs both channels", kind: "brief" },
        { id: "analyst", name: "Analyst", role: "Niche and competitor outliers", kind: "research" },
        { id: "strategist", name: "Strategist", role: "Topics and titles", kind: "ideas" },
        { id: "producer", name: "Producer", role: "Formats for your pipelines", kind: "ideas" },
        { id: "collector", name: "Data Collector", role: "Pulls channel stats hourly", kind: "stats" } ] },
    { id: "linkedai", name: "LinkedAI", color: "#4da3ff", grid: [2, 0], tagline: "LinkedIn tools market and promo content", ideaWord: "Content",
      agents: [
        { id: "lead", name: "Product Lead", role: "Weekly read on the market", kind: "brief" },
        { id: "watch", name: "Competitor Watch", role: "Extensions, pricing, reviews", kind: "research" },
        { id: "copywriter", name: "Copywriter", role: "Promo scripts and posts", kind: "ideas" } ] },
    { id: "growth", name: "Growth Architect", color: "#3ddc97", grid: [0, 1], tagline: "AI marketing tools market and promo content", ideaWord: "Content",
      agents: [
        { id: "lead", name: "Product Lead", role: "Weekly read on the market", kind: "brief" },
        { id: "watch", name: "Competitor Watch", role: "Positioning and pricing", kind: "research" },
        { id: "copywriter", name: "Copywriter", role: "Promo scripts and posts", kind: "ideas" } ] },
    { id: "opps", name: "AI Opportunities", color: "#ffd23d", grid: [1, 1], tagline: "New ways to make money with AI", ideaWord: "Opportunities",
      agents: [
        { id: "lead", name: "Venture Lead", role: "Picks the best bets", kind: "brief" },
        { id: "scout", name: "Scout", role: "Finds opportunities", kind: "research" },
        { id: "planner", name: "Planner", role: "How-to, hours, cost", kind: "ideas" } ] },
    { id: "hq", name: "Chief of Staff", color: "#a37bff", grid: [2, 1], tagline: "Your daily brief across every team", virtual: true,
      agents: [ { id: "chief", name: "Chief of Staff", role: "Daily brief at noon", kind: "brief" } ] }
  ]
};

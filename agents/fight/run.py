"""Fight & Court Intelligence. Usage:
  python3 agents/fight/run.py picks nba [--force]   daily NBA card: 3 parlays (+100 / +500 / +1000)
  python3 agents/fight/run.py picks ufc [--force]   Friday UFC card: event check, 3 parlays, underdog picks
  python3 agents/fight/run.py grade                 grade finished bets, update the record
  python3 agents/fight/run.py check                 test the Odds API key (free call), show credits and markets
  python3 agents/fight/run.py report                rebuild state.json from the ledger (no API calls)
Research and recommendations only: it never places bets and never logs into a sportsbook."""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import odds as O
import store as S

AGENT_FOR = {"check": "odds", "picks": None, "grade": "grader", "report": "lead"}
NAME = {"court": "Court Analyst", "fight": "Fight Analyst", "odds": "Odds Scout", "grader": "Results Grader", "lead": "Desk Lead"}


def main(argv):
    job = argv[0] if argv else "report"
    sport = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else None
    aid = AGENT_FOR.get(job) or ("court" if sport == "nba" else "fight")
    try:
        if job == "picks":
            import cards
            (cards.run_nba if sport == "nba" else cards.run_ufc)(force="--force" in argv)
        elif job == "grade":
            import grade; grade.run()
        elif job == "check":
            sports = {x["key"] for x in O.fetch_sports()}
            c = O.credits()
            print("Odds API key works. NBA:", "basketball_nba" in sports, "| UFC/MMA:", "mma_mixed_martial_arts" in sports,
                  "| credits left this month:", c.get("remaining"))
            print("Books: FanDuel + DraftKings only | Bet365: excluded | NBA games with props today (budget):", O.daily_prop_budget())
        else:
            import report; report.refresh(S.state(), S.ledger())
        return 0
    except O.NoKey as e:
        st = S.state()
        S.agent(st, aid, "waiting", "Waiting for Omar's free Odds API key (run scripts/server/setup_fight.sh)")
        S.log(st, NAME[aid], str(e))
        import report; report.refresh(st, S.ledger())
        print(e)
        return 0
    except O.LowCredits as e:
        st = S.state()
        S.agent(st, aid, "waiting", str(e)[:150])
        S.log(st, NAME[aid], str(e))
        import report; report.refresh(st, S.ledger())
        print(e)
        return 0
    except Exception as e:
        traceback.print_exc()
        st = S.state()
        S.agent(st, aid, "error", f"{job} failed: {str(e)[:110]}")
        S.log(st, NAME[aid], f"{job} {sport or ''} failed: {str(e)[:180]}")
        import report; report.refresh(st, S.ledger())
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

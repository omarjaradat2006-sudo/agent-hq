"""Fight & Court Intelligence. Usage:
  python3 agents/fight/run.py picks nba|ufc [--force]   daily card (singles, parlays, underdogs, or no bet)
  python3 agents/fight/run.py close nba|ufc             closing prices for picks about to start
  python3 agents/fight/run.py grade                     settle finished picks, update the record
  python3 agents/fight/run.py books                     weekly Ontario licence check
  python3 agents/fight/run.py check                     test the Odds API key (free call) and show credits left
  python3 agents/fight/run.py report                    rebuild state.json from the ledger (no API calls)
Research and recommendations only: it never places bets and never logs into a sportsbook."""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import odds as O
import store as S

AGENT_FOR = {"check": "odds", "picks": None, "close": "odds", "grade": "grader", "books": "odds", "report": "lead"}
NAME = {"court": "Court Analyst", "fight": "Fight Analyst", "odds": "Odds Scout", "grader": "Results Grader", "lead": "Desk Lead"}


def main(argv):
    job = argv[0] if argv else "report"
    sport = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else None
    aid = AGENT_FOR.get(job) or ("court" if sport == "nba" else "fight")
    try:
        if job == "picks":
            import picks; picks.run(sport, force="--force" in argv)
        elif job == "close":
            import close; close.run(sport)
        elif job == "grade":
            import grade; grade.run()
        elif job == "check":
            sports = {x["key"] for x in O._get("sports", {}, 0, "sports list (free)", min_left=0)}
            c = O.credits()
            print("Odds API key works.", "NBA:", "basketball_nba" in sports, "| MMA/UFC:", "mma_mixed_martial_arts" in sports,
                  "| credits left this month:", c.get("remaining"), "of 500 (free plan)")
            print("Ontario books in use:", ", ".join(b["name"] for b in O.active_books().values()), "| Bet365: excluded")
        elif job == "books":
            import books; books.run()
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

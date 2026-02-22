import uuid
import json
from colorama import Fore, Back, Style, init

init(autoreset=True)


# ─── Print helpers ────────────────────────────────────────

def _divider(char: str = "═", width: int = 64):
    print(Fore.WHITE + Style.DIM + char * width + Style.RESET_ALL)


def _header(title: str, color=Fore.CYAN):
    _divider()
    print(color + Style.BRIGHT + f"  {title}" + Style.RESET_ALL)
    _divider()


def _state_box(ctx_dict: dict):
    state = ctx_dict.get("state", "unknown").upper().replace("_", " ")
    data  = ctx_dict.get("data", {})

    print(Fore.CYAN + f"\n  ╔══ STATE: {state}" + Style.RESET_ALL)

    if data:
        for key, val in data.items():
            val_str = json.dumps(val, ensure_ascii=False) if isinstance(val, (list, dict)) else str(val)
            is_filled = val is not None and val != [] and val != ""
            val_color = Fore.GREEN if is_filled else Fore.RED + Style.DIM
            print(
                Fore.CYAN + "  ║  " +
                Fore.WHITE + Style.DIM + f"{key:<20}" +
                Style.RESET_ALL + " → " +
                val_color + val_str +
                Style.RESET_ALL
            )

    print(Fore.CYAN + "  ╚" + "═" * 50 + Style.RESET_ALL)


# ─── Single scenario runner ────────────────────────────────

def run_scenario(scenario, agent) -> dict:
    """
    Runs one scenario end to end.
    Returns a result dict: {scenario, turns, final_state, created_reservation_ids, error}
    """
    from app.memory.session_memory import memory

    session_id = str(uuid.uuid4())
    memory.init(session_id)

    print()
    _header(f"SCENARIO [{scenario.name}]", Fore.BLUE)
    print(Fore.WHITE + Style.DIM + f"  {scenario.description}" + Style.RESET_ALL)
    print()

    result = {
        "scenario":                scenario.name,
        "turns":                   [],
        "final_state":             None,
        "created_reservation_ids": [],
        "error":                   None,
    }

    try:
        for i, user_msg in enumerate(scenario.turns, 1):

            # ── Print user line ────────────────────────────
            print(
                Fore.GREEN + Style.BRIGHT + f"  [{i}] USER: " +
                Fore.GREEN + user_msg + Style.RESET_ALL
            )

            # ── Collect full agent response ────────────────
            response_text = ""
            try:
                for chunk in agent.respond_stream(session_id, user_msg):
                    response_text += chunk
            except Exception as e:
                response_text = f"[STREAM ERROR: {e}]"

            print(
                Fore.YELLOW + Style.BRIGHT + "       ANA: " +
                Fore.YELLOW + response_text.strip() + Style.RESET_ALL
            )

            # ── Show state ─────────────────────────────────
            ctx     = memory.get_context(session_id)
            ctx_dict = ctx.to_dict()
            _state_box(ctx_dict)

            # ── Track created reservations for cleanup ─────
            if ctx_dict.get("state") == "booking_complete":
                rid = ctx_dict.get("data", {}).get("reservation_id")
                if rid and rid not in result["created_reservation_ids"]:
                    result["created_reservation_ids"].append(rid)

            result["turns"].append({
                "user":  user_msg,
                "agent": response_text.strip(),
                "state": ctx_dict,
            })

            print()  # spacing

        result["final_state"] = memory.get_context(session_id).to_dict()

        print(Fore.GREEN + Style.BRIGHT + "  ✓  Scenario completed" + Style.RESET_ALL)

        if result["created_reservation_ids"]:
            print(
                Fore.MAGENTA + "  ⚠  Reservations written to reservations.json: " +
                str(result["created_reservation_ids"]) + Style.RESET_ALL
            )

    except Exception as e:
        result["error"] = str(e)
        print(Fore.RED + Style.BRIGHT + f"  ✗  Scenario crashed: {e}" + Style.RESET_ALL)

    return result


# ─── Run all scenarios ─────────────────────────────────────

def run_all_scenarios(scenarios: list, cleanup_after: bool = False) -> list[dict]:
    """
    Instantiates the agent once and runs each scenario sequentially.
    cleanup_after=True will delete any reservations created during tests.
    """
    from app.agent.base_agent import BaseAgent
    from app.agent.system_prompt import SYSTEM_PROMPT

    agent   = BaseAgent(system_prompt=SYSTEM_PROMPT)
    results = []

    print()
    _header("  MEDICAL SUPPORT AGENT — TEST RUNNER", Fore.MAGENTA)
    print(Fore.WHITE + Style.DIM + f"  Running {len(scenarios)} scenario(s)...\n")

    for scenario in scenarios:
        result = run_scenario(scenario, agent)
        results.append(result)

    # ── Optional cleanup ───────────────────────────────────
    if cleanup_after:
        _cleanup_test_reservations(results)

    # ── Summary ────────────────────────────────────────────
    print()
    _header("  SUMMARY", Fore.WHITE)

    passed = sum(1 for r in results if not r.get("error"))
    failed = len(results) - passed

    for r in results:
        ok           = not r.get("error")
        status_icon  = Fore.GREEN + "✓" if ok else Fore.RED + "✗"
        final_state  = (r.get("final_state") or {}).get("state", "unknown")
        pad_name     = r["scenario"].ljust(45)
        print(
            f"  {status_icon + Style.RESET_ALL}  "
            f"{Fore.WHITE}{pad_name}{Style.RESET_ALL}"
            f" → {Fore.CYAN}{final_state}{Style.RESET_ALL}"
        )

    print()
    print(
        Fore.WHITE + Style.BRIGHT + f"  Results: " +
        Fore.GREEN + f"{passed} passed" +
        Fore.WHITE + ", " +
        (Fore.RED if failed else Fore.WHITE) + f"{failed} failed" +
        Fore.WHITE + f" out of {len(results)} total\n" +
        Style.RESET_ALL
    )

    return results


# ─── Cleanup helper ────────────────────────────────────────

def _cleanup_test_reservations(results: list[dict]):
    """Delete all reservations that were created during test runs."""
    from app.agent.tools.reservations_store import delete_reservation

    all_ids = []
    for r in results:
        all_ids.extend(r.get("created_reservation_ids", []))

    if not all_ids:
        return

    print(Fore.MAGENTA + f"\n  Cleaning up {len(all_ids)} test reservation(s)..." + Style.RESET_ALL)
    for rid in all_ids:
        try:
            ok = delete_reservation(rid)
            icon = Fore.GREEN + "✓" if ok else Fore.RED + "✗"
            print(f"    {icon}  {rid}{Style.RESET_ALL}")
        except Exception as e:
            print(Fore.RED + f"    ✗  {rid} — {e}" + Style.RESET_ALL)
    print()
